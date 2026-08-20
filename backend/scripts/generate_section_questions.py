"""Write the end-of-section question set for every course section.

    python scripts/generate_section_questions.py [--force] [--only NT-C-001] [--dry-run]

Reads ``data/lms/modules/NT-C-*.json`` for the section and module breakdown and
``data/lms/extracted/NT-C-*.json`` for the course's skills, and writes one JSON
per course to ``data/lms/questions/``. Nothing here touches the database.

One gpt-5 call per section, four sections per course, 160 calls for the corpus.
Unlike ``extract_course_modules.py`` this is not a parser — the questions do not
exist anywhere in the source PDFs. What the corpus does give is the shape: every
section already declares ``assessment`` as "10 concept MCQ (30 marks) + 4
code/design scenarios (30) + 2 practical tasks (40)", and this script is that
promise made concrete.

Two things the model cannot be trusted to do, both handled here rather than in
the prompt:

* **The answer key.** Left to itself, gpt-5 put the correct option at B for nine
  of ten MCQs in the first section generated — a student who always answers B
  scores 27/30. Asking for a spread in the prompt invites the same bias back in
  a new shape, so ``balance_answer_key`` deals the correct positions from a
  balanced pool after the fact. Guaranteed rather than hoped for, and stable
  across re-runs of the same section.
* **The arithmetic.** ``validate`` re-checks the counts, the 30/30/40 marks
  split, each rubric summing to its question's marks, and that no question cites
  a skill outside ``skills_assessed``. A section that fails is regenerated, not
  written. These are cheap to check and expensive to find later — a rubric that
  sums to 9 out of 8 marks is invisible until an assessor is halfway through
  marking with it.
"""

import argparse
import hashlib
import json
import re
import sys
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services.llm.gemma_service import GemmaService  # noqa: E402
from services.llm.openai_service import OpenAIService  # noqa: E402

MODULES_DIR = BACKEND / "data" / "lms" / "modules"
EXTRACTED_DIR = BACKEND / "data" / "lms" / "extracted"
# One output directory per backend. The two models are being compared, and a
# comparison needs both sets to survive — writing them to the same place means
# whichever ran last is the only one left, which is how the first gpt-5 pilot
# nearly got overwritten by a Gemma re-run.
OUT_DIRS = {
    "gpt-5": BACKEND / "data" / "lms" / "questions",
    "gemma": BACKEND / "data" / "lms" / "questions_gemma",
}

LABELS = ("A", "B", "C", "D")

# Languages the interface can syntax-highlight. "text" is the escape hatch for
# artefacts with no language — ledger extracts, trial balances, report output —
# and is deliberately included so a Tally question has somewhere legal to put a
# stock summary.
FENCE_LANGUAGES = {
    # programming
    "python", "javascript", "jsx", "typescript", "tsx", "java", "csharp",
    "cpp", "c", "go", "rust", "ruby", "php", "kotlin", "swift", "scala",
    "perl", "r", "matlab", "vbnet", "abap", "groovy", "dart", "lua",
    # data and query. dax/mdx/powerquery earned their place on the first batch:
    # Power BI alone normalised 88 DAX blocks down to "text", which is the one
    # course where the artefact language IS the subject being assessed.
    "sql", "graphql", "json", "yaml", "xml", "csv", "toml", "ini",
    "dax", "mdx", "powerquery", "vba",
    # markup and style
    "html", "css", "scss", "markdown", "latex",
    # shell, infra and config
    "bash", "powershell", "dockerfile", "nginx", "apache", "terraform",
    "makefile", "properties", "http", "diff", "regex",
    # the escape hatch, and the reason it exists: ledger extracts, trial
    # balances, report output and directory trees have no language, and a
    # Tally question still needs somewhere legal to put a stock summary.
    "text",
}

