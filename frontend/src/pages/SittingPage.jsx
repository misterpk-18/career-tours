import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Flag,
  LogOut,
  Pause,
  Play,
  X,
} from 'lucide-react';
import { sittingsAPI, courseSittingsAPI, catalogueAPI } from '../services/api';
import PageSpinner from '../components/ui/PageSpinner';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import Modal from '../components/ui/Modal';
import QuestionContent from '../components/QuestionContent';
import CountUp from '../components/motion/CountUp';
import ProgressRing from '../components/motion/ProgressRing';
import Celebration from '../components/motion/Celebration';
import { cn } from '../lib/cn';

/**
 * One sitting: ten questions, one per screen, then a review step and submit.
 *
 * The review step exists because submit is irreversible for a graded sitting —
 * the score locks and no second graded sitting can ever exist for the section.
 * A blank nobody noticed is a permanent cost, so the last screen lists every
 * question with its answer and says plainly how many are unanswered.
 *
 * Three things are the server's business and are deliberately not reimplemented
 * here:
 *
 * - **The clock.** `seconds_remaining` arrives from the server and is ticked
 *   down locally for display only. Every mutation re-reads it from the response,
 *   so a tab that slept, a clock the user changed, or a stale render cannot buy
 *   time. When the local countdown hits zero we ask the server rather than
 *   deciding ourselves.
 * - **The answer key.** A graded sitting in progress is never told which option
 *   is correct — the payload simply omits it — so there is nothing here to leak.
 * - **The shuffle.** Options arrive in this sitting's own order and answers are
 *   sent back as the letters shown. The mapping back to the corpus is the
 *   server's, recomputed from the sitting id.
 */

const LABELS = ['A', 'B', 'C', 'D'];

const formatClock = (seconds) => {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  return `${String(minutes).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`;
};

