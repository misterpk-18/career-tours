from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.resume import Resume


class ResumeRepository:

    @staticmethod
    def create(
        student_id,
        file_url,
        raw_text=None
    ):
        result = db.session.execute(
            text("""
                INSERT INTO resumes (
                    student_id,
                    file_url,
                    raw_text,
                    parsed_at
                )
                VALUES (
                    :student_id,
                    :file_url,
                    :raw_text,
                    CURRENT_TIMESTAMP
                )
                RETURNING *
            """),
            {
                "student_id": student_id,
                "file_url": file_url,
                "raw_text": raw_text
            }
        )

        db.session.commit()

        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create resume")

        return Resume(**row._mapping)

    @staticmethod
    def get_by_id(resume_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM resumes
                WHERE resume_id = :resume_id
            """),
            {"resume_id": resume_id}
        )

        row = result.fetchone()
        return Resume(**row._mapping) if row else None

    @staticmethod
    def get_by_student_id(student_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM resumes
                WHERE student_id = :student_id
                ORDER BY created_at DESC
            """),
            {"student_id": student_id}
        )

        return [
            Resume(**row._mapping)
            for row in result
        ]

    @staticmethod
    def update_raw_text(
        resume_id,
        raw_text
    ):
        result = db.session.execute(
            text("""
                UPDATE resumes
                SET
                    raw_text = :raw_text,
                    parsed_at = CURRENT_TIMESTAMP
                WHERE resume_id = :resume_id
                RETURNING *
            """),
            {
                "resume_id": resume_id,
                "raw_text": raw_text
            }
        )

        db.session.commit()

        row = result.fetchone()
        return Resume(**row._mapping) if row else None

    @staticmethod
    def delete(resume_id):
        result = db.session.execute(
            text("""
                DELETE FROM resumes
                WHERE resume_id = :resume_id
            """),
            {"resume_id": resume_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0