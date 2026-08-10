"""Data access for the `jobs` table.

Rows come back as plain dicts rather than a dataclass. Every other repository
that returns a dataclass constructs it with ``Model(**row._mapping)``, which
breaks the moment a column exists that the dataclass does not declare — and this
table is expected to grow columns as job types are added. `LLMSummaryRepository`
already establishes the dict precedent.
"""

from typing import Any, cast

from sqlalchemy import text

from config.database import db

#: Statuses a job can no longer move out of.
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")

#: A running job whose worker has not written a heartbeat for this long is
#: presumed dead. Workers heartbeat on every progress write, so this is many
#: multiples of the normal gap.
STALE_RUNNING_SECONDS = 120

#: A queued job never picked up in this long means the invoke never landed.
STALE_QUEUED_SECONDS = 60


class JobRepository:
    @staticmethod
    def create(student_id, project_id, job_type):
        """Insert a queued job.

        Raises ``sqlalchemy.exc.IntegrityError`` if an active job already exists
        for this (project, type) — the caller is expected to catch that, roll
        back, and return the in-flight job from `get_active`. That collision is
        the normal double-submit path, not an error condition.
        """
        result = db.session.execute(
            text("""
                INSERT INTO jobs (student_id, project_id, job_type)
                VALUES (:student_id, :project_id, :job_type)
                RETURNING *
            """),
            {
                "student_id": student_id,
                "project_id": project_id,
                "job_type": job_type,
            },
        )

        row = result.fetchone()
        db.session.commit()

        if row is None:
            raise RuntimeError("Failed to create job")

        return dict(cast(Any, row._mapping))

    @staticmethod
    def get_by_id(job_id):
        result = db.session.execute(
            text("SELECT * FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        )

        row = result.fetchone()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def get_active(project_id, job_type):
        """The queued or running job for this (project, type), if any.

        The partial unique index guarantees there is at most one.
        """
        result = db.session.execute(
            text("""
                SELECT *
                FROM jobs
                WHERE project_id = :project_id
                  AND job_type = :job_type
                  AND status IN ('queued', 'running')
            """),
            {"project_id": project_id, "job_type": job_type},
        )

        row = result.fetchone()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def get_latest(project_id, job_type):
        """The most recent job of this type, whatever its status.

        This is how a reloaded page re-attaches to a run in progress without the
        client having stored anything.
        """
        result = db.session.execute(
            text("""
                SELECT *
                FROM jobs
                WHERE project_id = :project_id
                  AND job_type = :job_type
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"project_id": project_id, "job_type": job_type},
        )

        row = result.fetchone()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def claim(job_id, request_id=None):
        """Transition queued -> running, atomically.

        Returns the claimed row, or None if someone else already claimed it or
        it is already terminal. Lambda retries an asynchronous invocation twice
        on a function error, so the same job can legitimately arrive three
        times; the WHERE clause is what stops the second and third attempts
        re-running an expensive job. Checking-then-updating in Python would not,
        because the attempts can overlap.
        """
        result = db.session.execute(
            text("""
                UPDATE jobs
                SET status = 'running',
                    started_at = CURRENT_TIMESTAMP,
                    heartbeat_at = CURRENT_TIMESTAMP,
                    attempt = attempt + 1,
                    request_id = :request_id
                WHERE job_id = :job_id
                  AND status = 'queued'
                RETURNING *
            """),
            {"job_id": job_id, "request_id": request_id},
        )

        row = result.fetchone()
        db.session.commit()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def update_progress(
        job_id,
        stage=None,
        stage_done=None,
        stage_total=None,
        percent=None,
        message=None,
    ):
        """Record progress and refresh the heartbeat.

        Every argument is optional and a NULL leaves the existing value alone,
        so a caller can bump the heartbeat without claiming to have advanced.
        Only applies to a running job — a cancelled or failed job must not be
        resurrected by a straggling progress write.
        """
        result = db.session.execute(
            text("""
                UPDATE jobs
                SET stage = COALESCE(:stage, stage),
                    stage_done = COALESCE(:stage_done, stage_done),
                    stage_total = COALESCE(:stage_total, stage_total),
                    percent = COALESCE(:percent, percent),
                    message = COALESCE(:message, message),
                    heartbeat_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
                  AND status = 'running'
                RETURNING *
            """),
            {
                "job_id": job_id,
                "stage": stage,
                "stage_done": stage_done,
                "stage_total": stage_total,
                "percent": percent,
                "message": message,
            },
        )

        row = result.fetchone()
        db.session.commit()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def mark_succeeded(job_id, result_payload=None):
        return JobRepository._finish(
            job_id, "succeeded", percent=100, result_payload=result_payload
        )

    @staticmethod
    def mark_failed(job_id, error):
        """Fail a job with a message intended for the user.

        `error` is rendered in the UI, so it must never be an exception's own
        text: SQLAlchemy exceptions carry the full statement and its bound
        parameters, which is user data. Pass a written sentence and log the
        traceback separately.
        """
        return JobRepository._finish(job_id, "failed", error=error)

    @staticmethod
    def mark_cancelled(job_id, error=None):
        return JobRepository._finish(job_id, "cancelled", error=error)

    @staticmethod
    def _finish(job_id, status, percent=None, error=None, result_payload=None):
        """Move a job to a terminal status, once.

        The status guard makes every terminal transition idempotent, so the
        `finally` block that catches a worker dying cannot overwrite a real
        failure message with a generic one.
        """
        import json

        result = db.session.execute(
            text("""
                UPDATE jobs
                SET status = :status,
                    percent = COALESCE(:percent, percent),
                    error = COALESCE(:error, error),
                    result = COALESCE(CAST(:result_payload AS jsonb), result),
                    finished_at = CURRENT_TIMESTAMP,
                    heartbeat_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
                  AND status NOT IN ('succeeded', 'failed', 'cancelled')
                RETURNING *
            """),
            {
                "job_id": job_id,
                "status": status,
                "percent": percent,
                "error": error,
                "result_payload": (
                    json.dumps(result_payload) if result_payload is not None else None
                ),
            },
        )

        row = result.fetchone()
        db.session.commit()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def request_cancel(job_id):
        """Ask a job to stop at its next stage boundary.

        Cooperative: an in-flight OpenAI call cannot be aborted, so this sets a
        flag the worker checks between stages rather than stopping anything now.
        """
        result = db.session.execute(
            text("""
                UPDATE jobs
                SET cancel_requested = true
                WHERE job_id = :job_id
                  AND status IN ('queued', 'running')
                RETURNING *
            """),
            {"job_id": job_id},
        )

        row = result.fetchone()
        db.session.commit()

        return dict(cast(Any, row._mapping)) if row else None

    @staticmethod
    def reap_stale():
        """Fail jobs whose worker died without saying so.

        A Lambda that is OOM-killed, hits its timeout, or is replaced mid-run by
        a deployment writes no terminal status — from the database's point of
        view the job simply stops advancing. Without this, such a job stays
        `running` forever and the client polls it indefinitely.

        Called at the top of the polling endpoints rather than on a schedule, so
        it costs nothing when nobody is watching and resolves within one poll
        when somebody is.

        Note the messages are written for the user: the generator deletes a
        project's existing recommendations before writing new ones, so an
        interrupted run really does leave nothing behind.
        """
        result = db.session.execute(
            text("""
                UPDATE jobs
                SET status = 'failed',
                    error = CASE
                        WHEN status = 'running' THEN
                            'The run was interrupted before it finished. '
                            'Nothing was saved — please run it again.'
                        ELSE
                            'The run never started. Please try again.'
                    END,
                    finished_at = CURRENT_TIMESTAMP
                WHERE (
                        status = 'running'
                        AND heartbeat_at < CURRENT_TIMESTAMP
                            - make_interval(secs => :stale_running)
                      )
                   OR (
                        status = 'queued'
                        AND heartbeat_at IS NULL
                        AND created_at < CURRENT_TIMESTAMP
                            - make_interval(secs => :stale_queued)
                      )
                RETURNING job_id
            """),
            {
                "stale_running": STALE_RUNNING_SECONDS,
                "stale_queued": STALE_QUEUED_SECONDS,
            },
        )

        reaped = result.fetchall()
        db.session.commit()

        return len(reaped)

    @staticmethod
    def delete(job_id):
        """Remove a job row.

        Used when enqueueing the worker fails: the row was already committed to
        claim the unique index, so leaving it would block every later submit for
        that project with a job that will never run.
        """
        result = db.session.execute(
            text("DELETE FROM jobs WHERE job_id = :job_id RETURNING job_id"),
            {"job_id": job_id},
        )

        deleted = result.fetchall()
        db.session.commit()

        return len(deleted)
