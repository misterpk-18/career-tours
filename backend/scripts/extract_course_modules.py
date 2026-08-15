"""Extract the module breakdown from each knowledge-corpus PDF.

    python scripts/extract_course_modules.py [--force] [--only NT-C-001,NT-C-007] [--dry-run]

Reads ``data/lms/courses/NT-C-*.pdf`` and writes one JSON per course to
``data/lms/modules/``. Nothing here touches the database — see
``load_course_modules.py`` for that.

Unlike ``extract_course_profiles.py``, this is a parser, not an LLM call.

The corpus PDFs are machine-generated from a fixed template, and the template
holds across all 40 files: ten pages, four "Deep Knowledge" sections, two
modules per section, eight modules per course. Every module is introduced by
three consecutive lines — ``Module N - <title>``, ``Objective: ...``,
``Observable evidence: ...`` — and a regex finds all 320 of them with nothing
left over. Asking a model to re-derive text that is already sitting in the file
would cost 40 full-document calls to buy the one failure mode this data cannot
absorb: a module silently renumbered, retitled or merged into its neighbour.
Determinism is the whole point, so the run is free, takes seconds, and produces
byte-identical output every time.

Two details worth knowing:

* **The objective line is the topic list.** "Syntax, data types, control flow,
  functions" is four topics, not a sentence. ``split_topics`` splits it, but the
  raw string is written out beside the array — a bad split should be a cosmetic
  problem, never data loss.
* **A course that does not yield exactly eight modules fails.** Silent
  truncation is the only realistic way a parser like this goes wrong, so the
  count is asserted rather than trusted.
"""

import argparse
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from pypdf import PdfReader  # noqa: E402

PDF_DIR = BACKEND / "data" / "lms" / "courses"
OUT_DIR = BACKEND / "data" / "lms" / "modules"

CODE_RE = re.compile(r"^(NT-C-\d{3})")

# The three-line module header. The title runs to end of line, and the dash is
# either ASCII or an en dash depending on where in the corpus it was typeset.
MODULE_RE = re.compile(
    r"Module (\d+)\s*[-–]\s*([^\n]+)\n"
    r"Objective:\s*([^\n]+)\n"
    r"Observable evidence:\s*([^\n]+)"
)

# Section ids as they appear in the page header, e.g. "NT-C-001-S01 Deep
# Knowledge". Requiring two digits after the S keeps this off the skill-ontology
# ids on page 6 (NT-C-001-SK01), which are a different record type entirely.
SECTION_RE = re.compile(r"NT-C-\d{3}-S\d{2}")

# Each course states eight modules across four sections. Hard-coded because it
# is a property of the approved template, not of any one file — if a future
# corpus version changes it, this should stop the run and be looked at.
MODULES_PER_COURSE = 8


def course_text(pdf_path: Path) -> str:
    """Full text of a course PDF, one page per chunk.

    Same reader as ``extract_course_profiles.py``. The repeated page header is
    left in on purpose here too: it is where the section id lives, and the
    section id is the only thing tying a module to the section that owns it.
    """
    reader = PdfReader(str(pdf_path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def split_topics(objective: str) -> list:
    """The objective line, split into the topics it lists.

    Commas and semicolons are unambiguous separators. " and " is not — it joins
    the last two topics ("control flow and functions") but also sits inside
    single ones ("Recursion, divide-and-conquer and backtracking", "React or
    Angular"). So it is only split after the comma pass, once per fragment and
    from the right, which leaves an internal " and " in a hyphenated term alone.
    """
    cleaned = objective.strip().rstrip(".")

    topics = []

    for fragment in re.split(r"[;,]", cleaned):
        fragment = fragment.strip()

        if not fragment:
            continue

        if " and " in fragment:
            left, right = fragment.rsplit(" and ", 1)

            if left.strip() and right.strip():
                topics.extend([left.strip(), right.strip()])
                continue

        topics.append(fragment)

    return topics


def parse_modules(text: str) -> list:
    """Every module in one course's text, in the order the corpus states them.

    Sections are matched by position rather than by splitting the document: a
    module belongs to the last section id that appeared before it. That survives
    the page header repeating and the section ids reappearing later in the file
    as assessment-sample prefixes (NT-C-001-S01-EX01), because anything after
    the final module is simply never the "last id before" anything.
    """
    section_starts = [(m.start(), m.group(0)) for m in SECTION_RE.finditer(text)]

    modules = []

    for match in MODULE_RE.finditer(text):
        section_code = None

        for position, code in section_starts:
            if position < match.start():
                section_code = code
            else:
                break

        objective = match.group(3).strip()

        modules.append({
            "module_number": int(match.group(1)),
            "title": match.group(2).strip(),
            "objective": objective,
            "observable_evidence": match.group(4).strip(),
            "topics": split_topics(objective),
            "section_code": section_code,
        })

    return modules


def extract_one(code: str, pdf: Path, write: bool) -> str:
    """Parse and write one course. Returns "ok" or "failed"; never raises."""
    text = course_text(pdf)

    if not text.strip():
        print(f"  !! {code}: no extractable text (scanned PDF?), skipping")
        return "failed"

    modules = parse_modules(text)

    numbers = [module["module_number"] for module in modules]

    if numbers != list(range(1, MODULES_PER_COURSE + 1)):
        print(f"  !! {code}: expected modules 1-{MODULES_PER_COURSE}, parsed {numbers or 'none'}")
        return "failed"

    empty = [module["module_number"] for module in modules if not module["topics"]]

    if empty:
        print(f"  !! {code}: module(s) {empty} produced no topics from their objective")
        return "failed"

    payload = {"course_code": code, "source_pdf": pdf.name, "modules": modules}

    if write:
        (OUT_DIR / f"{code}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    sections = len({module["section_code"] for module in modules if module["section_code"]})
    topics = sum(len(module["topics"]) for module in modules)

    print(f"  ok {code}  {len(modules)} modules, {sections} sections, {topics} topics")

    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-parse courses that already have a JSON file",
    )
    parser.add_argument(
        "--only",
        help="comma-separated course codes to extract, e.g. NT-C-001,NT-C-007",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse everything and print the summary without writing any file",
    )
    args = parser.parse_args()

    wanted = {code.strip().upper() for code in args.only.split(",")} if args.only else None

    pdfs = sorted(PDF_DIR.glob("NT-C-*.pdf"))
    if not pdfs:
        print(f"no course PDFs under {PDF_DIR}", file=sys.stderr)
        return 1

    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    pending = []
    skipped = 0

    for pdf in pdfs:
        match = CODE_RE.match(pdf.name)
        if not match:
            print(f"  ?? {pdf.name}: no course code in filename, skipping")
            continue

        code = match.group(1)

        if wanted and code not in wanted:
            continue

        # --dry-run re-parses everything: skipping on an existing file would make
        # it report on work it did not actually redo.
        if (OUT_DIR / f"{code}.json").exists() and not args.force and not args.dry_run:
            skipped += 1
            continue

        pending.append((code, pdf))

    if not pending:
        print(f"nothing to do — {skipped} course(s) already extracted (use --force to redo them)")
        return 0

    print(f"parsing {len(pending)} course(s), {skipped} already present\n")

    results = [extract_one(code, pdf, write=not args.dry_run) for code, pdf in pending]

    done = results.count("ok")
    failed = results.count("failed")

    print(f"\nparsed {done}, skipped {skipped} already present, failed {failed}")

    if args.dry_run:
        print("-- dry run, nothing was written. --")
    else:
        print(f"JSON in {OUT_DIR}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
