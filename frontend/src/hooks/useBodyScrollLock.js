import { useEffect } from 'react';

// Reference counted so nested/stacked locks can't unlock early, and so
// StrictMode's double effect invocation in development stays balanced.
let lockCount = 0;
let previousOverflow = '';
let previousPaddingRight = '';

/** Prevents the page behind a modal from scrolling while `active`. */
export const useBodyScrollLock = (active) => {
  useEffect(() => {
    if (!active) return undefined;

    if (lockCount === 0) {
      const { body } = document;
      previousOverflow = body.style.overflow;
      previousPaddingRight = body.style.paddingRight;

      // Compensate for the scrollbar disappearing, or the page shifts sideways.
      const scrollbar = window.innerWidth - document.documentElement.clientWidth;
      if (scrollbar > 0) {
        body.style.paddingRight = `${scrollbar}px`;
      }
      // overflow:hidden rather than position:fixed — the latter would reset the
      // scroll position when the modal closes.
      body.style.overflow = 'hidden';
    }

    lockCount += 1;

    return () => {
      lockCount -= 1;
      if (lockCount === 0) {
        document.body.style.overflow = previousOverflow;
        document.body.style.paddingRight = previousPaddingRight;
      }
    };
  }, [active]);
};

export default useBodyScrollLock;
