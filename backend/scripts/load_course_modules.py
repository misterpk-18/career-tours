"""Load the extracted breakdowns into ``course_sections`` and ``course_modules``.

    python scripts/load_course_modules.py --dry-run
    python scripts/load_course_modules.py

Reads ``data/lms/modules/NT-C-*.json`` (written by ``extract_course_modules.py``)
and makes both tables match the approved knowledge corpus. No LLM calls happen
here, so it is free to re-run.

What it does, and why each part is the way it is:

* **Sections are written before modules.** ``course_modules.section_code``
  carries a foreign key into ``course_sections``, so the parent has to exist
  first — within the one transaction, that is just ordering.
* **Sections are upserted on ``section_code``, modules on
  ``(course_id, module_number)``.** The corpus names its own sections and
  numbers its own modules, so both have a stable natural key and a re-run
  updates the same 160 and 320 rows rather than appending a second set. This is
  the mistake ``03d3285`` had to go back and fix for project skills; there is no
  reason to make it twice.
* **Rows are not deleted first.** ``course_skills`` is wiped and rebuilt because
  it merges a pre-corpus hand-seeded set with the extracted one. Neither table
  here has that history — every row in both came from this script — so the
  upsert is sufficient, and not deleting means a partial run cannot quietly
  empty the other 39 courses.
* **A course code with no matching row in ``courses`` is a warning, not a
  crash.** The two loaders are independent and someone will eventually run this
  one first; saying so and carrying on is more useful than refusing to load the
  39 courses that are present.

Everything runs in one transaction and commits once at the end, which is why the
writes here are raw SQL rather than the repositories — those commit per call, so
a failure two courses in would leave the table half-corpus.
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

MODULES_DIR = BACKEND / "data" / "lms" / "modules"

MODULES_PER_COURSE = 8
SECTIONS_PER_COURSE = 4


def load_files():
    """Every extracted file, validated before the database is touched.

    Validation is up front and fatal for the same reason the commit is at the
    end: a file that is wrong is wrong before any row moves, and finding out
    halfway through is strictly worse than finding out at the start.
    """
    paths = sorted(MODULES_DIR.glob("NT-C-*.json"))

    if not paths:
        raise SystemExit(f"no extracted modules under {MODULES_DIR} — run extract_course_modules.py first")

    courses = []

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))

        if not payload.get("course_code"):
            raise SystemExit(f"{path.name}: missing course_code")

        sections = payload.get("sections") or []
        modules = payload.get("modules") or []

        if len(sections) != SECTIONS_PER_COURSE:
            raise SystemExit(
                f"{path.name}: expected {SECTIONS_PER_COURSE} sections, found {len(sections)} — re-run extract_course_modules.py"
            )

        if len(modules) != MODULES_PER_COURSE:
            raise SystemExit(
                f"{path.name}: expected {MODULES_PER_COURSE} modules, found {len(modules)} — re-run extract_course_modules.py"
            )

        for section in sections:
            missing = [f for f in ("section_code", "module_from", "module_to") if not section.get(f)]
            if missing:
                raise SystemExit(f"{path.name}: section missing required field(s) {', '.join(missing)}")

        known = {section["section_code"] for section in sections}

        for module in modules:
            missing = [f for f in ("module_number", "title") if not module.get(f)]
            if missing:
                raise SystemExit(f"{path.name}: module missing required field(s) {', '.join(missing)}")

            # The FK would catch this at INSERT time, but the message would name
            # a constraint rather than the file that needs re-extracting.
            if module.get("section_code") and module["section_code"] not in known:
                raise SystemExit(
                    f"{path.name}: module {module['module_number']} references unknown section {module['section_code']}"
                )

        courses.append(payload)

    return courses


def require_tables():
    for table, migration in (
        ("course_modules", "011_course_modules.sql"),
        ("course_sections", "012_course_sections.sql"),
    ):
        exists = db.session.execute(
            text("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = :table
            """),
            {"table": table},
        ).fetchone()

        if not exists:
            raise SystemExit(f"{table} is missing — apply migrations/{migration} first")


def course_id_for(course_code):
    row = db.session.execute(
        text("SELECT course_id FROM courses WHERE course_code = :course_code"),
        {"course_code": course_code},
    ).fetchone()

    return row[0] if row else None


