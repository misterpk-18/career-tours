from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class CourseRepository:

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM courses
                WHERE is_active = TRUE
                ORDER BY course_name
            """)
        )

        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_by_id(course_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM courses
                WHERE course_id = :course_id
            """),
            {"course_id": course_id}
        )

        row = result.fetchone()
        return dict(row._mapping) if row else None

    @staticmethod
    def create(
        course_name,
        description=None,
        duration_hours=None,
        level=None
    ):
        result = db.session.execute(
            text("""
                INSERT INTO courses (
                    course_name,
                    description,
                    duration_hours,
                    level
                )
                VALUES (
                    :course_name,
                    :description,
                    :duration_hours,
                    :level
                )
                RETURNING *
            """),
            {
                "course_name": course_name,
                "description": description,
                "duration_hours": duration_hours,
                "level": level
            }
        )

        db.session.commit()

        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create course")

        return dict(row._mapping)

    @staticmethod
    def delete(course_id):
        result = db.session.execute(
            text("""
                DELETE FROM courses
                WHERE course_id = :course_id
            """),
            {"course_id": course_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0

    @staticmethod
    def get_skills(course_id):
        result = db.session.execute(
            text("""
                SELECT
                    s.skill_id,
                    s.skill_name,
                    cs.coverage_weight
                FROM course_skills cs
                JOIN skills s
                    ON s.skill_id = cs.skill_id
                WHERE cs.course_id = :course_id
            """),
            {"course_id": course_id}
        )

        return [dict(row._mapping) for row in result]