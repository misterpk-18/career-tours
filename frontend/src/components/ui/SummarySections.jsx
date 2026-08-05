import React from 'react';
import { cn } from '../../lib/cn';
import Chip from './Chip';

/**
 * Renders the typed sections of an LLM summary.
 *
 * `sections` is an ordered list of `{ label, text }` (a paragraph) or
 * `{ label, items, tone }` (chips). Sections whose value is empty are dropped
 * rather than rendered as a bare heading — the model does occasionally return an
 * empty list for, say, skill_gaps, and a labelled void reads as a bug.
 *
 * Prose summaries go straight into `<AiInsightBox>`; this handles the structured
 * shape the API returns as `summary.structured`.
 */
export const SummarySections = ({ sections = [], className }) => {
  const filled = sections.filter((section) =>
    Array.isArray(section.items) ? section.items.length > 0 : Boolean(section.text)
  );

  if (filled.length === 0) return null;

  return (
    <div className={cn('space-y-4', className)}>
      {filled.map(({ label, text, items, tone }) => (
        <div key={label}>
          <div className="text-xs font-semibold text-fg-secondary mb-1.5">
            {label}
          </div>
          {Array.isArray(items) ? (
            <ul className="flex flex-wrap gap-2">
              {items.map((item) => (
                <li key={item}>
                  <Chip tone={tone || 'neutral'}>{item}</Chip>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-relaxed">{text}</p>
          )}
        </div>
      ))}
    </div>
  );
};

export default SummarySections;
