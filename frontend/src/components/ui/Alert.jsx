import React from 'react';
import { AlertCircle, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import { cn } from '../../lib/cn';

const TONES = {
  error: { box: 'bg-danger-subtle border-danger-fg/50 text-danger-fg', Icon: AlertCircle, role: 'alert' },
  success: { box: 'bg-success-subtle border-success-fg/50 text-success-fg', Icon: CheckCircle2, role: 'status' },
  warning: { box: 'bg-warning-subtle border-warning-fg/50 text-warning-fg', Icon: AlertTriangle, role: 'status' },
  info: { box: 'bg-brand-subtle border-brand-solid/40 text-brand-subtle-fg', Icon: Info, role: 'status' },
};

const SIZES = {
  sm: 'p-3 text-sm rounded-xl gap-2',
  md: 'p-4 text-sm rounded-xl gap-3',
};

/**
 * Replaces six divergent inline alert spellings that used three paddings and two
 * radii. `role="alert"` on the error tone means a failure is announced without
 * the user having to go looking for it.
 */
export const Alert = ({ tone = 'error', size = 'md', icon, action, className, children }) => {
  const { box, Icon, role } = TONES[tone] || TONES.error;
  const Glyph = icon || Icon;

  return (
    <div
      role={role}
      className={cn('border flex items-start', box, SIZES[size] || SIZES.md, className)}
    >
      <Glyph className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
      <div className="flex-1 min-w-0">{children}</div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
};

export default Alert;
