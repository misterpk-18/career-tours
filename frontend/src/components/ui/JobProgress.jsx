import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import ProgressBar from './ProgressBar';
import Alert from './Alert';
import { isTerminal, remainingLabel, stageLabel } from '../../lib/jobStages';

/**
 * Live state of a background job.
 *
 * The bar stays `brand` at every percentage. Percent complete is not a
 * success/warning/danger signal, and colouring it green near the end would
 * spend the palette's meaning on something that carries none. Only an actual
 * failure switches tone.
 *
 * A failed job arrives as a normal 200 response with `status: "failed"`, so
 * this branches on the field rather than expecting an error to have been thrown
 * upstream.
 */
export const JobProgress = ({ job, className }) => {
  const [elapsed, setElapsed] = useState(0);

  const startedAt = job?.started_at || job?.created_at;
  const running = job && !isTerminal(job.status);

  useEffect(() => {
    if (!running || !startedAt) return undefined;

    // Parsed as UTC: the API serialises naive timestamps, which JS would
    // otherwise read as local time and produce a wildly wrong elapsed.
    const startMs = Date.parse(`${startedAt}Z`);
    const tick = () => setElapsed(Math.max(0, (Date.now() - startMs) / 1000));

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [running, startedAt]);

  if (!job) return null;

  if (job.status === 'failed' || job.status === 'cancelled') {
    return (
      <Alert tone={job.status === 'failed' ? 'error' : 'warning'} className={className}>
        {job.error || 'The run did not finish. Please try again.'}
      </Alert>
    );
  }

  if (job.status === 'succeeded') return null;

  const eta = remainingLabel(job.percent, elapsed);
  const label = stageLabel(job.stage, 'Getting started…');
  const counter =
    job.stage_total > 1 ? ` (${job.stage_done ?? 0} of ${job.stage_total})` : '';

  return (
    <Alert tone="info" icon={Loader2} className={className}>
      <div className="space-y-2">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-semibold">
            {label}
            {counter}
          </span>
          <span className="text-xs tabular-nums shrink-0">{job.percent}%</span>
        </div>

        <ProgressBar value={job.percent} label={null} />

        <p className="text-xs opacity-80">
          {eta ? `${eta} — ` : ''}this keeps running if you leave this page.
        </p>
      </div>
    </Alert>
  );
};

export default JobProgress;
