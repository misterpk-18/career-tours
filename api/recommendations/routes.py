from uuid import UUID

from flask import Blueprint, jsonify

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
from services.reccomendations.generator import (
    RecommendationGenerator,
)

recommendations_bp = Blueprint(
    "recommendations",
    __name__,
)


@recommendations_bp.route(
    "/projects/<project_id>/generate",
    methods=["POST"]
)
def generate_recommendations(
    project_id: str
):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({
            "error":
                "project_id must be a valid UUID"
        }), 400

    project = ProjectRepository.get_by_id(
        project_uuid
    )

    if project is None:
        return jsonify({
            "error":
                "project not found"
        }), 404

    try:
        result = (
            RecommendationGenerator.generate(
                project_uuid
            )
        )
    except ValueError as exc:
        return jsonify({
            "error": str(exc)
        }), 400
    except Exception:
        return jsonify({
            "error":
                "failed to generate recommendations"
        }), 500

    return jsonify(result), 200


@recommendations_bp.route(
    "/projects/<project_id>/careers",
    methods=["GET"]
)
def get_career_recommendations(
    project_id: str
):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({
            "error":
                "project_id must be a valid UUID"
        }), 400

    careers = (
        CareerMatchRepository.get_by_project_id(
            project_uuid
        )
    )

    return jsonify({
        "project_id": project_id,
        "careers": careers,
    })


@recommendations_bp.route(
    "/projects/<project_id>/courses",
    methods=["GET"]
)
def get_course_recommendations(
    project_id: str
):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({
            "error":
                "project_id must be a valid UUID"
        }), 400

    courses = (
        CourseRecommendationRepository
        .get_by_project_id(
            project_uuid
        )
    )

    return jsonify({
        "project_id": project_id,
        "courses": courses,
    })


@recommendations_bp.route(
    "/projects/<project_id>",
    methods=["GET"]
)
def get_project_recommendations(
    project_id: str
):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({
            "error":
                "project_id must be a valid UUID"
        }), 400

    careers = (
        CareerMatchRepository.get_by_project_id(
            project_uuid
        )
    )

    courses = (
        CourseRecommendationRepository
        .get_by_project_id(
            project_uuid
        )
    )

    return jsonify({
        "project_id": project_id,
        "careers": careers,
        "courses": courses,
    })


@recommendations_bp.route(
    "/projects/<project_id>/careers/<occupation_id>",
    methods=["GET"]
)
def get_career_details(
    project_id: str,
    occupation_id: str
):
    try:
        project_uuid = UUID(project_id)
        occupation_uuid = UUID(
            occupation_id
        )
    except ValueError:
        return jsonify({
            "error":
                "invalid UUID supplied"
        }), 400

    career = (
        CareerMatchRepository
        .get_by_project_and_occupation(
            project_uuid,
            occupation_uuid,
        )
    )

    if career is None:
        return jsonify({
            "error":
                "career recommendation not found"
        }), 404

    summary = (
        LLMSummaryRepository
        .get_career_summary(
            project_uuid,
            occupation_uuid,
        )
    )

    skill_gaps = (
        CareerSkillGapRepository
        .get_by_occupation_id(
            project_uuid,
            occupation_uuid,
        )
    )

    return jsonify({
        "project_id":
            project_id,
        "occupation_id":
            occupation_id,
        "career":
            career,
        "summary":
            summary,
        "skill_gaps":
            skill_gaps,
    })


@recommendations_bp.route(
    "/projects/<project_id>/careers/<occupation_id>/courses",
    methods=["GET"]
)
def get_career_courses(
    project_id: str,
    occupation_id: str
):
    try:
        project_uuid = UUID(project_id)
        occupation_uuid = UUID(
            occupation_id
        )
    except ValueError:
        return jsonify({
            "error":
                "invalid UUID supplied"
        }), 400

    courses = (
        CourseRecommendationRepository
        .get_by_project_and_occupation(
            project_uuid,
            occupation_uuid,
        )
    )

    summaries = (
        LLMSummaryRepository
        .get_course_summaries(
            project_uuid,
            occupation_uuid,
        )
    )

    summary_map = {
        summary["course_id"]: summary
        for summary in summaries
    }

    response_courses = []

    for course in courses:
        response_courses.append({
            **course,
            "summary":
                summary_map.get(
                    course["course_id"]
                )
        })

    return jsonify({
        "project_id":
            project_id,
        "occupation_id":
            occupation_id,
        "courses":
            response_courses,
    })