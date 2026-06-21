from uuid import UUID

from flask import Blueprint, jsonify

from repositories.career_match_repository import (
    CareerMatchRepository,
)
from repositories.course_recommendation_repository import (
    CourseRecommendationRepository,
)
from repositories.project_repository import ProjectRepository
from services.reccomendations.generator import RecommendationGenerator

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