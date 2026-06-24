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
    def get_career_summary(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT *
                FROM llm_summaries
                WHERE project_id = :project_id
                  AND occupation_id = :occupation_id
                  AND summary_type = 'career_summary'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        row = result.fetchone()

        return (
            dict(cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def get_course_summary(
        project_id,
        occupation_id,
        course_id
    ):
        result = db.session.execute(
            text("""
                SELECT *
                FROM llm_summaries
                WHERE project_id = :project_id
                  AND occupation_id = :occupation_id
                  AND course_id = :course_id
                  AND summary_type = 'course_summary'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
                "course_id": course_id,
            }
        )

        row = result.fetchone()

        return (
            dict(cast(Any, row._mapping))
            if row else None
        )

    @staticmethod
    def get_course_summaries(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT *
                FROM llm_summaries
                WHERE project_id = :project_id
                  AND occupation_id = :occupation_id
                  AND summary_type = 'course_summary'
                ORDER BY created_at DESC
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def delete_by_project_id(project_id):
        result = db.session.execute(
            text("""
                DELETE FROM llm_summaries
                WHERE project_id = :project_id
                RETURNING id
            """),
            {"project_id": project_id}
        )

        deleted_rows = result.fetchall()
        db.session.commit()

        return len(deleted_rows)