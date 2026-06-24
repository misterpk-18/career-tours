from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class CareerMatchRepository:

    @staticmethod
    def bulk_create(
        student_id,
        project_id,
        recommendations
    ):
        for recommendation in recommendations:
            db.session.execute(
                text("""
                    INSERT INTO student_career_matches (
                        student_id,
                        project_id,
                        occupation_id,
                        match_percentage,
                        rank_position
                    )
                    VALUES (
                        :student_id,
                        :project_id,
                        :occupation_id,
                        :match_percentage,
                        :rank_position
                    )
                    ON CONFLICT (
                        project_id,
                        occupation_id
                    )
                    DO UPDATE SET
                        match_percentage = EXCLUDED.match_percentage,
                        rank_position = EXCLUDED.rank_position,
                        generated_at = CURRENT_TIMESTAMP
                """),
                {
                    "student_id": student_id,
                    "project_id": project_id,
                    "occupation_id": recommendation["occupation_id"],
                    "match_percentage": recommendation["score"],
                    "rank_position": recommendation["rank"],
                }
            )

        db.session.commit()

    @staticmethod
    def get_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT
                    scm.match_id,
                    scm.student_id,
                    scm.project_id,
                    scm.occupation_id,
                    o.occupation_name,
                    o.description,
                    o.average_salary,
                    o.growth_outlook,
                    scm.match_percentage,
                    scm.rank_position,
                    scm.generated_at
                FROM student_career_matches scm
                JOIN occupations o
                    ON o.occupation_id = scm.occupation_id
                WHERE scm.project_id = :project_id
                ORDER BY scm.rank_position
            """),
            {"project_id": project_id}
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def get_by_project_and_occupation(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    scm.match_id,
                    scm.student_id,
                    scm.project_id,
                    scm.occupation_id,
                    o.occupation_name,
                    o.description,
                    o.average_salary,
                    o.growth_outlook,
                    scm.match_percentage,
                    scm.rank_position,
                    scm.generated_at
                FROM student_career_matches scm
                JOIN occupations o
                    ON o.occupation_id = scm.occupation_id
                WHERE scm.project_id = :project_id
                  AND scm.occupation_id = :occupation_id
                LIMIT 1
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        row = result.fetchone()

        return (
            dict(cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def get_by_match_id(match_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM student_career_matches
                WHERE match_id = :match_id
            """),
            {"match_id": match_id}
        )

        row = result.fetchone()

        return (
            dict(cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def delete_by_project_id(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM student_career_matches
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0