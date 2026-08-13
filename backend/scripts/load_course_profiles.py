"""Load the extracted course profiles into ``courses`` and ``course_skills``.

    python scripts/load_course_profiles.py --dry-run
    python scripts/load_course_profiles.py

Reads ``data/lms/extracted/NT-C-*.json`` (written by
``extract_course_profiles.py``) and makes the database match the approved
knowledge corpus. No LLM calls happen here, so it is free to re-run.

What it does, and why each part is the way it is:

* **Courses are upserted on ``course_code``**, and a corpus course whose name
  already exists adopts that existing row rather than inserting beside it. The
  row keeps its ``course_id``, which matters because ``course_recommendations``
  points at it — inserting a second "Java Full Stack" would strand every
  recommendation already generated against the first one.
* **Courses outside the corpus are deactivated, not deleted.** ``is_active``
  already gates ``CourseRepository.get_all`` and the matching engine, so
  flipping it is enough to take them out of circulation, and a DELETE would
  cascade into ``course_recommendations`` and destroy history.
* **``course_skills`` is emptied and rebuilt in full.** The corpus is the
  source of truth for what a course teaches, and the pre-corpus rows were seeded
  by hand against a different set of courses; merging the two would leave skills
  attached to courses that no longer claim to teach them.

Everything runs in one transaction and commits once at the end, which is why
the writes here are raw SQL rather than the repositories — those commit per
call, so a failure two courses in would leave the tables half-corpus.
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
from services.skills.normalizer import SkillNormalizer  # noqa: E402
from services.skills.taxonomy import SkillTaxonomy  # noqa: E402

EXTRACTED_DIR = BACKEND / "data" / "lms" / "extracted"


def canonical_name(raw_name):
    """Best canonical spelling for an extracted skill name.

    The taxonomy is asked first — it is the repo-owned vocabulary and knows that
    ``AWS S3`` and ``Amazon S3`` are one skill. ``SkillNormalizer`` is the
    fallback for its small alias table, and a name neither knows is kept as the
    model wrote it.
    """
    return SkillTaxonomy.canonical(raw_name) or SkillNormalizer.normalize(raw_name)


def load_profiles():
    paths = sorted(EXTRACTED_DIR.glob("NT-C-*.json"))

    if not paths:
        raise SystemExit(f"no extracted profiles under {EXTRACTED_DIR} — run extract_course_profiles.py first")

    profiles = []

    for path in paths:
        profile = json.loads(path.read_text(encoding="utf-8"))

        missing = [f for f in ("course_code", "course_name", "skills") if not profile.get(f)]
        if missing:
            raise SystemExit(f"{path.name}: missing required field(s) {', '.join(missing)}")

        profiles.append(profile)

    return profiles


def require_course_code_column():
    exists = db.session.execute(
        text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'courses'
              AND column_name = 'course_code'
        """)
    ).fetchone()

    if not exists:
        raise SystemExit("courses.course_code is missing — apply migrations/009_courses_course_code.sql first")


def upsert_course(profile):
    """Return (course_id, action) for one profile, without committing."""
    params = {
        "course_code": profile["course_code"],
        "course_name": profile["course_name"],
        "description": profile.get("description"),
        "duration_hours": profile.get("duration_hours") or None,
        "level": profile.get("level"),
    }

    # By code first: this is the re-run path, and it is the only match that
    # survives the corpus re-wording a course title.
    row = db.session.execute(
        text("SELECT course_id FROM courses WHERE course_code = :course_code"),
        {"course_code": params["course_code"]},
    ).fetchone()

    action = "updated"

    if row is None:
        # Then by name, case-insensitively, to adopt a pre-corpus row instead of
        # duplicating it. Restricted to rows with no code of their own so two
        # corpus courses can never fight over the same row.
        row = db.session.execute(
            text("""
                SELECT course_id
                FROM courses
                WHERE LOWER(course_name) = LOWER(:course_name)
                  AND course_code IS NULL
                ORDER BY created_at
                LIMIT 1
            """),
            {"course_name": params["course_name"]},
        ).fetchone()

        action = "adopted" if row is not None else "inserted"

    if row is None:
        inserted = db.session.execute(
            text("""
                INSERT INTO courses (course_code, course_name, description, duration_hours, level, is_active)
                VALUES (:course_code, :course_name, :description, :duration_hours, :level, TRUE)
                RETURNING course_id
            """),
            params,
        ).fetchone()

        return inserted[0], action

    db.session.execute(
        text("""
            UPDATE courses
            SET course_code = :course_code,
                course_name = :course_name,
                description = :description,
                duration_hours = :duration_hours,
                level = :level,
                is_active = TRUE
            WHERE course_id = :course_id
        """),
        {**params, "course_id": row[0]},
    )

    return row[0], action


