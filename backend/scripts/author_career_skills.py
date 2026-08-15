"""Fill in the careers that have no weighted skills yet.

    python scripts/author_career_skills.py [--force] [--workers 8] [--only "AI Engineer"]

``data/imports/esco/_staging/author_input_*.json`` is the gap list, prepared by
whoever built this import: the 92 market titles that ESCO has no code for, plus
14 ESCO audio-visual careers that never made it into
``weights_esco_batch_*.json``. One JSON per career lands in
``_staging/authored/``, and a career that already has a file is skipped, so a
re-run costs nothing.

The two groups are not the same job:

* **market titles** — nothing upstream exists, so the model picks skills from
  the whole curated ``skills.csv`` vocabulary and weights them.
* **the 14 ESCO careers** — ``validate.py`` rejects any ESCO pair that is not in
  the upstream ESCO relations, so their candidate list is exactly their own rows
  and the model only assigns weights.

Structured like ``extract_course_profiles.py`` for the same reason: the careers
are independent, so the run is bounded by the slowest single call rather than
the sum of 106.
"""

import argparse
import csv
import json
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services.llm.openai_service import OpenAIService  # noqa: E402

ESCO_DIR = BACKEND / "data" / "imports" / "esco"
STAGING = ESCO_DIR / "_staging"
OUT_DIR = STAGING / "authored"

RETRY_DELAYS = (5, 15, 45)

_print_lock = threading.Lock()


def report(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def is_rate_limit(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    return status == 429 or type(error).__name__ == "RateLimitError"


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_inputs():
    """The gap list, plus the two candidate sources it is served from."""
    careers = []
    for path in sorted(STAGING.glob("author_input_*.json")):
        careers.extend(json.loads(path.read_text(encoding="utf-8")))

    vocabulary = [
        f"{s['skill_id']} | {s['skill_name']} | {s['skill_category']}"
        for s in read_csv(ESCO_DIR / "skills.csv")
    ]

    # Only pairs whose skill survived vocabulary curation are usable: validate.py
    # rejects a skill_id that is not in skills.csv just as firmly as it rejects
    # an untraceable ESCO pair, so the candidate set is the intersection.
    esco_pairs = defaultdict(list)
    for pair in read_csv(STAGING / "esco_pairs.csv"):
        esco_pairs[pair["career_title"]].append(pair)

    return careers, vocabulary, esco_pairs


def author_one(service, career, vocabulary, esco_pairs) -> str:
    title = career["career_title"]
    from_esco = career.get("source") == "esco"

    if from_esco:
        pairs = esco_pairs.get(title, [])
        candidates = [f"{p['skill_id']} | {p['skill_name']} | {p['relation_type']}" for p in pairs]

        if not candidates:
            report(f"  !! {title}: no usable ESCO pairs, skipping")
            return "failed"
    else:
        candidates = vocabulary

    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            profile = service.extract_career_skills(
                career_title=title,
                candidates=candidates,
                description=career.get("description", ""),
                fixed_relations=from_esco,
            )
        except Exception as error:
            if delay is not None and is_rate_limit(error):
                report(f"  .. {title}: rate limited, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue

            report(f"  !! {title}: {type(error).__name__}: {error}")
            return "failed"

        payload = {
            "career_title": title,
            "career_source": "esco" if from_esco else "market",
            "domain": career.get("domain"),
            "skills": [s.model_dump() for s in profile.skills],
        }
        (OUT_DIR / f"{slug(title)}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        essential = sum(1 for s in profile.skills if s.relation_type == "essential")
        report(f"  ok {title}  ({len(profile.skills)} skills, {essential} essential)")
        return "ok"

    return "failed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="redo careers that already have a file")
    parser.add_argument("--only", help="comma-separated career titles to author")
    parser.add_argument("--workers", type=int, default=8, help="careers authored concurrently (default 8)")
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    careers, vocabulary, esco_pairs = load_inputs()

    if not careers:
        print(f"no author_input_*.json under {STAGING}", file=sys.stderr)
        return 1

    wanted = {t.strip() for t in args.only.split(",")} if args.only else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pending = []
    skipped = 0

    for career in careers:
        if wanted and career["career_title"] not in wanted:
            continue

        if (OUT_DIR / f"{slug(career['career_title'])}.json").exists() and not args.force:
            skipped += 1
            continue

        pending.append(career)

    if not pending:
        print(f"nothing to do — {skipped} career(s) already authored (use --force to redo them)")
        return 0

    workers = min(args.workers, len(pending))
    print(f"authoring {len(pending)} career(s) with {workers} worker(s), {skipped} already present")
    print(f"vocabulary: {len(vocabulary)} skills\n")

    started = time.perf_counter()

    # Shared by every worker: the client multiplexes concurrent requests over
    # one connection pool, so 106 of these would be pure waste.
    service = OpenAIService()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(author_one, service, career, vocabulary, esco_pairs) for career in pending]
        results = [future.result() for future in as_completed(futures)]

    done = results.count("ok")
    failed = results.count("failed")

    print(f"\nauthored {done}, skipped {skipped} already present, failed {failed} in {time.perf_counter() - started:.0f}s")
    print(f"JSON in {OUT_DIR}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
