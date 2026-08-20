"""XP, levels, streaks and badges for the COURSE track.

The project track's gamification (``AchievementRepository``) is derived from
``project_section_sittings``. This is its independent twin, derived only from
``course_section_sittings`` — a separate XP pool so the two tracks stay fully
independent: a course-track submission moves these numbers and never the
project ones, and vice versa.

The rules themselves are identical and are reused from the project repository
(the XP arithmetic, the level curve, the badge definitions), so "score 30/30"
means the same thing in both places. Only the source table differs, and the
queries are a touch simpler here because the owner column is student_id
directly — there is no projects table to join through.
"""

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from repositories.achievement_repository import (
    BADGES,
    GRADED_CLEAR_BONUS,
    PRACTICE_XP_PER_SECTION,
    level_for,
)


class CourseAchievementRepository:
    @staticmethod
    def _totals(student_id) -> dict:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                WITH mine AS (
                    SELECT s.*, LEFT(s.section_code, 8) AS course_code
                    FROM course_section_sittings s
                    WHERE s.student_id = :student_id
                ),
                graded AS (
                    SELECT * FROM mine WHERE mode = 'graded' AND status = 'submitted'
                ),
                practised AS (
                    SELECT DISTINCT section_code FROM mine
                    WHERE mode = 'practice' AND status = 'submitted'
                )
                SELECT
                    (SELECT COUNT(*) FROM graded)                        AS graded_sections,
                    (SELECT COALESCE(SUM(marks_awarded), 0) FROM graded) AS marks_total,
                    (SELECT COALESCE(MAX(marks_awarded), 0) FROM graded) AS best_marks,
                    (SELECT COUNT(*) FROM practised)                     AS practised_sections,
                    (SELECT COUNT(DISTINCT course_code) FROM mine)       AS courses_touched,
                    (SELECT COUNT(*) FROM (
                        SELECT course_code FROM graded
                        GROUP BY course_code HAVING COUNT(*) >= 4
                    ) done)                                             AS courses_completed
            """),
            {"student_id": student_id},
        ))
        return dict(result.mappings().one())

    @staticmethod
    def _streaks(student_id) -> dict:
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                WITH days AS (
                    SELECT DISTINCT DATE(s.submitted_at) AS day
                    FROM course_section_sittings s
                    WHERE s.student_id = :student_id AND s.submitted_at IS NOT NULL
                ),
                runs AS (
                    SELECT day, day - (ROW_NUMBER() OVER (ORDER BY day))::int AS grp
                    FROM days
                ),
                lengths AS (
                    SELECT grp, COUNT(*) AS length, MAX(day) AS last_day
                    FROM runs GROUP BY grp
                )
                SELECT
                    COALESCE(MAX(length), 0) AS longest,
                    COALESCE(MAX(CASE
                        WHEN last_day >= CURRENT_DATE - 1 THEN length
                    END), 0) AS current
                FROM lengths
            """),
            {"student_id": student_id},
        ))
        row = result.mappings().one()
        return {"streak": int(row["current"]), "longest_streak": int(row["longest"])}

    @staticmethod
    def profile(student_id) -> dict:
        totals = CourseAchievementRepository._totals(student_id)
        streaks = CourseAchievementRepository._streaks(student_id)

        xp = (
            int(totals["marks_total"])
            + int(totals["graded_sections"]) * GRADED_CLEAR_BONUS
            + int(totals["practised_sections"]) * PRACTICE_XP_PER_SECTION
        )

        level, into, needed = level_for(xp)
        stats = {**{k: int(v) for k, v in totals.items()}, **streaks}

        return {
            "xp": xp,
            "level": level,
            "xp_into_level": into,
            "xp_for_level": needed,
            "streak": streaks["streak"],
            "longest_streak": streaks["longest_streak"],
            "sections_submitted": stats["graded_sections"],
            "courses_completed": stats["courses_completed"],
            "marks_total": stats["marks_total"],
            "badges": [
                {
                    "code": code,
                    "name": name,
                    "icon": icon,
                    "criterion": criterion,
                    "earned": bool(rule(stats)),
                }
                for code, name, icon, criterion, rule in BADGES
            ],
        }