def resolve_skill(raw_name, category, created):
    """Return the ``skill_id`` for an extracted skill name, creating it if new.

    ``created`` collects the names this run had to invent, purely so the run can
    report them — a corpus course naming a skill the catalog has never heard of
    is worth a human glance.
    """
    name = canonical_name(raw_name)

    if not name:
        return None

    row = db.session.execute(
        text("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(:skill_name)"),
        {"skill_name": name},
    ).fetchone()

    if row is not None:
        return row[0]

    # A canonical taxonomy name carries its own category; the model's guess is
    # only used for names the taxonomy does not know.
    skill_category = SkillTaxonomy.category(name) or category

    inserted = db.session.execute(
        text("""
            INSERT INTO skills (skill_name, skill_category, description)
            VALUES (:skill_name, :skill_category, :description)
            RETURNING skill_id
        """),
        {
            "skill_name": name,
            "skill_category": skill_category,
            "description": "Added from the Nipuna CareerTours approved knowledge corpus v3.0.",
        },
    ).fetchone()

    created.append(name)

    return inserted[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do all the work, print the summary, then roll back",
    )
    args = parser.parse_args()

    profiles = load_profiles()

    with app.app_context():
        require_course_code_column()

        before = {
            "courses": db.session.execute(text("SELECT count(*) FROM courses")).scalar(),
            "active": db.session.execute(text("SELECT count(*) FROM courses WHERE is_active")).scalar(),
            "skills": db.session.execute(text("SELECT count(*) FROM skills")).scalar(),
            "course_skills": db.session.execute(text("SELECT count(*) FROM course_skills")).scalar(),
        }

        try:
            # Wiped up front, before any course row moves, so the rebuild below
            # is the only thing that can put rows back.
            db.session.execute(text("DELETE FROM course_skills"))

            created_skills = []
            actions = {"inserted": 0, "adopted": 0, "updated": 0}
            course_ids = []
            skill_links = 0

            for profile in profiles:
                course_id, action = upsert_course(profile)
                actions[action] += 1
                course_ids.append(course_id)

                for skill in profile["skills"]:
                    skill_id = resolve_skill(skill["skill_name"], skill.get("category"), created_skills)

                    if skill_id is None:
                        continue

                    weight = max(0.0, min(100.0, float(skill.get("coverage_weight") or 0)))

                    # Two extracted names can canonicalize onto one skill (say
                    # "Amazon S3" and "AWS S3" in the same course), so the
                    # conflict is expected rather than exceptional. The stronger
                    # weight wins — a skill named twice is not covered less.
                    db.session.execute(
                        text("""
                            INSERT INTO course_skills (course_id, skill_id, coverage_weight)
                            VALUES (:course_id, :skill_id, :coverage_weight)
                            ON CONFLICT (course_id, skill_id) DO UPDATE
                            SET coverage_weight = GREATEST(course_skills.coverage_weight, EXCLUDED.coverage_weight)
                        """),
                        {"course_id": course_id, "skill_id": skill_id, "coverage_weight": weight},
                    )

                    skill_links += 1

            deactivated = db.session.execute(
                text("""
                    UPDATE courses
                    SET is_active = FALSE
                    WHERE course_code IS NULL
                      AND is_active
                    RETURNING course_name
                """)
            ).fetchall()

            after_links = db.session.execute(text("SELECT count(*) FROM course_skills")).scalar()

            print(f"courses:  {actions['inserted']} inserted, {actions['adopted']} adopted by name, {actions['updated']} updated")
            print(f"deactivated {len(deactivated)} non-corpus course(s):")
            for row in deactivated:
                print(f"  - {row[0]}")

            print(f"\ncourse_skills: {before['course_skills']} deleted, {after_links} written ({skill_links} links before dedup)")

            print(f"\nnew skills created: {len(created_skills)}")
            for name in sorted(created_skills, key=str.casefold):
                print(f"  + {name}")

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
            "active": db.session.execute(text("SELECT count(*) FROM courses WHERE is_active")).scalar(),
            "skills": db.session.execute(text("SELECT count(*) FROM skills")).scalar(),
            "course_skills": db.session.execute(text("SELECT count(*) FROM course_skills")).scalar(),
        }

        print("\ncommitted.")
        for key in before:
            print(f"  {key:14s} {before[key]:4d} -> {after[key]:4d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
