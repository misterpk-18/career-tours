import { useEffect, useRef } from 'react';

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * Confines Tab/Shift+Tab to `containerRef` while `active`, moves focus in on
 * activation, and restores it to the previously focused element on teardown.
 *
 * Written to be idempotent because React StrictMode double-invokes effects in
 * development: the previously-focused element is captured in a ref rather than
 * recomputed, so a second invocation cannot overwrite it with the dialog itself.
 */
export const useFocusTrap = (containerRef, active, initialFocusRef) => {
  const previouslyFocused = useRef(null);
  const restoreHandle = useRef(0);

  useEffect(() => {
    if (!active) return undefined;

    const container = containerRef.current;
    if (!container) return undefined;

    // A StrictMode double-invoke tears the trap down and sets it back up. The
    // teardown queues a focus restore, which would otherwise land AFTER this
    // re-run's focus-in and pull focus back out of the open dialog.
    if (restoreHandle.current) {
      cancelAnimationFrame(restoreHandle.current);
      restoreHandle.current = 0;
    }

    if (!previouslyFocused.current) {
      previouslyFocused.current = document.activeElement;
    }

    const focusables = () => Array.from(container.querySelectorAll(FOCUSABLE)).filter((el) => el.offsetParent !== null || el === document.activeElement);

    const target = initialFocusRef?.current || focusables()[0] || container;
    target.focus?.();

    const onKeyDown = (event) => {
      if (event.key !== 'Tab') return;

      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        return;
      }

      const first = items[0];
      const last = items[items.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    container.addEventListener('keydown', onKeyDown);

    return () => {
      container.removeEventListener('keydown', onKeyDown);
      const restore = previouslyFocused.current;
      // Restore asynchronously: the trigger may still be unmounting this tick.
      // previouslyFocused is cleared inside the callback, not here, so a
      // cancelled restore (see the StrictMode note above) keeps the trigger.
      if (restore?.focus) {
        restoreHandle.current = requestAnimationFrame(() => {
          restoreHandle.current = 0;
          previouslyFocused.current = null;
          restore.focus();
        });
      }
    };
  }, [active, containerRef, initialFocusRef]);
};

export default useFocusTrap;
