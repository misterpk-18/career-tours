"""Progress reporting for background jobs.

The pipeline reports where it is; this module decides what percentage that is
and how often to write it down. Keeping the arithmetic here means the generator
never has to know it is being watched — it calls `stage()` and `advance()`, and
the same calls are no-ops on the synchronous path.

Percentages come from **fixed weights**, not from elapsed time. A bar driven by
a clock has to either lie or go backwards when a stage runs long; one driven by
declared work does neither. The weights below are rough measurements of where
the ~73 seconds actually goes, and they only need to be right enough that the
bar does not stall visibly in one place.
"""

import time

from repositories.job_repository import JobRepository


class JobCancelled(Exception):
    """The user asked for this job to stop."""


class JobDeadlineExceeded(Exception):
    """Not enough Lambda execution time remains to finish safely."""


#: Stage weights for `generate_recommendations`, summing to 100.
GENERATE_WEIGHTS = {
    "matching": 15,
    "career_summaries": 25,
    "persisting": 5,
    "courses": 55,
}

#: Human-readable stage labels. The client can render its own, but a job row
#: should be legible on its own in psql when something has gone wrong.
STAGE_MESSAGES = {
    "matching": "Matching your skills against occupations",
    "career_summaries": "Writing career summaries",
    "persisting": "Saving matches",
    "courses": "Finding and summarising courses",
    "extracting": "Reading your resume",
}

#: Minimum gap between progress writes. Stage transitions ignore this — they are
#: the writes that actually tell the user something changed.
WRITE_INTERVAL_SECONDS = 1.5

#: Bail out rather than start more work with less than this much time left. A
#: Lambda that hits its hard timeout writes no status at all, so the job would
#: sit `running` until the stale reaper caught it a full two minutes later.
DEADLINE_MARGIN_MS = 30_000


class ProgressReporter:
    """Translates pipeline events into throttled writes on a job row."""

    def __init__(self, job_id, context=None, weights=None):
        self.job_id = job_id
        self.context = context
        self.weights = weights or GENERATE_WEIGHTS

        self._stage = None
        self._done = 0
        self._total = None
        self._completed_weight = 0
        self._last_write = 0.0

    def stage(self, name, total=None, message=None):
        """Enter a stage. Always writes, and always checks for a stop signal.

        Stage boundaries are the only safe place to abandon a run: an in-flight
        OpenAI call cannot be interrupted, and stopping midway through one would
        leave the project's recommendations half-deleted.
        """
        if self._stage is not None:
            self._completed_weight += self.weights.get(self._stage, 0)

        self._stage = name
        self._done = 0
        self._total = total

        self._check_cancelled()
        self._check_deadline()
        self._write(message or STAGE_MESSAGES.get(name), force=True)

    def advance(self, count=1, message=None):
        """Record progress within the current stage."""
        self._done += count
        self._check_deadline()
        self._write(message, force=False)

    def percent(self):
        weight = self.weights.get(self._stage, 0)

        if self._total:
            fraction = min(self._done / self._total, 1.0)
        else:
            # Unknown total — hold at the stage's start rather than inventing
            # movement. The client renders an indeterminate bar for this.
            fraction = 0.0

        return min(int(self._completed_weight + weight * fraction), 99)

    def _write(self, message, force):
        now = time.monotonic()

        if not force and now - self._last_write < WRITE_INTERVAL_SECONDS:
            return

        self._last_write = now

        JobRepository.update_progress(
            self.job_id,
            stage=self._stage,
            stage_done=self._done,
            stage_total=self._total,
            percent=self.percent(),
            message=message,
        )

    def _check_cancelled(self):
        job = JobRepository.get_by_id(self.job_id)

        if job is not None and job["cancel_requested"]:
            raise JobCancelled()

    def _check_deadline(self):
        if self.context is None:
            return

        remaining = getattr(self.context, "get_remaining_time_in_millis", None)

        if remaining is not None and remaining() < DEADLINE_MARGIN_MS:
            raise JobDeadlineExceeded()


class NullProgress:
    """No-op reporter for the synchronous path.

    Lets the generator carry progress calls unconditionally instead of guarding
    every one of them with `if progress is not None`.
    """

    def stage(self, name, total=None, message=None):
        pass

    def advance(self, count=1, message=None):
        pass


NULL_PROGRESS = NullProgress()
