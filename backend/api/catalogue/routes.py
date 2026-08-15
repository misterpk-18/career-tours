"""The catalogue: every course and every career, independent of any project.

Distinct from `api/recommendations`, which answers "what should *this student*
study next" and only ever returns the handful of rows that scored. These
endpoints answer "what exists at all", which is a browsing question, so they
return the whole table and let the client filter.

Filtering is deliberately left to the client. The catalogue is 40 courses and
267 occupations — small enough that one response is cheaper than a round trip
per keystroke to a database in another region, and search that never leaves the
browser has no latency to design around.

Authentication is still required. Nothing here is per-student, but the whole API
sits behind a login and an unauthenticated endpoint would be a new front door.
"""

from uuid import UUID

from flask import Blueprint, jsonify

from api.auth.utils import require_auth
from repositories.course_module_repository import CourseModuleRepository
from repositories.course_repository import CourseRepository
from repositories.course_skill_repository import CourseSkillRepository
from repositories.occupation_repository import OccupationRepository

catalogue_bp = Blueprint(
    "catalogue",
    __name__,
)


def _serialize_course(course: dict, skills: list, module_count: int) -> dict:
    return {
        "course_id": str(course["course_id"]),
        "course_code": course.get("course_code"),
        "course_name": course["course_name"],
        "description": course.get("description"),
        "duration_hours": course.get("duration_hours"),
        "level": course.get("level"),
        "module_count": module_count,
        # The card shows a few and the search matches all of them, so the list
        # response carries the names. Coverage weight is a scoring input with
        # nothing to say to someone browsing, so it is left to the detail view.
        "skills": [skill["skill_name"] for skill in skills],
    }


@catalogue_bp.route("/courses", methods=["GET"])
@require_auth
def list_courses():
    """Every active course, with its skills and module count.

    Three queries for the whole catalogue rather than three per course: the
    skills and the modules are fetched for all courses at once and grouped in
    Python. Against a cross-region database the round trip dominates, so 40
    courses one at a time would be 120 trips for the same rows.
    """
    courses = CourseRepository.get_all()

    skills_by_course: dict = {}
    for row in CourseSkillRepository.get_all_active():
        skills_by_course.setdefault(str(row["course_id"]), []).append(row)

    modules_by_course = CourseModuleRepository.get_for_course_ids(
        [course["course_id"] for course in courses]
    )

    return jsonify(
        [
            _serialize_course(
                course,
                skills_by_course.get(str(course["course_id"]), []),
                len(modules_by_course.get(course["course_id"], [])),
            )
            for course in courses
        ]
    )


@catalogue_bp.route("/courses/<course_id>", methods=["GET"])
@require_auth
def get_course(course_id: str):
    """One course and the syllabus a learner would work through.

    The syllabus is the sections-with-modules shape the recommendation views
    already render, reused rather than re-derived so the learning journey and
    the recommendation card cannot describe the same course differently.
    """
    try:
        course_uuid = UUID(course_id)
    except ValueError:
        return jsonify({"error": "course_id must be a valid UUID"}), 400

    course = CourseRepository.get_by_id(course_uuid)

    if course is None or not course.get("is_active", True):
        return jsonify({"error": "course not found"}), 404

    skills = CourseSkillRepository.get_by_course_id(course_uuid)

    syllabus = CourseModuleRepository.get_syllabus_for_course_ids([course_uuid])

    payload = _serialize_course(course, skills, 0)
    payload["syllabus"] = syllabus.get(course_uuid, [])
    # Recomputed from the syllabus so the count and the list it labels can never
    # disagree — the list view derives it from a different query.
    payload["module_count"] = sum(
        len(section["modules"]) for section in payload["syllabus"]
    )
    # Coverage weight is worth showing here: on a page about one course, how
    # heavily it covers a skill is the substance rather than noise.
    payload["skill_coverage"] = [
        {
            "skill_name": skill["skill_name"],
            "coverage_weight": float(skill["coverage_weight"]),
        }
        for skill in sorted(skills, key=lambda s: float(s["coverage_weight"]), reverse=True)
    ]

    return jsonify(payload)


# How many skill names each career carries into the list response.
#
# The full set is 8,372 rows across 267 careers, which is several hundred KB of
# JSON to render a card that shows a handful. The counts below are exact and the
# preview is what the card and the client-side search read; a career's complete
# skill list belongs to a detail view, which does not exist yet.
CAREER_SKILL_PREVIEW = 8


@catalogue_bp.route("/careers", methods=["GET"])
@require_auth
def list_careers():
    """Every occupation, with skill counts and the heaviest few skill names.

    Essential and optional are counted separately rather than summed. ESCO marks
    5,150 of its 8,114 pairs optional, so a single "31 skills" figure would
    describe a job by things nobody is required to know — the same conflation
    migration 010 exists to undo. Only essential skills feed the preview.
    """
    occupations = OccupationRepository.get_all()
    skills_by_occupation = OccupationRepository.get_skills_by_occupation()

    def career(occupation: dict) -> dict:
        skills = skills_by_occupation.get(occupation["occupation_id"], [])

        # A NULL relation_type reads as essential, matching the scorer: the 32
        # occupations predating the ESCO import have nothing to read.
        essential = [
            skill for skill in skills if (skill.get("relation_type") or "essential") == "essential"
        ]

        return {
            "occupation_id": str(occupation["occupation_id"]),
            "occupation_name": occupation["occupation_name"],
            "description": occupation.get("description"),
            "average_salary": (
                float(occupation["average_salary"])
                if occupation.get("average_salary") is not None
                else None
            ),
            "growth_outlook": occupation.get("growth_outlook"),
            "essential_skill_count": len(essential),
            "optional_skill_count": len(skills) - len(essential),
            "skills": [
                skill["skill_name"]
                for skill in sorted(
                    essential, key=lambda s: float(s["weight"]), reverse=True
                )[:CAREER_SKILL_PREVIEW]
            ],
        }

    return jsonify([career(occupation) for occupation in occupations])
