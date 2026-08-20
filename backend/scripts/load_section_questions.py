"""Load the generated question sets into ``course_section_questions``.

    python scripts/load_section_questions.py --dry-run
    python scripts/load_section_questions.py

Reads ``data/lms/questions/NT-C-*.json`` (written by
``generate_section_questions.py``) and makes the table match the corpus. No LLM
calls happen here, so it is free to re-run.

What it does, and why:

* **Everything is validated before a single row moves.** The same ``validate``
  the generator uses, re-run here against the files on disk. The generator
  validated what the model returned; this validates what is actually being
  loaded, and those are only the same thing if nothing touched the files in
  between. Cheap to check, and a bad row is far more expensive to find once it
  is in a table people are reading from.

* **Skill names are checked against ``skills.skill_name``, not just the file.**
  This is the check that matters most. ``skills_covered`` is a text[] of names,
  so a name that does not exist in the skills table is not a foreign key error —
  it is a row that loads perfectly and then silently matches nothing forever.
  gpt-5 has already produced a whole section of skills named "Tally Prime
  (course-level coverage 90/100, technical)"; every internal check passed,
  because the corrupted names were used consistently. Only comparing against
  the real vocabulary catches that, and it has to happen here as well as at
  generation time because the two can drift.

* **Rows are upserted on (section_code, question_type, question_number).**
  The corpus numbers its own questions, so a re-run updates the same 2,560 rows
  rather than appending a second set.

* **Rows are not deleted first.** A partial run then cannot quietly empty a
  section that this run did not reach. The one exception is ``--prune``, which
  removes rows for sections present in the database but absent from the files —
  off by default, because deleting questions is not something a load should do
  as a side effect.

Everything runs in one transaction and commits once at the end, which is why the
writes are raw SQL rather than the repositories — those commit per call, so a
failure two courses in would leave the table half-corpus.
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app import app  # noqa: E402
from config.database import db  # noqa: E402

sys.path.insert(0, str(BACKEND / "scripts"))
from generate_section_questions import validate  # noqa: E402

QUESTIONS_DIR = BACKEND / "data" / "lms" / "questions"
EXTRACTED_DIR = BACKEND / "data" / "lms" / "extracted"

SECTIONS_PER_COURSE = 4
QUESTIONS_PER_SECTION = 16

# (json key, question_type, the fields that key carries)
GROUPS = (
    ("concept_mcqs", "mcq",
     ("stem", "options", "correct_option", "explanation", "distractor_rationale")),
    ("scenario_questions", "scenario",
     ("scenario", "task", "expected_answer", "rubric")),
    ("practical_tasks", "practical",
     ("title", "brief", "deliverable", "acceptance_criteria", "rubric")),
)

JSON_COLUMNS = {"options", "rubric", "acceptance_criteria"}

COLUMNS = (
    "section_code", "question_type", "question_number", "marks",
    "stem", "options", "correct_option", "explanation", "distractor_rationale",
    "scenario", "task", "expected_answer",
    "title", "brief", "deliverable", "acceptance_criteria",
    "rubric", "skills_covered", "modules_covered",
)

UPSERT = text(f"""
    INSERT INTO course_section_questions ({", ".join(COLUMNS)})
    VALUES ({", ".join(f":{c}" for c in COLUMNS)})
    ON CONFLICT (section_code, question_type, question_number) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c not in
                   ("section_code", "question_type", "question_number"))}
""")


def load_files() -> list:
    """Every generated file, validated before the database is touched.

    Validation is up front and fatal for the same reason the commit is at the
    end: a file that is wrong is wrong before any row moves, and finding out
    halfway through is strictly worse than finding out at the start.
    """
    paths = sorted(QUESTIONS_DIR.glob("NT-C-*.json"))
    if not paths:
        sys.exit(f"no question files under {QUESTIONS_DIR} — run generate_section_questions.py first")

    courses = []
    problems = []

    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        code = doc["course_code"]

        profile = EXTRACTED_DIR / f"{code}.json"
        if not profile.exists():
            problems.append(f"{code}: no extracted profile at {profile}")
            continue

        vocabulary = {s["skill_name"] for s in json.loads(profile.read_text())["skills"]}

        if len(doc["sections"]) != SECTIONS_PER_COURSE:
            problems.append(f"{code}: {len(doc['sections'])} sections, expected {SECTIONS_PER_COURSE}")

        for section in doc["sections"]:
            for problem in validate(section, section["section_code"], vocabulary):
                problems.append(f"{section['section_code']}: {problem}")

        courses.append(doc)

    if problems:
        print(f"{len(problems)} problem(s) in the files — nothing loaded:", file=sys.stderr)
        for problem in problems[:20]:
            print(f"  - {problem}", file=sys.stderr)
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more", file=sys.stderr)
        sys.exit(1)

    return courses


def rows_for(section: dict) -> list:
    """One section's sixteen questions, as parameter dicts ready for the upsert."""
    rows = []

    for key, question_type, fields in GROUPS:
        for item in section[key]:
            row = {column: None for column in COLUMNS}
            row.update(
                section_code=section["section_code"],
                question_type=question_type,
                question_number=item.get("question_number", item.get("task_number")),
                marks=item["marks"],
                skills_covered=item["skills_covered"],
                modules_covered=item["modules_covered"],
            )

            for field in fields:
                value = item[field]
                row[field] = json.dumps(value) if field in JSON_COLUMNS else value

            rows.append(row)

    return rows


