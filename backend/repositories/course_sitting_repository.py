"""Course-track sittings: the project-independent twin of the section sittings.

Identical behaviour to :mod:`repositories.section_sitting_repository` — same
clock, same shuffle-driven grading, same "first graded submit locks the score"
— but every row is owned by a STUDENT rather than a project, and lives in the
``course_section_sittings`` / ``course_question_attempts`` tables. The two
tracks share no rows and no state, which is the whole point: a section can be
sat here and in a project independently, and neither score moves the other.

The question projection, the option shuffle and the clock arithmetic are pure
and section-only, so they are reused from ``SectionSittingRepository`` rather
than copied — duplicating the seeded-shuffle key helpers would be duplicating
the one thing that MUST agree between the two tracks for grading to mean the
same thing.
"""

from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from repositories.section_sitting_repository import (
    DEFAULT_TIME_LIMIT_SECONDS,  # noqa: F401  (re-exported for the routes)
    OPEN_STATUSES,  # noqa: F401
    SectionSittingRepository,
)


class CourseSittingRepository:
    # ---------------------------------------------------------------- questions
    # These are section-only and identical to the project track. Reused so the
    # option shuffle and mark totals cannot drift between the two.
    mcq_keys_for_section = staticmethod(SectionSittingRepository.mcq_keys_for_section)
    mcqs_for_section = staticmethod(SectionSittingRepository.mcqs_for_section)
    marks_available = staticmethod(SectionSittingRepository.marks_available)
    clock = staticmethod(SectionSittingRepository.clock)

    # ----------------------------------------------------------------- sittings

    @staticmethod
    def get(sitting_id, student_id) -> Optional[dict]:
        """One sitting, scoped to the student so a stray id cannot reach across
        accounts even if the route forgot to check.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT *,
                    GREATEST(0, seconds_remaining - CASE
                        WHEN status = 'in_progress' AND resumed_at IS NOT NULL
                        THEN FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - resumed_at)))::int
                        ELSE 0
                    END) AS seconds_left
                FROM course_section_sittings
                WHERE sitting_id = :sitting_id AND student_id = :student_id
            """),
            {"sitting_id": sitting_id, "student_id": student_id},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def find(student_id, section_code: str, mode: str, open_only: bool = False):
        """The graded sitting for a section, or the open practice one."""
        result = cast(CursorResult[Any], db.session.execute(
            text(f"""
                SELECT *,
                    GREATEST(0, seconds_remaining - CASE
                        WHEN status = 'in_progress' AND resumed_at IS NOT NULL
                        THEN FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - resumed_at)))::int
                        ELSE 0
                    END) AS seconds_left
                FROM course_section_sittings
                WHERE student_id = :student_id
                  AND section_code = :section_code
                  AND mode = :mode
                  {"AND status IN ('in_progress', 'paused')" if open_only else ""}
                ORDER BY started_at DESC
                LIMIT 1
            """),
            {"student_id": student_id, "section_code": section_code, "mode": mode},
        ))
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def start(student_id, section_code: str, mode: str, time_limit: int,
              marks_available: int) -> dict:
        """Open a sitting. Does NOT commit — the caller may be discarding an
        earlier one in the same transaction.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                INSERT INTO course_section_sittings (
                    student_id, section_code, mode, status,
                    time_limit_seconds, seconds_remaining, resumed_at,
                    marks_available
                ) VALUES (
                    :student_id, :section_code, :mode, 'in_progress',
                    :time_limit, :time_limit, CURRENT_TIMESTAMP,
                    :marks_available
                )
                RETURNING *
            """),
            {
                "student_id": student_id, "section_code": section_code, "mode": mode,
                "time_limit": time_limit, "marks_available": marks_available,
            },
        ))
        return dict(result.mappings().one())

    @staticmethod
    def discard(sitting_id) -> int:
        """Delete an unsubmitted sitting and its answers ("start new")."""
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                DELETE FROM course_section_sittings
                WHERE sitting_id = :sitting_id AND status <> 'submitted'
            """),
            {"sitting_id": sitting_id},
        ))
        return result.rowcount

    # -------------------------------------------------------------------- clock

    @staticmethod
    def pause(sitting_id) -> Optional[dict]:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE course_section_sittings
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
                UPDATE course_section_sittings
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
        """Record or revise one answer inside a sitting. Does NOT commit."""
        is_correct = stored_option == question["correct_option"]

        result = cast(CursorResult[Any], db.session.execute(
            text("""
                INSERT INTO course_question_attempts (
                    sitting_id, student_id, question_id, section_code,
                    selected_option, presented_option,
                    is_correct, marks_awarded, max_marks, graded_by, graded_at
                ) VALUES (
                    :sitting_id, :student_id, :question_id, :section_code,
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
                "student_id": sitting["student_id"],
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
                FROM course_question_attempts a
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
        """Close a sitting and lock its score. Does NOT commit."""
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE course_section_sittings s
                SET status = 'submitted',
                    submitted_at = CURRENT_TIMESTAMP,
                    resumed_at = NULL,
                    seconds_remaining = CASE
                        WHEN s.status = 'in_progress' THEN GREATEST(0, s.seconds_remaining -
                            FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - s.resumed_at)))::int)
                        ELSE s.seconds_remaining
                    END,
                    marks_awarded = COALESCE((
                        SELECT SUM(a.marks_awarded) FROM course_question_attempts a
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
    def section_overview(student_id, course_code: str) -> list:
        """Per-section state for one course's sections, for this student.

        Filtered to the course (by the section-code prefix) rather than the
        whole account, because the caller is one course page — the project
        track's equivalent is scoped by project for the same reason.
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
                FROM course_section_sittings
                WHERE student_id = :student_id
                  AND LEFT(section_code, 8) = :course_code
                GROUP BY section_code
                ORDER BY section_code
            """),
            {"student_id": student_id, "course_code": course_code},
        ))
        return [dict(row) for row in result.mappings()]
