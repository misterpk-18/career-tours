import React, { useEffect, useRef, useState } from 'react';
import { ClipboardCheck, Layers, Lock, Play, RefreshCw, RotateCcw } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';
import Alert from './ui/Alert';
import Modal from './ui/Modal';
import SectionHeading from './ui/SectionHeading';
import XpBar from './motion/XpBar';
import ProgressRing from './motion/ProgressRing';
import { cn } from '../lib/cn';

/**
 * The section list a student sits a course from — one row per section, with the
 * button the server's state dictates:
 *
 *   no row             -> Start test        (never attempted)
 *   in_progress/paused -> Continue / Start new
 *   submitted          -> Practice          (score is locked)
 *
 * Shared by the project track (ProjectCoursePage) and the project-independent
 * course track (CourseJourneyPage). The two differ only in where the sittings
 * live and where the buttons navigate; that difference is entirely in the
 * `onStart` callback and the `xp`/`progress` the parent supplies, so the list,
 * the badges and the "start new" confirm modal are written once here.
 */

const MARKS_TONE = (awarded, available) => {
  if (awarded == null || !available) return 'neutral';
  const share = awarded / available;
  if (share >= 0.7) return 'success';
  if (share >= 0.4) return 'warning';
  return 'danger';
};

export const SectionAssessment = ({
  title = 'Sections',
  sections = [],
  progress = {},
  xp = null,
  starting = '',
  error = '',
  onStart,
  focusSection = null,
}) => {
  // "Start new" is destructive (it discards an in-progress attempt), so it asks
  // first; every other action is immediate.
  const [deciding, setDeciding] = useState(null);

  // When the student arrives here via "Continue to next section", that section
  // is named so it can be scrolled to and ringed briefly — a nudge, not a state.
  const sectionRefs = useRef({});
  const [highlight, setHighlight] = useState(null);
  useEffect(() => {
    if (!focusSection) return undefined;
    const node = sectionRefs.current[focusSection];
    if (node) node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setHighlight(focusSection);
    const timer = setTimeout(() => setHighlight(null), 2500);
    return () => clearTimeout(timer);
  }, [focusSection]);

  const open = (sectionCode, opts) => {
    setDeciding(null);
    onStart(sectionCode, opts);
  };

  return (
    <div className="space-y-6">
      {xp ? (
        <XpBar
          xp={xp.xp}
          level={xp.level}
          xpIntoLevel={xp.xp_into_level}
          xpForLevel={xp.xp_for_level}
          streak={xp.streak}
          className="animate-rise-in"
        />
      ) : null}

      {error ? <Alert tone="error">{error}</Alert> : null}

      <SectionHeading as="h2" icon={Layers} iconClassName="text-brand-fg">
        {title}
      </SectionHeading>

      <ul className="space-y-4">
        {sections.map((section, index) => {
          const state = progress[section.section_code];
          const status = state?.graded_status;
          const isSubmitted = status === 'submitted';
          const isOpen = status === 'in_progress' || status === 'paused';
          const busy = starting === section.section_code;

          return (
            <li
              key={section.section_code ?? index}
              ref={(node) => {
                if (section.section_code) sectionRefs.current[section.section_code] = node;
              }}
              className={cn(
                'animate-rise-in scroll-mt-24 rounded-2xl transition-shadow duration-500',
                highlight === section.section_code &&
                  'ring-2 ring-focus ring-offset-2 ring-offset-canvas'
              )}
              style={{ animationDelay: `${Math.min(index, 10) * 60}ms` }}
            >
              <Card as="section" padding="lg" lift className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-fg-muted">
                        {section.section_code}
                      </span>
                      {section.weight_pct != null ? (
                        <Badge>{section.weight_pct}% of assessment</Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-fg">
                      Section {index + 1} ·{' '}
                      {section.modules?.map((m) => m.title).join(' + ') || 'two modules'}
                    </p>
                  </div>

                  {isSubmitted ? (
                    <div className="flex items-center gap-2.5">
                      <Badge tone={MARKS_TONE(state.marks_awarded, state.marks_available)} mono>
                        {state.marks_awarded}/{state.marks_available}
                      </Badge>
                      <ProgressRing
                        value={state.marks_awarded}
                        max={state.marks_available}
                        size={40}
                        thickness={4}
                        tone={
                          state.marks_awarded / state.marks_available >= 0.7 ? 'earned' : 'brand'
                        }
                      />
                    </div>
                  ) : isOpen ? (
                    <Badge tone="warning">
                      {status === 'paused' ? 'Paused' : 'In progress'}
                    </Badge>
                  ) : (
                    <Badge tone="neutral">Not started</Badge>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
                  {isSubmitted ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={RefreshCw}
                        loading={busy}
                        onClick={() => open(section.section_code, { mode: 'practice' })}
                      >
                        {state.open_practice_sitting_id ? 'Resume practice' : 'Practice'}
                      </Button>
                      <span className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
                        <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                        Score locked
                        {state.practice_runs > 0
                          ? ` · ${state.practice_runs} practice run${state.practice_runs === 1 ? '' : 's'}`
                          : ''}
                      </span>
                    </>
                  ) : isOpen ? (
                    <>
                      <Button
                        size="sm"
                        icon={Play}
                        loading={busy}
                        onClick={() => open(section.section_code)}
                      >
                        Continue previous attempt
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={RotateCcw}
                        onClick={() => setDeciding(section)}
                      >
                        Start new
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      icon={ClipboardCheck}
                      loading={busy}
                      onClick={() => open(section.section_code)}
                    >
                      Start test
                    </Button>
                  )}
                </div>
              </Card>
            </li>
          );
        })}
      </ul>

      {/* "Start new" throws away answers and cannot be undone, so it asks.
          Continue does not, so it does not. */}
      <Modal
        open={Boolean(deciding)}
        onClose={() => setDeciding(null)}
        title="Start a new attempt?"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-secondary">
            This discards your previous attempt at{' '}
            <span className="font-mono text-fg">{deciding?.section_code}</span> and every answer
            in it, and the new attempt starts with the full 20 minutes. Your previous answers
            cannot be recovered.
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setDeciding(null)}>
              Keep my attempt
            </Button>
            <Button
              variant="danger"
              size="sm"
              icon={RotateCcw}
              loading={Boolean(starting)}
              onClick={() => open(deciding.section_code, { restart: true })}
            >
              Discard and start new
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SectionAssessment;
