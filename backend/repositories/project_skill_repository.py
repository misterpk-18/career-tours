from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class ProjectSkillRepository:
    # Width of project_skills.source; see StudentSkillRepository.SOURCE_MAX_LENGTH.
    SOURCE_MAX_LENGTH = 100

    @staticmethod
    def bulk_create(project_id, skills):
        """Insert every extracted skill. Does NOT commit -- the caller owns the
        transaction so project and student skills land together or not at all."""
        for skill in skills:
            db.session.execute(
                text("""
                    INSERT INTO project_skills (
                        project_id,
                        skill_id,
                        skill_name,
                        proficiency_level,
                        confidence_score,
                        source
                    )
                    VALUES (
                        :project_id,
                        :skill_id,
                        :skill_name,
                        :proficiency_level,
                        :confidence_score,
                        :source
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "project_id": project_id,
                    "skill_id": skill.get("skill_id"),
                    "skill_name": skill.get("skill_name"),
                    "proficiency_level": skill.get("proficiency_level", 5),
                    "confidence_score": skill.get("confidence_score", 1.0),
                    "source": (skill.get("source") or "resume")[
                        : ProjectSkillRepository.SOURCE_MAX_LENGTH
                    ],
                },
            )

    @staticmethod
    def get_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT
                    ps.project_skill_id,
                    ps.project_id,
                    ps.skill_id,
                    COALESCE(s.skill_name, ps.skill_name) AS skill_name,
                    ps.proficiency_level,
                    ps.confidence_score,
                    ps.source,
                    ps.created_at
                FROM project_skills ps
                LEFT JOIN skills s
                    ON s.skill_id = ps.skill_id
                WHERE ps.project_id = :project_id
                ORDER BY skill_name
            """),
            {"project_id": project_id},
        )

        return [dict(cast(Any, row._mapping)) for row in result]

    @staticmethod
    def delete_by_project_id(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM project_skills
                WHERE project_id = :project_id
            """),
            {"project_id": project_id},
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
            {"project_id": project_id},
        )

        return [row.skill_id for row in result]
