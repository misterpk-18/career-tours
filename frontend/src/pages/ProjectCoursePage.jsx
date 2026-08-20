import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { catalogueAPI, projectsAPI, sittingsAPI, achievementsAPI } from '../services/api';
import PageShell from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import Alert from '../components/ui/Alert';
import ProgressRing from '../components/motion/ProgressRing';
import CountUp from '../components/motion/CountUp';
import SectionAssessment from '../components/SectionAssessment';
import { apiErrorMessage } from '../lib/apiError';

/**
 * One course inside one project: the syllabus, and the test for each section.
 *
 * Project-scoped rather than an addition to the catalogue's course page,
 * because a score belongs to a project and a student may hold several. The
 * section list, its buttons and the "start new" confirm live in the shared
 * <SectionAssessment>, which the catalogue's project-independent course page
 * reuses; this page supplies the project's sittings and where they navigate.
 */

export const ProjectCoursePage = () => {
  const { projectId, courseId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // When the student arrives via "Continue to next section" on a result screen,
  // that section is named in navigation state so it can be highlighted.
  const focusSection = location.state?.focusSection || null;

  const [course, setCourse] = useState(null);
  const [project, setProject] = useState(null);
  // Keyed by section_code. Absent key means the section was never started.
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState('');
  const [achievements, setAchievements] = useState(null);

  const loadProgress = useCallback(async () => {
    const rows = await sittingsAPI.progress(projectId);
    setProgress(Object.fromEntries(rows.map((row) => [row.section_code, row])));
    achievementsAPI.mine().then(setAchievements).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [courseData, projectData, rows, earned] = await Promise.all([
          catalogueAPI.getCourse(courseId),
          projectsAPI.getById(projectId),
          sittingsAPI.progress(projectId),
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
        setError(apiErrorMessage(err, 'Unable to start this test.'));
        loadProgress().catch(() => {});
      } finally {
        setStarting('');
      }
    },
    [loadProgress, navigate, projectId]
  );

  // Course-level totals, from the same rows the section badges use.
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

        <SectionAssessment
          sections={syllabus}
          progress={progress}
          xp={achievements}
          starting={starting}
          error={error}
          onStart={open}
          focusSection={focusSection}
        />
      </div>
    </PageShell>
  );
};

export default ProjectCoursePage;
