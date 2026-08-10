"""Handing work to a background worker.

This is the only place that knows *how* a job gets executed, so it is also the
only place that changes if the mechanism ever moves to SQS or Step Functions.

On Lambda the function invokes **itself** with `InvocationType='Event'`. That
needs no new AWS resources — only `lambda:InvokeFunction` on its own ARN — and
the worker lands in an identical container with the same code and configuration.

A background thread is deliberately *not* used on Lambda. The execution
environment is frozen the moment the handler returns: CPU drops to effectively
zero, and the sandbox is only thawed by a later invocation that may not even be
the same sandbox. A 73-second thread would make partial, unpredictable progress
spread across unrelated later requests, while holding a database connection.

Off Lambda there is no freeze, so a thread is exactly right — it keeps the whole
submit-then-poll loop testable locally without any AWS involvement.
"""

import json
import os
import threading

from flask import current_app


class EnqueueFailed(Exception):
    """The worker could not be started, so the job will never run."""


def enqueue(task, job_id, **payload):
    """Start `task` in the background. Raises EnqueueFailed if it cannot.

    Callers must treat the exception as fatal for that job: the row is already
    committed to hold the active-job index, so leaving it would block every
    later submit for that project behind a job nobody is running.
    """
    event = {"ct_task": task, "job_id": str(job_id), **payload}
    function_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME")

    if function_name:
        _invoke_self(function_name, event)
    else:
        _run_in_thread(event)


def _invoke_self(function_name, event):
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        boto3.client("lambda").invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps(event).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        # Most likely the execution role is missing lambda:InvokeFunction on its
        # own ARN. Name it, because the AccessDenied alone reads like an
        # application bug.
        raise EnqueueFailed(
            f"could not invoke {function_name} asynchronously: {exc}"
        ) from exc


def _run_in_thread(event):
    """Local development path.

    The app context has to be pushed inside the thread — Flask's context is
    thread-local, so the worker cannot inherit the request's.
    """
    app = current_app._get_current_object()

    def _run():
        from services.jobs.worker import run_task

        with app.app_context():
            run_task(event, None)

    threading.Thread(target=_run, daemon=True).start()
