/**
 * Presentation for background job stages.
 *
 * The server sends a stage key, a percent and a message; this decides what the
 * user reads. Labels live here rather than in the component so the same wording
 * is reused if another page ever renders a job.
 */

export const JOB_GENERATE_RECOMMENDATIONS = 'generate_recommendations';
export const JOB_EXTRACT_SKILLS = 'extract_skills';

const STAGE_LABELS = {
  matching: 'Matching your skills against careers',
  career_summaries: 'Writing your career summaries',
  persisting: 'Saving your matches',
  courses: 'Finding courses to close your gaps',
  extracting: 'Reading your resume',
  saving_skills: 'Saving your skills',
};

export const stageLabel = (stage, fallback = 'Working…') =>
  STAGE_LABELS[stage] || fallback;

export const isTerminal = (status) =>
  status === 'succeeded' || status === 'failed' || status === 'cancelled';

export const isActive = (status) => status === 'queued' || status === 'running';

/**
 * A rough remaining-time estimate, deliberately coarse.
 *
 * Rounded to half minutes and phrased as "about", because a countdown that
 * ticks second by second invites the user to notice every time it is wrong.
 * Returns null rather than guessing before there is enough signal — no estimate
 * is better than one that jumps around.
 */
export const remainingLabel = (percent, elapsedSeconds) => {
  if (!percent || percent < 5 || !elapsedSeconds || elapsedSeconds < 5) return null;

  const projectedTotal = (elapsedSeconds / percent) * 100;
  const remaining = projectedTotal - elapsedSeconds;

  if (remaining <= 20) return 'almost done';
  if (remaining < 90) return 'about a minute left';

  return `about ${Math.round(remaining / 30) / 2} minutes left`;
};
