"""Extract a storable course profile from each knowledge-corpus PDF.

    python scripts/extract_course_profiles.py [--force] [--workers 8] [--only NT-C-001,NT-C-007]

Reads ``data/lms/courses/NT-C-*.pdf`` and writes one JSON per course to
``data/lms/extracted/``. Nothing here touches the database — see
``load_course_profiles.py`` for that.

The split is the point. Each course is an independent gpt-5 call, so a run that
dies on course 31 has still banked the first 30, and a re-run skips every course
that already has a file rather than paying for it twice. It also means the raw
model output can be read, diffed and hand-corrected before it is allowed
anywhere near ``courses``.

That independence is also what makes the run parallel. The courses share
nothing — no ordering, no accumulated state, and each writes to its own file —
so the whole job is bounded by the slowest single call rather than the sum of
40, and a gpt-5 call on ten pages of corpus is around a minute. The work is
pure network wait, so threads are enough; the OpenAI client is safe to share
across them.
"""

import argparse
import csv
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from pypdf import PdfReader  # noqa: E402

from services.llm.openai_service import OpenAIService  # noqa: E402
from services.skills.taxonomy import SkillTaxonomy  # noqa: E402

PDF_DIR = BACKEND / "data" / "lms" / "courses"
OUT_DIR = BACKEND / "data" / "lms" / "extracted"

# The vocabulary the rest of the system speaks, assembled from the two places
# that already own skill names: the curated ESCO list that occupation_skills was
# built from, and the repo's own taxonomy that resume extraction snaps onto.
# Reading the CSV rather than the database keeps this script free of a DB
# dependency, and both feed through the same canonicalization in the loader, so
# they resolve to the same skill_id either way.
ESCO_SKILLS = BACKEND / "data" / "imports" / "esco" / "skills.csv"


def skill_vocabulary():
    names = set()

    if ESCO_SKILLS.exists():
        with ESCO_SKILLS.open(newline="", encoding="utf-8") as handle:
            names.update(row["skill_name"] for row in csv.DictReader(handle))

    names.update(SkillTaxonomy.names())

    return sorted(names, key=str.casefold)

CODE_RE = re.compile(r"^(NT-C-\d{3})")

# Backoff for a rate-limited call, in seconds. Concurrency is the thing that
# provokes a 429, so the retry has to exist for the parallelism to be safe:
# without it, one burst against a throttled key would fail a dozen courses at
# once and the "just re-run it" recovery would provoke the same burst again.
RETRY_DELAYS = (5, 15, 45)

# stdout is shared, and a half-written progress line interleaved with another
# thread's is worse than no line at all.
_print_lock = threading.Lock()


def report(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def is_rate_limit(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    return status == 429 or type(error).__name__ == "RateLimitError"


def course_text(pdf_path: Path) -> str:
    """Full text of a course PDF, one page per chunk.

    The repeated page header ("NIPUNA TECHNOLOGIES | ... | Page 17") is left in.
    It is a handful of tokens per page and it carries the course code, which is
    the one thing that lets the model notice it has been handed the wrong file.
    """
    reader = PdfReader(str(pdf_path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def extract_one(service, code: str, pdf: Path, vocabulary) -> str:
    """Extract and write one course. Returns "ok" or "failed"; never raises.

    A raised exception here would only be re-raised out of the future, and one
    course's bad luck is not a reason to abandon the other 39 — the whole design
    is that each file stands alone and a re-run resumes.
    """
    text = course_text(pdf)

    if not text.strip():
        report(f"  !! {code}: no extractable text (scanned PDF?), skipping")
        return "failed"

    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            profile = service.extract_course_profile(code, text, vocabulary=vocabulary)
        except Exception as error:
            if delay is not None and is_rate_limit(error):
                report(f"  .. {code}: rate limited, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue

            report(f"  !! {code}: {type(error).__name__}: {error}")
            return "failed"

        payload = {"course_code": code, "source_pdf": pdf.name, **profile.model_dump()}
        (OUT_DIR / f"{code}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        report(
            f"  ok {code}  {profile.course_name}  "
            f"({len(profile.skills)} skills, {profile.duration_hours}h, {profile.level})"
        )
        return "ok"

    return "failed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-extract courses that already have a JSON file (costs tokens again)",
    )
    parser.add_argument(
        "--only",
        help="comma-separated course codes to extract, e.g. NT-C-001,NT-C-007",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="courses extracted concurrently (default 8; lower it if the key gets rate limited)",
    )
    parser.add_argument(
        "--no-vocabulary",
        action="store_true",
        help="let the model name skills freely (produces names nothing else in the system uses)",
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    wanted = {code.strip().upper() for code in args.only.split(",")} if args.only else None

    pdfs = sorted(PDF_DIR.glob("NT-C-*.pdf"))
    if not pdfs:
        print(f"no course PDFs under {PDF_DIR}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Constructed once and shared by every worker: it builds an OpenAI client,
    # and 40 of those would be 40 connection pools for no reason. The client
    # multiplexes concurrent requests over one pool, which is the behaviour we
    # want here.
    service = OpenAIService()

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

        if (OUT_DIR / f"{code}.json").exists() and not args.force:
            skipped += 1
            continue

        pending.append((code, pdf))

    if not pending:
        print(f"nothing to do — {skipped} course(s) already extracted (use --force to redo them)")
        return 0

    vocabulary = [] if args.no_vocabulary else skill_vocabulary()

    workers = min(args.workers, len(pending))
    print(f"extracting {len(pending)} course(s) with {workers} worker(s), {skipped} already present")
    print(f"vocabulary: {len(vocabulary) or 'none — skills will be named freely'}\n")

    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(extract_one, service, code, pdf, vocabulary) for code, pdf in pending]
        results = [future.result() for future in as_completed(futures)]

    done = results.count("ok")
    failed = results.count("failed")

    print(f"\nextracted {done}, skipped {skipped} already present, failed {failed} in {time.perf_counter() - started:.0f}s")
    print(f"JSON in {OUT_DIR}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
