import React from 'react';
import SectionLabel from './SectionLabel';

/**
 * Panel for model-generated content, so it reads as distinct from data the app
 * computed itself.
 *
 * A left rule rather than a tinted, bordered, rounded box: nested inside a Card
 * that box was the third of four surface levels, and the amber `Sparkles` on its
 * label read as a warning attached to the text.
 */
export const AiInsightBox = ({ label = 'Why this matches', labelAs = 'h4', className, children }) => (
  <div className={className}>
    <SectionLabel as={labelAs}>{label}</SectionLabel>
    <div className="text-sm text-fg-secondary leading-relaxed border-l-2 border-brand-solid/40 pl-4">
      {children}
    </div>
  </div>
);

export default AiInsightBox;
