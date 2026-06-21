from sqlalchemy import text

from config.database import db


class CourseSkillRepository:

    @staticmethod
    def get_by_course_id(course_id):
        result = db.session.execute(
            text("""
                SELECT
                    cs.course_skill_id,
                    cs.course_id,
                    cs.skill_id,
                    s.skill_name,
                    cs.coverage_weight
                FROM course_skills cs
                JOIN skills s
                    ON s.skill_id = cs.skill_id
                WHERE cs.course_id = :course_id
            """),
            {"course_id": course_id}
        )

        return [
            dict(row._mapping)
            for row in result
        ]

    @staticmethod
    def get_by_skill_id(skill_id):
        result = db.session.execute(
            text("""
                SELECT
                    cs.course_id,
                    c.course_name,
                    cs.skill_id,
                    cs.coverage_weight
                FROM course_skills cs
                JOIN courses c
                    ON c.course_id = cs.course_id
                WHERE cs.skill_id = :skill_id
                  AND c.is_active = TRUE
            """),
            {"skill_id": skill_id}
        )

        return [
            dict(row._mapping)
            for row in result
        ]