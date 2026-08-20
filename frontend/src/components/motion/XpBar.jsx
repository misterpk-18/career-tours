import React from 'react';
import { Flame, Sparkles, Trophy } from 'lucide-react';
import CountUp from './CountUp';
import { cn } from '../../lib/cn';

/**
 * Level, XP progress and streak — the achievement strip.
 *
 * Amber throughout, because the revised colour contract reserves the accent for
 * exactly this: things the student earned. Indigo would read as "another panel".
 *
 * Every number here is DERIVED from submitted sittings rather than stored, so
 * this cannot drift from the scores it is computed from. The sheen sweep is
 * decorative and purely CSS, so reduced-motion flattens it with everything else.
 */
export const XpBar = ({ xp = 0, level = 1, xpIntoLevel = 0, xpForLevel = 100, streak = 0, className }) => {
  const share = xpForLevel > 0 ? Math.min(100, (xpIntoLevel / xpForLevel) * 100) : 0;

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border p-4',
        // Light and dark need OPPOSITE treatments here, which is why this is not
        // one token.
        //
        // The tinted wash that reads beautifully on a dark ground (a 0.15-alpha
        // gradient) resolves to almost nothing over rgb(250,251,253) — measured,
        // and it is exactly why this panel looked ordinary in light mode. On
        // white, colour has to be CONCENTRATED to register: a crisp surface, a
        // a real edge and a full-strength gradient rail along the top. The wash
        // separates from the Solarized ground on its own, so no shadow is needed
        // here — the rail and the border do the work.
        'bg-earned border-accent-solid/30',
        className
      )}
    >
      {/* The colour, concentrated. Full-strength brand-to-accent, and the only
          place on this panel the gradient runs at full saturation. */}
      <div className="absolute inset-x-0 top-0 h-[3px] bg-xp" aria-hidden="true" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {/* Filled Solarized yellow with base03 text on it — 4.68:1, and the
              way round Solarized intends for a filled control. */}
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-solid text-fg-on-solid shadow-e1">
            <Trophy className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="leading-tight">
            <p className="text-base font-bold text-fg">Level {level}</p>
            {/* accent-fg is Solarized yellow lifted 42% toward base2 — 5.29:1 at
                worst across every surface this can sit on. The raw yellow is
                4.68 on canvas and would fail here. */}
            <p className="text-xs font-semibold text-accent-fg">
              <CountUp value={xp} /> XP earned
            </p>
          </div>
        </div>

        {streak > 0 ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-solid/45 bg-accent-subtle px-3 py-1.5 text-xs font-bold text-accent-subtle-fg">
            <Flame className="h-3.5 w-3.5 animate-flame-flicker" aria-hidden="true" />
            {streak} day{streak === 1 ? '' : 's'}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Submit a section to start a streak
          </span>
        )}
      </div>

      <div className="mt-3 space-y-1.5">
        <div className="relative h-3 overflow-hidden rounded-full bg-surface-3 ring-1 ring-inset ring-line">
          <div
            className="h-full rounded-full bg-xp transition-[width] duration-700 ease-enter"
            style={{ width: `${share}%` }}
          />
          {/* Sheen only when there is a bar to sweep across. */}
          {share > 6 ? (
            <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-full">
              <div className="h-full w-1/3 animate-sheen bg-sheen" />
            </div>
          ) : null}
        </div>
        <p className="text-2xs uppercase tracking-wider text-fg-muted">
          {xpIntoLevel} / {xpForLevel} XP to level {level + 1}
        </p>
      </div>
    </div>
  );
};

export default XpBar;
