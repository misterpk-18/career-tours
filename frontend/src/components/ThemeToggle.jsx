import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { cn } from '../lib/cn';

// A three-way control rather than a two-state switch: once a user taps a
// two-state toggle, "follow my OS" becomes unreachable forever, and that is the
// right default for most people.
const OPTIONS = [
  { value: 'light', Icon: Sun, label: 'Light theme' },
  { value: 'dark', Icon: Moon, label: 'Dark theme' },
  { value: 'system', Icon: Monitor, label: 'Match system theme' },
];

export const ThemeToggle = ({ className }) => {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className={cn(
        'flex items-center gap-0.5 rounded-lg border border-line bg-surface-3 p-0.5',
        className
      )}
    >
      {OPTIONS.map(({ value, Icon, label }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setTheme(value)}
            className={cn(
              'grid h-7 w-7 place-items-center rounded-md transition-colors',
              active
                ? 'bg-surface text-brand-fg shadow-e1'
                : 'text-fg-muted hover:bg-surface/60 hover:text-fg'
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
};

export default ThemeToggle;
