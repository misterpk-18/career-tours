"""Sittings and the answers inside them.

One repository rather than two, because a sitting and its answers are one thing:
an answer outside a sitting has no meaning, the score is a property of the run
and not of any single answer, and every write to either has to respect the same
clock. Splitting them would mean the clock is checked in two places.

Only MCQs take part. The scenarios and practical tasks stay in the corpus and
are deliberately not offered, because they are worth 70 of a section's 100 marks
and cannot be scored without a human — and this system has no assessor role.
Every score here is therefore out of the MCQ total, and ``marks_available`` says
so on the row instead of leaving it implied.

The clock is authoritative here and nowhere else. ``seconds_remaining`` is only
correct as of the last pause; while a sitting runs, the truth is
``seconds_remaining - (now - resumed_at)``, which is what ``clock`` returns and
what every mutating method checks first. Trusting a client-sent value would be
trusting the one party with a reason to change it.
"""

import threading
import time
from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db

# Twenty minutes for ten MCQs — two minutes a question, which the artefact-heavy
# stems in this corpus need. Passed in by the caller rather than read here so a
# section can carry its own limit later without changing this module.
DEFAULT_TIME_LIMIT_SECONDS = 20 * 60

OPEN_STATUSES = ("in_progress", "paused")

# A section's question keys — ids, options, correct option — are immutable
# between corpus loads, and every answer save needs all ten of them to rebuild
# the option shuffle. Against this Neon instance that is a 74ms round trip, paid
# ten times per test, for data that has not changed since the last deploy.
#
# TTL rather than a permanent cache, because the corpus CAN be reloaded by
# scripts/load_section_questions.py without a restart. Five minutes bounds how
# long a process can serve a stale shuffle; Lambda containers rarely live longer
# than that anyway, so in production this is usually a per-container memo.
#
# Cached rows are treated as read-only by every caller: present() copies the
# option list before permuting it, and grading only compares fields.
_KEY_CACHE_TTL_SECONDS = 300
_key_cache: dict = {}
_key_cache_lock = threading.Lock()


