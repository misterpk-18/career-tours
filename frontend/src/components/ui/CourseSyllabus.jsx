import React, { useState } from 'react';
import { ChevronDown, Target } from 'lucide-react';
import Badge from './Badge';
import { cn } from '../../lib/cn';

/**
 * The corpus syllabus for one course: four sections, two modules each.
 *
 * Collapsed by default. A course card is a "should I take this?" surface, and
 * eight modules of detail opened on every card would bury the coverage bar and
 * the rationale that answer that question.
 *
 * Three fields the API returns are deliberately not rendered. `objective` is the
 * same words as `topics`, comma-joined, so showing both prints every module
 * twice. `competency` and `completion_evidence` are the section's two modules'
 * objective and evidence lines concatenated — verified identical for all 160
 * sections — so they would repeat the modules listed directly beneath them.
 * What sections genuinely add is the assessment weight and the marks split,
 * which is what the header here shows.
 */
export const CourseSyllabus = ({ syllabus }) => {
  const [open, setOpen] = useState(false);

  if (!syllabus?.length) return null;

  const moduleCount = syllabus.reduce((total, section) => total + section.modules.length, 0);

  // The corpus states the same assessment split on all four of a course's
  // section headers — true for all 40 — so it is a course-level fact and
  // printing it per section repeats one line four times. Hoisted when the
  // sections agree, left in place if a future corpus ever varies it.
  const assessments = new Set(syllabus.map((section) => section.assessment).filter(Boolean));
  const sharedAssessment = assessments.size === 1 ? [...assessments][0] : null;

  return (
    <div className="border-t border-line pt-4">
      <button
        type="button"
        onClick={() => setOpen((wasOpen) => !wasOpen)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-sm font-semibold text-fg-muted transition-colors hover:text-fg"
      >
        <ChevronDown
          className={cn('w-4 h-4 shrink-0 transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
        <span>What you&apos;ll learn</span>
        <span className="font-normal">
          · {moduleCount} modules in {syllabus.length} sections
        </span>
      </button>

      {open && sharedAssessment && (
        <p className="mt-3 text-2xs leading-relaxed text-fg-muted">
          <span className="font-semibold">Assessed by:</span> {sharedAssessment}
        </p>
      )}

      {open && (
        <ol className="mt-4 space-y-5">
          {syllabus.map((section) => (
            <li key={section.section_code ?? `${section.module_from}-${section.module_to}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <h6 className="text-2xs font-semibold uppercase tracking-wide text-fg-muted">
                  Modules {section.module_from}&ndash;{section.module_to}
                </h6>
                {section.weight_pct != null && (
                  <span className="text-2xs text-fg-muted">
                    {section.weight_pct}% of assessment
                  </span>
                )}
              </div>

              {!sharedAssessment && section.assessment && (
                <p className="mt-1 text-2xs leading-relaxed text-fg-muted">{section.assessment}</p>
              )}

              <ul className="mt-3 space-y-3">
                {section.modules.map((module) => (
                  <li key={module.module_number} className="flex gap-3">
                    <span
                      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-3 text-2xs font-semibold text-fg-muted"
                      aria-hidden="true"
                    >
                      {module.module_number}
                    </span>

                    <div className="min-w-0 space-y-2">
                      <p className="text-sm font-semibold leading-snug text-fg">{module.title}</p>

                      {module.topics?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {module.topics.map((topic) => (
                            <Badge key={topic}>{topic}</Badge>
                          ))}
                        </div>
                      )}

                      {module.observable_evidence && (
                        <p className="flex items-start gap-1.5 text-xs leading-relaxed text-fg-muted">
                          <Target className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
                          <span>{module.observable_evidence}</span>
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};

export default CourseSyllabus;