def upsert_section(course_id, section):
    db.session.execute(
        text("""
            INSERT INTO course_sections
                (course_id, section_code, module_from, module_to, competency,
                 completion_evidence, weight_pct, assessment, remediation)
            VALUES
                (:course_id, :section_code, :module_from, :module_to, :competency,
                 :completion_evidence, :weight_pct, :assessment, :remediation)
            ON CONFLICT (section_code) DO UPDATE
            SET course_id = EXCLUDED.course_id,
                module_from = EXCLUDED.module_from,
                module_to = EXCLUDED.module_to,
                competency = EXCLUDED.competency,
                completion_evidence = EXCLUDED.completion_evidence,
                weight_pct = EXCLUDED.weight_pct,
                assessment = EXCLUDED.assessment,
                remediation = EXCLUDED.remediation
        """),
        {
            "course_id": course_id,
            "section_code": section["section_code"],
            "module_from": section["module_from"],
            "module_to": section["module_to"],
            "competency": section.get("competency"),
            "completion_evidence": section.get("completion_evidence"),
            "weight_pct": section.get("weight_pct"),
            "assessment": section.get("assessment"),
            "remediation": section.get("remediation"),
        },
    )


def upsert_module(course_id, module):
    db.session.execute(
        text("""
            INSERT INTO course_modules
                (course_id, module_number, title, objective, observable_evidence, topics, section_code)
            VALUES
                (:course_id, :module_number, :title, :objective, :observable_evidence,
                 CAST(:topics AS jsonb), :section_code)
            ON CONFLICT (course_id, module_number) DO UPDATE
            SET title = EXCLUDED.title,
                objective = EXCLUDED.objective,
                observable_evidence = EXCLUDED.observable_evidence,
                topics = EXCLUDED.topics,
                section_code = EXCLUDED.section_code
        """),
        {
            "course_id": course_id,
            "module_number": module["module_number"],
            "title": module["title"],
            "objective": module.get("objective"),
            "observable_evidence": module.get("observable_evidence"),
            # Serialised here rather than passed as a list: psycopg2 would adapt
            # a Python list to a Postgres array, and the column is jsonb.
            "topics": json.dumps(module.get("topics") or [], ensure_ascii=False),
            "section_code": module.get("section_code"),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do all the work, print the summary, then roll back",
    )
    args = parser.parse_args()

    courses = load_files()

    with app.app_context():
        require_tables()

        before = {
            "courses": db.session.execute(text("SELECT count(*) FROM courses")).scalar(),
            "course_sections": db.session.execute(text("SELECT count(*) FROM course_sections")).scalar(),
            "course_modules": db.session.execute(text("SELECT count(*) FROM course_modules")).scalar(),
        }

        try:
            sections_written = 0
            modules_written = 0
            missing_courses = []

            for payload in courses:
                course_id = course_id_for(payload["course_code"])

                if course_id is None:
                    missing_courses.append(payload["course_code"])
                    continue

                # Sections first: course_modules.section_code points at them.
                for section in payload["sections"]:
                    upsert_section(course_id, section)
                    sections_written += 1

                for module in payload["modules"]:
                    upsert_module(course_id, module)
                    modules_written += 1

            loaded = len(courses) - len(missing_courses)

            print(f"course_sections: {sections_written} section(s) upserted across {loaded} course(s)")
            print(f"course_modules:  {modules_written} module(s) upserted across {loaded} course(s)")

            if missing_courses:
                print(f"\nskipped {len(missing_courses)} course code(s) with no row in courses:")
                for code in missing_courses:
                    print(f"  - {code}")
                print("  run load_course_profiles.py first if this is unexpected")

            if args.dry_run:
                db.session.rollback()
                print("\n-- dry run, rolled back. Nothing was written. --")
                return 0

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        after = {
            "courses": db.session.execute(text("SELECT count(*) FROM courses")).scalar(),
            "course_sections": db.session.execute(text("SELECT count(*) FROM course_sections")).scalar(),
            "course_modules": db.session.execute(text("SELECT count(*) FROM course_modules")).scalar(),
        }

        print("\ncommitted.")
        for key in before:
            print(f"  {key:14s} {before[key]:4d} -> {after[key]:4d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
