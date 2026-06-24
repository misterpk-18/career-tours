from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


class CourseRecommendationRepository:

    @staticmethod
    def bulk_create(
        student_id,
        project_id,
        occupation_id,
        recommendations
    ):
        for recommendation in recommendations:
            db.session.execute(
                text("""
                    INSERT INTO course_recommendations (
                        student_id,
                        project_id,
                        occupation_id,
                        course_id,
                        coverage_percentage,
                        recommendation_rank
                    )
                    VALUES (
                        :student_id,
                        :project_id,
                        :occupation_id,
                        :course_id,
                        :coverage_percentage,
                        :recommendation_rank
                    )
                    ON CONFLICT (
                        project_id,
                        occupation_id,
                        course_id
                    )
                    DO UPDATE SET
                        coverage_percentage =
                            EXCLUDED.coverage_percentage,
                        recommendation_rank =
                            EXCLUDED.recommendation_rank
                """),
                {
                    "student_id": student_id,
                    "project_id": project_id,
                    "occupation_id": occupation_id,
                    "course_id": recommendation["course_id"],
                    "coverage_percentage":
                        recommendation["coverage_percentage"],
                    "recommendation_rank":
                        recommendation["rank"],
                }
            )

        db.session.commit()

    @staticmethod
    def get_by_project_id(project_id):
        result = db.session.execute(
            text("""
                SELECT
                    cr.recommendation_id,
                    cr.student_id,
                    cr.project_id,
                    cr.occupation_id,
                    cr.course_id,
                    c.course_name,
                    c.description,
                    c.duration_hours,
                    c.level,
                    cr.coverage_percentage,
                    cr.recommendation_rank,
                    cr.created_at
                FROM course_recommendations cr
                JOIN courses c
                    ON c.course_id = cr.course_id
                WHERE cr.project_id = :project_id
                ORDER BY
                    cr.occupation_id,
                    cr.recommendation_rank
            """),
            {"project_id": project_id}
        )

        return [
            dict(cast(Any, row._mapping))
            for row in result
        ]

    @staticmethod
    def get_by_project_and_occupation(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    cr.recommendation_id,
                    cr.student_id,
                    cr.project_id,
                    cr.occupation_id,
                    cr.course_id,
                    c.course_name,
                    c.description,
                    c.duration_hours,
                    c.level,
                    cr.coverage_percentage,
                    cr.recommendation_rank,
                    cr.created_at
                FROM course_recommendations cr
                JOIN courses c
                    ON c.course_id = cr.course_id
                WHERE cr.project_id = :project_id
                  AND cr.occupation_id = :occupation_id
                ORDER BY cr.recommendation_rank
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
    def get_by_occupation_id(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                SELECT
                    cr.recommendation_id,
                    cr.student_id,
                    cr.project_id,
                    cr.occupation_id,
                    cr.course_id,
                    c.course_name,
                    c.description,
                    c.duration_hours,
                    c.level,
                    cr.coverage_percentage,
                    cr.recommendation_rank,
                    cr.created_at
                FROM course_recommendations cr
                JOIN courses c
                    ON c.course_id = cr.course_id
                WHERE cr.project_id = :project_id
                  AND cr.occupation_id = :occupation_id
                ORDER BY cr.recommendation_rank
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
                DELETE FROM course_recommendations
                WHERE project_id = :project_id
            """),
            {"project_id": project_id}
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0

    @staticmethod
    def delete_by_occupation_id(
        project_id,
        occupation_id
    ):
        result = db.session.execute(
            text("""
                DELETE FROM course_recommendations
                WHERE project_id = :project_id
                  AND occupation_id = :occupation_id
            """),
            {
                "project_id": project_id,
                "occupation_id": occupation_id,
            }
        )

        db.session.commit()

        cursor_result = cast(CursorResult[Any], result)
        return cursor_result.rowcount or 0