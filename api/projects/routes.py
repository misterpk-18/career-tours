from uuid import UUID

from flask import Blueprint, jsonify, request

from repositories.project_repository import ProjectRepository


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
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


@projects_bp.route("", methods=["POST"])
def create_project():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("student_id"):
        return jsonify({"error": "student_id is required"}), 400

    if not data.get("project_name"):
        return jsonify({"error": "project_name is required"}), 400

    try:
        project = ProjectRepository.create(data)
    except Exception:
        return jsonify({"error": "failed to create project"}), 500

    return jsonify(_serialize_project(project)), 201


@projects_bp.route("/<project_id>", methods=["GET"])
def get_project(project_id: str):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({"error": "project_id must be a valid UUID"}), 400

    project = ProjectRepository.get_by_id(project_uuid)

    if project is None:
        return jsonify({"error": "project not found"}), 404

    return jsonify(_serialize_project(project))


@projects_bp.route("/student/<student_id>", methods=["GET"])
def get_student_projects(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    projects = ProjectRepository.get_by_student_id(student_uuid)

    return jsonify([
        _serialize_project(project)
        for project in projects
    ])


@projects_bp.route("/<project_id>", methods=["PUT"])
def update_project(project_id: str):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({"error": "project_id must be a valid UUID"}), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    project = ProjectRepository.update(
        project_uuid,
        data
    )

    if project is None:
        return jsonify({"error": "project not found"}), 404

    return jsonify(_serialize_project(project))


@projects_bp.route("/<project_id>", methods=["DELETE"])
def delete_project(project_id: str):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({"error": "project_id must be a valid UUID"}), 400

    deleted = ProjectRepository.delete(project_uuid)

    if not deleted:
        return jsonify({"error": "project not found"}), 404

    return jsonify({
        "message": "project deleted successfully"
    })