# What the model reaches for versus what we call it. gpt-5 wrote ```docker for a
# Dockerfile and ```nginx for a server block on the very first probe course, and
# both were the right instinct — the whitelist was what was wrong. Mapping is
# strictly better than rejecting: an unknown tag costs a whole regeneration
# (~150s and 15k tokens) for something cosmetic, and under all-or-nothing the
# third failure throws away three good sections with it.
FENCE_ALIASES = {
    "js": "javascript", "node": "javascript", "ts": "typescript",
    "py": "python", "py3": "python", "golang": "go", "rb": "ruby",
    "sh": "bash", "shell": "bash", "zsh": "bash", "console": "bash",
    "terminal": "bash", "cmd": "bash", "ps1": "powershell", "pwsh": "powershell",
    "yml": "yaml", "jsonc": "json", "htm": "html", "md": "markdown",
    "docker": "dockerfile", "compose": "yaml", "k8s": "yaml", "helm": "yaml",
    "tf": "terraform", "hcl": "terraform", "conf": "nginx", "config": "ini",
    "cs": "csharp", "c#": "csharp", "c++": "cpp", "cxx": "cpp",
    "postgres": "sql", "postgresql": "sql", "mysql": "sql", "tsql": "sql",
    "plsql": "sql", "sqlite": "sql", "oracle": "sql",
    "m": "powerquery", "powerquery-m": "powerquery", "pq": "powerquery",
    "vb": "vba", "vbs": "vba", "excel": "text", "formula": "text",
    "plaintext": "text", "plain": "text", "txt": "text", "none": "text",
    "output": "text", "log": "text", "tree": "text", "ascii": "text",
}

FENCE = re.compile(r"```([A-Za-z0-9+#-]*)")

# A line that can only be the start of a real code/artefact block. Used to catch
# code that was pasted into a field with NO fence around it, which is what both
# gpt-5 and Gemma 4 did on their first attempts: the JSON looks fine, the
# validator was happy, and the page renders a Python function as one run-together
# paragraph with its indentation collapsed. Deliberately narrow — it must not
# fire on prose that merely mentions `git merge` or a column name.
CODE_LINE = re.compile(
    r"^[ \t]*("
    r"(def|class|import|from|return|yield|elif|else:|try:|except|finally:|with|while|for|assert|raise)\b"
    r"|(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|FROM|WHERE|GROUP BY|JOIN)\b"
    r"|(const|let|var|function|export|async)\b"
    r"|(public|private|static|void)\b"
    r"|[a-zA-Z_$][\w$]*\s*=\s*[^=]"
    r"|[<>{}]"
    r")",
    re.MULTILINE,
)

# Characters no question should contain. NUL is the one that matters: Postgres
# text cannot hold 0x00 at all, so a single one aborts the entire 2,560-row load
# with a driver-level ValueError that names no field. gpt-5 produced three, all
# in questions ABOUT invisible characters — it corrupted its own \u00A0 escapes
# into \x00A while writing a Power BI text-normalisation stem and an Excel
# duplicate-detection brief. Real non-breaking spaces sat correctly elsewhere in
# the same fields, so this is a mangled escape rather than a misunderstanding,
# and it is caught here rather than repaired: guessing which character was meant
# is inventing content, and regenerating the section costs ninety seconds.
#
# \n and \t are legitimate — fenced blocks depend on both.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# Markdown that does not belong in a question card. Bullet and numbered lists
# are deliberately NOT here: a model answer or a task brief is often genuinely a
# list of points, and banning them made gpt-5 fail four expected_answer fields
# three times running rather than write worse prose. Headings imply a document
# structure a question does not have, and pipe tables are the wrong tool for the
# tabular data in this corpus — ledger extracts and stock summaries need their
# column alignment preserved, which is what a ```text fence is for.
STRAY_MARKDOWN = re.compile(r"^\s*(#{1,6}\s|\|)", re.MULTILINE)

MCQ_MARKS = 30
SCENARIO_MARKS = 30
PRACTICAL_MARKS = 40

# Same backoff as the other LLM scripts: concurrency is what provokes a 429, so
# the retry is what makes the parallelism safe rather than a way to double down.
RETRY_DELAYS = (5, 15, 45)

