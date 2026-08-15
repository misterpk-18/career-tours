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

    @staticmethod
    def get_syllabus_for_course_ids(course_ids):
        """Sections with their modules nested, grouped by ``course_id``.

        This is the shape the course views render: four sections per course,
        each carrying its assessment weight and the two modules it owns. It is
        one query rather than one per course and one per section, for the same
        cross-region round-trip reason as ``get_for_course_ids`` — the join
        repeats the section columns across two rows, which is cheaper than the
        trip that would avoid the repetition.

        ``objective`` is left out for the same reason it is not rendered: it is
        the comma-joined form of ``topics``, so shipping both sends every
        module's content twice.

        Three stored section columns are deliberately left out.
        ``competency`` and ``completion_evidence`` are the section's own modules'
        objective and evidence lines joined with "; " — identical for all 160
        sections — so selecting them would ship every module's text a second
        time. ``remediation`` is real content but nothing renders it yet, and
        together the three were 29% of the course-list response. They stay in
        the table; add them back here when something reads them.

        A module whose section is missing is still returned, under a ``None``
        section key, so a corpus gap shows up as an ungrouped module rather
        than a silently absent one.
        """
        if not course_ids:
            return {}

        result = db.session.execute(
            text("""
                SELECT
                    cm.course_id,
                    cm.section_code,
                    cs.module_from,
                    cs.module_to,
                    cs.weight_pct,
                    cs.assessment,
                    cm.module_number,
                    cm.title,
                    cm.observable_evidence,
                    cm.topics
                FROM course_modules cm
                LEFT JOIN course_sections cs
                    ON cs.section_code = cm.section_code
                WHERE cm.course_id = ANY(:course_ids)
                ORDER BY cm.course_id, cm.module_number
            """),
            {"course_ids": list(course_ids)},
        )

        grouped = {}
        seen = {}

        for row in result:
            data = dict(row._mapping)
            course_id = data["course_id"]
            section_code = data["section_code"]

            key = (course_id, section_code)

            if key not in seen:
                seen[key] = {
                    "section_code": section_code,
                    "module_from": data["module_from"],
                    "module_to": data["module_to"],
                    "weight_pct": data["weight_pct"],
                    "assessment": data["assessment"],
                    "modules": [],
                }
                grouped.setdefault(course_id, []).append(seen[key])

            seen[key]["modules"].append({
                "module_number": data["module_number"],
                "title": data["title"],
                "observable_evidence": data["observable_evidence"],
                "topics": data["topics"],
            })

        return grouped
