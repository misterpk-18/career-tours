from dataclasses import asdict
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.project import Project


class ProjectRepository:

    @staticmethod
    def create(project):
        project_data = {
            "student_id": None,
            "project_name": None,
            "description": None,
            "status": "active"
        }
        project_data.update(project)

        result = db.session.execute(
            text("""
                INSERT INTO projects (
                    student_id,
                    project_name,
                    description,
                    status
                )
                VALUES (
                    :student_id,
                    :project_name,
                    :description,
                    :status
                )
                RETURNING *
            """),
            project_data
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create project")

        return Project(**cast(Any, row._mapping))

    @staticmethod
    def get_by_id(project_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        row = result.fetchone()

        return (
            Project(**cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def get_by_student_id(student_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                WHERE student_id = :student_id
                ORDER BY created_at DESC
            """),
            {"student_id": student_id}
        )

        return [
            Project(**cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                ORDER BY created_at DESC
            """)
        )

        return [
            Project(**cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def update(project_id, data):
        existing = ProjectRepository.get_by_id(project_id)

        if not existing:
            return None

        existing_data = asdict(existing)

        update_params = {
            **existing_data,
            **data,
            "project_id": project_id
        }

        result = db.session.execute(
            text("""
                UPDATE projects
                SET
                    project_name = :project_name,
                    description = :description,
                    status = :status,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_id = :project_id
                RETURNING *
            """),
            update_params
        )

        row = result.fetchone()
        db.session.commit()

        return (
            Project(**cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def delete(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM projects
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()

        cursor_result = cast(
            CursorResult[Any],
            result
        )

        return (
            cursor_result.rowcount or 0
        ) > 0