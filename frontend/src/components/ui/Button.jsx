import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/cn';

// One filled style. The `success` variant was removed: all three of its callers
// were navigation ("View recommended careers", "Download"), not confirmation, so
// a green fill competed with the primary action for the eye while signalling
// nothing. `danger` stays because destructive really is a state.
const VARIANTS = {
  primary: 'btn-brand',
  secondary:
    'bg-surface-2 hover:bg-surface-3 text-fg-secondary hover:text-fg border border-line-strong',
  ghost: 'text-fg-muted hover:text-fg hover:bg-surface-2 border border-transparent',
  danger:
    'bg-danger-subtle hover:bg-danger-subtle text-danger-fg border border-danger-fg/50',
};

// Sizes are the component's business — callers must not pass padding through
// className, because tailwind-merge would drop one axis and keep the other.
const SIZES = {
  xs: 'px-3 py-2 text-xs gap-1.5 rounded-lg',
  sm: 'px-4 py-2.5 text-sm gap-2 rounded-xl',
  md: 'px-5 py-2.5 text-sm gap-2 rounded-xl',
  lg: 'px-6 py-3.5 text-sm gap-2 rounded-xl',
};

/**
 * The single button. Replaces six distinct inline padding combinations and two
 * radii across the app.
 *
 * `type` defaults to "button" so a button inside a form can't submit it by
 * accident — form submit buttons must set type="submit" explicitly.
 */
export const Button = React.forwardRef(
  (
    {
      as: Tag = 'button',
      variant = 'primary',
      size = 'md',
      icon: Icon,
      iconRight: IconRight,
      loading = false,
      loadingText,
      disabled = false,
      fullWidth = false,
      type,
      className,
      children,
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <Tag
        ref={ref}
        type={Tag === 'button' ? type || 'button' : type}
        disabled={Tag === 'button' ? isDisabled : undefined}
        aria-disabled={Tag !== 'button' && isDisabled ? true : undefined}
        aria-busy={loading || undefined}
        className={cn(
          'inline-flex items-center justify-center font-semibold transition-all',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          'disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:transform-none',
          VARIANTS[variant] || VARIANTS.primary,
          SIZES[size] || SIZES.md,
          fullWidth && 'w-full',
          className
        )}
        {...rest}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />
        ) : Icon ? (
          <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
        ) : null}
        <span>{loading && loadingText ? loadingText : children}</span>
        {IconRight && !loading ? <IconRight className="w-4 h-4 shrink-0" aria-hidden="true" /> : null}
      </Tag>
    );
  }
);

Button.displayName = 'Button';

export default Button;