class SectionSittingRepository:
    # ---------------------------------------------------------------- questions

    @staticmethod
    def mcq_keys_for_section(section_code: str) -> list:
        """Just what present() and grading need: ids, options, correct option.

        The full row carries the stem, explanation and distractor rationale —
        several kilobytes per question, ten questions, fetched cross-region on
        every single answer save purely to rebuild the option shuffle. This
        projection is a fraction of the bytes, and cached, so the common case is
        no round trip at all.
        """
        now = time.monotonic()

        with _key_cache_lock:
            cached = _key_cache.get(section_code)
            if cached and now - cached[0] < _KEY_CACHE_TTL_SECONDS:
                return cached[1]

        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT question_id, question_number, options, correct_option, marks
                FROM course_section_questions
                WHERE section_code = :section_code AND question_type = 'mcq'
                ORDER BY question_number
            """),
            {"section_code": section_code},
        ))
        rows = [dict(row) for row in result.mappings()]

        # Only cache a complete section. An empty result means the section code
        # is wrong or the corpus is not loaded, and caching that for five minutes
        # would turn a transient state into a sticky one.
        if rows:
            with _key_cache_lock:
                _key_cache[section_code] = (now, rows)

        return rows

    @staticmethod
    def mcqs_for_section(section_code: str) -> list:
        """The section's MCQs in corpus order, with everything needed to present
        and grade them. The sitting shuffles this; the corpus order is the input.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT question_id, question_number, stem, options, correct_option,
                       explanation, distractor_rationale, marks
                FROM course_section_questions
                WHERE section_code = :section_code AND question_type = 'mcq'
                ORDER BY question_number
            """),
            {"section_code": section_code},
        ))
        return [dict(row) for row in result.mappings()]

    @staticmethod
    def marks_available(section_code: str) -> int:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT COALESCE(SUM(marks), 0) FROM course_section_questions
                WHERE section_code = :section_code AND question_type = 'mcq'
            """),
            {"section_code": section_code},
        ))
        return int(result.scalar_one())

    # ----------------------------------------------------------------- sittings

    @staticmethod
    def get(sitting_id, project_id) -> Optional[dict]:
        """One sitting, scoped to the project so a stray id cannot reach across
        projects even if the route forgot to check.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT *,
                    GREATEST(0, seconds_remaining - CASE
                        WHEN status = 'in_progress' AND resumed_at IS NOT NULL
                        THEN FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - resumed_at)))::int
                        ELSE 0
                    END) AS seconds_left
                FROM project_section_sittings
                WHERE sitting_id = :sitting_id AND project_id = :project_id
            """),
            {"sitting_id": sitting_id, "project_id": project_id},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def find(project_id, section_code: str, mode: str, open_only: bool = False):
        """The graded sitting for a section, or the open practice one."""
        result = cast(CursorResult[Any], db.session.execute(
            text(f"""
                SELECT *,
                    GREATEST(0, seconds_remaining - CASE
                        WHEN status = 'in_progress' AND resumed_at IS NOT NULL
                        THEN FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - resumed_at)))::int
                        ELSE 0
                    END) AS seconds_left
                FROM project_section_sittings
                WHERE project_id = :project_id
                  AND section_code = :section_code
                  AND mode = :mode
                  {"AND status IN ('in_progress', 'paused')" if open_only else ""}
                ORDER BY started_at DESC
                LIMIT 1
            """),
            {"project_id": project_id, "section_code": section_code, "mode": mode},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def start(project_id, section_code: str, mode: str, time_limit: int,
              marks_available: int) -> dict:
        """Open a sitting. Does NOT commit — the caller may be discarding an
        earlier one in the same transaction, and the two must not half-happen.

        The clock starts immediately: a sitting is created in progress with
        resumed_at set, because Start is the student clicking Start.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                INSERT INTO project_section_sittings (
                    project_id, section_code, mode, status,
                    time_limit_seconds, seconds_remaining, resumed_at,
                    marks_available
                ) VALUES (
                    :project_id, :section_code, :mode, 'in_progress',
                    :time_limit, :time_limit, CURRENT_TIMESTAMP,
                    :marks_available
                )
                RETURNING *
            """),
            {
                "project_id": project_id, "section_code": section_code, "mode": mode,
                "time_limit": time_limit, "marks_available": marks_available,
            },
        ))
        return dict(result.mappings().one())

    @staticmethod
    def discard(sitting_id) -> int:
        """Delete an unsubmitted sitting and its answers.

        This is what "start new" does. It deletes rather than marking abandoned
        because the unique index allows one graded sitting per section in ANY
        status — an abandoned row would keep occupying the slot and the student
        could never start again. Submitted sittings are never reachable here;
        the route refuses before calling this.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                DELETE FROM project_section_sittings
                WHERE sitting_id = :sitting_id AND status <> 'submitted'
            """),
            {"sitting_id": sitting_id},
        ))
        return result.rowcount

    # -------------------------------------------------------------------- clock

    @staticmethod
    def clock(sitting: dict) -> int:
        """Seconds actually left, right now. Never negative.

        ``seconds_remaining`` on the row is only current as of the last pause;
        while a sitting runs, the elapsed time since ``resumed_at`` has to come
        off it. That subtraction is done by the database in the SAME query that
        reads the row, and arrives as ``seconds_left``.

        It used to be its own ``SELECT EXTRACT(EPOCH ...)`` round trip. Against
        this Neon instance one round trip is ~74ms and every request that touches
        a sitting made this call, so it was 74ms of pure latency on the critical
        path of answering a question — for a subtraction the previous query could
        have done for free.

        The fallback below is for a sitting dict that came from somewhere without
        the computed column (``start``, ``pause``, ``resume`` all RETURNING *).
        Those have just written the clock themselves, so the stored value is
        current by construction and no arithmetic is needed.
        """
        if sitting.get("seconds_left") is not None:
            return int(sitting["seconds_left"])

        remaining = int(sitting["seconds_remaining"])

        if sitting["status"] != "in_progress" or sitting["resumed_at"] is None:
            return max(0, remaining)

        # A running sitting whose row carries no computed clock: only reachable
        # straight after start/resume, where no measurable time has passed.
        return max(0, remaining)

    @staticmethod
    def pause(sitting_id) -> Optional[dict]:
        """Stop the clock, banking what is left.

        The subtraction happens in SQL against CURRENT_TIMESTAMP so the value
        stored is the database's own view of elapsed time, not a Python clock on
        whichever worker took the request. GREATEST(0, ...) because a sitting
        that ran out while nobody was looking must not store a negative.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE project_section_sittings
                SET seconds_remaining = GREATEST(0, seconds_remaining -
                        FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - resumed_at)))::int),
                    resumed_at = NULL,
                    status = 'paused'
                WHERE sitting_id = :sitting_id AND status = 'in_progress'
                RETURNING *
            """),
            {"sitting_id": sitting_id},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def resume(sitting_id) -> Optional[dict]:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE project_section_sittings
                SET resumed_at = CURRENT_TIMESTAMP, status = 'in_progress'
                WHERE sitting_id = :sitting_id AND status = 'paused'
                  AND seconds_remaining > 0
                RETURNING *
            """),
            {"sitting_id": sitting_id},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    # ------------------------------------------------------------------ answers

    @staticmethod
    def save_answer(sitting: dict, question: dict, presented_option: str,
                    stored_option: str) -> dict:
        """Record or revise one answer inside a sitting. Does NOT commit.

        Two letters are kept. ``selected_option`` is the corpus letter, so
        ``is_correct`` compares like with like and stays meaningful however the
        options were shuffled; ``presented_option`` is what the student actually
        clicked, which is what a review screen has to show them. Deriving either
        from the other later would mean recomputing a shuffle to read a result.

        Grading happens here for every mode. A practice sitting still needs to
        know whether the answer was right — that is the point of practice — and
        keeping the score off the section is the sitting's job, not the answer's.
        """
        is_correct = stored_option == question["correct_option"]

        result = cast(CursorResult[Any], db.session.execute(
            text("""
                INSERT INTO project_question_attempts (
                    sitting_id, project_id, question_id, section_code,
                    selected_option, presented_option,
                    is_correct, marks_awarded, max_marks, graded_by, graded_at
                ) VALUES (
                    :sitting_id, :project_id, :question_id, :section_code,
                    :selected_option, :presented_option,
                    :is_correct, :marks_awarded, :max_marks, 'auto', CURRENT_TIMESTAMP
                )
                ON CONFLICT (sitting_id, question_id) DO UPDATE SET
                    selected_option  = EXCLUDED.selected_option,
                    presented_option = EXCLUDED.presented_option,
                    is_correct       = EXCLUDED.is_correct,
                    marks_awarded    = EXCLUDED.marks_awarded,
                    graded_at        = CURRENT_TIMESTAMP,
                    submitted_at     = CURRENT_TIMESTAMP
                RETURNING *
            """),
            {
                "sitting_id": sitting["sitting_id"],
                "project_id": sitting["project_id"],
                "question_id": question["question_id"],
                "section_code": sitting["section_code"],
                "selected_option": stored_option,
                "presented_option": presented_option,
                "is_correct": is_correct,
                "marks_awarded": question["marks"] if is_correct else 0,
                "max_marks": question["marks"],
            },
        ))
        return dict(result.mappings().one())

    @staticmethod
    def answers_for(sitting_id) -> list:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT a.*, q.question_number
                FROM project_question_attempts a
                JOIN course_section_questions q ON q.question_id = a.question_id
                WHERE a.sitting_id = :sitting_id
                ORDER BY q.question_number
            """),
            {"sitting_id": sitting_id},
        ))
        return [dict(row) for row in result.mappings()]

    # ------------------------------------------------------------------- submit

    @staticmethod
    def submit(sitting_id) -> Optional[dict]:
        """Close a sitting and lock its score. Does NOT commit.

        The score is computed from the answers in one statement and written onto
        the sitting, rather than left to be summed on every read. That is
        deliberate and is the one place a stored aggregate is right: this number
        is a result, it must never change again, and a query that recomputed it
        would silently follow the corpus if a question were ever re-graded.

        Unanswered questions simply score nothing — there is no row for them, so
        the SUM ignores them. The guard is on status, so a second submit of the
        same sitting returns None and the route reports it rather than
        overwriting a locked score.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE project_section_sittings s
                SET status = 'submitted',
                    submitted_at = CURRENT_TIMESTAMP,
                    resumed_at = NULL,
                    seconds_remaining = CASE
                        WHEN s.status = 'in_progress' THEN GREATEST(0, s.seconds_remaining -
                            FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - s.resumed_at)))::int)
                        ELSE s.seconds_remaining
                    END,
                    marks_awarded = COALESCE((
                        SELECT SUM(a.marks_awarded) FROM project_question_attempts a
                        WHERE a.sitting_id = s.sitting_id
                    ), 0)
                WHERE s.sitting_id = :sitting_id
                  AND s.status IN ('in_progress', 'paused')
                RETURNING *
            """),
            {"sitting_id": sitting_id},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    # ----------------------------------------------------------------- overview

    @staticmethod
    def section_overview(project_id) -> list:
        """Per-section state for the syllabus: what the button should say.

        One row per section the project has touched. ``graded_status`` drives the
        button — absent means Start, open means Continue-or-start-new, submitted
        means Practice — and the locked score comes from the graded sitting
        rather than from a sum over answers, because it is a result and not a
        running total.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT
                    section_code,
                    MAX(CASE WHEN mode = 'graded' THEN status END)          AS graded_status,
                    MAX(CASE WHEN mode = 'graded' THEN marks_awarded END)   AS marks_awarded,
                    MAX(CASE WHEN mode = 'graded' THEN marks_available END) AS marks_available,
                    MAX(CASE WHEN mode = 'graded' THEN submitted_at END)    AS submitted_at,
                    MAX(CASE WHEN mode = 'practice'
                             AND status IN ('in_progress', 'paused')
                        THEN sitting_id::text END)                          AS open_practice_id,
                    COUNT(*) FILTER (
                        WHERE mode = 'practice' AND status = 'submitted'
                    )                                                       AS practice_runs
                FROM project_section_sittings
                WHERE project_id = :project_id
                GROUP BY section_code
                ORDER BY section_code
            """),
            {"project_id": project_id},
        ))
        return [dict(row) for row in result.mappings()]
