import React from 'react';
import { Lock } from 'lucide-react';
import { cn } from '../../lib/cn';

/**
 * The badge shelf, laid out the way a competitive-programming profile lays it
 * out: earned medallions first and full colour, locked ones after and dimmed.
 *
 * Three things carried over from that pattern deliberately:
 *
 * - **A count in the header.** "Badges 5" is the number a student screenshots.
 *   Without it the grid is just decoration.
 * - **Earned first, locked after, in one grid.** Hiding locked badges makes the
 *   shelf look finished at three of eight; a separate collapsed section makes
 *   them feel like an afterthought. Dimmed-in-place says "there are five more
 *   and here is what they take".
 * - **The medallion, not a chip.** A circular emblem reads as something won. A
 *   rounded rectangle with a label reads as a table row.
 *
 * Locked badges keep their criterion visible rather than hiding it behind a
 * hover — a student on a phone has no hover, and the criterion is the only part
 * that tells them what to do next.
 */
export const BadgeShelf = ({ badges = [], className }) => {
  if (!badges.length) return null;

  const earned = badges.filter((b) => b.earned);
  const locked = badges.filter((b) => !b.earned);
  // Earned first, and in the order the API declares them so the shelf does not
  // reshuffle itself every time one is unlocked.
  const ordered = [...earned, ...locked];

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center gap-3">
        <span className="rounded-xl bg-earned-strong px-3 py-1.5 text-lg font-bold tabular-nums text-white shadow-e1">
          {earned.length}
          <span className="text-sm font-semibold opacity-80"> / {badges.length}</span>
        </span>
        <span className="text-sm text-fg-muted">
          badge{badges.length === 1 ? '' : 's'} earned
        </span>
      </div>

      <ul className="grid grid-cols-3 gap-x-3 gap-y-5 sm:grid-cols-4">
        {ordered.map((badge, index) => (
          <li
            key={badge.code}
            className="group animate-rise-in flex flex-col items-center text-center"
            style={{ animationDelay: `${Math.min(index, 10) * 45}ms` }}
          >
            <div
              className={cn(
                'relative flex h-[68px] w-[68px] items-center justify-center rounded-full',
                'transition-transform duration-200 ease-spring',
                badge.earned
                  ? [
                      'bg-earned-strong',
                      // A coin on paper. On a white page a saturated disc with no
                      // elevation reads flat, so the medallion gets three things
                      // the first version lacked: a thick surface-coloured halo
                      // that separates it from the page, a drop shadow tinted with
                      // its own amber rather than neutral grey, and the gloss
                      // highlight below. Together they are the difference between
                      // "a coloured circle" and "something won".
                      'ring-4 ring-surface',
                      'shadow-[0_8px_20px_-8px_rgb(var(--accent-solid)/0.55)]',
                      'group-hover:-translate-y-1 group-hover:scale-[1.07]',
                    ]
                  : [
                      'border-2 border-dashed border-line-strong bg-surface-2',
                      'group-hover:border-line-strong/80',
                    ]
              )}
            >
              {/* Gloss. A top-down white fade over the gradient face, which is
                  what makes an enamel badge look convex instead of printed. */}
              {badge.earned ? (
                <span
                  className="pointer-events-none absolute inset-0 rounded-full bg-gradient-to-b from-white/45 via-white/5 to-transparent"
                  aria-hidden="true"
                />
              ) : null}

              <span
                className={cn(
                  'relative text-[26px] leading-none',
                  badge.earned
                    ? 'drop-shadow-[0_1px_2px_rgb(0_0_0/0.35)]'
                    : 'opacity-30 grayscale'
                )}
                aria-hidden="true"
              >
                {badge.icon}
              </span>

              {!badge.earned ? (
                <span className="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-line bg-surface text-fg-muted">
                  <Lock className="h-2.5 w-2.5" aria-hidden="true" />
                </span>
              ) : null}
            </div>

            <p
              className={cn(
                'mt-2 text-xs font-semibold leading-tight',
                badge.earned ? 'text-fg' : 'text-fg-muted'
              )}
            >
              {badge.name}
            </p>

            <p className="mt-0.5 text-2xs leading-snug text-fg-muted">
              {badge.earned ? 'Earned' : badge.criterion}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default BadgeShelf;
