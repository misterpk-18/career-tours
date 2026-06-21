from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class ProjectSkillRepository:

    @staticmethod
    def bulk_create(
        project_id,
        skill_ids,
        proficiency_level=5,
        confidence_score=1.0,
        source="resume"
    ):
        for skill_id in skill_ids:
            db.session.execute(
                text("""
                    INSERT INTO project_skills (
                        project_id,
                        skill_id,
                        proficiency_level,
                        confidence_score,
                        source
                    )
                    VALUES (
                        :project_id,
                        :skill_id,
                        :proficiency_level,
                        :confidence_score,
                        :source
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "project_id": project_id,
                    "skill_id": skill_id,
                    "proficiency_level": proficiency_level,
                    "confidence_score": confidence_score,
                    "source": source,
                }
            )

        db.session.commit()

    @staticmethod
    def get_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT
                    ps.project_skill_id,
                    ps.project_id,
                    ps.skill_id,
                    s.skill_name,
                    ps.proficiency_level,
                    ps.confidence_score,
                    ps.source,
                    ps.created_at
                FROM project_skills ps
                JOIN skills s
                    ON s.skill_id = ps.skill_id
                WHERE ps.project_id = :project_id
                ORDER BY s.skill_name
            """),
            {"project_id": project_id}
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def delete_by_project_id(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM project_skills
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0

    @staticmethod
    def get_skill_ids_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT skill_id
                FROM project_skills
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        return [
            row.skill_id
            for row in result
        ]