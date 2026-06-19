from uuid import UUID

from flask import Blueprint, jsonify, request

from config.database import db
from repositories.resume_repository import ResumeRepository
from repositories.student_repository import StudentRepository
from services.matching.ranking import CareerRankingService
from services.resume.extractor import ResumeSkillExtractor

recommendations_bp = Blueprint(
    "recommendations",
    __name__,
)


def _serialize_recommendation(match: dict) -> dict:
    result = {
        "rank": match["rank"],
        "occupation_id": str(match["occupation_id"]),
        "occupation_name": match["occupation_name"],
        "score": match["score"],
        "matched_skills": match["matched_skills"],
        "missing_skills": match["missing_skills"],
        "skill_breakdown": match["skill_breakdown"],
    }

    if "summary" in match:
        result["summary"] = match["summary"]

    return result


@recommendations_bp.route("/students/<student_id>/careers", methods=["GET"])
def get_career_recommendations(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    if StudentRepository.get_by_id(student_uuid) is None:
        return jsonify({"error": "student not found"}), 404

    top_n = request.args.get("top", default=5, type=int)
    include_summary = request.args.get(
        "include_summary",
        default="false",
    ).lower() in {"1", "true", "yes"}

    if top_n < 1 or top_n > 20:
        return jsonify({"error": "top must be between 1 and 20"}), 400

    try:
        result = CareerRankingService.recommend(
            student_uuid,
            top_n=top_n,
            include_summary=include_summary,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "failed to generate recommendations"}), 500

    return jsonify({
        "student_id": str(result["student_id"]),
        "recommendations": [
            _serialize_recommendation(match)
            for match in result["recommendations"]
        ],
    })
