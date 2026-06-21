from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class StudentSkillRepository:

    @staticmethod
    def create(
        student_id,
        skill_id,
        proficiency_level,
        confidence_score,
        source
    ):
        result = db.session.execute(
            text("""
                INSERT INTO student_skills (
                    student_id,
                    skill_id,
                    proficiency_level,
                    confidence_score,
                    source
                )
                VALUES (
                    :student_id,
                    :skill_id,
                    :proficiency_level,
                    :confidence_score,
                    :source
                )
                RETURNING *
            """),
            {
                "student_id": student_id,
                "skill_id": skill_id,
                "proficiency_level": proficiency_level,
                "confidence_score": confidence_score,
                "source": source
            }
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create student skill")

        return dict(row._mapping)

    @staticmethod
    def bulk_create(
        student_id,
        skills
    ):
        for skill in skills:
            db.session.execute(
                text("""
                    INSERT INTO student_skills (
                        student_id,
                        skill_id,
                        proficiency_level,
                        confidence_score,
                        source
                    )
                    VALUES (
                        :student_id,
                        :skill_id,
                        :proficiency_level,
                        :confidence_score,
                        :source
                    )
                    ON CONFLICT (
                        student_id,
                        skill_id
                    )
                    DO UPDATE SET
                        proficiency_level = EXCLUDED.proficiency_level,
                        confidence_score = EXCLUDED.confidence_score,
                        source = EXCLUDED.source
                """),
                {
                    "student_id": student_id,
                    "skill_id": skill["skill_id"],
                    "proficiency_level": skill["proficiency_level"],
                    "confidence_score": skill["confidence_score"],
                    "source": skill["source"]
                }
            )

        db.session.commit()

    @staticmethod
    def get_by_student_id(
        student_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    ss.student_skill_id,
                    ss.student_id,
                    ss.skill_id,
                    s.skill_name,
                    ss.proficiency_level,
                    ss.confidence_score,
                    ss.source,
                    ss.created_at
                FROM student_skills ss
                JOIN skills s
                    ON s.skill_id = ss.skill_id
                WHERE ss.student_id = :student_id
                ORDER BY s.skill_name
            """),
            {
                "student_id": student_id
            }
        )

        return [
            dict(row._mapping)
            for row in result
        ]

    @staticmethod
    def delete(
        student_id,
        skill_id
    ):
        result = db.session.execute(
            text("""
                DELETE FROM student_skills
                WHERE student_id = :student_id
                  AND skill_id = :skill_id
            """),
            {
                "student_id": student_id,
                "skill_id": skill_id
            }
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0

    @staticmethod
    def delete_all_by_student(
        student_id
    ):
        result = db.session.execute(
            text("""
                DELETE FROM student_skills
                WHERE student_id = :student_id
            """),
            {
                "student_id": student_id
            }
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0