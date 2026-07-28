import React, { useCallback, useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import IconButton from './IconButton';
import useFocusTrap from '../../hooks/useFocusTrap';
import useBodyScrollLock from '../../hooks/useBodyScrollLock';
import { cn } from '../../lib/cn';

const SIZES = { sm: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-3xl' };

/**
 * Accessible dialog. Adopting this fixes, for every modal at once: the missing
 * role/aria-modal/aria-labelledby, no Escape handler, no focus trap, no focus
 * restore, no body scroll lock, no backdrop dismissal, and close buttons with no
 * accessible name.
 *
 * Rendered through a portal so the dialog can't be clipped or re-stacked by a
 * transformed or overflow-hidden ancestor.
 */
export const Modal = ({
  open,
  onClose,
  title,
  description,
  icon: Icon,
  size = 'lg',
  footer,
  initialFocusRef,
  closeOnBackdrop = true,
  children,
}) => {
  const dialogRef = useRef(null);
  const generatedId = useId();
  const titleId = `${generatedId}-title`;
  const descId = `${generatedId}-desc`;

  useFocusTrap(dialogRef, open, initialFocusRef);
  useBodyScrollLock(open);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose?.();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  // mousedown rather than click: a drag that starts inside the dialog and ends
  // on the backdrop would otherwise dismiss it.
  const onBackdropMouseDown = useCallback(
    (event) => {
      if (!closeOnBackdrop) return;
      if (event.target === event.currentTarget) onClose?.();
    },
    [closeOnBackdrop, onClose]
  );

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 scrim animate-fade-in"
      onMouseDown={onBackdropMouseDown}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className={cn(
          'w-full surface-glass rounded-2xl p-6 shadow-e3 border border-line relative',
          // Every modal scrolls internally instead of overflowing the viewport —
          // two of the three previously had no max height at all.
          'max-h-[90vh] flex flex-col',
          SIZES[size] || SIZES.lg
        )}
      >
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-line shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {Icon ? (
              <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center shrink-0">
                <Icon className="w-5 h-5 text-fg-on-solid" aria-hidden="true" />
              </div>
            ) : null}
            <div className="min-w-0">
              <h2 id={titleId} className="text-lg font-bold text-fg">
                {title}
              </h2>
              {description ? (
                <p id={descId} className="text-sm text-fg-muted">
                  {description}
                </p>
              ) : null}
            </div>
          </div>
          <IconButton icon={X} label="Close dialog" size="sm" onClick={onClose} className="shrink-0" />
        </div>

        <div className="py-4 overflow-y-auto flex-1 space-y-4">{children}</div>

        {footer ? (
          <div className="pt-4 flex items-center justify-end gap-3 border-t border-line shrink-0 flex-wrap">
            {footer}
          </div>
        ) : null}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
