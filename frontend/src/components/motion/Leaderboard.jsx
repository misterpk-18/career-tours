import React from 'react';
import { Trophy } from 'lucide-react';
import { cn } from '../../lib/cn';

/**
 * Anonymous XP ranking.
 *
 * Ranks and numbers, never names. That is a deliberate product decision, not an
 * unfinished one: a named board publishes one student's academic standing to
 * another, which cannot be unseen. Rank supplies the motivation; identity would
 * only supply the exposure.
 *
 * The viewer's own row is highlighted and always included, even when it falls
 * outside the top ten — a board that cannot show you yourself is demotivating
 * in the one case where motivation matters most.
 */
export const Leaderboard = ({ entries = [], className }) => {
  if (!entries.length) return null;

  const top = Math.max(...entries.map((e) => e.xp), 1);

  return (
    <div className={cn('space-y-1.5', className)}>
      {entries.map((entry, index) => (
        <div
          key={`${entry.position}-${entry.is_me ? 'me' : index}`}
          className={cn(
            'animate-rise-in relative flex items-center gap-3 overflow-hidden rounded-xl border px-3 py-2',
            entry.is_me
              ? 'border-accent-solid/40 bg-accent-subtle'
              : 'border-line bg-surface-2'
          )}
          style={{ animationDelay: `${Math.min(index, 10) * 35}ms` }}
        >
          {/* A bar behind the row, proportional to XP. Reads as a ranking at a
              glance without a chart. */}
          <div
            className="absolute inset-y-0 left-0 bg-brand-solid/[0.07]"
            style={{ width: `${(entry.xp / top) * 100}%` }}
            aria-hidden="true"
          />

          <span
            className={cn(
              'relative flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold tabular-nums',
              entry.position === 1
                ? 'bg-accent-solid/20 text-accent-fg'
                : 'bg-surface-3 text-fg-muted'
            )}
          >
            {entry.position === 1 ? (
              <Trophy className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              entry.position
            )}
          </span>

          <span
            className={cn(
              'relative flex-1 truncate text-sm',
              entry.is_me ? 'font-semibold text-accent-subtle-fg' : 'text-fg-secondary'
            )}
          >
            {entry.is_me ? 'You' : 'Anonymous student'}
          </span>

          <span className="relative shrink-0 text-sm font-semibold tabular-nums text-fg">
            {entry.xp.toLocaleString()} XP
          </span>
        </div>
      ))}
    </div>
  );
};

export default Leaderboard;
