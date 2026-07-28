import React from 'react';
import { cn } from '../../lib/cn';

/**
 * Wrapper that makes a group of SelectableCards a real listbox. Required for
 * role="option" to be valid — options must be children of the listbox, so this
 * sits directly around them rather than around the whole column.
 */
export const SelectableList = ({ label, className, children }) => (
  <div role="listbox" aria-label={label} className={cn('space-y-3', className)}>
    {children}
  </div>
);

/**
 * A keyboard-operable selectable card.
 *
 * The inline versions were <div onClick> with no role, tabIndex or key handler,
 * so the five ranked cards on each recommendation page were unreachable by
 * keyboard and announced as static text. Selection was also conveyed by colour
 * and a 1% scale alone; aria-selected now carries it for assistive tech.
 */
export const SelectableCard = ({ selected = false, onSelect, disabled = false, className, children }) => {
  const activate = () => {
    if (!disabled) onSelect?.();
  };

  return (
    <div
      role="option"
      aria-selected={selected}
      tabIndex={disabled ? -1 : 0}
      onClick={activate}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          // Space would otherwise scroll the page.
          event.preventDefault();
          activate();
        }
      }}
      className={cn(
        'surface-glass-interactive p-5 rounded-2xl border transition-all',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
        selected ? 'border-brand-solid bg-surface-2 shadow-e2' : 'border-line',
        className
      )}
    >
      {children}
    </div>
  );
};

export default SelectableCard;
