"""Assemble ``data/imports/esco/career_skills.csv`` from the staged parts.

    python scripts/build_career_skills.py

Pure assembly — no LLM calls, no database. Two sources, one per group of
careers:

* the 133 ESCO careers already weighted in ``_staging/weights_esco_batch_*.json``,
  whose ``relation_type`` comes from ``_staging/esco_pairs.csv`` (the weights
  files carry only a weight);
* the 106 careers authored into ``_staging/authored/`` by
  ``author_career_skills.py``, which carry both.

Then run ``python3 data/imports/esco/validate.py``, which is the real
acceptance test — this script only reports what it wrote and which careers are
still missing.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

ESCO_DIR = BACKEND / "data" / "imports" / "esco"
STAGING = ESCO_DIR / "_staging"
OUT_PATH = ESCO_DIR / "career_skills.csv"

FIELDS = ["career_title", "skill_id", "weight", "relation_type", "career_source"]


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    careers = read_csv(ESCO_DIR / "careers.csv")
    source_of = {c["career_title"]: c["source"] for c in careers}
    known_skills = {s["skill_id"] for s in read_csv(ESCO_DIR / "skills.csv")}

    # relation_type lives in esco_pairs, weight lives in the batch files; a pair
    # needs both, so a weight with no matching relation is dropped rather than
    # guessed at.
    relation = {
        (p["career_title"], p["skill_id"]): p["relation_type"]
        for p in read_csv(STAGING / "esco_pairs.csv")
    }

    rows = []
    seen = set()
    dropped_no_relation = 0

    for path in sorted(STAGING.glob("weights_esco_batch_*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            key = (entry["career_title"], entry["skill_id"])

            if key in seen:
                continue

            if key not in relation:
                dropped_no_relation += 1
                continue

            seen.add(key)
            rows.append(
                {
                    "career_title": entry["career_title"],
                    "skill_id": entry["skill_id"],
                    "weight": int(entry["weight"]),
                    "relation_type": relation[key],
                    "career_source": source_of.get(entry["career_title"], "esco"),
                }
            )

    authored_dir = STAGING / "authored"

    for path in sorted(authored_dir.glob("*.json")) if authored_dir.exists() else []:
        profile = json.loads(path.read_text(encoding="utf-8"))
        title = profile["career_title"]

        for skill in profile["skills"]:
            key = (title, skill["skill_id"])

            # The model was given a closed vocabulary, but a hallucinated id
            # would fail validate.py with a referential error that points at the
            # CSV rather than at the career that produced it. Dropping it here
            # keeps the failure legible as "too few skills" instead.
            if key in seen or skill["skill_id"] not in known_skills:
                continue

            seen.add(key)
            rows.append(
                {
                    "career_title": title,
                    "skill_id": skill["skill_id"],
                    "weight": int(skill["weight"]),
                    "relation_type": skill["relation_type"],
                    "career_source": source_of.get(title, profile.get("career_source", "market")),
                }
            )

    rows.sort(key=lambda r: (r["career_title"].casefold(), -r["weight"], r["skill_id"]))

    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    by_career = defaultdict(list)
    for row in rows:
        by_career[row["career_title"]].append(row)

    missing = sorted({c["career_title"] for c in careers} - set(by_career))
    thin = sorted(t for t, rs in by_career.items() if len(rs) < 5)

    print(f"wrote {OUT_PATH.relative_to(BACKEND)}: {len(rows)} pairs across {len(by_career)} careers")

    if dropped_no_relation:
        print(f"  dropped {dropped_no_relation} weighted pair(s) with no relation_type in esco_pairs.csv")

    if missing:
        print(f"\n{len(missing)} career(s) with NO skills:")
        for title in missing:
            print(f"  - {title}")

    if thin:
        print(f"\n{len(thin)} career(s) with fewer than 5 skills (validate.py needs >= 5):")
        for title in thin:
            print(f"  - {title} ({len(by_career[title])})")

    print("\nnow run: python3 data/imports/esco/validate.py")

    return 1 if (missing or thin) else 0


if __name__ == "__main__":
    raise SystemExit(main())
