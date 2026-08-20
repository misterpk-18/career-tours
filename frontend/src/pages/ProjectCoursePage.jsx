import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ClipboardCheck,
  Layers,
  Lock,
  Play,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import { catalogueAPI, projectsAPI, sittingsAPI } from '../services/api';
import PageShell from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import SectionHeading from '../components/ui/SectionHeading';
import Modal from '../components/ui/Modal';
import ProgressRing from '../components/motion/ProgressRing';
import XpBar from '../components/motion/XpBar';
import CountUp from '../components/motion/CountUp';
import { achievementsAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';
import { cn } from '../lib/cn';

/**
 * One course inside one project: the syllabus, and the test for each section.
 *
 * Project-scoped rather than an addition to the catalogue's course page,
 * because a score belongs to a project and a student may hold several. A page
 * that had to guess which project was "active" would eventually file a score
 * against the wrong one, and a locked score cannot be moved.
 *
 * A section's button is decided entirely by what the server says about it:
 *
 *   no row            -> Start test        (never attempted)
 *   in_progress/paused -> Continue / Start new
 *   submitted          -> Practice         (score is locked)
 *
 * Sections the student has not touched are ABSENT from /progress rather than
 * returned with zeros, which is deliberate on the server side — it keeps "not
 * started" distinguishable from "scored nothing" — so a missing row here means
 * not started and must not be read as a zero score.
 */

const MARKS_TONE = (awarded, available) => {
  if (awarded == null || !available) return 'neutral';
  const share = awarded / available;
  if (share >= 0.7) return 'success';
  if (share >= 0.4) return 'warning';
  return 'danger';
};

export const ProjectCoursePage = () => {
  const { projectId, courseId } = useParams();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [project, setProject] = useState(null);
  // Keyed by section_code. Absent key means the section was never started.
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState('');
  const [achievements, setAchievements] = useState(null);
  // The section a "continue or start new" decision is pending for.
  const [deciding, setDeciding] = useState(null);

  const loadProgress = useCallback(async () => {
    const rows = await sittingsAPI.progress(projectId);
    setProgress(Object.fromEntries(rows.map((row) => [row.section_code, row])));
    // XP is derived from submitted sittings, so it changes the moment a score
    // lands. Re-read it here rather than leaving the strip showing a total that
    // predates the section the student just finished.
    achievementsAPI.mine().then(setAchievements).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        // In parallel: none of the three depends on another, and serialising
        // them would show a spinner for the sum of three round trips.
        const [courseData, projectData, rows, earned] = await Promise.all([
          catalogueAPI.getCourse(courseId),
          projectsAPI.getById(projectId),
          sittingsAPI.progress(projectId),
          // Achievements are decoration, not the page: a failure here must not
          // stop the syllabus rendering, so it resolves to null instead of
          // rejecting the whole Promise.all.
          achievementsAPI.mine().catch(() => null),
        ]);
        if (cancelled) return;
        setCourse(courseData);
        setProject(projectData);
        setProgress(Object.fromEntries(rows.map((row) => [row.section_code, row])));
        setAchievements(earned);
      } catch (err) {
        console.error('Failed to load the course for this project:', err);
        if (!cancelled) setError(apiErrorMessage(err, 'Unable to load this course.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [courseId, projectId]);

  const open = useCallback(
    async (sectionCode, { mode = 'graded', restart = false } = {}) => {
      setStarting(sectionCode);
      setError('');
      try {
        const { sitting } = await sittingsAPI.start(projectId, sectionCode, { mode, restart });
        navigate(`/projects/${projectId}/sittings/${sitting.sitting_id}`);
      } catch (err) {
        console.error('Failed to start the sitting:', err);
        // A 409 here is meaningful, not a crash: the section was submitted
        // while this page was open, or the attempt expired. Re-reading progress
        // makes the button correct itself rather than staying wrong.
        setError(apiErrorMessage(err, 'Unable to start this test.'));
        loadProgress().catch(() => {});
      } finally {
        setStarting('');
        setDeciding(null);
      }
    },
    [loadProgress, navigate, projectId]
  );

  // Course-level totals, from the same rows the section badges use — one source
  // for both, so the ring and the badges can never disagree.
  const courseMarks = Object.values(progress).reduce(
    (totals, row) =>
      row.graded_status === 'submitted'
        ? {
            awarded: totals.awarded + (row.marks_awarded ?? 0),
            available: totals.available + (row.marks_available ?? 0),
            submitted: totals.submitted + 1,
          }
        : totals,
    { awarded: 0, available: 0, submitted: 0 }
  );

  if (loading) return <PageSpinner label="Loading course" />;

  if (error && !course) {
    return (
      <PageShell>
        <Alert tone="error">{error}</Alert>
      </PageShell>
    );
  }

  const syllabus = course?.syllabus ?? [];

  return (
    <PageShell>
      <div className="space-y-6">
        <Link
          to={`/projects/${projectId}/courses`}
          className="inline-flex items-center gap-2 text-sm font-medium text-fg-muted transition-colors hover:text-fg"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to recommended courses
        </Link>

        <div className="flex flex-wrap items-center justify-between gap-5">
          <div className="animate-rise-in space-y-2">
            <h1 className="text-3xl font-bold text-fg">{course?.course_name}</h1>
            <p className="text-sm text-fg-muted">
              {project?.project_name ? `${project.project_name} · ` : ''}
              {syllabus.length} sections · each test is 10 questions, 30 marks, 20 minutes
            </p>
          </div>

          {/* Course completion at a glance. Brand, not accent: a percentage is
              not an achievement, and the contract keeps amber for things earned. */}
          {courseMarks.available > 0 ? (
            <div className="flex items-center gap-3">
              <ProgressRing
                value={courseMarks.awarded}
                max={courseMarks.available}
                size={64}
                thickness={6}
                label={
                  <CountUp
                    value={Math.round((courseMarks.awarded / courseMarks.available) * 100)}
                    format={(n) => `${n}%`}
                  />
                }
              />
              <div className="text-xs leading-tight text-fg-muted">
                <p className="font-semibold text-fg">
                  {courseMarks.submitted} of {syllabus.length} sections
                </p>
                <p>
                  {courseMarks.awarded} / {courseMarks.available} marks
                </p>
              </div>
            </div>
          ) : null}
        </div>

        {achievements ? (
          <XpBar
            xp={achievements.xp}
            level={achievements.level}
            xpIntoLevel={achievements.xp_into_level}
            xpForLevel={achievements.xp_for_level}
            streak={achievements.streak}
            className="animate-rise-in"
          />
        ) : null}

        {error ? (
          <Alert tone="error">{error}</Alert>
        ) : null}

        <SectionHeading as="h2" icon={Layers} iconClassName="text-brand-fg">
          Sections
        </SectionHeading>

        <ul className="space-y-4">
          {syllabus.map((section, index) => {
            const state = progress[section.section_code];
            const status = state?.graded_status;
            const isSubmitted = status === 'submitted';
            const isOpen = status === 'in_progress' || status === 'paused';
            const busy = starting === section.section_code;

            return (
              <li
                key={section.section_code ?? index}
                className="animate-rise-in"
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
      </div>

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
    </PageShell>
  );
};

export default ProjectCoursePage;
