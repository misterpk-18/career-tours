/**
 * Shared formatting helpers.
 *
 * Postgres `numeric` columns are serialised by Flask as JSON *strings*
 * ("90.00"), because psycopg2 returns Decimal and Flask stringifies it. Every
 * helper here therefore coerces with Number() before doing arithmetic — a raw
 * string silently breaks sums, and `width: "90.00%"` happens to render while
 * `width: "${"85.00" * 1.1}%"` does not.
 */

/** Clamp a percentage-ish value to an integer 0-100. */
export const toPct = (value) => Math.max(0, Math.min(100, Math.round(Number(value) || 0)));

/** Course duration, e.g. 140 -> "140 hrs". Falsy/absent reads as self-paced. */
export const toHours = (value) => (Number(value) ? `${Number(value)} hrs` : 'Self-paced');

/** Sum a numeric field across rows, tolerating string values. */
export const sumBy = (rows, key) =>
  (rows || []).reduce((total, row) => total + (Number(row?.[key]) || 0), 0);

export const formatCurrency = (value) => {
  if (!value) return 'Competitive';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number(value));
};

export const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

/** Deduplicate skills by skill_name, keeping the last occurrence. */
export const deduplicateSkills = (skills) => {
  const seen = new Map();
  for (const skill of skills || []) {
    const key = (skill?.skill_name || '').toLowerCase().trim();
    if (!key) continue;
    seen.set(key, skill);
  }
  return Array.from(seen.values());
};
