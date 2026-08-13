"""Load ``data/imports/esco/`` into ``occupations`` and ``occupation_skills``.

    python scripts/load_careers.py --dry-run
    python scripts/load_careers.py

Reads the three validated CSVs — ``careers.csv``, ``skills.csv`` and
``career_skills.csv`` — and makes the database match them. No LLM calls, so it
is free to re-run. Run ``data/imports/esco/validate.py`` first; this script
declines to load a career_skills.csv that has careers with fewer than 5 skills.

Choices worth knowing about:

* **Occupations are upserted on ``occupation_name``**, so the 6 careers that
  already exist keep their ``occupation_id``. ``student_career_matches`` and
  ``career_skill_gaps`` point at that id, and inserting a second "React
  Developer" would strand every match already computed against the first.
* **Occupations outside the import are left completely alone.** 32 of the
  existing 38 are not in ``careers.csv``; ``occupations`` has no ``is_active``
  column to retire them with, and deleting them would cascade into
  ``student_career_matches``.
* **``occupation_skills`` is rebuilt only for the occupations being loaded.**
  Emptying the whole table would strip the skills off those 32 untouched
  occupations, which career matching still reads — leaving them present but
  unmatchable, which is worse than either keeping or deleting them.

**Everything is batched, and that is not a micro-optimisation.** Postgres is on
Neon in another region, so a statement costs a network round trip whether it
writes one row or eight thousand. A row-at-a-time version of this script spent
16 minutes with the server sitting in ``ClientRead`` — idle, waiting on us — for
work the database itself does in seconds. Resolving the catalogs in bulk and
inserting with ``executemany`` turns ~9,700 round trips into a couple of dozen.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app import app  # noqa: E402
from config.database import db  # noqa: E402
from services.skills.normalizer import SkillNormalizer  # noqa: E402
from services.skills.taxonomy import SkillTaxonomy  # noqa: E402

ESCO_DIR = BACKEND / "data" / "imports" / "esco"

# Rows per INSERT statement. Postgres caps a statement at 65535 bound
# parameters, so with 3 columns the ceiling is ~21k rows; 1000 stays well clear
# and keeps each statement small enough to be readable in pg_stat_activity.
CHUNK = 1000


def bulk_insert(table: str, columns, rows) -> None:
    """INSERT many rows using multi-row VALUES statements.

    Not ``executemany``. SQLAlchemy's ``text()`` with a list of parameter dicts
    hands off to psycopg2's ``executemany``, which loops and sends one statement
    per row — against a cross-region database that is thousands of round trips
    and minutes of ``ClientRead``. Building the VALUES clause explicitly is what
    actually makes it one statement.
    """
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start : start + CHUNK]

        values = ", ".join(
            "(" + ", ".join(f":{column}_{index}" for column in columns) + ")"
            for index in range(len(chunk))
        )

        params = {
            f"{column}_{index}": row[column]
            for index, row in enumerate(chunk)
            for column in columns
        }

        db.session.execute(
            text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES {values}"),
            params,
        )


def read_csv(path: Path):
    if not path.exists():
        raise SystemExit(f"{path} is missing — run build_career_skills.py first")

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def canonical_name(raw_name):
    """Best canonical spelling for an ESCO skill name.

    Same resolution order as ``load_course_profiles.canonical_name``: the
    repo-owned taxonomy first, then the normalizer's alias table, then the name
    as written. Sharing the order is the point — it is what lets an occupation
    and a course end up pointing at the same ``skill_id``.
    """
    return SkillTaxonomy.canonical(raw_name) or SkillNormalizer.normalize(raw_name)


def skill_catalog():
    """``{casefolded skill_name: skill_id}`` for the whole catalog."""
    rows = db.session.execute(text("SELECT skill_id, skill_name FROM skills")).fetchall()
    return {name.casefold(): skill_id for skill_id, name in rows}


def resolve_skills(wanted_names):
    """Map every needed skill name to a ``skill_id``, creating what is missing.

    Two round trips for the reads and one for the writes, regardless of how many
    skills are involved.
    """
    catalog = skill_catalog()

    missing = {}
    for name in wanted_names:
        canonical = canonical_name(name)

        if not canonical or canonical.casefold() in catalog:
            continue

        # Keyed by casefolded name so two ESCO spellings that canonicalize the
        # same way do not both try to insert.
        missing.setdefault(canonical.casefold(), canonical)

    if missing:
        bulk_insert(
            "skills",
            ("skill_name", "skill_category", "description"),
            [
                {
                    "skill_name": name,
                    "skill_category": SkillTaxonomy.category(name) or "technical",
                    "description": "Added from the ESCO career import.",
                }
                for name in missing.values()
            ],
        )

        catalog = skill_catalog()

    return catalog, sorted(missing.values(), key=str.casefold)


def resolve_occupations(careers):
    """Map every career title to an ``occupation_id``, creating what is missing."""

    def fetch():
        rows = db.session.execute(text("SELECT occupation_id, occupation_name FROM occupations")).fetchall()
        return {name.casefold(): occupation_id for occupation_id, name in rows}

    existing = fetch()

    new_rows = [
        {
            "occupation_name": c["career_title"],
            "description": (c.get("description") or "").strip() or None,
        }
        for c in careers
        if c["career_title"].casefold() not in existing
    ]

    adopted = len(careers) - len(new_rows)

    if new_rows:
        bulk_insert("occupations", ("occupation_name", "description"), new_rows)

    # Only fills a blank description: the pre-existing occupations may carry a
    # hand-written one, and ESCO's is not automatically an improvement on it.
    fills = [
        {
            "occupation_name": c["career_title"],
            "description": (c.get("description") or "").strip(),
        }
        for c in careers
        if c["career_title"].casefold() in existing and (c.get("description") or "").strip()
    ]

    if fills:
        db.session.execute(
            text("""
                UPDATE occupations
                SET description = COALESCE(description, :description)
                WHERE LOWER(occupation_name) = LOWER(:occupation_name)
            """),
            fills,
        )

    return fetch(), len(new_rows), adopted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="do the work, print the summary, then roll back")
    args = parser.parse_args()

    careers = read_csv(ESCO_DIR / "careers.csv")
    skills = read_csv(ESCO_DIR / "skills.csv")
    pairs = read_csv(ESCO_DIR / "career_skills.csv")

    skill_names = {s["skill_id"]: s["skill_name"] for s in skills}

    by_career = defaultdict(list)
    for pair in pairs:
        by_career[pair["career_title"]].append(pair)

    thin = sorted(t for t, ps in by_career.items() if len(ps) < 5)
    if thin:
        raise SystemExit(
            f"{len(thin)} career(s) have fewer than 5 skills — run validate.py and fix them first: {thin[:5]}"
        )

    loadable = [c for c in careers if by_career.get(c["career_title"])]

    with app.app_context():
        before = {
            "occupations": db.session.execute(text("SELECT count(*) FROM occupations")).scalar(),
            "skills": db.session.execute(text("SELECT count(*) FROM skills")).scalar(),
            "occupation_skills": db.session.execute(text("SELECT count(*) FROM occupation_skills")).scalar(),
        }

        try:
            catalog, created_skills = resolve_skills(skill_names.values())
            occupations, inserted, adopted = resolve_occupations(loadable)

            unresolved = set()
            rows = {}

            for career in loadable:
                occupation_id = occupations[career["career_title"].casefold()]

                for pair in by_career[career["career_title"]]:
                    name = skill_names.get(pair["skill_id"])

                    if not name:
                        unresolved.add(pair["skill_id"])
                        continue

                    canonical = canonical_name(name)
                    skill_id = catalog.get(canonical.casefold()) if canonical else None

                    if skill_id is None:
                        continue

                    weight = max(0.0, min(100.0, float(pair["weight"])))

                    # Deduplicated here rather than with ON CONFLICT: two ESCO
                    # names can canonicalize onto one catalog skill, and Postgres
                    # rejects an executemany batch that hits the same conflict
                    # target twice. Strongest weight wins.
                    key = (occupation_id, skill_id)
                    rows[key] = max(rows.get(key, 0.0), weight)

            occupation_ids = [occupations[c["career_title"].casefold()] for c in loadable]

            # Scoped to the occupations being loaded, so the ones outside the
            # import keep the skills they already have. One statement.
            db.session.execute(
                text("DELETE FROM occupation_skills WHERE occupation_id = ANY(:ids)"),
                {"ids": occupation_ids},
            )

            if rows:
                bulk_insert(
                    "occupation_skills",
                    ("occupation_id", "skill_id", "weight"),
                    [
                        {"occupation_id": occupation_id, "skill_id": skill_id, "weight": weight}
                        for (occupation_id, skill_id), weight in rows.items()
                    ],
                )

            after_links = db.session.execute(text("SELECT count(*) FROM occupation_skills")).scalar()

            print(f"occupations:  {inserted} inserted, {adopted} adopted by name")
            print(f"occupation_skills: {len(rows)} links written ({len(pairs)} CSV pairs), {after_links} rows total")
            print(f"new skills created: {len(created_skills)}")

            if unresolved:
                print(f"\n{len(unresolved)} skill_id(s) in career_skills.csv absent from skills.csv: {sorted(unresolved)[:5]}")

            if args.dry_run:
                db.session.rollback()
                print("\n-- dry run, rolled back. Nothing was written. --")
                return 0

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        after = {
            "occupations": db.session.execute(text("SELECT count(*) FROM occupations")).scalar(),
            "skills": db.session.execute(text("SELECT count(*) FROM skills")).scalar(),
            "occupation_skills": db.session.execute(text("SELECT count(*) FROM occupation_skills")).scalar(),
        }

        print("\ncommitted.")
        for key in before:
            print(f"  {key:20s} {before[key]:5d} -> {after[key]:5d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
