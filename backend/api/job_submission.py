"""Turning a long operation into a 202 and a job id.

Shared by every route that hands work to the background worker. The sequence is
identical each time and each step of it is load-bearing, so it lives in one
place rather than being retyped per endpoint.
"""

from flask import current_app, jsonify
from sqlalchemy.exc import IntegrityError

from api.serializers import serialize_job
from config.database import db
from repositories.job_repository import JobRepository
from services.jobs.dispatch import EnqueueFailed, enqueue


def job_response(job, status_code=202):
    """The wire shape for an accepted job: the row plus where to poll it."""
    return (
        jsonify({**serialize_job(job), "poll_url": f"/api/jobs/{job['job_id']}"}),
        status_code,
    )


def submit_job(student_id, project_id, job_type, **payload):
    """Create a job, start it, and return the view's response.

    Returns a Flask response tuple in every case — callers just `return` it.
    """
    try:
        job = JobRepository.create(
            student_id=student_id,
            project_id=project_id,
            job_type=job_type,
        )
    except IntegrityError:
        # The partial unique index rejected a second active job for this
        # (project, type). That is a double submit, not an error — hand back the
        # run already in flight so the client attaches to it instead of starting
        # another expensive one. This holds across Lambda sandboxes, which no
        # client-side guard can.
        db.session.rollback()
        existing = JobRepository.get_active(project_id, job_type)

        if existing is not None:
            return job_response(existing)

        # The in-flight job finished between our INSERT and this SELECT. Rare,
        # and pressing again is the right recovery.
        return jsonify({"error": "a run just finished; please try again"}), 409

    try:
        enqueue(job_type, job["job_id"], **payload)
    except EnqueueFailed:
        # The row is already committed and holds the active-job index, so
        # leaving it would block every later submit for this project behind a
        # job nobody is running.
        JobRepository.delete(job["job_id"])
        current_app.logger.exception("submit_job: could not enqueue %s", job_type)
        return jsonify({"error": "could not start the run; please try again"}), 503

    return job_response(job)
