"""The background half of the application.

`run_task` is what a self-invoke lands in. It runs inside an app context pushed
by the dispatching handler in app.py, which is what lets every existing
repository work here unchanged.

Its contract is that **a job never stays `running`**. Whatever happens — a
domain error, a cancellation, running out of Lambda time, an unhandled
exception — the row reaches a terminal status with a message written for a
person, because the client polls this row and has nothing else to go on.
"""

from uuid import UUID

from flask import current_app

from config.database import db
from repositories.job_repository import JobRepository
from services.jobs.progress import (
    EXTRACT_WEIGHTS,
    GENERATE_WEIGHTS,
    JobCancelled,
    JobDeadlineExceeded,
    ProgressReporter,
)

JOB_GENERATE_RECOMMENDATIONS = "generate_recommendations"
JOB_EXTRACT_SKILLS = "extract_skills"


def run_task(event, context):
    task = event.get("ct_task")
    job_id = event.get("job_id")

    if not task or not job_id:
        current_app.logger.error("worker: malformed event, missing ct_task or job_id")
        return {"ok": False, "reason": "malformed event"}

    handler = _TASKS.get(task)

    if handler is None:
        current_app.logger.error("worker: unknown task %s", task)
        return {"ok": False, "reason": "unknown task"}

    request_id = getattr(context, "aws_request_id", None)

    # Claim before doing anything. Lambda retries an asynchronous invocation
    # twice on a function error, so the same job can legitimately arrive three
    # times; this UPDATE is what stops attempts two and three from re-running
    # 73 seconds of paid work. Checking in Python would not, because the
    # attempts can overlap.
    job = JobRepository.claim(job_id, request_id=request_id)

    if job is None:
        current_app.logger.info(
            "worker: job %s was already claimed or finished, skipping", job_id
        )
        return {"ok": True, "skipped": True}

    progress = ProgressReporter(job_id, context=context, weights=_WEIGHTS[task])

    try:
        # The event is passed through because a task may need arguments that do
        # not live on the job row — extract_skills needs the resume id, since a
        # project can have had more than one resume.
        result = handler(job, progress, event)
        JobRepository.mark_succeeded(job_id, result)
        return {"ok": True, "job_id": str(job_id)}

    except JobCancelled:
        # The generator clears a project's existing recommendations before
        # writing new ones, so an abandoned run really does leave nothing.
        JobRepository.mark_cancelled(
            job_id,
            "Cancelled. Nothing was saved — run it again when you are ready.",
        )
        return {"ok": True, "cancelled": True}

    except JobDeadlineExceeded:
        current_app.logger.error("worker: job %s ran out of time", job_id)
        JobRepository.mark_failed(
            job_id,
            "This took longer than expected and was stopped. "
            "Nothing was saved — please try again.",
        )
        return {"ok": False, "reason": "deadline"}

    except ValueError as exc:
        # Raised by our own pipeline for conditions the user can act on, such as
        # a project with no extracted skills. Safe to show verbatim.
        db.session.rollback()
        JobRepository.mark_failed(job_id, str(exc))
        return {"ok": False, "reason": "invalid input"}

    except Exception:
        db.session.rollback()
        current_app.logger.exception("worker: job %s failed", job_id)
        # Never put the exception text in `error`. SQLAlchemy exceptions carry
        # the statement and its bound parameters, which is user data, and this
        # field is rendered in the browser.
        JobRepository.mark_failed(
            job_id,
            "Something went wrong on our side. "
            "Nothing was saved — please try again.",
        )
        return {"ok": False, "reason": "error"}

    finally:
        # Belt and braces for a path that returned without settling the row.
        # _finish ignores an already-terminal job, so this cannot overwrite a
        # real message with a generic one.
        JobRepository.mark_failed(
            job_id, "The run ended unexpectedly. Please try again."
        )


def _generate_recommendations(job, progress, event):
    from services.recommendations.generator import RecommendationGenerator

    return RecommendationGenerator.generate(job["project_id"], progress=progress)


def _extract_skills(job, progress, event):
    from repositories.resume_repository import ResumeRepository
    from services.resume.extractor import ResumeSkillExtractor

    resume = ResumeRepository.get_by_id(UUID(event["resume_id"]))

    # The route validated all of this before enqueueing, so reaching any of these
    # means the row changed underneath us — a deleted resume, most likely. Raised
    # as ValueError because run_task shows that message to the user verbatim.
    if resume is None or str(resume.student_id) != str(job["student_id"]):
        raise ValueError("That resume is no longer available. Please upload it again.")

    if not resume.raw_text:
        raise ValueError("That resume has no readable text. Please upload it again.")

    result = ResumeSkillExtractor.extract_and_save(
        resume.project_id,
        resume.student_id,
        resume.raw_text,
        event.get("questionnaire_answers"),
        progress=progress,
    )

    # Only counts go in the job row. The skills themselves are read back from
    # GET /api/projects/<id>/skills, which the page already calls — putting them
    # here would duplicate the read model into a jsonb column and bloat every
    # poll response with the full list.
    return {
        "resume_id": str(resume.resume_id),
        "skills_saved": result["skills_saved"],
        "additional_skills_saved": result["additional_skills_saved"],
    }


_TASKS = {
    JOB_GENERATE_RECOMMENDATIONS: _generate_recommendations,
    JOB_EXTRACT_SKILLS: _extract_skills,
}

_WEIGHTS = {
    JOB_GENERATE_RECOMMENDATIONS: GENERATE_WEIGHTS,
    JOB_EXTRACT_SKILLS: EXTRACT_WEIGHTS,
}
