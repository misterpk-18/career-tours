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
        """Upsert catalog-matched skills in one statement. Does NOT commit -- the
        caller owns the transaction, so a failure here cannot leave project_skills
        already written with student_skills missing.

        This was a loop of single-row inserts, which cost one network round trip
        per skill. With Postgres in a different region from the function that is
        ~65ms each, so a 19-skill resume spent over a second here — on the
        *cached* extract-skills path, which is supposed to be a read.

        Note that passing a list of parameter dicts would not fix it: psycopg2
        implements executemany as a loop of statements, so the round trips remain.
        The VALUES list has to be built into the SQL.
        """
        if not skills:
            return

        # Postgres refuses to let ON CONFLICT DO UPDATE touch the same row twice
        # in one statement ("cannot affect row a second time"), so a skill_id
        # repeated within this batch would abort the whole insert where the old
        # loop quietly upserted it twice. Duplicates do occur — the frontend
        # carries a deduplicateSkills helper for the same reason. Last one wins,
        # which is what the sequential upserts effectively did.
        deduplicated = {}
        for skill in skills:
            deduplicated[skill["skill_id"]] = skill

        values = []
        params = {"student_id": student_id}

        for index, skill in enumerate(deduplicated.values()):
            values.append(
                f"(:student_id, :skill_id_{index}, :proficiency_level_{index}, "
                f":confidence_score_{index}, :source_{index})"
            )
            params[f"skill_id_{index}"] = skill["skill_id"]
            params[f"proficiency_level_{index}"] = skill["proficiency_level"]
            params[f"confidence_score_{index}"] = skill["confidence_score"]
            params[f"source_{index}"] = StudentSkillRepository._clip_source(
                skill["source"]
            )

        db.session.execute(
            text(f"""
                INSERT INTO student_skills (
                    student_id,
                    skill_id,
                    proficiency_level,
                    confidence_score,
                    source
                )
                VALUES {", ".join(values)}
                ON CONFLICT (
                    student_id,
                    skill_id
                )
                DO UPDATE SET
                    proficiency_level = EXCLUDED.proficiency_level,
                    confidence_score = EXCLUDED.confidence_score,
                    source = EXCLUDED.source
            """),
            params,
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
