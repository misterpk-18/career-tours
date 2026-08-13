from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class ProjectSkillRepository:
    # Width of project_skills.source; see StudentSkillRepository.SOURCE_MAX_LENGTH.
    SOURCE_MAX_LENGTH = 100

    @staticmethod
    def bulk_create(project_id, skills):
        """Upsert every extracted skill. Does NOT commit -- the caller owns the
        transaction so project and student skills land together or not at all.

        The conflict target is the partial unique index added in
        migrations/008_project_skills_unique_name.sql. Before that index existed
        this said a bare `ON CONFLICT DO NOTHING`, which could never fire —
        project_skills had no unique constraint but its primary key on a
        generated id — so every re-extraction appended a duplicate set.

        DO UPDATE rather than DO NOTHING: the only way to reach a second
        extraction for a project is `{"force": true}`, which means the caller
        deliberately asked for a fresh reading. Keeping the stale proficiency
        would ignore what they asked for.
        """
        if not skills:
            return

        # Two reasons this is deduplicated before it is sent. Postgres refuses to
        # let ON CONFLICT DO UPDATE touch the same row twice in one statement, so
        # a name repeated within this batch would abort the whole insert. And the
        # LLM does return the same skill under two casings often enough to matter
        # -- which is exactly why the index is on lower(skill_name).
        deduplicated = {}
        for skill in skills:
            name = skill.get("skill_name")
            if not name:
                continue
            deduplicated[name.lower()] = skill

        if not deduplicated:
            return

        values = []
        params = {"project_id": project_id}

        for index, skill in enumerate(deduplicated.values()):
            values.append(
                f"(:project_id, :skill_id_{index}, :skill_name_{index}, "
                f":proficiency_level_{index}, :confidence_score_{index}, :source_{index})"
            )
            params[f"skill_id_{index}"] = skill.get("skill_id")
            params[f"skill_name_{index}"] = skill.get("skill_name")
            params[f"proficiency_level_{index}"] = skill.get("proficiency_level", 5)
            params[f"confidence_score_{index}"] = skill.get("confidence_score", 1.0)
            params[f"source_{index}"] = (skill.get("source") or "resume")[
                : ProjectSkillRepository.SOURCE_MAX_LENGTH
            ]

        db.session.execute(
            text(f"""
                INSERT INTO project_skills (
                    project_id,
                    skill_id,
                    skill_name,
                    proficiency_level,
                    confidence_score,
                    source
                )
                VALUES {", ".join(values)}
                ON CONFLICT (project_id, lower(skill_name)) WHERE skill_name IS NOT NULL
                DO UPDATE SET
                    skill_id = COALESCE(EXCLUDED.skill_id, project_skills.skill_id),
                    skill_name = EXCLUDED.skill_name,
                    proficiency_level = EXCLUDED.proficiency_level,
                    confidence_score = EXCLUDED.confidence_score,
                    source = EXCLUDED.source
            """),
            params,
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
