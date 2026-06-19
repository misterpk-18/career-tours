from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.skill import Skill


class SkillRepository:

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT
                    skill_id,
                    skill_name,
                    skill_category,
                    description,
                    created_at
                FROM skills
                ORDER BY skill_name
            """)
        )

        return [Skill(**row._mapping) for row in result]

    @staticmethod
    def get_by_id(skill_id):
        result = db.session.execute(
            text("""
                SELECT
                    skill_id,
                    skill_name,
                    skill_category,
                    description,
                    created_at
                FROM skills
                WHERE skill_id = :skill_id
            """),
            {"skill_id": skill_id}
        )

        row = result.fetchone()
        return Skill(**row._mapping) if row else None

    @staticmethod
    def get_by_name(skill_name):
        result = db.session.execute(
            text("""
                SELECT
                    skill_id,
                    skill_name,
                    skill_category,
                    description,
                    created_at
                FROM skills
                WHERE LOWER(skill_name) = LOWER(:skill_name)
            """),
            {"skill_name": skill_name}
        )

        row = result.fetchone()
        return Skill(**row._mapping) if row else None

    @staticmethod
    def create(skill_name, skill_category=None, description=None):
        result = db.session.execute(
            text("""
                INSERT INTO skills (
                    skill_name,
                    skill_category,
                    description
                )
                VALUES (
                    :skill_name,
                    :skill_category,
                    :description
                )
                RETURNING
                    skill_id,
                    skill_name,
                    skill_category,
                    description,
                    created_at
            """),
            {
                "skill_name": skill_name,
                "skill_category": skill_category,
                "description": description
            }
        )

        db.session.commit()

        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create skill")

        return Skill(**row._mapping)

    @staticmethod
    def delete(skill_id):
        result = db.session.execute(
            text("""
                DELETE FROM skills
                WHERE skill_id = :skill_id
            """),
            {"skill_id": skill_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0