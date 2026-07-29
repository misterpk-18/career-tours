from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class StudentSkillRepository:
    # Width of student_skills.source. The LLM writes a free-text provenance note
    # there, and an over-long one used to abort the whole extraction, so clip it to
    # what the column accepts -- the value is descriptive, never matched on.
    SOURCE_MAX_LENGTH = 100

    @staticmethod
    def _clip_source(source):
        if isinstance(source, str):
            return source[: StudentSkillRepository.SOURCE_MAX_LENGTH]
        return source

    @staticmethod
    def create(student_id, skill_id, proficiency_level, confidence_score, source):
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
                "source": StudentSkillRepository._clip_source(source),
            },
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create student skill")

        return dict(row._mapping)

    @staticmethod
    def bulk_create(student_id, skills):
        """Insert catalog-matched skills. Does NOT commit -- the caller owns the
        transaction, so a failure here cannot leave project_skills already written
        with student_skills missing."""
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
                    "source": StudentSkillRepository._clip_source(skill["source"]),
                },
            )

    @staticmethod
    def get_by_student_id(student_id):
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
            {"student_id": student_id},
        )

        return [dict(row._mapping) for row in result]

    @staticmethod
    def delete(student_id, skill_id):
        result = db.session.execute(
            text("""
                DELETE FROM student_skills
                WHERE student_id = :student_id
                  AND skill_id = :skill_id
            """),
            {"student_id": student_id, "skill_id": skill_id},
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0

    @staticmethod
    def delete_all_by_student(student_id):
        result = db.session.execute(
            text("""
                DELETE FROM student_skills
                WHERE student_id = :student_id
            """),
            {"student_id": student_id},
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0
