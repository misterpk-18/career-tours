from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.student import Student


class StudentRepository:

    @staticmethod
    def create(student):
        result = db.session.execute(
            text("""
                INSERT INTO students (
                    full_name,
                    email,
                    phone,
                    college_name,
                    degree_name,
                    branch_name,
                    current_year_semester,
                    graduation_year,
                    preferred_job_location,
                    target_role,
                    career_interest,
                    learning_hours_per_week,
                    internship_preference,
                    work_mode_preference
                )
                VALUES (
                    :full_name,
                    :email,
                    :phone,
                    :college_name,
                    :degree_name,
                    :branch_name,
                    :current_year_semester,
                    :graduation_year,
                    :preferred_job_location,
                    :target_role,
                    :career_interest,
                    :learning_hours_per_week,
                    :internship_preference,
                    :work_mode_preference
                )
                RETURNING *
            """),
            student
        )

        db.session.commit()

        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create student")

        return Student(**row._mapping)

    @staticmethod
    def get_by_id(student_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                WHERE student_id = :student_id
            """),
            {"student_id": student_id}
        )

        row = result.fetchone()
        return Student(**row._mapping) if row else None

    @staticmethod
    def get_by_email(email):
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                WHERE email = :email
            """),
            {"email": email}
        )

        row = result.fetchone()
        return Student(**row._mapping) if row else None

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                ORDER BY created_at DESC
            """)
        )

        return [Student(**row._mapping) for row in result]

    @staticmethod
    def update(student_id, data):
        result = db.session.execute(
            text("""
                UPDATE students
                SET
                    full_name = :full_name,
                    phone = :phone,
                    college_name = :college_name,
                    degree_name = :degree_name,
                    branch_name = :branch_name,
                    current_year_semester = :current_year_semester,
                    graduation_year = :graduation_year,
                    preferred_job_location = :preferred_job_location,
                    target_role = :target_role,
                    career_interest = :career_interest,
                    learning_hours_per_week = :learning_hours_per_week,
                    internship_preference = :internship_preference,
                    work_mode_preference = :work_mode_preference,
                    updated_at = CURRENT_TIMESTAMP
                WHERE student_id = :student_id
                RETURNING *
            """),
            {
                **data,
                "student_id": student_id
            }
        )

        db.session.commit()

        row = result.fetchone()
        return Student(**row._mapping) if row else None

    @staticmethod
    def delete(student_id):
        result = db.session.execute(
            text("""
                DELETE FROM students
                WHERE student_id = :student_id
            """),
            {"student_id": student_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0