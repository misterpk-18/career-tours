import React, { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '../../hooks/useReducedMotion';

/**
 * A number that counts up to its value.
 *
 * Used for scores and XP, where the number IS the reward and arriving at it
 * instantly wastes the only moment the student is looking. Decelerates, so the
 * last few digits land slowly and the final value is what the eye rests on.
 *
 * Honours prefers-reduced-motion by rendering the value immediately — a
 * requestAnimationFrame loop is invisible to the CSS media query that handles
 * the rest of the app's motion.
 */
export const CountUp = ({ value = 0, duration = 900, className, format = (n) => n }) => {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? value : 0);
  const frame = useRef();

  useEffect(() => {
    if (reduced) {
      setShown(value);
      return undefined;
    }

    const from = 0;
    const started = performance.now();

    const tick = (now) => {
      const progress = Math.min(1, (now - started) / duration);
      // Cubic ease-out: fast start, slow landing.
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(Math.round(from + (value - from) * eased));
      if (progress < 1) frame.current = requestAnimationFrame(tick);
    };

    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [duration, reduced, value]);

  return (
    <span className={className} style={{ fontVariantNumeric: 'tabular-nums' }}>
      {format(shown)}
    </span>
  );
};

export default CountUp;
