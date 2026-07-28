import React from 'react';
import { Sparkles } from 'lucide-react';
import SectionLabel from './SectionLabel';
import { cn } from '../../lib/cn';

/** Tinted panel for LLM-generated prose, so AI output is visually distinct. */
export const AiInsightBox = ({ label = 'AI Strategic Insights', labelAs = 'h4', className, children }) => (
  <div className={className}>
    <SectionLabel as={labelAs} icon={Sparkles} iconClassName="text-warning-fg">
      {label}
    </SectionLabel>
    <div
      className={cn(
        'text-sm text-fg-secondary leading-relaxed bg-brand-subtle/40 p-4 rounded-xl border border-brand-solid/25'
      )}
    >
      {children}
    </div>
  </div>
);

export default AiInsightBox;
