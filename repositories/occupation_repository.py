from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class OccupationRepository:

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM occupations
                ORDER BY occupation_name
            """)
        )

        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_by_id(occupation_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM occupations
                WHERE occupation_id = :occupation_id
            """),
            {"occupation_id": occupation_id}
        )

        row = result.fetchone()
        return dict(row._mapping) if row else None

    @staticmethod
    def create(
        occupation_name,
        description=None,
        average_salary=None,
        growth_outlook=None
    ):
        result = db.session.execute(
            text("""
                INSERT INTO occupations (
                    occupation_name,
                    description,
                    average_salary,
                    growth_outlook
                )
                VALUES (
                    :occupation_name,
                    :description,
                    :average_salary,
                    :growth_outlook
                )
                RETURNING *
            """),
            {
                "occupation_name": occupation_name,
                "description": description,
                "average_salary": average_salary,
                "growth_outlook": growth_outlook
            }
        )

        db.session.commit()

        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create occupation")

        return dict(row._mapping)

    @staticmethod
    def delete(occupation_id):
        result = db.session.execute(
            text("""
                DELETE FROM occupations
                WHERE occupation_id = :occupation_id
            """),
            {"occupation_id": occupation_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0

    @staticmethod
    def get_skills(occupation_id):
        result = db.session.execute(
            text("""
                SELECT
                    s.skill_id,
                    s.skill_name,
                    os.weight
                FROM occupation_skills os
                JOIN skills s
                    ON s.skill_id = os.skill_id
                WHERE os.occupation_id = :occupation_id
            """),
            {"occupation_id": occupation_id}
        )

        return [dict(row._mapping) for row in result]