from uuid import UUID

import json

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from api.auth.utils import require_auth
from api.guards import owned_project
from api.serializers import serialize_job
from config.database import db
from repositories.job_repository import JobRepository
from repositories.career_match_repository import (
    CareerMatchRepository,
)
from repositories.career_skill_gap_repository import (
    CareerSkillGapRepository,
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
from services.jobs.dispatch import EnqueueFailed, enqueue
from services.jobs.worker import JOB_GENERATE_RECOMMENDATIONS
from services.recommendations.generator import (
    RecommendationGenerator,
)

recommendations_bp = Blueprint(
    "recommendations",
    __name__,
)


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


def _job_response(job, status_code):
    return jsonify({**serialize_job(job), "poll_url": f"/api/jobs/{job['job_id']}"}), status_code


def _enqueue_generate(project):
    """Start a generate run in the background and return 202 immediately.

    Generation takes ~73 seconds, which no API Gateway integration will wait
    for. The client gets a job id and polls GET /api/jobs/<id>.
    """
    try:
        job = JobRepository.create(
            student_id=project.student_id,
            project_id=project.project_id,
            job_type=JOB_GENERATE_RECOMMENDATIONS,
        )
    except IntegrityError:
        # The partial unique index rejected a second active job for this
        # project. That is a double submit, not an error — hand back the run
        # already in flight so the client attaches to it rather than starting
        # another 73 seconds of paid work.
        db.session.rollback()
        existing = JobRepository.get_active(
            project.project_id, JOB_GENERATE_RECOMMENDATIONS
        )

        if existing is not None:
            return _job_response(existing, 202)

        # The job finished between our INSERT and this SELECT. Rare, and the
        # user can simply press it again.
        return jsonify({"error": "a run just finished; please try again"}), 409

    try:
        enqueue(JOB_GENERATE_RECOMMENDATIONS, job["job_id"])
    except EnqueueFailed:
        # The row holds the active-job index, so leaving it would block every
        # later submit behind a job nobody is running.
        JobRepository.delete(job["job_id"])
        current_app.logger.exception("generate: could not enqueue background job")
        return jsonify({"error": "could not start the run; please try again"}), 503

    return _job_response(job, 202)


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
            "courses": courses,
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
            "courses": courses,
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
            "courses": response_courses,
        }
    )
