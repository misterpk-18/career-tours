"""XP, levels, streaks, badges and the leaderboard.

Every number here is DERIVED from ``project_section_sittings``. Nothing is
stored, and that is the point: a stored XP column can disagree with the scores
it was computed from, and the first disagreement is unfindable — you cannot tell
whether the total is stale or the sittings are wrong. Same reasoning as
per-section progress, which is also a query rather than a column.

It also means there is no backfill. Every score already submitted counts
immediately, including the ones recorded before any of this existed.

THE XP RULE, stated once, here:

* A submitted GRADED sitting earns its marks as XP (0-30), plus a flat 20 for
  clearing the section at all.
* A submitted PRACTICE sitting earns 5 XP, once per section, however many times
  it is run.

That shape is deliberate. Practice is unlimited by design, so any XP that scaled
with practice would be farmable — a student could grind the same ten questions
for an unbounded score, which rewards persistence at a keyboard rather than
learning. Graded sittings are capped at one per section by a unique index, so the
graded component is bounded by construction: 160 sections x 50 = 8,000 XP is the
ceiling for the whole corpus, and it cannot be exceeded by repetition.
"""

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db

GRADED_CLEAR_BONUS = 20
PRACTICE_XP_PER_SECTION = 5

# Levels get progressively longer, so an early level arrives quickly and a later
# one still means something. Level n needs 100 * n XP, i.e. cumulative
# 100, 300, 600, 1000 ... which is 50 * n * (n + 1) to reach level n + 1.
LEVEL_STEP = 100


def level_for(xp: int) -> tuple:
    """(level, xp_into_level, xp_needed_for_next). Level 1 starts at 0 XP."""
    level = 1
    consumed = 0

    while True:
        needed = LEVEL_STEP * level
        if xp - consumed < needed:
            return level, xp - consumed, needed
        consumed += needed
        level += 1


# Badge rules live beside the query that evaluates them, so the criterion a
# student reads and the condition that awards it cannot drift apart.
BADGES = (
    ("first_submit", "First Submit", "🎯", "Submit any section",
     lambda s: s["graded_sections"] >= 1),
    ("perfect_section", "Perfect 30", "💯", "Score 30/30 in one section",
     lambda s: s["best_marks"] == 30),
    ("strong_finish", "Distinction", "⭐", "Score 24/30 or better",
     lambda s: s["best_marks"] >= 24),
    ("course_complete", "Course Cleared", "🏁", "Submit all four sections of a course",
     lambda s: s["courses_completed"] >= 1),
    ("streak_3", "On a Roll", "🔥", "Practise or submit 3 days in a row",
     lambda s: s["longest_streak"] >= 3),
    ("streak_7", "Week Strong", "⚡", "Seven days in a row",
     lambda s: s["longest_streak"] >= 7),
    ("explorer", "Explorer", "🧭", "Start sections in 3 different courses",
     lambda s: s["courses_touched"] >= 3),
    ("grinder", "Ten Down", "📚", "Submit ten sections",
     lambda s: s["graded_sections"] >= 10),
)


class AchievementRepository:
    @staticmethod
    def _totals(student_id) -> dict:
        """One query for everything countable about a student's sittings."""
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                WITH mine AS (
                    SELECT s.*, LEFT(s.section_code, 8) AS course_code
                    FROM project_section_sittings s
                    JOIN projects p ON p.project_id = s.project_id
                    WHERE p.student_id = :student_id
                ),
                graded AS (
                    SELECT * FROM mine WHERE mode = 'graded' AND status = 'submitted'
                ),
                practised AS (
                    -- DISTINCT section, not per run: practice XP is once per
                    -- section however many times it is repeated.
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
        """Current and longest run of consecutive ACTIVE DAYS.

        A day counts if any sitting was submitted on it, practice included —
        showing up is the behaviour a streak is meant to reward.

        The gaps-and-islands trick: rank the distinct dates, subtract the rank
        from the date, and every consecutive run collapses to the same value.
        Done in SQL because doing it in Python means shipping every date a
        student has ever been active across the wire to count them.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                WITH days AS (
                    SELECT DISTINCT DATE(s.submitted_at) AS day
                    FROM project_section_sittings s
                    JOIN projects p ON p.project_id = s.project_id
                    WHERE p.student_id = :student_id AND s.submitted_at IS NOT NULL
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
        # A run counts as current if it reaches yesterday: a student mid-streak
        # who has not opened the app yet today has not broken it.
        return {"streak": int(row["current"]), "longest_streak": int(row["longest"])}

    @staticmethod
    def profile(student_id) -> dict:
        totals = AchievementRepository._totals(student_id)
        streaks = AchievementRepository._streaks(student_id)

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

    @staticmethod
    def leaderboard(student_id, limit: int = 10) -> dict:
        """Anonymous ranking by XP, plus where this student sits in it.

        No names, no ids, no course detail — a rank and a number. A leaderboard
        that named people would publish one student's academic standing to
        another, which nobody asked for and which cannot be taken back once
        seen. Rank alone gives the motivation without the exposure.

        XP is recomputed here with the same arithmetic as ``profile``, in SQL,
        so the board and the student's own card cannot report different totals.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text(f"""
                WITH per_student AS (
                    SELECT
                        p.student_id,
                        COALESCE(SUM(CASE
                            WHEN s.mode = 'graded' AND s.status = 'submitted'
                            THEN s.marks_awarded + {GRADED_CLEAR_BONUS} ELSE 0
                        END), 0)
                        + COALESCE(COUNT(DISTINCT CASE
                            WHEN s.mode = 'practice' AND s.status = 'submitted'
                            THEN s.section_code
                        END) * {PRACTICE_XP_PER_SECTION}, 0) AS xp
                    FROM projects p
                    LEFT JOIN project_section_sittings s ON s.project_id = p.project_id
                    GROUP BY p.student_id
                ),
                ranked AS (
                    SELECT student_id, xp,
                           RANK() OVER (ORDER BY xp DESC) AS position
                    FROM per_student WHERE xp > 0
                )
                SELECT position, xp, (student_id = :student_id) AS is_me
                FROM ranked
                WHERE position <= :limit OR student_id = :student_id
                ORDER BY position
            """),
            {"student_id": student_id, "limit": limit},
        ))
        rows = [dict(row) for row in result.mappings()]

        return {
            "entries": [
                {"position": int(r["position"]), "xp": int(r["xp"]), "is_me": bool(r["is_me"])}
                for r in rows
            ],
            "total_ranked": len({r["position"] for r in rows}) if rows else 0,
        }
