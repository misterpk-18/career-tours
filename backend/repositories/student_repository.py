from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.student import Student


class StudentRepository:
    # The registration and profile forms post every field they render, so fields the
    # user left blank arrive as "" rather than being absent. They have to be stored
    # as NULL: `phone` carries a UNIQUE constraint, and Postgres treats "" as an
    # ordinary value (only NULLs are mutually distinct), so the second student to
    # submit an empty phone would collide with the first. The same applies to the
    # columns with CHECK constraints, which "" does not satisfy.
    NULLABLE_TEXT_FIELDS = (
        "phone",
        "college_name",
        "degree_name",
        "branch_name",
        "preferred_job_location",
        "target_role",
        "career_interest",
        "internship_preference",
        "work_mode_preference",
    )

    @staticmethod
    def _blank_to_none(params):
        for field in StudentRepository.NULLABLE_TEXT_FIELDS:
            value = params.get(field)
            if isinstance(value, str) and not value.strip():
                params[field] = None
        return params

    @staticmethod
    def create(student):
        # Provide default None values for all optional fields to prevent bind parameter errors
        student_data = {
            "full_name": None,
            "email": None,
            "password_hash": None,
            "phone": None,
            "college_name": None,
            "degree_name": None,
            "branch_name": None,
            "current_year_semester": None,
            "graduation_year": None,
            "preferred_job_location": None,
            "target_role": None,
            "career_interest": None,
            "learning_hours_per_week": None,
            "internship_preference": None,
            "work_mode_preference": None,
        }
        student_data.update(student)
        StudentRepository._blank_to_none(student_data)

        # Hash password if provided in input
        if "password" in student:
            from werkzeug.security import generate_password_hash

            student_data["password_hash"] = generate_password_hash(student["password"])

        result = db.session.execute(
            text("""
                INSERT INTO students (
                    full_name,
                    email,
                    password_hash,
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
                    :password_hash,
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
            student_data,
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create student")

        return Student(**cast(Any, row._mapping))

    @staticmethod
    def get_by_id(student_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                WHERE student_id = :student_id
            """),
            {"student_id": student_id},
        )

        row = result.fetchone()
        return Student(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def get_by_email(email):
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                WHERE email = :email
            """),
            {"email": email},
        )

        row = result.fetchone()
        return Student(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def get_by_phone(phone):
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                WHERE phone = :phone
            """),
            {"phone": phone},
        )

        row = result.fetchone()
        return Student(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM students
                ORDER BY created_at DESC
            """)
        )

        return [Student(**cast(Any, row._mapping)) for row in result]

    @staticmethod
    def update(student_id, data):
        existing = StudentRepository.get_by_id(student_id)
        if not existing:
            return None

        # Convert the existing student dataclass to a dictionary
        from dataclasses import asdict

        existing_data = asdict(existing)

        # Merge with updated fields to ensure all bind parameters are populated
        update_params = StudentRepository._blank_to_none(
            {**existing_data, **data, "student_id": student_id}
        )

        # Hash password if provided in update data
        if "password" in data:
            from werkzeug.security import generate_password_hash

            update_params["password_hash"] = generate_password_hash(data["password"])

        result = db.session.execute(
            text("""
                UPDATE students
                SET
                    full_name = :full_name,
                    email = :email,
                    password_hash = :password_hash,
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
            update_params,
        )

        row = result.fetchone()
        db.session.commit()

        return Student(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def delete(student_id):
        result = db.session.execute(
            text("""
                DELETE FROM students
                WHERE student_id = :student_id
            """),
            {"student_id": student_id},
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return (cursor_result.rowcount or 0) > 0
