import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  ClipboardCheck,
  Clock,
  GraduationCap,
  Layers,
  Target,
} from 'lucide-react';
import {
  catalogueAPI,
  courseSittingsAPI,
  courseAchievementsAPI,
} from '../services/api';
import PageShell, { NarrowShell } from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import SectionHeading from '../components/ui/SectionHeading';
import ProgressBar from '../components/ui/ProgressBar';
import SectionAssessment from '../components/SectionAssessment';
import { apiErrorMessage } from '../lib/apiError';

/**
 * One course, laid out as the sequence a learner works through.
 *
 * Not CourseSyllabus. That component is a collapsed disclosure built for a
 * recommendation card, where the syllabus is supporting evidence for "should I
 * take this?". Here the syllabus IS the page, so it is open, numbered, and
 * ordered — the modules are shown as consecutive steps because `module_number`
 * is the corpus's own sequence, which is the order a learner takes them in.
 */
export const CourseJourneyPage = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Set when the student lands here via "Continue to next section".
  const focusSection = location.state?.focusSection || null;

  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // The course-track assessment state — independent of any project.
  const [progress, setProgress] = useState({});
  const [xp, setXp] = useState(null);
  const [starting, setStarting] = useState('');
  const [sittingError, setSittingError] = useState('');

  const loadAssessment = useCallback(async (courseCode) => {
    if (!courseCode) return;
    try {
      const rows = await courseSittingsAPI.progress(courseId, courseCode);
      setProgress(Object.fromEntries(rows.map((row) => [row.section_code, row])));
    } catch {
      /* progress is decoration on top of the syllabus; a failure must not blank the page */
    }
    courseAchievementsAPI.mine().then(setXp).catch(() => {});
  }, [courseId]);

  useEffect(() => {
    let cancelled = false;

    const fetchCourse = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await catalogueAPI.getCourse(courseId);
        if (cancelled) return;
        setCourse(data);
        // Assessment state depends on the course code, so it can only run once
        // the course is known. A failure here leaves the syllabus intact.
        loadAssessment(data.course_code);
      } catch (err) {
        console.error('Failed to load the course:', err);
        // Cancelled requests must not paint an error: the component is gone.
        if (!cancelled) setError(apiErrorMessage(err, 'Unable to load this course.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCourse();

    return () => {
      cancelled = true;
    };
  }, [courseId, loadAssessment]);

  const open = useCallback(
    async (sectionCode, { mode = 'graded', restart = false } = {}) => {
      setStarting(sectionCode);
      setSittingError('');
      try {
        const { sitting } = await courseSittingsAPI.start(courseId, sectionCode, { mode, restart });
        navigate(`/courses/${courseId}/sittings/${sitting.sitting_id}`);
      } catch (err) {
        console.error('Failed to start the sitting:', err);
        setSittingError(apiErrorMessage(err, 'Unable to start this test.'));
        if (course?.course_code) loadAssessment(course.course_code).catch(() => {});
      } finally {
        setStarting('');
      }
    },
    [course, courseId, loadAssessment, navigate]
  );

  if (loading) {
    return <PageSpinner message="Loading the learning journey…" className="py-24" />;
  }

  if (error || !course) {
    return (
      <NarrowShell>
        <EmptyState
          icon={AlertTriangle}
          iconTone="danger"
          title="Course unavailable"
          titleAs="h1"
          description={error || 'We could not find this course in the catalogue.'}
          action={
            <Button as={Link} to="/courses" icon={ArrowLeft}>
              Back to courses
            </Button>
          }
        />
      </NarrowShell>
    );
  }

  const totalModules = course.module_count || 0;

  // Running module count so each section can say where it starts in the course
  // as a whole, rather than restarting at 1 and losing the sense of a sequence.
  let moduleCursor = 0;

  return (
    <PageShell>
      <HeroBanner
        eyebrow={course.course_code || 'Course'}
        eyebrowIcon={GraduationCap}
        title={course.course_name}
        description={course.description}
      >
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-line pt-6 text-sm text-fg-secondary">
          {course.level ? (
            <span className="flex items-center gap-2">
              <Target className="h-4 w-4 text-fg-muted" aria-hidden="true" />
              {course.level}
            </span>
          ) : null}
          {course.duration_hours ? (
            <span className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-fg-muted" aria-hidden="true" />
              {course.duration_hours} hours
            </span>
          ) : null}
          {totalModules ? (
            <span className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-fg-muted" aria-hidden="true" />
              {totalModules} modules across {course.syllabus.length} sections
            </span>
          ) : null}
          {course.skill_coverage?.length ? (
            <span className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-fg-muted" aria-hidden="true" />
              {course.skill_coverage.length} skills covered
            </span>
          ) : null}
        </div>
      </HeroBanner>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Journey */}
        <div className="space-y-6 lg:col-span-2">
          {/* The assessment: sit any section's test, independent of any project.
              Only shown when the course carries a question corpus (a syllabus). */}
          {course.syllabus?.length ? (
            <SectionAssessment
              title="Assessment"
              sections={course.syllabus}
              progress={progress}
              xp={xp}
              starting={starting}
              error={sittingError}
              onStart={open}
              focusSection={focusSection}
            />
          ) : null}

          <SectionHeading as="h2" icon={Layers} iconClassName="text-brand-fg">
            The learning journey
          </SectionHeading>

          {course.syllabus?.length ? (
            <ol className="space-y-5">
              {course.syllabus.map((section, index) => {
                const start = moduleCursor + 1;
                moduleCursor += section.modules.length;

                return (
                  <li key={section.section_code ?? `section-${index}`}>
                    <Card as="section" padding="lg" className="space-y-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-2xs font-bold uppercase tracking-widest text-fg-muted">
                            Stage {index + 1} of {course.syllabus.length}
                          </p>
                          <h3 className="mt-1 text-xl font-bold text-fg">
                            Modules {start}&ndash;{moduleCursor}
                          </h3>
                        </div>
                        {section.weight_pct != null ? (
                          <Badge>{section.weight_pct}% of assessment</Badge>
                        ) : null}
                      </div>

                      {section.assessment ? (
                        <p className="flex items-start gap-2 text-xs leading-relaxed text-fg-muted">
                          <ClipboardCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                          <span>{section.assessment}</span>
                        </p>
                      ) : null}

                      <ol className="space-y-5">
                        {section.modules.map((module) => (
                          <li key={module.module_number} className="flex gap-4">
                            <span
                              className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-subtle text-xs font-bold text-brand-subtle-fg"
                              aria-hidden="true"
                            >
                              {module.module_number}
                            </span>

                            <div className="min-w-0 flex-1 space-y-2.5">
                              <h4 className="text-base font-semibold leading-snug text-fg">
                                {module.title}
                              </h4>

                              {module.topics?.length ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {module.topics.map((topic) => (
                                    <Badge key={topic}>{topic}</Badge>
                                  ))}
                                </div>
                              ) : null}

                              {module.observable_evidence ? (
                                <p className="flex items-start gap-2 text-sm leading-relaxed text-fg-muted">
                                  <Target className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                                  <span>
                                    <span className="font-semibold text-fg-secondary">
                                      You can show this by:{' '}
                                    </span>
                                    {module.observable_evidence}
                                  </span>
                                </p>
                              ) : null}
                            </div>
                          </li>
                        ))}
                      </ol>
                    </Card>
                  </li>
                );
              })}
            </ol>
          ) : (
            <EmptyState
              icon={Layers}
              title="No syllabus recorded"
              titleAs="h3"
              description="This course has no modules in the corpus yet, so there is no journey to lay out."
            />
          )}
        </div>

        {/* Skills */}
        <div className="space-y-6">
          <SectionHeading as="h2" icon={BookOpen} iconClassName="text-brand-fg">
            Skills you gain
          </SectionHeading>

          {course.skill_coverage?.length ? (
            <Card className="space-y-4">
              {course.skill_coverage.map((skill) => (
                <div key={skill.skill_name} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 text-sm font-semibold text-fg">{skill.skill_name}</span>
                    {/* Neutral, not success: coverage is a degree, not a state
                        that can be good or failed. See the colour contract. */}
                    <span className="shrink-0 text-xs text-fg-muted">
                      {Math.round(skill.coverage_weight)}%
                    </span>
                  </div>
                  <ProgressBar value={skill.coverage_weight} />
                </div>
              ))}
            </Card>
          ) : (
            <EmptyState
              icon={BookOpen}
              title="No skills mapped"
              titleAs="h3"
              size="sm"
              description="Nothing in the skill catalogue is linked to this course yet."
            />
          )}
        </div>
      </div>
    </PageShell>
  );
};

export default CourseJourneyPage;