export const SittingPage = ({ scope = 'project' }) => {
  const { projectId, courseId, sittingId } = useParams();
  const navigate = useNavigate();

  const isCourse = scope === 'course';

  // One adapter over the two tracks. The project track's calls carry a
  // project id; the course track's are keyed on the sitting alone, its owner
  // taken from the token. Every call site below goes through this, so the page
  // itself is scope-agnostic.
  const api = useMemo(
    () =>
      isCourse
        ? {
            get: () => courseSittingsAPI.get(sittingId),
            save: (answers) => courseSittingsAPI.saveAnswers(sittingId, answers),
            pause: () => courseSittingsAPI.pause(sittingId),
            resume: () => courseSittingsAPI.resume(sittingId),
            submit: () => courseSittingsAPI.submit(sittingId),
          }
        : {
            get: () => sittingsAPI.get(projectId, sittingId),
            save: (answers) => sittingsAPI.saveAnswers(projectId, sittingId, answers),
            pause: () => sittingsAPI.pause(projectId, sittingId),
            resume: () => sittingsAPI.resume(projectId, sittingId),
            submit: () => sittingsAPI.submit(projectId, sittingId),
          },
    [isCourse, projectId, sittingId]
  );

  // Where the result screen and the toolbar Exit point. "Exit" leaves the
  // course entirely (the catalogue list, or the project's recommended courses);
  // "back to the course" and "continue" return to this course's page.
  const exitUrl = isCourse ? '/courses' : `/projects/${projectId}/courses`;

  const [sitting, setSitting] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [index, setIndex] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(null);
  const [remaining, setRemaining] = useState(0);
  // Which way the last navigation went, so the incoming question slides in from
  // the side it came from. Without this, Previous and Next feel identical and
  // the animation stops carrying information.
  const [direction, setDirection] = useState('forward');

  // Answers the student has chosen, as the letters they saw. Held alongside the
  // server's copy so a click paints immediately rather than after a round trip.
  const [chosen, setChosen] = useState({});

  const apply = useCallback((payload) => {
    setSitting(payload.sitting);
    setRemaining(payload.sitting.seconds_remaining);
    if (payload.questions) {
      setQuestions(payload.questions);
      setChosen(
        Object.fromEntries(
          payload.questions
            .filter((q) => q.answered_option)
            .map((q) => [q.question_id, q.answered_option])
        )
      );
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const data = await api.get();
        if (!cancelled) apply(data);
      } catch (err) {
        console.error('Failed to load the sitting:', err);
        if (!cancelled) setError('Unable to load this test.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [apply, api]);

  const isRunning = sitting?.status === 'in_progress';
  const isSubmitted = sitting?.status === 'submitted';
  const isPractice = sitting?.mode === 'practice';

  // Where "Continue" and "Back to the course" point after a submit. The sitting
  // only knows its own section_code (e.g. NT-C-023-S01); the course id and the
  // ordered section list live in the catalogue, so resolve them once the result
  // screen is showing. Section codes embed the course code, so the lookup is
  // code -> course_id -> syllabus, then the section AFTER this one, if any.
  //
  // Resolved only when submitted — an in-progress test needs neither, and this
  // keeps two cross-region calls off the answering path. A failure is
  // non-fatal: the result still renders and the buttons fall back to the list.
  const [courseNav, setCourseNav] = useState(null);
  useEffect(() => {
    if (!isSubmitted || !sitting?.section_code || courseNav) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const code = sitting.section_code;
        const courseCode = code.replace(/-S\d+$/, '');
        const courses = await catalogueAPI.listCourses();
        const match = courses.find((c) => c.course_code === courseCode);
        if (!match) {
          if (!cancelled) setCourseNav({ courseId: null, nextSectionCode: null });
          return;
        }
        const detail = await catalogueAPI.getCourse(match.course_id);
        const syllabus = detail?.syllabus ?? [];
        const i = syllabus.findIndex((s) => s.section_code === code);
        const next = i >= 0 ? syllabus[i + 1]?.section_code : undefined;
        if (!cancelled) {
          setCourseNav({ courseId: match.course_id, nextSectionCode: next || null });
        }
      } catch (err) {
        console.error('Could not resolve the next section:', err);
        if (!cancelled) setCourseNav({ courseId: null, nextSectionCode: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSubmitted, sitting, courseNav]);

  // This course's page. In the course track the id is already in the URL; in
  // the project track it is whatever the resolver above found. Falls back to
  // the exit target if the course could not be resolved.
  const resolvedCourseId = isCourse ? courseId : courseNav?.courseId;
  const coursePageUrl = resolvedCourseId
    ? (isCourse
        ? `/courses/${resolvedCourseId}`
        : `/projects/${projectId}/courses/${resolvedCourseId}`)
    : exitUrl;

  // Display-only countdown. The server holds the real clock; this just stops
  // the number looking frozen between requests.
  useEffect(() => {
    if (!isRunning) return undefined;
    const timer = setInterval(() => setRemaining((left) => Math.max(0, left - 1)), 1000);
    return () => clearInterval(timer);
  }, [isRunning]);

  // Local zero is a prompt to ask the server, not a verdict. The server
  // auto-submits an expired sitting on any read, so one request settles it.
  useEffect(() => {
    if (!isRunning || remaining > 0) return;
    api
      .get()
      .then(apply)
      .catch(() => {});
  }, [apply, api, isRunning, remaining]);

  // Leaving costs time, so say so. Best-effort by design: the browser only
  // allows a generic prompt, and a crash or a killed tab never fires it at all
  // — which is exactly why the clock keeps running server-side.
  useEffect(() => {
    if (!isRunning) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = '';
      return '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [isRunning]);

  // beforeunload covers closing the tab and reloading, but NOT an in-app
  // navigation: clicking "Courses" in the rail is a react-router transition, the
  // page never unloads, and the student would leave a running test with no
  // warning at all. Caught here at the capture phase, before the router sees the
  // click.
  //
  // The browser's own Back button is deliberately NOT intercepted. Doing so
  // needs history manipulation, and going back is a designed path in this flow
  // rather than an accident — the syllabus meets the student with "continue
  // previous attempt or start new", which is the same choice a warning would
  // offer, only clearer.
  useEffect(() => {
    if (!isRunning) return undefined;

    const guard = (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey) return;

      const link = event.target.closest?.('a[href]');
      if (!link || link.target === '_blank') return;

      const href = link.getAttribute('href');
      if (!href?.startsWith('/') || href === window.location.pathname) return;

      const stay = !window.confirm(
        'Leave this test? The timer keeps running while you are away. Pause it first if you need a break.'
      );

      if (stay) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    document.addEventListener('click', guard, true);
    return () => document.removeEventListener('click', guard, true);
  }, [isRunning]);

  const answeredCount = useMemo(
    () => questions.filter((q) => chosen[q.question_id]).length,
    [chosen, questions]
  );

  const choose = useCallback(
    async (question, letter) => {
      if (!isRunning) return;

      const previous = chosen[question.question_id];
      setChosen((all) => ({ ...all, [question.question_id]: letter }));
      setSaving(question.question_id);
      setError('');

      try {
        const result = await api.save([
          { question_id: question.question_id, selected_option: letter },
        ]);
        setSitting(result.sitting);
        setRemaining(result.sitting.seconds_remaining);

        // Practice tells you immediately; the graded run tells you nothing. The
        // server decides which — this only renders what came back.
        // The reveal arrives whole — verdict, correct letter and explanation —
        // so the panel appears with the tick rather than only after a reload.
        if (result.results?.length) {
          const verdict = result.results[0];
          setQuestions((all) =>
            all.map((q) =>
              q.question_id === question.question_id
                ? {
                    ...q,
                    revealed: true,
                    is_correct: verdict.is_correct,
                    correct_option: verdict.correct_option,
                    explanation: verdict.explanation,
                    distractor_rationale: verdict.distractor_rationale,
                  }
                : q
            )
          );
        }
      } catch (err) {
        console.error('Failed to save the answer:', err);
        // Put the previous choice back rather than leaving the UI claiming an
        // answer the server never accepted.
        setChosen((all) => ({ ...all, [question.question_id]: previous }));
        setError('That answer was not saved. Check your connection and try again.');
      } finally {
        setSaving(null);
      }
    },
    [api, chosen, isRunning]
  );

  const togglePause = useCallback(async () => {
    setError('');
    try {
      const result = await (isRunning ? api.pause() : api.resume());
      setSitting(result.sitting);
      setRemaining(result.sitting.seconds_remaining);
    } catch (err) {
      console.error('Failed to pause or resume:', err);
      setError('Could not change the timer. Reload to see the current state.');
    }
  }, [api, isRunning]);

  const submit = useCallback(async () => {
    setSubmitting(true);
    setError('');
    try {
      await api.submit();
      const fresh = await api.get();
      apply(fresh);
      setConfirming(false);
      setReviewing(false);
    } catch (err) {
      console.error('Failed to submit:', err);
      setError('Could not submit. Nothing was lost — try again.');
    } finally {
      setSubmitting(false);
    }
  }, [apply, api]);

  if (loading) return <PageSpinner label="Loading test" />;

  if (!sitting) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <Alert tone="error">{error || 'This test could not be found.'}</Alert>
      </div>
    );
  }

  const question = questions[index];
  const scoreShare = isSubmitted ? sitting.marks_awarded / sitting.marks_available : 0;

  return (
    /* Full-bleed exam chrome.
     *
     * This route renders OUTSIDE AppLayout (see ExamRoute in App.jsx), so there
     * is no nav rail and no app top bar — the screen is the test. Two reasons
     * beyond wanting it to feel like one: a sidebar full of links is an
     * invitation to wander off mid-question, and the artefact-heavy stems in
     * this corpus are 30+ lines of SQL or Java that read far better with the
     * whole viewport than inside a 48rem column.
     *
     * `w-full` with no mx-auto or max-w on the outer shell is the whole point of
     * the layout: the header, the footer and the divider rules run edge to edge.
     */
    <div className="flex min-h-screen w-full flex-col bg-canvas">
      {/* ------------------------------------------------------------ header */}
      <header className="sticky top-0 z-30 w-full border-b border-line bg-surface/95 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2.5 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {/* The only way out, since the rail is gone. Confirmed, because the
                clock keeps running and a mis-click should not cost time. */}
            <Button
              size="xs"
              variant="ghost"
              icon={LogOut}
              onClick={() => {
                if (
                  isSubmitted ||
                  window.confirm(
                    'Leave this test? The timer keeps running while you are away. Pause it first if you need a break.'
                  )
                ) {
                  navigate(exitUrl);
                }
              }}
            >
              Exit
            </Button>

            <span className="hidden h-5 w-px bg-line sm:block" aria-hidden="true" />

            <span className="truncate font-mono text-xs text-fg-muted">
              {sitting.section_code}
            </span>
            <Badge tone={isPractice ? 'neutral' : 'brand'}>
              {isPractice ? 'Practice' : 'Graded'}
            </Badge>
            {sitting.status === 'paused' ? <Badge tone="warning">Paused</Badge> : null}
          </div>

          <div className="flex items-center gap-2">
            {!isSubmitted ? (
              <>
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 font-mono text-sm tabular-nums transition-colors duration-300',
                    remaining <= 60
                      ? 'bg-danger-subtle text-danger-fg'
                      : remaining <= 300
                        ? 'bg-warning-subtle text-warning-fg'
                        : 'bg-surface-2 text-fg-secondary'
                  )}
                  aria-live="off"
                >
                  <Clock
                    className={cn('h-4 w-4', remaining <= 60 && 'animate-pulse-urgent')}
                    aria-hidden="true"
                  />
                  {formatClock(remaining)}
                </span>

                <Button
                  size="xs"
                  variant="secondary"
                  icon={isRunning ? Pause : Play}
                  onClick={togglePause}
                >
                  {isRunning ? 'Pause' : 'Resume'}
                </Button>

                <Button size="xs" icon={Flag} onClick={() => setConfirming(true)}>
                  Submit
                </Button>
              </>
            ) : (
              <Badge tone={scoreShare >= 0.7 ? 'success' : scoreShare >= 0.4 ? 'warning' : 'danger'} mono>
                {sitting.marks_awarded}/{sitting.marks_available}
              </Badge>
            )}
          </div>
        </div>

        {/* Edge-to-edge progress. Answered count only — a graded sitting reveals
            nothing about correctness, so this is momentum, not score. */}
        {!isSubmitted ? (
          <div className="h-0.5 w-full bg-surface-2">
            <div
              className="h-full bg-brand-solid transition-[width] duration-500 ease-enter"
              style={{ width: `${(answeredCount / Math.max(1, questions.length)) * 100}%` }}
            />
          </div>
        ) : null}
      </header>

      {/* ------------------------------------------------- question + palette */}
      <div className="flex flex-1 flex-col lg:flex-row">
        <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 lg:px-8">
          {error ? (
            <Alert tone="error" className="mb-4">
              {error}
            </Alert>
          ) : null}

          {sitting.status === 'paused' ? (
            <Alert tone="warning" className="mb-4">
              The timer is stopped with {formatClock(sitting.seconds_remaining)} left. Resume to
              carry on answering.
            </Alert>
          ) : null}

          {isSubmitted ? (
            <ReviewList
              questions={questions}
              chosen={chosen}
              sitting={sitting}
              nextSectionCode={courseNav?.nextSectionCode}
              onContinue={() =>
                navigate(coursePageUrl, {
                  state: { focusSection: courseNav?.nextSectionCode },
                })
              }
              onBackToCourse={() => navigate(coursePageUrl)}
              onExit={() => navigate(exitUrl)}
            />
          ) : reviewing ? (
            <div className="space-y-5">
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-fg">Check your answers</h2>
                <p className="text-sm text-fg-muted">
                  {answeredCount === questions.length
                    ? 'All ten answered.'
                    : `${questions.length - answeredCount} question${
                        questions.length - answeredCount === 1 ? '' : 's'
                      } still blank. Blank answers score nothing.`}
                </p>
              </div>

              <ul className="divide-y divide-line">
                {questions.map((q, i) => (
                  <li key={q.question_id} className="flex items-center justify-between gap-3 py-2.5">
                    <button
                      type="button"
                      onClick={() => {
                        setDirection(i > index ? 'forward' : 'back');
                        setIndex(i);
                        setReviewing(false);
                      }}
                      className="flex min-w-0 items-center gap-3 text-left text-sm text-fg-secondary transition-colors hover:text-fg"
                    >
                      <span className="w-6 shrink-0 font-mono text-xs tabular-nums text-fg-muted">
                        {i + 1}
                      </span>
                      <span className="truncate">
                        {q.stem.replace(/```[\s\S]*?```/g, '[code]')}
                      </span>
                    </button>
                    {chosen[q.question_id] ? (
                      <Badge tone="brand" mono>
                        {chosen[q.question_id]}
                      </Badge>
                    ) : (
                      <Badge tone="warning">Blank</Badge>
                    )}
                  </li>
                ))}
              </ul>

              <div className="flex flex-wrap justify-between gap-2 border-t border-line pt-4">
                <Button
                  variant="ghost"
                  size="sm"
                  icon={ChevronLeft}
                  onClick={() => setReviewing(false)}
                >
                  Back to questions
                </Button>
                <Button size="sm" icon={Flag} onClick={() => setConfirming(true)}>
                  Submit {isPractice ? 'practice' : 'test'}
                </Button>
              </div>
            </div>
          ) : question ? (
            /* No Card. A question is the page during an exam, not a tile on it —
             * a bordered panel inside a full-bleed shell just reinstates the
             * frame the shell removed. The options below keep their borders
             * because they are controls; the question is content. */
            <div
              key={question.question_id}
              className={cn(
                'space-y-5',
                direction === 'forward' ? 'animate-slide-in-right' : 'animate-slide-in-left'
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">
                  Question {index + 1} of {questions.length}
                </span>
                <span className="text-xs text-fg-muted">{question.marks} marks</span>
              </div>

              <QuestionContent>{question.stem}</QuestionContent>

              <div className="space-y-2">
                {question.options.map((option, i) => {
                  const letter = LABELS[i];
                  const picked = chosen[question.question_id] === letter;
                  const revealed = isPractice && question.revealed && picked;

                  return (
                    <button
                      key={letter}
                      type="button"
                      disabled={!isRunning || saving === question.question_id}
                      onClick={() => choose(question, letter)}
                      className={cn(
                        'flex w-full items-start gap-3 rounded-xl border p-3 text-left',
                        'transition-all duration-150 ease-spring active:scale-[0.99]',
                        picked
                          ? 'border-brand-solid bg-brand-subtle shadow-e1'
                          : 'border-line bg-surface-2 hover:-translate-y-px hover:border-line-strong hover:bg-surface-3',
                        !isRunning && 'cursor-not-allowed opacity-70 active:scale-100'
                      )}
                    >
                      <span
                        className={cn(
                          'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border font-mono text-xs transition-colors duration-150',
                          picked
                            ? 'animate-pop border-brand-solid bg-brand-solid text-fg-on-solid'
                            : 'border-line text-fg-muted'
                        )}
                      >
                        {letter}
                      </span>
                      <span className="min-w-0 flex-1">
                        <QuestionContent>{option}</QuestionContent>
                      </span>
                      {revealed ? (
                        question.is_correct ? (
                          <CheckCircle2
                            className="mt-0.5 h-5 w-5 shrink-0 animate-pop-tick text-success-fg"
                            aria-label="correct"
                          />
                        ) : (
                          <X
                            className="mt-0.5 h-5 w-5 shrink-0 animate-pop-tick text-danger-fg"
                            aria-label="incorrect"
                          />
                        )
                      ) : null}
                    </button>
                  );
                })}
              </div>

              {isPractice && question.revealed && question.explanation ? (
                <div
                  className={cn(
                    'animate-rise-in space-y-3 rounded-xl border p-4',
                    question.is_correct
                      ? 'border-success-fg/30 bg-success-subtle'
                      : 'border-danger-fg/30 bg-danger-subtle'
                  )}
                >
                  <p className="text-xs font-semibold uppercase tracking-wider text-fg-muted">
                    {question.is_correct ? 'Correct' : `Correct answer: ${question.correct_option}`}
                  </p>
                  <QuestionContent className="text-sm">{question.explanation}</QuestionContent>
                </div>
              ) : null}
            </div>
          ) : null}
        </main>

        {/* The palette. A right rail on desktop the way an exam interface puts
            it, and a horizontal strip under the question on a phone — the same
            buttons either way, so the two cannot drift. */}
        {!isSubmitted ? (
          <aside className="w-full shrink-0 border-t border-line bg-surface/40 px-4 py-4 sm:px-6 lg:w-64 lg:border-l lg:border-t-0 lg:px-5">
            <div className="lg:sticky lg:top-24 space-y-4">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-fg-muted">
                  Questions
                </p>
                <p className="text-sm font-bold tabular-nums text-fg">
                  {answeredCount}
                  <span className="text-xs font-medium text-fg-muted">
                    /{questions.length}
                  </span>
                </p>
              </div>

              <div className="grid grid-cols-10 gap-1.5 lg:grid-cols-5">
                {questions.map((q, i) => (
                  <button
                    key={q.question_id}
                    type="button"
                    onClick={() => {
                      setDirection(i > index ? 'forward' : 'back');
                      setIndex(i);
                      setReviewing(false);
                    }}
                    aria-label={`Question ${i + 1}${
                      chosen[q.question_id] ? ', answered' : ', not answered'
                    }`}
                    aria-current={!reviewing && i === index ? 'true' : undefined}
                    className={cn(
                      'flex aspect-square items-center justify-center rounded-lg border text-xs font-semibold tabular-nums transition-all duration-150 ease-spring active:scale-95',
                      chosen[q.question_id]
                        ? 'border-brand-solid/50 bg-brand-subtle text-brand-subtle-fg'
                        : 'border-line bg-surface-2 text-fg-muted hover:border-line-strong hover:text-fg',
                      !reviewing && i === index && 'ring-2 ring-focus'
                    )}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>

              <Button
                size="sm"
                variant="secondary"
                fullWidth
                icon={Check}
                onClick={() => setReviewing(true)}
              >
                Review answers
              </Button>
            </div>
          </aside>
        ) : null}
      </div>

      {/* ------------------------------------------------------------ footer */}
      {!isSubmitted && !reviewing ? (
        <footer className="sticky bottom-0 z-30 w-full border-t border-line bg-surface/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <Button
              variant="ghost"
              size="sm"
              icon={ChevronLeft}
              disabled={index === 0}
              onClick={() => {
                setDirection('back');
                setIndex((i) => Math.max(0, i - 1));
              }}
            >
              Previous
            </Button>

            <span className="text-xs tabular-nums text-fg-muted">
              {index + 1} / {questions.length}
            </span>

            {index === questions.length - 1 ? (
              <Button size="sm" icon={Check} onClick={() => setReviewing(true)}>
                Review answers
              </Button>
            ) : (
              <Button
                size="sm"
                iconRight={ChevronRight}
                onClick={() => {
                  setDirection('forward');
                  setIndex((i) => Math.min(questions.length - 1, i + 1));
                }}
              >
                Next
              </Button>
            )}
          </div>
        </footer>
      ) : null}

      <Modal
        open={confirming}
        onClose={() => setConfirming(false)}
        title={isPractice ? 'Finish this practice run?' : 'Submit this test?'}
        icon={AlertTriangle}
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-secondary">
            {isPractice ? (
              <>
                This ends the practice run and shows your results. Your locked section score is
                not affected.
              </>
            ) : (
              <>
                This decides your score for{' '}
                <span className="font-mono text-fg">{sitting.section_code}</span> and cannot be
                undone or retaken. After this, the section is practice only.
              </>
            )}
          </p>
          {answeredCount < questions.length ? (
            <Alert tone="warning" size="sm">
              {questions.length - answeredCount} question
              {questions.length - answeredCount === 1 ? '' : 's'} still blank, scoring nothing.
            </Alert>
          ) : null}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
              Keep answering
            </Button>
            <Button size="sm" icon={Flag} loading={submitting} onClick={submit}>
              {isPractice ? 'Finish practice' : 'Submit and lock score'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

/** The results of a submitted sitting: every question, with the explanation. */
const ReviewList = ({
  questions,
  chosen,
  sitting,
  nextSectionCode,
  onContinue,
  onBackToCourse,
  onExit,
}) => {
  const correct = questions.filter((q) => q.is_correct).length;
  const share = sitting.marks_available ? sitting.marks_awarded / sitting.marks_available : 0;

  // 70% is the celebration threshold — the same line the syllabus badge uses for
  // its success tone, so the confetti and the colour agree about what "good"
  // means rather than each having an opinion.
  const celebrate = share >= 0.7;

  return (
    <div className="space-y-4 pb-8">
      {/* The one moment worth spending motion on: the score arrives once, and
          the student is looking directly at it. Ring fills, number counts, and
          the confetti fires only when there is something to celebrate — a burst
          over 9/30 would read as mockery. */}
      <Card
        padding="lg"
        className={cn(
          'relative overflow-hidden !rounded-2xl',
          // Same light/dark split as the XP strip, and for the same measured
          // reason: a 0.15-alpha wash over rgb(250,251,253) is invisible, so on
          // light the colour is concentrated into the rail and the ring while the
          // surface stays crisp and elevated. This is the one card in the app a
          // student stares at, and it must not look like every other panel.
          celebrate && 'bg-earned border-accent-solid/35'
        )}
      >
        {celebrate ? (
          <div className="absolute inset-x-0 top-0 h-1 bg-xp" aria-hidden="true" />
        ) : null}
        <Celebration active={celebrate} />

        <div className="relative flex flex-wrap items-center gap-5">
          <ProgressRing
            value={sitting.marks_awarded}
            max={sitting.marks_available}
            size={92}
            thickness={8}
            tone={celebrate ? 'earned' : 'brand'}
            label={
              <span className="text-base font-bold">
                <CountUp value={Math.round(share * 100)} format={(n) => `${n}%`} />
              </span>
            }
            className="animate-pop"
          />

          <div className="min-w-0 space-y-1">
            <h2 className="text-2xl font-bold text-fg">
              {sitting.mode === 'practice'
                ? 'Practice complete'
                : celebrate
                  ? 'Nicely done'
                  : 'Section submitted'}
            </h2>
            <p className="text-4xl font-bold tabular-nums text-fg">
              <CountUp value={sitting.marks_awarded} />
              <span className="text-lg font-medium text-fg-muted">
                {' '}/ {sitting.marks_available} marks
              </span>
            </p>
            <p className="text-sm text-fg-muted">
              {correct} of {questions.length} correct
              {sitting.mode === 'graded' ? ' · this score is final' : ' · your score is unaffected'}
            </p>
          </div>
        </div>

        {/* Where to next. When another section follows this one in the course,
            offer the two the student asked for — carry on, or step out — rather
            than a single dead-end "back". On the last section there is nothing
            to continue to, so it collapses to one button back into the course. */}
        <div className="relative flex flex-wrap gap-2 pt-4">
          {nextSectionCode ? (
            <>
              <Button size="sm" iconRight={ChevronRight} onClick={onContinue}>
                Continue to next section
              </Button>
              <Button size="sm" variant="ghost" icon={LogOut} onClick={onExit}>
                Exit
              </Button>
            </>
          ) : (
            <Button size="sm" variant="secondary" icon={ChevronLeft} onClick={onBackToCourse}>
              Back to the course
            </Button>
          )}
        </div>
      </Card>

      {/* Separated by rules rather than boxed. Ten bordered tiles down a results
          page reads as a list of cards; ten ruled sections reads as a paper. The
          score hero above keeps its surface — that one IS a tile, deliberately. */}
      {questions.map((question, i) => (
        <section
          key={question.question_id}
          className="animate-rise-in space-y-4 border-t border-line pt-6"
          style={{ animationDelay: `${Math.min(i, 10) * 45}ms` }}
        >
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-medium uppercase tracking-wider text-fg-muted">
            Question {i + 1}
          </span>
          {chosen[question.question_id] ? (
            <Badge tone={question.is_correct ? 'success' : 'danger'}>
              {question.is_correct ? 'Correct' : 'Incorrect'}
            </Badge>
          ) : (
            <Badge tone="warning">Not answered</Badge>
          )}
        </div>

        <QuestionContent>{question.stem}</QuestionContent>

        <ul className="space-y-1.5">
          {question.options.map((option, oi) => {
            const letter = LABELS[oi];
            const picked = chosen[question.question_id] === letter;
            const correct = question.correct_option === letter;

            return (
              <li
                key={letter}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-2.5 text-sm',
                  correct
                    ? 'border-success-fg/40 bg-success-subtle'
                    : picked
                      ? 'border-danger-fg/40 bg-danger-subtle'
                      : 'border-line'
                )}
              >
                <span className="mt-0.5 font-mono text-xs text-fg-muted">{letter}</span>
                <span className="min-w-0 flex-1">
                  <QuestionContent className="text-sm">{option}</QuestionContent>
                </span>
                {correct ? <Check className="h-4 w-4 shrink-0 text-success-fg" aria-label="correct answer" /> : null}
              </li>
            );
          })}
        </ul>

          {question.explanation ? (
            <div className="rounded-xl border border-line bg-surface-2 p-4">
              <QuestionContent className="text-sm">{question.explanation}</QuestionContent>
            </div>
          ) : null}
        </section>
      ))}
    </div>
  );
};

export default SittingPage;
