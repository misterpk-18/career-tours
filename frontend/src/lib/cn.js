import { clsx } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

/**
 * tailwind-merge validates against Tailwind's DEFAULT theme, so it does not know
 * about this project's custom scale and semantic colour names. Two collisions
 * have to be taught explicitly, or `cn` resolves them wrong:
 *
 *   1. `text-2xs` is not a known font size, so twMerge classifies it as a text
 *      COLOUR — meaning `cn('text-base', 'text-2xs')` keeps both instead of
 *      letting the later size win.
 *   2. `text-fg-muted`, `text-brand-fg` etc. are multi-segment colour names that
 *      twMerge would otherwise read as font sizes for the same reason.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': [{ text: ['2xs'] }],
      'text-color': [
        {
          text: [
            'fg',
            'fg-secondary',
            'fg-muted',
            'fg-on-solid',
            'brand-fg',
            'brand-subtle-fg',
            'accent-fg',
            'success-fg',
            'warning-fg',
            'danger-fg',
          ],
        },
      ],
    },
  },
});

/**
 * Merge conditional class names, with later Tailwind utilities beating earlier
 * ones in the same group.
 *
 * Note twMerge knows nothing about the hand-written component classes in
 * index.css (`surface-glass`, `btn-brand`, `field`, …). Passing two of those
 * together produces a real cascade conflict it cannot resolve, so components
 * should expose a prop for that choice rather than accepting it via className.
 */
export const cn = (...inputs) => twMerge(clsx(inputs));

export default cn;
