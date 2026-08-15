from sqlalchemy import text

from config.database import db


class CourseModuleRepository:
    @staticmethod
    def get_by_course_id(course_id):
        """One course's syllabus, in the order the corpus states it.

        ``module_number`` is the corpus's own numbering, so ordering by it is
        ordering by the sequence a learner actually takes the modules in —
        ``created_at`` would only reflect the order the loader happened to write
        them, which a re-run is free to change.
        """
        result = db.session.execute(
            text("""
                SELECT
                    cm.module_id,
                    cm.course_id,
                    cm.module_number,
                    cm.title,
                    cm.objective,
                    cm.observable_evidence,
                    cm.topics,
                    cm.section_code
                FROM course_modules cm
                WHERE cm.course_id = :course_id
                ORDER BY cm.module_number
            """),
            {"course_id": course_id},
        )

        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_by_course_code(course_code):
        """Same, addressed by the corpus code rather than the internal uuid."""
        result = db.session.execute(
            text("""
                SELECT
                    cm.module_id,
                    cm.course_id,
                    cm.module_number,
                    cm.title,
                    cm.objective,
                    cm.observable_evidence,
                    cm.topics,
                    cm.section_code
                FROM course_modules cm
                JOIN courses c
                    ON c.course_id = cm.course_id
                WHERE c.course_code = :course_code
                ORDER BY cm.module_number
            """),
            {"course_code": course_code},
        )

        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_for_course_ids(course_ids):
        """Modules for several courses at once, grouped by ``course_id``.

        The recommendation views render a handful of courses together, and one
        query beats one per course against a cross-region database where the
        round trip, not the row count, is the cost.
        """
        if not course_ids:
            return {}

        result = db.session.execute(
            text("""
                SELECT
                    cm.course_id,
                    cm.module_number,
                    cm.title,
                    cm.objective,
                    cm.observable_evidence,
                    cm.topics,
                    cm.section_code
                FROM course_modules cm
                WHERE cm.course_id = ANY(:course_ids)
                ORDER BY cm.course_id, cm.module_number
            """),
            {"course_ids": list(course_ids)},
        )

        grouped = {}

        for row in result:
            module = dict(row._mapping)
            grouped.setdefault(module["course_id"], []).append(module)

        return grouped
