"""Row serializers shared by the route modules.

These live outside any one blueprint because the same row shape is returned from
more than one endpoint, and the client compares the payloads. A project skill,
for example, is returned by both `POST /resumes/<id>/extract-skills` and
`GET /projects/<id>/skills`; if the two drifted, the page would render different
fields depending on which call happened to populate it.
"""


def serialize_project_skill(skill: dict) -> dict:
    return {
        "project_skill_id": str(skill["project_skill_id"]),
        "project_id": str(skill["project_id"]),
        "skill_id": str(skill["skill_id"]) if skill["skill_id"] is not None else None,
        "skill_name": skill["skill_name"],
        "proficiency_level": skill["proficiency_level"],
        "confidence_score": float(skill["confidence_score"]),
        "source": skill["source"],
        "created_at": skill["created_at"].isoformat(),
    }


def _iso(value):
    return value.isoformat() if value is not None else None


def serialize_job(job: dict) -> dict:
    """Wire shape for a job row, returned by every endpoint that exposes one.

    Deliberately omits the columns that exist for the worker rather than the
    client — `cancel_requested`, `attempt`, `request_id`, `heartbeat_at`. They
    are operational detail, and `request_id` in particular maps a job to a
    CloudWatch log stream, which is not something to hand to a browser.

    Note that a failed job is still an HTTP 200 with `status: "failed"`. Callers
    must branch on this field; a `catch` block will never see it.
    """
    return {
        "job_id": str(job["job_id"]),
        "job_type": job["job_type"],
        "project_id": str(job["project_id"]) if job["project_id"] else None,
        "status": job["status"],
        "stage": job["stage"],
        "stage_done": job["stage_done"],
        "stage_total": job["stage_total"],
        "percent": job["percent"],
        "message": job["message"],
        "error": job["error"],
        "result": job["result"],
        "created_at": _iso(job["created_at"]),
        "started_at": _iso(job["started_at"]),
        "finished_at": _iso(job["finished_at"]),
    }
