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


def serialize_attempt(attempt: dict) -> dict:
    """One recorded answer inside a sitting.

    Both letters are reported. ``selected_option`` is the corpus letter, which
    is what ``is_correct`` was decided against; ``presented_option`` is the
    letter the student actually clicked in their shuffled layout, which is the
    only one that means anything on a review screen.
    """
    return {
        "attempt_id": str(attempt["attempt_id"]),
        "sitting_id": str(attempt["sitting_id"]),
        "question_id": str(attempt["question_id"]),
        "question_number": attempt.get("question_number"),
        "section_code": attempt["section_code"],
        "selected_option": attempt["selected_option"],
        "presented_option": attempt["presented_option"],
        "is_correct": attempt["is_correct"],
        "marks_awarded": attempt["marks_awarded"],
        "max_marks": attempt["max_marks"],
        "submitted_at": _iso(attempt["submitted_at"]),
    }


def serialize_sitting(sitting: dict, seconds_remaining: int) -> dict:
    """A sitting's state.

    ``seconds_remaining`` is passed in rather than read off the row: the stored
    column is only current as of the last pause, and a running sitting has to
    have the elapsed time subtracted. Serialising the raw column would hand the
    client a clock that stops whenever it is not looking.
    """
    return {
        "sitting_id": str(sitting["sitting_id"]),
        # A sitting is owned by a project (the project track) or by a student
        # directly (the course track). Report whichever is present rather than
        # assuming project_id, so one serializer serves both.
        "project_id": str(sitting["project_id"]) if sitting.get("project_id") else None,
        "student_id": str(sitting["student_id"]) if sitting.get("student_id") else None,
        "section_code": sitting["section_code"],
        "mode": sitting["mode"],
        "status": sitting["status"],
        "time_limit_seconds": sitting["time_limit_seconds"],
        "seconds_remaining": seconds_remaining,
        "marks_awarded": sitting["marks_awarded"],
        "marks_available": sitting["marks_available"],
        "started_at": _iso(sitting["started_at"]),
        "submitted_at": _iso(sitting["submitted_at"]),
    }


def serialize_section_state(row: dict) -> dict:
    """What the syllabus needs to decide which button to show for a section."""
    return {
        "section_code": row["section_code"],
        "graded_status": row["graded_status"],
        "marks_awarded": row["marks_awarded"],
        "marks_available": row["marks_available"],
        "submitted_at": _iso(row["submitted_at"]),
        "open_practice_sitting_id": row["open_practice_id"],
        "practice_runs": row["practice_runs"],
    }
