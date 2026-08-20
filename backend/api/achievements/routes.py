from flask import Blueprint, g, jsonify, request

from api.auth.utils import require_auth
from repositories.achievement_repository import AchievementRepository

achievements_bp = Blueprint("achievements", __name__)

# A board longer than this stops being motivating and starts being a directory.
MAX_LEADERBOARD = 25


@achievements_bp.route("", methods=["GET"])
@require_auth
def get_achievements():
    """XP, level, streak and badges for the authenticated student.

    Always the caller's own, taken from the token rather than a path parameter.
    An id in the URL would be an invitation to read someone else's progress, and
    there is no reason for one student to see another's.

    Every figure is derived from submitted sittings on request, so a section
    submitted a second ago is already counted and there is nothing to backfill.
    """
    return jsonify(AchievementRepository.profile(g.student_id))


@achievements_bp.route("/leaderboard", methods=["GET"])
@require_auth
def get_leaderboard():
    """Anonymous ranking by XP, with the caller's own position marked.

    Ranks and numbers only. Naming people here would publish one student's
    academic standing to another — which nobody asked for, and which cannot be
    unseen once it has been. If names are ever wanted, that needs to be an
    explicit opt-in rather than a default of this endpoint.
    """
    try:
        limit = min(MAX_LEADERBOARD, max(3, int(request.args.get("limit", 10))))
    except (TypeError, ValueError):
        limit = 10

    return jsonify(AchievementRepository.leaderboard(g.student_id, limit))
