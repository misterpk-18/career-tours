import { useCallback, useEffect, useRef, useState } from 'react';
import { jobsAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';
import { isActive, isTerminal } from '../lib/jobStages';

/**
 * Tracks one background job by polling, and re-attaches to one already running.
 *
 * Three things here are deliberate:
 *
 * - **setTimeout, not setInterval.** The next poll is scheduled only after the
 *   previous one resolves. An interval keeps firing while a slow request is in
 *   flight, so requests stack up against a backend that is already struggling.
 *
 * - **Backoff, then pause when hidden.** A job takes a couple of minutes, so
 *   polling every second for its whole life is wasted work. The gap widens, and
 *   a backgrounded tab stops polling entirely until it is looked at again.
 *
 * - **A failed job is an HTTP 200.** The request succeeds and the payload says
 *   `status: "failed"` — no catch block will ever see it. Callers must read
 *   `job.status`; `error` here is only for the poll request itself failing.
 */

const FIRST_DELAY = 1000;
const MAX_DELAY = 4000;
const BACKOFF = 1.6;

export const useJob = ({ projectId, jobType, onSucceeded } = {}) => {
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);

  const timerRef = useRef(null);
  const abortRef = useRef(null);
  const delayRef = useRef(FIRST_DELAY);
  const jobIdRef = useRef(null);
  // onSucceeded is usually an inline arrow, so a new identity every render. Kept
  // in a ref so the polling effect does not restart on each parent render.
  const onSucceededRef = useRef(onSucceeded);
  onSucceededRef.current = onSucceeded;

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const stop = useCallback(() => {
    clearTimer();
    abortRef.current?.abort();
    abortRef.current = null;
    jobIdRef.current = null;
  }, []);

  const poll = useCallback(async () => {
    const jobId = jobIdRef.current;
    if (!jobId) return;

    if (document.hidden) {
      timerRef.current = setTimeout(poll, MAX_DELAY);
      return;
    }

    abortRef.current = new AbortController();

    try {
      const next = await jobsAPI.get(jobId, { signal: abortRef.current.signal });

      // A later mount may have stopped us while this was in flight.
      if (jobIdRef.current !== jobId) return;

      setJob(next);

      if (isTerminal(next.status)) {
        jobIdRef.current = null;
        if (next.status === 'succeeded') await onSucceededRef.current?.(next);
        return;
      }
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
      // Keep polling through a transient failure: the job itself is still
      // running on the server, and giving up here would strand the user on a
      // frozen bar with no way back to it.
      console.error('Job poll failed:', err);
      setError(apiErrorMessage(err, 'Lost contact with the server. Still trying…'));
    }

    delayRef.current = Math.min(delayRef.current * BACKOFF, MAX_DELAY);
    timerRef.current = setTimeout(poll, delayRef.current);
  }, []);

  const track = useCallback(
    (nextJob) => {
      setError('');
      setJob(nextJob);

      if (!nextJob || isTerminal(nextJob.status)) return;

      jobIdRef.current = nextJob.job_id;
      delayRef.current = FIRST_DELAY;
      clearTimer();
      timerRef.current = setTimeout(poll, FIRST_DELAY);
    },
    [poll]
  );

  /** Submit a job and start tracking whatever comes back. */
  const start = useCallback(
    async (submit) => {
      if (starting || isActive(job?.status)) return undefined;

      setStarting(true);
      setError('');
      try {
        // A double submit returns 202 with the job already in flight, so this
        // attaches to it rather than starting a second expensive run.
        const created = await submit();
        track(created);
        return created;
      } catch (err) {
        console.error('Failed to start job:', err);
        setError(apiErrorMessage(err, 'Could not start. Please try again.'));
        return undefined;
      } finally {
        setStarting(false);
      }
    },
    [starting, job?.status, track]
  );

  // Re-attach on mount. This is what makes a reload, a navigation away and back,
  // or a second tab pick the run up again without anything stored client-side.
  useEffect(() => {
    if (!projectId || !jobType) return undefined;

    let cancelled = false;

    (async () => {
      try {
        const { job: latest } = await jobsAPI.latestForProject(projectId, jobType);
        if (!cancelled && latest && isActive(latest.status)) track(latest);
      } catch (err) {
        // Nothing to re-attach to is the normal case, not a failure.
        console.debug('No job to re-attach:', err?.message);
      }
    })();

    return () => {
      cancelled = true;
      stop();
    };
  }, [projectId, jobType, track, stop]);

  // Poll immediately when a hidden tab is looked at again, rather than making
  // the user wait out the backoff they never saw.
  useEffect(() => {
    const onVisible = () => {
      if (!document.hidden && jobIdRef.current) {
        clearTimer();
        delayRef.current = FIRST_DELAY;
        timerRef.current = setTimeout(poll, 0);
      }
    };

    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [poll]);

  return {
    job,
    error,
    start,
    starting,
    stop,
    active: isActive(job?.status),
    failed: job?.status === 'failed',
    succeeded: job?.status === 'succeeded',
  };
};

export default useJob;
