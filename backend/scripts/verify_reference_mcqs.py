"""Check the collected Tier A reference MCQs against the rules they were given.

    python scripts/verify_reference_mcqs.py

Reads ``data/lms/reference_mcqs/NT-C-*.json`` and re-checks every claim a
collector could get wrong, because a collector reporting its own work is not
evidence. The skill-name check is the one that matters most: gpt-5 once produced
a whole section of skills named "Tally Prime (course-level coverage 90/100,
technical)" and every internal consistency check passed, because the corrupted
names were used consistently. Only comparing against the course's real skill list
catches that class of error.
"""

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BACKEND / "data" / "lms" / "reference_mcqs"
EXTRACTED_DIR = BACKEND / "data" / "lms" / "extracted"

LABELS = ("A", "B", "C", "D")

REQUIRED = {
    "question_number", "stem", "options", "correct_option", "explanation",
    "distractor_rationale", "skills_covered", "difficulty",
    "source_name", "source_url", "provenance",
}

# The forms the brief bans outright — asking a candidate to define a term.
#
# Distinguishing these from legitimate diagnostic stems is the whole difficulty.
# "What is the most likely cause?" and "What is the value of `x`?" share an
# opening with "What is a permission boundary?" but are the opposite kind of
# question. Two guards, because either alone produced false positives on real
# questions: the head noun must not be one of the diagnostic ones, and the stem
# must be short. A genuine glossary item is a single sentence; every false
# positive caught so far was a 200+ character scenario that merely ENDED with a
# diagnostic question.
DIAGNOSTIC_HEADS = (
    "cause", "outcome", "result", "effect", "impact", "consequence", "value",
    "output", "state", "status", "behaviour", "behavior", "minimum", "maximum",
    "best", "next", "most", "least", "correct order", "net effect", "final",
    "resulting", "difference in", "total", "number of", "expected",
)

GLOSSARY = re.compile(
    r"(^|[.?]\s+)\s*(what is (a|an|the)?\s*[a-z]"
    r"|which of the following best describes"
    r"|what is the purpose of|what is the primary difference|which is a benefit of)",
    re.IGNORECASE,
)

# Above this length a stem carries a scenario, and the trailing question is a
# diagnostic rather than a request for a definition.
SCENARIO_CHARS = 160


def is_glossary_form(stem: str) -> bool:
    match = GLOSSARY.search(stem)
    if not match:
        return False

    if len(stem.strip()) >= SCENARIO_CHARS:
        return False

    # end() - 1 because the pattern consumes the first letter of the head noun,
    # which would otherwise leave "utcome?" and never match "outcome".
    tail = stem[match.end() - 1:].lstrip().lower()
    return not tail.startswith(DIAGNOSTIC_HEADS)


def check(path: Path) -> list:
    problems = []
    code = path.stem

    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return [f"does not parse: {error}"]

    extracted = EXTRACTED_DIR / f"{code}.json"
    if not extracted.exists():
        return [f"no extracted profile at {extracted}"]

    vocabulary = {s["skill_name"] for s in json.loads(extracted.read_text())["skills"]}

    questions = doc.get("questions", [])
    if len(questions) != 10:
        problems.append(f"{len(questions)} questions, expected 10")

    if not doc.get("sources"):
        problems.append("no sources block")

    seen_numbers = set()

    for q in questions:
        number = q.get("question_number", "?")

        if missing := REQUIRED - set(q):
            problems.append(f"Q{number}: missing fields {sorted(missing)}")
            continue

        if number in seen_numbers:
            problems.append(f"Q{number}: duplicate question_number")
        seen_numbers.add(number)

        if len(q["options"]) != 4:
            problems.append(f"Q{number}: {len(q['options'])} options, expected 4")

        if q["correct_option"] not in LABELS:
            problems.append(f"Q{number}: correct_option {q['correct_option']!r} is not A-D")

        if stray := sorted(set(q["skills_covered"]) - vocabulary):
            problems.append(f"Q{number}: skills not in the course list: {'; '.join(stray[:2])}")

        if not q["skills_covered"]:
            problems.append(f"Q{number}: no skills_covered")

        if q["provenance"] not in ("verbatim", "adapted"):
            problems.append(f"Q{number}: provenance {q['provenance']!r}")

        if not str(q["source_url"]).startswith("http"):
            problems.append(f"Q{number}: source_url is not a URL: {q['source_url']!r}")

        if is_glossary_form(q["stem"]):
            problems.append(f"Q{number}: banned glossary form in stem")

        # An option that merely restates the stem's subject is filler, not a
        # distractor. Cheap proxy: any option under 3 characters.
        if short := [o for o in q["options"] if len(o.strip()) < 3]:
            problems.append(f"Q{number}: {len(short)} option(s) too short to be real distractors")

    return problems


def main() -> int:
    files = sorted(REFERENCE_DIR.glob("NT-C-*.json"))
    if not files:
        print(f"nothing collected yet in {REFERENCE_DIR}")
        return 0

    failed = 0

    for path in files:
        problems = check(path)
        doc = json.loads(path.read_text()) if path.stat().st_size else {}
        questions = doc.get("questions", [])

        adapted = sum(1 for q in questions if q.get("provenance") == "adapted")
        sources = len({q.get("source_url") for q in questions})

        if problems:
            failed += 1
            print(f"{path.stem}: {len(problems)} PROBLEM(S)")
            for problem in problems:
                print(f"   - {problem}")
        else:
            print(
                f"{path.stem}: CLEAN  {len(questions)} questions, "
                f"{adapted} adapted, {sources} distinct sources"
            )

    print(f"\n{len(files) - failed}/{len(files)} collected file(s) clean")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
