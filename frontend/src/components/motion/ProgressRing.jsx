import React from 'react';
import { cn } from '../../lib/cn';

/**
 * A circular progress ring, drawn as SVG stroke.
 *
 * `tone` follows the app's colour contract rather than the value: a percentage
 * is not a state, so a section at 40% is not "warning" — it is brand-coloured
 * like everything else. `earned` is the one exception and uses the achievement
 * accent, for the score reveal.
 *
 * The fill animates via stroke-dashoffset, which is a CSS transition and
 * therefore already covered by the reduced-motion block in index.css.
 */
export const ProgressRing = ({
  value = 0,
  max = 100,
  size = 56,
  thickness = 5,
  tone = 'brand',
  label,
  className,
}) => {
  const share = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  const strokes = {
    brand: 'stroke-brand-solid',
    earned: 'stroke-accent-solid',
    success: 'stroke-success-solid',
    muted: 'stroke-fg-muted',
  };

  return (
    <div className={cn('relative inline-flex shrink-0 items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          className="stroke-line"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - share)}
          className={cn(strokes[tone] || strokes.brand, 'transition-[stroke-dashoffset] duration-700 ease-enter')}
        />
      </svg>
      {label ? (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold tabular-nums">
          {label}
        </span>
      ) : null}
    </div>
  );
};

export default ProgressRing;
