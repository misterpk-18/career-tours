import React from 'react';
import { cn } from '../../lib/cn';

const VARIANTS = {
  ghost: 'text-fg-muted hover:text-fg hover:bg-surface-2',
  danger: 'text-fg-muted hover:text-danger-fg hover:bg-danger-subtle',
};

const SIZES = {
  sm: 'p-1.5',
  md: 'p-2',
};

/**
 * Icon-only button. `label` is required and becomes the accessible name — every
 * icon-only control in the app previously announced only "button".
 */
export const IconButton = React.forwardRef(
  ({ icon: Icon, label, variant = 'ghost', size = 'md', className, ...rest }, ref) => {
    if (!label) {
      throw new Error('IconButton requires a `label` prop for its accessible name.');
    }

    return (
      <button
        ref={ref}
        type="button"
        aria-label={label}
        title={label}
        className={cn(
          'rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          VARIANTS[variant] || VARIANTS.ghost,
          SIZES[size] || SIZES.md,
          className
        )}
        {...rest}
      >
        <Icon className="w-5 h-5" aria-hidden="true" />
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

export default IconButton;
