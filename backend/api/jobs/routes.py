"""Polling endpoints for long-running work.

Read-only. Nothing here creates a job — the producers live on the blueprints
that own the work (recommendations, resumes). This module only answers "how is
it going", which is what the client calls once a second while it waits.
"""

from uuid import UUID

from flask import Blueprint, g, jsonify

from api.auth.utils import require_auth
from api.serializers import serialize_job
from repositories.job_repository import JobRepository


jobs_bp = Blueprint(
    "jobs",
    __name__,
)


@jobs_bp.route("/<job_id>", methods=["GET"])
@require_auth
def get_job(job_id):
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        return jsonify({"error": "job_id must be a valid UUID"}), 400

    # Resolve dead workers before reading. A job whose Lambda was killed writes
    # no terminal status, so without this the client polls `running` forever.
    # Doing it here means it costs nothing unless somebody is actually watching.
    JobRepository.reap_stale()

    job = JobRepository.get_by_id(job_uuid)

    # 404 rather than 403 for another student's job, matching api/guards.py:
    # a 403 confirms the id exists, which is the one bit an enumerating caller
    # is after.
    if job is None or job["student_id"] != g.student_id:
        return jsonify({"error": "job not found"}), 404

    return jsonify(serialize_job(job))
