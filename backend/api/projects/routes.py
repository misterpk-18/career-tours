from uuid import UUID

from flask import Blueprint, g, jsonify, request

from api.auth.utils import require_auth
from api.guards import owned_project
from api.serializers import serialize_job, serialize_project_skill
from repositories.job_repository import JobRepository
from repositories.project_repository import ProjectRepository
from repositories.project_skill_repository import ProjectSkillRepository


projects_bp = Blueprint(
    "projects",
    __name__,
)


def _serialize_project(project) -> dict:
    return {
        "project_id": str(project.project_id),
        "student_id": str(project.student_id),
        "project_name": project.project_name,
        "description": project.description,
        "status": project.status,
        "resume_id": str(project.resume_id) if project.resume_id else None,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


@projects_bp.route("", methods=["POST"])
@require_auth
def create_project():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("project_name"):
        return jsonify({"error": "project_name is required"}), 400

    # The owner comes from the token, never the body. Trusting a body-supplied
    # student_id would let any caller file a project under someone else's account.
    project_data = {**data, "student_id": g.student_id}

    try:
        project = ProjectRepository.create(project_data)
    except Exception:
        return jsonify({"error": "failed to create project"}), 500

    return jsonify(_serialize_project(project)), 201


@projects_bp.route("/<project_id>", methods=["GET"])
@require_auth
def get_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    return jsonify(_serialize_project(project))


@projects_bp.route("/<project_id>/skills", methods=["GET"])
@require_auth
def get_project_skills(project_id: str):
    """The stored skills for a project, or an empty list if none were extracted.

    The page needs this to decide which step of the pipeline the project is on.
    Without it the client had no way to ask, so it cached the extraction response
    in localStorage and guessed — which read as "no skills extracted" in any
    other browser.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    skills = ProjectSkillRepository.get_by_project_id(project.project_id)

    return jsonify([serialize_project_skill(skill) for skill in skills])


@projects_bp.route("/<project_id>/jobs/latest", methods=["GET"])
@require_auth
def get_latest_project_job(project_id: str):
    """The most recent job of a given type for this project, or null.

    This is how a page re-attaches to a run already in progress after a reload,
    a navigation, or a switch to another device — without the client having
    stored a job id anywhere. The same reasoning as `get_project_skills` above:
    if the server cannot be asked, the client caches and guesses, and the guess
    is wrong in every other browser.
    """
    job_type = request.args.get("type")

    if not job_type:
        return jsonify({"error": "type query parameter is required"}), 400

    project, error = owned_project(project_id)
    if error:
        return error

    # Same reasoning as GET /api/jobs/<id>: resolve dead workers before reading,
    # so a page reloaded after a deploy sees `failed` rather than a job stuck
    # `running` forever.
    JobRepository.reap_stale()

    job = JobRepository.get_latest(project.project_id, job_type)

    return jsonify({"job": serialize_job(job) if job else None})


@projects_bp.route("/student/<student_id>", methods=["GET"])
@require_auth
def get_student_projects(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    if student_uuid != g.student_id:
        return jsonify({"error": "student not found"}), 404

    projects = ProjectRepository.get_by_student_id(student_uuid)

    return jsonify([_serialize_project(project) for project in projects])


@projects_bp.route("/<project_id>", methods=["PUT"])
@require_auth
def update_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    # Ownership is not editable: a PUT carrying student_id must not reassign the
    # project, and project_id in the body must not redirect the update.
    payload = {key: value for key, value in data.items() if key not in ("student_id", "project_id")}

    updated = ProjectRepository.update(project.project_id, payload)

    if updated is None:
        return jsonify({"error": "project not found"}), 404

    return jsonify(_serialize_project(updated))


@projects_bp.route("/<project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    deleted = ProjectRepository.delete(project.project_id)

    if not deleted:
        return jsonify({"error": "project not found"}), 404

    return jsonify({"message": "project deleted successfully"})
