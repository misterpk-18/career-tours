"""Ownership guards shared by the route modules.

`require_auth` establishes *who* the caller is; these establish *what they may
reach*. Authentication without an ownership check is not access control: every
id in this API is a UUID in a URL, and UUIDs travel — they appear in the
frontend, in logs, and in shared links.

A row belonging to another student is reported as **404, not 403**. A 403
confirms the id exists, which is the one bit an enumerating caller wants. This
matches the choice already made in `preview_resume`.
"""

from uuid import UUID

from flask import g, jsonify

from repositories.project_repository import ProjectRepository


def owned_project(project_id: str):
    """Resolve a project the authenticated caller owns.

    Returns ``(project, None)`` on success, or ``(None, response)`` where
    `response` is what the view should return. Requires `require_auth` to have
    run first, since it reads `g.student_id`.

    Usage:
        project, error = owned_project(project_id)
        if error:
            return error
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return None, (jsonify({"error": "project_id must be a valid UUID"}), 400)

    project = ProjectRepository.get_by_id(project_uuid)

    if project is None or project.student_id != g.student_id:
        return None, (jsonify({"error": "project not found"}), 404)

    return project, None