# One bad generation is worth re-asking for; three means the prompt is wrong and
# spending more tokens will not fix it.
VALIDATION_ATTEMPTS = 3

# The langsmith wrapper round-trips every response through a union of every
# Responses API item type, and pydantic warns once per type that our
# SectionAssessment is not a LocalShellCallAction. Fifteen lines of noise per
# call, which on a 160-section run buries the errors that matter — the first
# probe run lost the reason a section failed to exactly this.
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

_print_lock = threading.Lock()


def report(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def is_rate_limit(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    return status == 429 or type(error).__name__ == "RateLimitError"


# Set the moment the account runs out of credit. Everything still queued then
# returns immediately instead of making its own doomed call: with 160 sections in
# flight, a spend limit reached at section 30 would otherwise produce 130 more
# failures, each after its own retry backoff, and bury the one error that matters.
_out_of_credit = threading.Event()

# Billing failures, not rate limits. A 402 means the balance is gone and waiting
# 45 seconds changes nothing, so these must never enter the retry path.
BILLING_MARKERS = ("insufficient_quota", "exceeded your current quota", "payment required",
                   "insufficient credits", "spend limit", "credits have run out")


def is_billing_failure(error: Exception) -> bool:
    if getattr(error, "status_code", None) == 402:
        return True
    text = str(error).lower()
    return any(marker in text for marker in BILLING_MARKERS)


def seeded_order(seed: str, count: int) -> list:
    """A deterministic permutation of ``range(count)``, by Fisher-Yates.

    Driven by a SHA-256 digest rather than ``random`` because the ordering has
    to be reproducible across processes and across runs: these questions get
    reviewed by people, and a re-run that reshuffles every answer produces a
    diff nobody can read.
    """
    digest = hashlib.sha256(seed.encode()).digest()

    order = list(range(count))
    for i in range(count - 1, 0, -1):
        j = digest[i % len(digest)] % (i + 1)
        order[i], order[j] = order[j], order[i]

    return order


def balance_answer_key(mcqs: list, section_code: str) -> list:
    """Reposition every correct answer so the section's key is evenly spread.

    Left to itself gpt-5 put the correct option at B for nine of ten MCQs in the
    first section generated, and for seven of ten in another — a student who
    always answers B scores 21-27 of 30 without reading a question.

    Shuffling each question independently fixes this only on average. Measured
    over all 160 sections an independent shuffle does land uniformly, but it
    still deals individual sections a 7-of-10 run, and a section is what a
    learner actually sits. So the positions are dealt from a balanced pool
    instead: ten questions draw from A/B/C/D cycled, giving 3/3/2/2, and only
    the assignment of those slots to questions is seeded. No letter can appear
    more than three times in a section, by construction rather than by luck.

    The distractors are then permuted within the remaining slots so the wrong
    options do not keep their original relative order either.
    """
    targets = [LABELS[i % len(LABELS)] for i in range(len(mcqs))]
    targets = [targets[i] for i in seeded_order(f"{section_code}:key", len(targets))]

    balanced = []

    for mcq, target in zip(mcqs, targets):
        options = list(mcq["options"])
        correct = options.pop(LABELS.index(mcq["correct_option"]))

        order = seeded_order(f"{section_code}:{mcq['question_number']}", len(options))
        distractors = iter(options[i] for i in order)

        slot = LABELS.index(target)
        rebuilt = [correct if i == slot else next(distractors) for i in range(len(mcq["options"]))]

        balanced.append({**mcq, "options": rebuilt, "correct_option": target})

    return balanced


def text_slots(assessment: dict):
    """Every human-facing string, as (where, container, key) so it can be rewritten.

    The interface renders all of these, so all of them have to obey the same
    formatting contract — an unclosed fence in a distractor rationale breaks the
    page just as thoroughly as one in a stem. Rubric criteria are in here too:
    they render alongside the question, and the earlier version of this walk
    skipped them because ``rubric`` is a list of dicts rather than of strings.
    """
    for group in ("concept_mcqs", "scenario_questions", "practical_tasks"):
        for item in assessment[group]:
            number = item.get("question_number", item.get("task_number"))
            where = f"{group} {number}"

            # list() because callers rewrite the values as they go, and a bare
            # items() view is a fragile thing to be mutating through.
            for field, value in list(item.items()):
                if isinstance(value, str):
                    yield f"{where}.{field}", item, field
                elif field in ("options", "acceptance_criteria"):
                    for i in range(len(value)):
                        yield f"{where}.{field}[{i}]", value, i
                elif field == "rubric":
                    for i, criterion in enumerate(value):
                        yield f"{where}.rubric[{i}]", criterion, "criterion"


def text_fields(assessment: dict):
    """Every human-facing string in a section, as (where, text) pairs."""
    for where, container, key in text_slots(assessment):
        yield where, container[key]


def normalize_fences(assessment: dict) -> list:
    """Canonicalise every fence language tag in place. Returns what it changed.

    Run before validation, so the model gets judged on whether it fenced its
    artefacts at all rather than on whether it guessed our vocabulary for them.
    An unrecognised tag degrades to ``text``: highlighting is lost, the content
    and its indentation are not, and that is a far better outcome than throwing
    away an otherwise good section over the word "docker".

    Unclosed fences are deliberately left alone for ``check_formatting`` to
    fail on — those genuinely break the page, and guessing where the author
    meant to close the block would be inventing content.
    """
    notes = []

    for where, container, key in text_slots(assessment):
        value = container[key]
        if "```" not in value:
            continue

        parts = value.split("```")
        if len(parts) % 2 == 0:
            continue

        # Odd indices are the fenced blocks; each opens with its language tag.
        for i in range(1, len(parts), 2):
            tag, newline, body = parts[i].partition("\n")

            # No newline means something like ```x``` inline — malformed, and
            # not worth guessing at. check_formatting will have its say.
            if not newline:
                continue

            original = tag.strip()
            canonical = FENCE_ALIASES.get(original.lower(), original.lower())
            if canonical not in FENCE_LANGUAGES:
                canonical = "text"

            if canonical != original:
                notes.append(f"{where}: fence '{original or 'untagged'}' -> '{canonical}'")
                parts[i] = canonical + newline + body

        container[key] = "```".join(parts)

    return notes


def check_formatting(assessment: dict) -> list:
    """Fenced blocks are closed, tagged, and the only markdown present.

    Worth failing a section over. These strings go straight into the page, so an
    unclosed ``` swallows the rest of the question into a code block, and an
    untagged one renders as grey soup with no highlighting. Both are invisible
    in the JSON and obvious to the first learner who sees them.
    """
    problems = []

    for where, value in text_fields(assessment):
        if found := CONTROL_CHARS.findall(value):
            problems.append(
                f"{where}: control character {', '.join(sorted({hex(ord(c)) for c in found}))} in the text"
            )

        tags = FENCE.findall(value)

        if len(tags) % 2:
            problems.append(f"{where}: unclosed code fence")
            continue

        # Fences alternate open/close; only the opening ones carry a language.
        for tag in tags[::2]:
            if not tag:
                problems.append(f"{where}: code fence with no language tag")
            elif tag.lower() not in FENCE_LANGUAGES:
                problems.append(f"{where}: unsupported fence language '{tag}'")

        # Only look for stray markdown outside the fenced blocks — a "# comment"
        # in Python or a "- item" in YAML is legitimate inside one.
        outside = "".join(value.split("```")[::2])
        if STRAY_MARKDOWN.search(outside):
            problems.append(f"{where}: markdown outside a code fence")

        # Unfenced code. Two or more code-looking lines outside any fence is a
        # block that should have been fenced — one line alone is too often a
        # legitimate inline mention, so it is not worth the false positives.
        if len(CODE_LINE.findall(outside)) >= 2 and "\n" in outside.strip():
            problems.append(f"{where}: code outside a fenced block")

    return problems


def validate(assessment: dict, section_code: str, vocabulary: set | None = None) -> list:
    """Everything the prompt asks for that is cheap to check. Returns problems.

    ``vocabulary`` is the course's real skill names. Checking against it is not
    optional pedantry: gpt-5 generated one section whose skills_assessed read
    "Tally Prime (course-level coverage 90/100, technical)" — it had copied the
    annotation the prompt puts beside each name. Every internal-consistency
    check still passed, because the corrupted names were used consistently
    throughout that section. Nothing would have surfaced it until the loader
    tried to join those strings to ``course_skills`` and matched nothing, which
    is the precise failure the skill map exists to prevent.
    """
    problems = []

    if assessment["section_code"] != section_code:
        problems.append(f"section_code is {assessment['section_code']}, expected {section_code}")

    groups = (
        ("concept_mcqs", 10, MCQ_MARKS),
        ("scenario_questions", 4, SCENARIO_MARKS),
        ("practical_tasks", 2, PRACTICAL_MARKS),
    )

    for key, count, total in groups:
        items = assessment[key]
        if len(items) != count:
            problems.append(f"{key}: {len(items)} items, expected {count}")

        marks = sum(item["marks"] for item in items)
        if marks != total:
            problems.append(f"{key}: {marks} marks, expected {total}")

    for mcq in assessment["concept_mcqs"]:
        if len(mcq["options"]) != 4:
            problems.append(f"MCQ {mcq['question_number']}: {len(mcq['options'])} options, expected 4")

    # Only the human-marked questions carry rubrics; an MCQ's mark is all-or-nothing.
    for key in ("scenario_questions", "practical_tasks"):
        for item in assessment[key]:
            number = item.get("question_number", item.get("task_number"))
            rubric = sum(criterion["marks"] for criterion in item["rubric"])
            if rubric != item["marks"]:
                problems.append(f"{key} {number}: rubric sums to {rubric}, question is worth {item['marks']}")

    problems.extend(check_formatting(assessment))

    assessed = set(assessment["skills_assessed"])
    if not assessed:
        problems.append("skills_assessed is empty")

    if vocabulary is not None and (unknown := sorted(assessed - vocabulary)):
        problems.append(
            f"skills_assessed names not in the course's skill list: {'; '.join(unknown[:3])}"
            + (f" (+{len(unknown) - 3} more)" if len(unknown) > 3 else "")
        )

    covered = set()
    for key, _, _ in groups:
        for item in assessment[key]:
            covered.update(item["skills_covered"])

    if stray := sorted(covered - assessed):
        problems.append(f"questions cite skills outside skills_assessed: {', '.join(stray)}")

    # The reverse is deliberately NOT an error. A skill the section teaches but
    # that no question happens to reach is fine — sixteen questions cannot go
    # deep on nine skills at once, and requiring full coverage buys breadth by
    # spending the depth that makes these questions worth setting. Only the
    # direction above matters, because a skill name appearing on a question but
    # not in skills_assessed is an unmapped name, which breaks the join.

    return problems


def generate_section(service, course: dict, section: dict, modules: list) -> dict | None:
    """Generate, validate and normalize one section. Returns None if it failed.

    Never raises: one section's bad luck is not a reason to abandon the other
    159, and every section stands alone so a re-run resumes.
    """
    code = section["section_code"]

    if _out_of_credit.is_set():
        return None

    for attempt in range(VALIDATION_ATTEMPTS):
        assessment = None

        for delay in (*RETRY_DELAYS, None):
            try:
                assessment = service.generate_section_assessment(course, section, modules).model_dump()
                break
            except Exception as error:
                if is_billing_failure(error):
                    if not _out_of_credit.is_set():
                        _out_of_credit.set()
                        report(f"  !! {code}: OUT OF CREDIT — {str(error)[:160]}")
                        report("     abandoning the remaining sections; completed courses are already written")
                    return None

                if delay is not None and is_rate_limit(error):
                    report(f"  .. {code}: rate limited, retrying in {delay}s")
                    time.sleep(delay)
                    continue

                report(f"  !! {code}: {type(error).__name__}: {error}")
                return None

        if assessment is None:
            report(f"  !! {code}: still rate limited after {len(RETRY_DELAYS)} retries")
            return None

        if notes := normalize_fences(assessment):
            report(f"  .. {code}: {len(notes)} fence tag(s) normalised, e.g. {notes[0].split(': ', 1)[1]}")

        if problems := validate(assessment, code, {s["skill_name"] for s in course["skills"]}):
            if attempt + 1 < VALIDATION_ATTEMPTS:
                report(f"  .. {code}: invalid ({problems[0]}), regenerating")
                continue

            report(f"  !! {code}: still invalid after {VALIDATION_ATTEMPTS} attempts:")
            for problem in problems:
                report(f"       - {problem}")
            return None

        assessment["concept_mcqs"] = balance_answer_key(assessment["concept_mcqs"], code)

        spread = {label: 0 for label in LABELS}
        for mcq in assessment["concept_mcqs"]:
            spread[mcq["correct_option"]] += 1

        report(
            f"  ok {code}  {len(assessment['skills_assessed'])} skills  "
            f"key {'/'.join(str(spread[label]) for label in LABELS)}"
        )
        return assessment

    return None


def course_jobs(code: str) -> tuple:
    """One course's inputs, as (course, [(section, modules), ...])."""
    modules_doc = json.loads((MODULES_DIR / f"{code}.json").read_text(encoding="utf-8"))
    course = json.loads((EXTRACTED_DIR / f"{code}.json").read_text(encoding="utf-8"))
    course["course_code"] = code

    jobs = [
        (section, [m for m in modules_doc["modules"] if m["section_code"] == section["section_code"]])
        for section in modules_doc["sections"]
    ]

    return course, jobs


def write_course(course: dict, sections: list, out_dir: Path) -> str:
    """Write one course's file, but only if every section survived.

    All-or-nothing per course: a file holding three of four sections looks
    complete to the loader and to anyone reading it, and the missing one is only
    noticed when a learner reaches it. A course that failed is simply absent, so
    a plain re-run picks it up.
    """
    code = course["course_code"]

    if failures := sum(section is None for section in sections):
        report(f"  !! {code}: {failures} of {len(sections)} sections failed, not writing")
        return "failed"

    payload = {
        "course_code": code,
        "course_name": course["course_name"],
        "sections": sections,
    }

    (out_dir / f"{code}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report(f"  -> {code}.json")
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate courses that already have a JSON file (costs tokens again)",
    )
    parser.add_argument(
        "--only",
        help="comma-separated course codes to generate, e.g. NT-C-001,NT-C-038",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="sections generated concurrently (default 8; lower it if the key gets rate limited)",
    )
    parser.add_argument(
        "--backend",
        choices=("gpt-5", "gemma"),
        default="gpt-5",
        help="which model authors the questions (default gpt-5; gemma goes via the HF router)",
    )
    parser.add_argument(
        "--mcq-batch",
        type=int,
        default=5,
        help="MCQs per call for --backend gemma (default 5; 10 means one call for all of them)",
    )
    parser.add_argument(
        "--provider",
        help="pin one HF inference provider for --backend gemma, e.g. together, novita, cerebras",
    )
    parser.add_argument(
        "--sections",
        help="generate only these section codes, e.g. NT-C-002-S04 — a cheap probe, "
             "since one section is a quarter of a course in both time and tokens",
    )
    parser.add_argument(
        "--out-dir",
        help="where the course JSON goes (default: questions/ for gpt-5, questions_gemma/ for gemma)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the courses that would be generated and stop",
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIRS[args.backend]

    wanted = {code.strip().upper() for code in args.only.split(",")} if args.only else None
    sections_wanted = (
        {code.strip().upper() for code in args.sections.split(",")} if args.sections else None
    )

    # A section probe names its own courses, so --only becomes redundant noise.
    if sections_wanted and not wanted:
        wanted = {code.rsplit("-S", 1)[0] for code in sections_wanted}

    codes = sorted(path.stem for path in MODULES_DIR.glob("NT-C-*.json"))
    if not codes:
        print(f"no module files under {MODULES_DIR} — run extract_course_modules.py first", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    pending = []
    skipped = 0

    for code in codes:
        if wanted and code not in wanted:
            continue

        if not (EXTRACTED_DIR / f"{code}.json").exists():
            print(f"  ?? {code}: no extracted profile, skipping (run extract_course_profiles.py)")
            continue

        if (out_dir / f"{code}.json").exists() and not args.force and not sections_wanted:
            skipped += 1
            continue

        pending.append(code)

    if not pending:
        print(f"nothing to do — {skipped} course(s) already generated (use --force to redo them)")
        return 0

    if args.dry_run:
        count = len(sections_wanted) if sections_wanted else len(pending) * 4
        print(f"would generate {len(pending)} course(s), {count} section(s):")
        for code in sorted(sections_wanted) if sections_wanted else pending:
            print(f"  {code}")
        return 0

    # Every section across every pending course goes into one pool. Running
    # course by course would cap concurrency at four however high --workers is,
    # because a course only has four sections.
    inputs = [course_jobs(code) for code in pending]

    if sections_wanted:
        inputs = [
            (course, [job for job in jobs if job[0]["section_code"] in sections_wanted])
            for course, jobs in inputs
        ]
        if unknown := sections_wanted - {
            job[0]["section_code"] for _, jobs in inputs for job in jobs
        }:
            print(f"no such section: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 1

    flat = [(course, section, modules) for course, jobs in inputs for section, modules in jobs]

    print(f"generating {len(pending)} course(s) = {len(flat)} sections, {args.workers} worker(s)")
    print(f"{skipped} already present\n")

    started = time.perf_counter()

    # Constructed once and shared: it builds an OpenAI client, and one per
    # worker would be a connection pool each for no reason. The client
    # multiplexes concurrent requests over one pool, which is what we want.
    if args.backend == "gemma":
        service = GemmaService(provider=args.provider, mcq_batch=args.mcq_batch)
        print(f"backend: gemma (MCQs {args.mcq_batch} per call)"
              + (f" via {args.provider}" if args.provider else ""))
    else:
        service = OpenAIService()
        print("backend: gpt-5")

    with ThreadPoolExecutor(max_workers=min(args.workers, len(flat))) as pool:
        generated = list(pool.map(lambda job: generate_section(service, *job), flat))

    # A section probe writes one file per section, NOT a course file. A course
    # JSON holding one of four sections would look complete to the loader and to
    # anyone reading it, and the absence would only surface when a learner
    # reached the missing section — the same trap write_course exists to avoid.
    if sections_wanted:
        written = 0
        for assessment in generated:
            if assessment is None:
                continue
            path = out_dir / f"{assessment['section_code']}.section.json"
            path.write_text(json.dumps(assessment, indent=2, ensure_ascii=False), encoding="utf-8")
            report(f"  -> {path.name}")
            written += 1

        failed = len(generated) - written
        print(f"\nprobe: {written} section(s) written, {failed} failed in {time.perf_counter() - started:.0f}s")
        print(f"JSON in {out_dir}  (section probes, not loadable course files)")
        return 1 if failed else 0

    # Back into per-course groups, in the order the sections went out.
    results = []
    cursor = 0
    for course, jobs in inputs:
        results.append(write_course(course, generated[cursor : cursor + len(jobs)], out_dir))
        cursor += len(jobs)

    done = results.count("ok")
    failed = results.count("failed")

    print(f"\ngenerated {done}, skipped {skipped} already present, failed {failed} in {time.perf_counter() - started:.0f}s")
    print(f"JSON in {out_dir}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