def canonicalise_skills(rows: list) -> list:
    """Point every cited skill name at the real row in ``skills``. Returns strays.

    This is the check that matters most, and it cannot be a foreign key: the
    names live in a text[], so Postgres sees an array of strings and has nothing
    to point them at. A name that is wrong does not fail — it loads cleanly and
    then joins to nothing, forever.

    Case is the common failure and is worth repairing rather than refusing. The
    extracted profiles and the ``skills`` table disagree on it for a handful of
    entries ("design systems" against "Design systems"), which an exact join
    treats as two different skills and a human reading either would call one.
    Matching case-insensitively and storing the canonical spelling makes the
    join work without editing a reference table.

    A name with no match at any casing is left exactly as written and returned
    for the caller to report. Rewriting it would be inventing a mapping, and
    dropping it would quietly lose the fact that the question assesses
    something — the array is descriptive, and a skill missing from ``skills`` is
    a gap in that table rather than a corrupt question.
    """
    canonical = {
        name.lower(): name
        for name in db.session.execute(text("SELECT skill_name FROM skills")).scalars()
    }

    cited, repaired, strays = set(), set(), set()

    for row in rows:
        rewritten = []
        for name in row["skills_covered"]:
            cited.add(name)
            match = canonical.get(name.lower())
            if match is None:
                strays.add(name)
                rewritten.append(name)
            else:
                if match != name:
                    repaired.add((name, match))
                rewritten.append(match)
        row["skills_covered"] = rewritten

    print(f"  {len(cited)} distinct skill names cited; "
          f"{len(repaired)} repaired to the spelling in skills, {len(strays)} unmatched")
    for was, now in sorted(repaired):
        print(f"    {was!r} -> {now!r}")

    return sorted(strays)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate everything and report the counts, without writing")
    parser.add_argument("--prune", action="store_true",
                        help="also delete rows for sections that no longer have a file")
    args = parser.parse_args()

    courses = load_files()
    sections = sum(len(c["sections"]) for c in courses)
    rows = [row for course in courses for section in course["sections"] for row in rows_for(section)]

    print(f"{len(courses)} course(s), {sections} section(s), {len(rows)} question(s) validated")

    with app.app_context():
        known_sections = set(
            db.session.execute(text("SELECT section_code FROM course_sections")).scalars()
        )
        wanted = {row["section_code"] for row in rows}

        if orphans := sorted(wanted - known_sections):
            print(f"{len(orphans)} section(s) have no row in course_sections — "
                  f"run load_course_modules.py first: {', '.join(orphans[:5])}", file=sys.stderr)
            return 1

        strays = canonicalise_skills(rows)
        if strays:
            print(f"  !! {len(strays)} name(s) match nothing in skills and will join to nothing:")
            for name in strays:
                print(f"       {name!r}")
            print("     loaded as written — add them to skills, or correct the course profile")

        before = db.session.execute(
            text("SELECT count(*) FROM course_section_questions")
        ).scalar()

        if args.dry_run:
            stale = len(known_sections - wanted)
            print(f"\ndry run — would upsert {len(rows)} row(s); table currently holds {before}")
            if stale:
                print(f"  {stale} section(s) in the database have no file"
                      + (" and would be pruned" if args.prune else " (left alone; --prune removes them)"))
            return 0

        db.session.execute(UPSERT, rows)

        pruned = 0
        if args.prune and (stale := sorted(known_sections - wanted)):
            pruned = db.session.execute(
                text("DELETE FROM course_section_questions WHERE section_code = ANY(:codes)"),
                {"codes": stale},
            ).rowcount

        db.session.commit()

        after = db.session.execute(
            text("SELECT count(*) FROM course_section_questions")
        ).scalar()

        print(f"\nupserted {len(rows)} row(s){f', pruned {pruned}' if pruned else ''}")
        print(f"course_section_questions: {before} -> {after}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
