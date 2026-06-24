from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class CareerSkillGapRepository:

    @staticmethod
    def bulk_create(
        student_id,
        project_id,
        occupation_id,
        skill_gaps
    ):
        for skill_gap in skill_gaps:
            db.session.execute(
                text("""
                    INSERT INTO career_skill_gaps (
                        student_id,
                        project_id,
                        occupation_id,
                        skill_id,
                        gap_percentage
                    )
                    VALUES (
                        :student_id,
                        :project_id,
                        :occupation_id,
                        :skill_id,
                        :gap_percentage
                    )
                    ON CONFLICT (
                        project_id,
                        occupation_id,
                        skill_id
                    )
                    DO UPDATE SET
                        gap_percentage =
                            EXCLUDED.gap_percentage
                """),
                {
                    "student_id": student_id,
                    "project_id": project_id,
                    "occupation_id": occupation_id,
                    "skill_id": skill_gap["skill_id"],
                    "gap_percentage":
                        skill_gap["gap_percentage"],
                }
            )

        db.session.commit()

    @staticmethod
    def get_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT
                    csg.gap_id,
                    csg.student_id,
                    csg.project_id,
                    csg.occupation_id,
                    o.occupation_name,
                    csg.skill_id,
                    s.skill_name,
                    csg.gap_percentage,
                    csg.created_at
                FROM career_skill_gaps csg
                JOIN skills s
                    ON s.skill_id = csg.skill_id
                JOIN occupations o
                    ON o.occupation_id =
                        csg.occupation_id
                WHERE csg.project_id =
                    :project_id
                ORDER BY
                    csg.occupation_id,
                    csg.gap_percentage DESC
            """),
            {"project_id": project_id}
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def get_by_occupation_id(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    csg.gap_id,
                    csg.student_id,
                    csg.project_id,
                    csg.occupation_id,
                    o.occupation_name,
                    csg.skill_id,
                    s.skill_name,
                    csg.gap_percentage,
                    csg.created_at
                FROM career_skill_gaps csg
                JOIN skills s
                    ON s.skill_id = csg.skill_id
                JOIN occupations o
                    ON o.occupation_id =
                        csg.occupation_id
                WHERE csg.project_id =
                    :project_id
                  AND csg.occupation_id =
                    :occupation_id
                ORDER BY
                    csg.gap_percentage DESC,
                    s.skill_name
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def get_by_skill_id(
        project_id,
        skill_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    csg.gap_id,
                    csg.student_id,
                    csg.project_id,
                    csg.occupation_id,
                    o.occupation_name,
                    csg.skill_id,
                    s.skill_name,
                    csg.gap_percentage,
                    csg.created_at
                FROM career_skill_gaps csg
                JOIN skills s
                    ON s.skill_id = csg.skill_id
                JOIN occupations o
                    ON o.occupation_id =
                        csg.occupation_id
                WHERE csg.project_id =
                    :project_id
                  AND csg.skill_id =
                    :skill_id
                ORDER BY
                    csg.gap_percentage DESC
            """),
            {
                "project_id": project_id,
                "skill_id": skill_id,
            }
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def delete_by_project_id(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM career_skill_gaps
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()

        cursor_result = cast(
            CursorResult[Any],
            result
        )

        return cursor_result.rowcount or 0

    @staticmethod
    def delete_by_occupation_id(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                DELETE FROM career_skill_gaps
                WHERE project_id = :project_id
                  AND occupation_id = :occupation_id
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        db.session.commit()

        cursor_result = cast(
            CursorResult[Any],
            result
        )

        return cursor_result.rowcount or 0