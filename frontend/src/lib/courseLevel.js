/**
 * `courses.level` is free-form text in the database. Real values observed
 * include "Beginner", "Intermediate" and "Beginner to Intermediate", so this
 * matches on substrings rather than exact keys — an exact-key map left the
 * spanning phrases on the neutral fallback.
 *
 * Checked high-to-low: a range is coloured by the highest level it reaches.
 */
const LEVEL_TONES = [
  ['advanced', 'bg-accent-fg/10 border-accent-fg/40 text-accent-fg'],
  ['intermediate', 'bg-warning-subtle border-warning-fg/40 text-warning-fg'],
  ['beginner', 'bg-success-subtle border-success-fg/40 text-success-fg'],
];

const FALLBACK_TONE = 'bg-surface-3 border-line-strong text-fg-secondary';

export const levelTone = (level) => {
  const normalized = String(level || '').toLowerCase();
  const match = LEVEL_TONES.find(([keyword]) => normalized.includes(keyword));
  return match ? match[1] : FALLBACK_TONE;
};

export default levelTone;
