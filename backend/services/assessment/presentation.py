"""How one sitting's questions are laid out for the student.

Nothing here is stored. Question order and option order are deterministic
functions of the sitting id, so the layout a student saw can be recomputed by
any process at any time — the page that resumes a paused sitting, the grader
that maps a clicked letter back to the corpus, and the review screen afterwards
all derive the same arrangement instead of sharing state. A stored permutation
would be a second source of truth that can disagree with the answers keyed
against it.

Shuffling per sitting would normally throw away the answer-key balance the
corpus generator built deliberately: ten independently shuffled questions land
the correct option wherever chance puts it, and a sitting dealt seven B's is a
sitting a student can pass by pressing B. So the correct positions are dealt
from a balanced pool here too — A/B/C/D cycled, giving 3/3/2/2 over ten
questions — and only the assignment of those slots is seeded. The shuffle is
real, and no letter can appear more than three times in a sitting.

This is the same algorithm as ``scripts/generate_section_questions.py``, seeded
by sitting rather than by section. It is duplicated rather than imported because
that file is an offline generator that pulls in the OpenAI client at import
time, and the request path must not.
"""

import hashlib

LABELS = ("A", "B", "C", "D")


def seeded_order(seed: str, count: int) -> list:
    """A deterministic permutation of ``range(count)``, by Fisher-Yates.

    Driven by a SHA-256 digest rather than ``random`` so it is reproducible
    across processes and across requests: the same sitting must lay out
    identically on every page load, in a different worker, after a restart.
    """
    digest = hashlib.sha256(seed.encode()).digest()

    order = list(range(count))
    for i in range(count - 1, 0, -1):
        j = digest[i % len(digest)] % (i + 1)
        order[i], order[j] = order[j], order[i]

    return order


def question_order(sitting_id, count: int) -> list:
    """The order this sitting presents its questions in."""
    return seeded_order(f"{sitting_id}:questions", count)


def present(sitting_id, questions: list) -> list:
    """The questions as this sitting shows them: shuffled, options rearranged.

    Each returned entry carries ``options`` in display order and ``answer_map``,
    which maps the letter the student can click to the letter stored in the
    corpus. The map is what makes grading possible without trusting the client
    to tell us which option it displayed where.

    ``questions`` must be the section's MCQs; the caller decides that, because
    which types appear in the UI is a product decision and not this module's to
    make.

    ``stem`` and ``marks`` are optional. The grading path rebuilds the shuffle
    from a projection that omits the prose — several KB per question, fetched
    cross-region on every answer save purely to recompute a permutation — and it
    only ever reads ``answer_map``. Requiring the stem here would force that
    path to fetch text nobody looks at.
    """
    order = question_order(sitting_id, len(questions))
    balanced = [LABELS[i % len(LABELS)] for i in range(len(questions))]
    balanced = [balanced[i] for i in seeded_order(f"{sitting_id}:key", len(balanced))]

    presented = []

    for position, (index, target) in enumerate(zip(order, balanced), start=1):
        question = questions[index]
        options = list(question["options"])

        correct = options.pop(LABELS.index(question["correct_option"]))

        # The distractors are permuted among themselves as well, so they do not
        # keep their stored order around the moved answer.
        spread = seeded_order(f"{sitting_id}:{question['question_id']}", len(options))
        distractors = iter(options[i] for i in spread)

        slot = LABELS.index(target)
        shown = [correct if i == slot else next(distractors) for i in range(len(LABELS))]

        presented.append({
            "position": position,
            "question_id": question["question_id"],
            "question_number": question["question_number"],
            "stem": question.get("stem"),
            "options": shown,
            "marks": question.get("marks"),
            # displayed letter -> stored letter. Only the correct one differs in
            # meaning; the rest are needed so a wrong answer records which
            # corpus option it actually was.
            "answer_map": {
                LABELS[i]: LABELS[question["options"].index(shown[i])]
                for i in range(len(LABELS))
            },
        })

    return presented
