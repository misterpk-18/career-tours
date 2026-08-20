import { useEffect, useState } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

/**
 * Whether this visitor asked for less motion.
 *
 * index.css flattens every CSS animation and transition to 0.01ms under this
 * media query, which covers everything driven by a class. It cannot cover
 * anything driven by JavaScript — a requestAnimationFrame counter, a canvas
 * burst — so those have to ask, and this is how they ask.
 *
 * Read once up front rather than assumed false: a component that animates on
 * mount has already animated by the time an effect could correct it.
 */
export const useReducedMotion = () => {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.(QUERY).matches
  );

  useEffect(() => {
    const media = window.matchMedia?.(QUERY);
    if (!media) return undefined;

    const onChange = (event) => setReduced(event.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  return reduced;
};

export default useReducedMotion;
