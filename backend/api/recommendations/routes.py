from uuid import UUID

import json

from flask import Blueprint, current_app, jsonify, request

from api.auth.utils import require_auth
from api.guards import owned_project
from api.job_submission import submit_job
from config.database import db
from repositories.career_match_repository import (
    CareerMatchRepository,
)
from repositories.career_skill_gap_repository import (
    CareerSkillGapRepository,
)
from repositories.course_module_repository import (
    CourseModuleRepository,
)
from repositories.course_recommendation_repository import (
    CourseRecommendationRepository,
)
from repositories.llm_summary_repository import (
    LLMSummaryRepository,
)
from repositories.project_repository import (
    ProjectRepository,
)
from services.jobs.worker import JOB_GENERATE_RECOMMENDATIONS
from services.recommendations.generator import (
    RecommendationGenerator,
)

recommendations_bp = Blueprint(
    "recommendations",
    __name__,
)


def _with_syllabus(courses):
    """Attach each course's section-and-module breakdown as `syllabus`.

    Served inline rather than behind a lazy per-course endpoint. The breakdown
    is about 1.6 KB per course and the whole 40-course catalog is under 64 KB,
    so shipping it with the list costs a few kilobytes on a response the client
    already has to make; fetching it on expand would cost a fresh round trip to
    a cross-region database every time a card is opened. One query covers every
    course on the page, so the join does not scale with the number of cards.

    Courses predating the corpus have no modules and get an empty list, which
    the client renders as no syllabus section rather than an empty one.
    """
    if not courses:
        return courses

    syllabus = CourseModuleRepository.get_syllabus_for_course_ids(
        {course["course_id"] for course in courses}
    )

    return [
        {**course, "syllabus": syllabus.get(course["course_id"], [])}
        for course in courses
    ]


def _with_structured_summary(summary):
    """Expose the summary's typed sections as `structured`.

    llm_summaries.summary_text now holds the JSON of a CareerSummary/CourseSummary.
    Rows written before the summaries were structured hold prose instead, and rows
    are only rewritten when recommendations are regenerated, so `structured` is None
    for those and the client falls back to rendering summary_text as a paragraph.
    """
    if summary is None:
        return None

    structured = None
    summary_text = summary.get("summary_text")

    if isinstance(summary_text, str):
        try:
            candidate = json.loads(summary_text)
        except ValueError:
            candidate = None

        if isinstance(candidate, dict):
            structured = candidate

    return {**summary, "structured": structured}


def _enqueue_generate(project):
    """Start a generate run in the background and return 202 immediately.

    Generation takes ~73 seconds, which no API Gateway integration will wait
    for. The client gets a job id and polls GET /api/jobs/<id>.
    """
    return submit_job(
        student_id=project.student_id,
        project_id=project.project_id,
        job_type=JOB_GENERATE_RECOMMENDATIONS,
    )


@recommendations_bp.route("/projects/<project_id>/generate", methods=["POST"])
@require_auth
def generate_recommendations(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    if request.args.get("async") == "1":
        return _enqueue_generate(project)

    project_uuid = project.project_id

    try:
        result = RecommendationGenerator.generate(project_uuid)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("generate: failed to generate recommendations")
        return jsonify({"error": "failed to generate recommendations"}), 500

    return jsonify(result), 200


@recommendations_bp.route("/projects/<project_id>/careers", methods=["GET"])
@require_auth
def get_career_recommendations(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    careers = CareerMatchRepository.get_by_project_id(project_uuid)

    return jsonify(
        {
            "project_id": project_id,
            "careers": careers,
        }
    )


@recommendations_bp.route("/projects/<project_id>/courses", methods=["GET"])
@require_auth
def get_course_recommendations(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    courses = CourseRecommendationRepository.get_by_project_id(project_uuid)

    return jsonify(
        {
            "project_id": project_id,
            "courses": _with_syllabus(courses),
        }
    )


@recommendations_bp.route("/projects/<project_id>", methods=["GET"])
@require_auth
def get_project_recommendations(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    careers = CareerMatchRepository.get_by_project_id(project_uuid)

    courses = CourseRecommendationRepository.get_by_project_id(project_uuid)

    return jsonify(
        {
            "project_id": project_id,
            "careers": careers,
            "courses": _with_syllabus(courses),
        }
    )


@recommendations_bp.route("/projects/<project_id>/careers/<occupation_id>", methods=["GET"])
@require_auth
def get_career_details(project_id: str, occupation_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    try:
        occupation_uuid = UUID(occupation_id)
    except ValueError:
        return jsonify({"error": "invalid UUID supplied"}), 400

    career = CareerMatchRepository.get_by_project_and_occupation(
        project_uuid,
        occupation_uuid,
    )

    if career is None:
        return jsonify({"error": "career recommendation not found"}), 404

    summary = LLMSummaryRepository.get_career_summary(
        project_uuid,
        occupation_uuid,
    )

    skill_gaps = CareerSkillGapRepository.get_by_occupation_id(
        project_uuid,
        occupation_uuid,
    )

    return jsonify(
        {
            "project_id": project_id,
            "occupation_id": occupation_id,
            "career": career,
            "summary": _with_structured_summary(summary),
            "skill_gaps": skill_gaps,
        }
    )


@recommendations_bp.route("/projects/<project_id>/careers/<occupation_id>/courses", methods=["GET"])
@require_auth
def get_career_courses(project_id: str, occupation_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    try:
        occupation_uuid = UUID(occupation_id)
    except ValueError:
        return jsonify({"error": "invalid UUID supplied"}), 400

    courses = CourseRecommendationRepository.get_by_project_and_occupation(
        project_uuid,
        occupation_uuid,
    )

    summaries = LLMSummaryRepository.get_course_summaries(
        project_uuid,
        occupation_uuid,
    )

    summary_map = {summary["course_id"]: summary for summary in summaries}

    response_courses = []

    for course in courses:
        response_courses.append(
            {
                **course,
                "summary": _with_structured_summary(summary_map.get(course["course_id"])),
            }
        )

    return jsonify(
        {
            "project_id": project_id,
            "occupation_id": occupation_id,
            "courses": _with_syllabus(response_courses),
        }
    )
