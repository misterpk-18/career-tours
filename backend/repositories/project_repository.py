from dataclasses import asdict
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db
from models.project import Project


class ProjectRepository:
    @staticmethod
    def create(project):
        project_data = {"student_id": None, "project_name": None, "description": None, "status": "active"}
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
            project_data,
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create project")

        return Project(**cast(Any, row._mapping))

    @staticmethod
    def get_by_id(project_id):
        # Soft-deleted projects are invisible everywhere: this is what every
        # project-scoped route resolves through (via owned_project), so a
        # deleted project 404s on its pages and cannot start a sitting, exactly
        # as if it were gone — while its rows stay in the database.
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                WHERE project_id = :project_id
                  AND deleted_at IS NULL
            """),
            {"project_id": project_id},
        )

        row = result.fetchone()

        return Project(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def active_name_exists(student_id, project_name, exclude_project_id=None):
        """Whether this student already has an ACTIVE project with this exact
        name. Soft-deleted projects don't count, so a deleted name is reusable.
        ``exclude_project_id`` lets a rename skip the project being renamed.
        """
        result = db.session.execute(
            text("""
                SELECT 1
                FROM projects
                WHERE student_id = :student_id
                  AND project_name = :project_name
                  AND deleted_at IS NULL
                  AND (CAST(:exclude AS uuid) IS NULL
                       OR project_id <> CAST(:exclude AS uuid))
                LIMIT 1
            """),
            {
                "student_id": student_id,
                "project_name": project_name,
                "exclude": exclude_project_id,
            },
        )
        return result.first() is not None

    @staticmethod
    def get_by_student_id(student_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                WHERE student_id = :student_id
                  AND deleted_at IS NULL
                ORDER BY created_at DESC
            """),
            {"student_id": student_id},
        )

        return [Project(**cast(Any, row._mapping)) for row in result]

    @staticmethod
    def get_all():
        result = db.session.execute(
            text("""
                SELECT *
                FROM projects
                ORDER BY created_at DESC
            """)
        )

        return [Project(**cast(Any, row._mapping)) for row in result]

    @staticmethod
    def update(project_id, data):
        existing = ProjectRepository.get_by_id(project_id)

        if not existing:
            return None

        existing_data = asdict(existing)

        update_params = {**existing_data, **data, "project_id": project_id}

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
            update_params,
        )

        row = result.fetchone()
        db.session.commit()

        return Project(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def set_resume_id(project_id, resume_id):
        result = db.session.execute(
            text("""
                UPDATE projects
                SET
                    resume_id = :resume_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_id = :project_id
                RETURNING *
            """),
            {"project_id": project_id, "resume_id": resume_id},
        )

        row = result.fetchone()
        db.session.commit()

        return Project(**cast(Any, row._mapping)) if row else None

    @staticmethod
    def soft_delete(project_id):
        """Hide a project without destroying it or anything that cascades off it.

        Stamps deleted_at so every read through get_by_id / get_by_student_id
        stops returning it. Guarded on ``deleted_at IS NULL`` so deleting an
        already-deleted project reports "not found" rather than silently
        re-stamping. The sittings, scores and recommendations stay in place.
        """
        result = db.session.execute(
            text("""
                UPDATE projects
                SET deleted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_id = :project_id
                  AND deleted_at IS NULL
            """),
            {"project_id": project_id},
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)

        return (cursor_result.rowcount or 0) > 0

    @staticmethod
    def delete(project_id):
        """HARD delete — removes the row and cascades to sittings, scores and
        recommendations. Not reachable from the API, which soft-deletes; kept
        for admin/scripts that genuinely need to purge.
        """
        result = db.session.execute(
            text("""
                DELETE FROM projects
                WHERE project_id = :project_id
            """),
            {"project_id": project_id},
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)

        return (cursor_result.rowcount or 0) > 0
