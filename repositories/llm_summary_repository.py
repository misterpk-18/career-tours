from typing import Any, cast

from sqlalchemy import text

from config.database import db


class LLMSummaryRepository:

    @staticmethod
    def create(
        student_id,
        project_id,
        summary_type,
        summary_text,
        occupation_id=None,
        course_id=None,
    ):
        result = db.session.execute(
            text("""
                INSERT INTO llm_summaries (
                    student_id,
                    project_id,
                    occupation_id,
                    course_id,
                    summary_type,
                    summary_text
                )
                VALUES (
                    :student_id,
                    :project_id,
                    :occupation_id,
                    :course_id,
                    :summary_type,
                    :summary_text
                )
                RETURNING *
            """),
            {
                "student_id": student_id,
                "project_id": project_id,
                "occupation_id": occupation_id,
                "course_id": course_id,
                "summary_type": summary_type,
                "summary_text": summary_text,
            }
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create LLM summary")

        return dict(cast(Any, row._mapping))

    @staticmethod
    def get_project_summaries(project_id):
        result = db.session.execute(
            text("""
                SELECT *
                FROM llm_summaries
                WHERE project_id = :project_id
                ORDER BY created_at DESC
            """),
            {"project_id": project_id}
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def delete_by_project_id(project_id):
        db.session.execute(
            text("""
                DELETE FROM llm_summaries
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()