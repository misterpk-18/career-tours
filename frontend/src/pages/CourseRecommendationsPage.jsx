import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { recommendationsAPI, projectsAPI } from '../services/api';
import {
  GraduationCap,
  BookOpen,
  Clock,
  Layers,
  Award,
  Compass,
  ArrowLeft,
  AlertTriangle,
  RefreshCw,
  ChevronRight
} from 'lucide-react';
import PageShell, { NarrowShell } from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import PaneSpinner from '../components/ui/PaneSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Chip from '../components/ui/Chip';
import EmptyState from '../components/ui/EmptyState';
import MetricTile from '../components/ui/MetricTile';
import ProgressBar from '../components/ui/ProgressBar';
import RankBadge from '../components/ui/RankBadge';
import SectionHeading from '../components/ui/SectionHeading';
import AiInsightBox from '../components/ui/AiInsightBox';
import SummarySections from '../components/ui/SummarySections';
import CourseSyllabus from '../components/ui/CourseSyllabus';
import SelectableCard, { SelectableList } from '../components/ui/SelectableCard';
import { toPct, toHours, sumBy } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

export const CourseRecommendationsPage = () => {
  const { projectId } = useParams();

  const [project, setProject] = useState(null);
  const [careers, setCareers] = useState([]);
  const [courseCountByCareer, setCourseCountByCareer] = useState({});
  const [coursesByCareer, setCoursesByCareer] = useState({});
  const [selectedOccupationId, setSelectedOccupationId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState('');

  useEffect(() => {
    if (projectId) {
      fetchInitial();
    }
  }, [projectId]);

  const fetchInitial = async () => {
    setLoading(true);
    setError('');
    try {
      const [projData, overview] = await Promise.all([
        projectsAPI.getById(projectId),
        recommendationsAPI.getProjectOverview(projectId),
      ]);

      setProject(projData);

      const careerList = overview.careers || [];
      setCareers(careerList);

      // The overview already contains every course row, so per-career counts
      // come free — no extra request needed to populate the left-hand list.
      const counts = (overview.courses || []).reduce((acc, course) => {
        acc[course.occupation_id] = (acc[course.occupation_id] || 0) + 1;
        return acc;
      }, {});
      setCourseCountByCareer(counts);

      if (careerList.length > 0) {
        const firstId = careerList[0].occupation_id;
        setSelectedOccupationId(firstId);
        loadCareerCourses(firstId);
      }
    } catch (err) {
      console.error('Failed to load course recommendations:', err);
      setError(apiErrorMessage(err, 'Unable to load course recommendations right now.'));
    } finally {
      setLoading(false);
    }
  };

  const loadCareerCourses = async (occupationId) => {
    // Only the per-career endpoint returns AI summaries, so it has to be called
    // per selection. Results are cached, making re-selection instant.
    if (coursesByCareer[occupationId]) {
      setCoursesError('');
      return;
    }

    setCoursesLoading(true);
    setCoursesError('');
    try {
      const data = await recommendationsAPI.getCareerCourses(projectId, occupationId);
      setCoursesByCareer((prev) => ({ ...prev, [occupationId]: data.courses || [] }));
    } catch (err) {
      console.error('Failed to load courses for career:', err);
      setCoursesError(apiErrorMessage(err, 'Unable to load courses for this career path.'));
    } finally {
      setCoursesLoading(false);
    }
  };

  const handleSelectCareer = (occupationId) => {
    setSelectedOccupationId(occupationId);
    loadCareerCourses(occupationId);
  };

  const selectedCareer = careers.find((c) => c.occupation_id === selectedOccupationId) || null;
  const activeCourses = coursesByCareer[selectedOccupationId] || [];
  const coursesLoaded = Object.prototype.hasOwnProperty.call(coursesByCareer, selectedOccupationId);
  const totalHours = sumBy(activeCourses, 'duration_hours');
  const noCoursesAnywhere =
    careers.length > 0 && careers.every((c) => !courseCountByCareer[c.occupation_id]);

  // 1. Page-level loading
  if (loading) {
    return <PageSpinner message="Loading courses…" />;
  }

  // 2. Page-level error — distinct from "nothing generated yet"
  if (error) {
    return (
      <NarrowShell>
        <EmptyState
          icon={AlertTriangle}
          title="Could Not Load Course Recommendations"
          titleAs="h1"
          description={error}
          action={
            <>
              <Button icon={RefreshCw} onClick={fetchInitial}>
                Try Again
              </Button>
              <Button as={Link} to={`/projects/${projectId}`} variant="secondary" icon={ArrowLeft}>
                Back to Project
              </Button>
            </>
          }
        />
      </NarrowShell>
    );
  }

  // 3. Nothing generated yet
  if (careers.length === 0) {
    return (
      <NarrowShell>
        <EmptyState
          icon={GraduationCap}
          title="No Course Recommendations Yet"
          titleAs="h1"
          description="Courses are generated alongside your career matches. Head back to the project workspace, extract your resume skills, and run the recommendation engine first."
          action={
            <Button as={Link} to={`/projects/${projectId}`} icon={ArrowLeft}>
              Back to project
            </Button>
          }
        />
      </NarrowShell>
    );
  }

  return (
    <PageShell>
      {/* This row was two ghost links, "Back to Project Workspace" and "View
          Career Matches". Both are in the shell now — the breadcrumb's back
          arrow and the rail's "Current project" section. */}
      <HeroBanner
        eyebrow="Recommended Learning Path"
        eyebrowIcon={GraduationCap}
        title={
          <>
            Courses to Close Your Gaps in{' '}
            {project?.project_name}
          </>
        }
        description="For every career we matched you with, these are the courses that cover the skills you are missing — ranked by how much of the gap each one closes."
      />

      {/* 4. Careers exist, but the engine produced no courses at all */}
      {noCoursesAnywhere && (
        <EmptyState
          icon={BookOpen}
          size="sm"
          title="No Courses Matched Your Skill Gaps"
          titleAs="h2"
          description="Your career matches were generated, but the course catalogue has nothing mapped to the missing skills yet."
          className="border-warning-fg/50"
        />
      )}

      {/* Master / Detail: careers on the left, their courses on the right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: recommended careers */}
        <div className="lg:col-span-5 space-y-4">
          <SectionHeading as="h2" icon={Award} iconClassName="text-warning-fg" right="Select to see courses">
            Matched Careers
          </SectionHeading>

          <SelectableList label="Matched careers">
            {careers.slice(0, 5).map((item, idx) => {
              const rank = item.rank_position || idx + 1;
              const matchPct = toPct(item.match_percentage);
              const courseCount = courseCountByCareer[item.occupation_id] || 0;
              const isSelected = selectedOccupationId === item.occupation_id;

              return (
                <SelectableCard
                  key={item.match_id || item.occupation_id || idx}
                  selected={isSelected}
                  onSelect={() => handleSelectCareer(item.occupation_id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <RankBadge rank={rank} />
                      <div className="min-w-0">
                        <h3 className="text-base font-bold text-fg">{item.occupation_name}</h3>
                        <p className="text-sm text-fg-muted line-clamp-1">{item.description}</p>
                      </div>
                    </div>

                    <ChevronRight
                      className={`w-5 h-5 shrink-0 transition-transform ${
                        isSelected ? 'text-brand-fg translate-x-1' : 'text-fg-muted'
                      }`}
                      aria-hidden="true"
                    />
                  </div>

                  <div className="mt-4 pt-3 border-t border-line flex items-center justify-between text-xs font-semibold">
                    <span className="inline-flex items-center gap-1.5 text-brand-fg">
                      <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
                      {courseCount} {courseCount === 1 ? 'course' : 'courses'}
                    </span>
                    <span className="text-success-fg font-bold">{matchPct}% Match</span>
                  </div>
                </SelectableCard>
              );
            })}
          </SelectableList>
        </div>

        {/* Right Column: courses for the selected career */}
        <div className="lg:col-span-7 space-y-6">
          {/* 5. Right-pane loading — also covers the gap between selecting a
              career and the request registering, so the header never flashes
              with an empty course list. */}
          {coursesLoading || (selectedCareer && !coursesLoaded && !coursesError) ? (
            <PaneSpinner message="Loading courses…" />
          ) : /* 6. Right-pane error, with retry */
          coursesError ? (
            <Alert
              tone="error"
              action={
                <Button
                  size="xs"
                  variant="secondary"
                  icon={RefreshCw}
                  onClick={() => loadCareerCourses(selectedOccupationId)}
                >
                  Retry
                </Button>
              }
            >
              {coursesError}
            </Alert>
          ) : /* 8. Nothing selected */
          !selectedCareer ? (
            <Card padding="lg" className="text-center text-fg-muted">
              Select a career from the list to view its recommended courses.
            </Card>
          ) : /* 7. Loaded, but this career has no courses */
          coursesLoaded && activeCourses.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              size="sm"
              title="No Courses for This Career Yet"
              titleAs="h3"
              description={`We could not map any catalogue courses to the skill gaps for ${selectedCareer.occupation_name}.`}
            />
          ) : (
            <div className="space-y-4">
              {/* Selected career header */}
              <Card>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-fg uppercase tracking-wider mb-1">
                      <Compass className="w-4 h-4" aria-hidden="true" /> Career #
                      {selectedCareer.rank_position || 1}
                    </div>
                    <h3 className="text-2xl font-bold text-fg">
                      {selectedCareer.occupation_name}
                    </h3>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <MetricTile layout="stack" label="Courses" value={activeCourses.length} />
                    <MetricTile
                      layout="stack"
                      label="Total Time"
                      value={totalHours ? `${totalHours} hrs` : '—'}
                    />
                  </div>
                </div>
              </Card>

              {/* Course cards, in the rank order the backend returned */}
              {activeCourses.map((course, idx) => {
                const coveragePct = toPct(course.coverage_percentage);
                const rank = course.recommendation_rank || idx + 1;

                return (
                  <Card
                    key={course.recommendation_id || course.course_id || idx}
                    variant="interactive"
                    padding="sm"
                    className="p-5 space-y-4"
                  >
                    <div className="flex items-start gap-3">
                      <RankBadge rank={rank} />
                      <div className="min-w-0">
                        <h4 className="text-base font-bold text-fg">{course.course_name}</h4>
                        {course.description && (
                          <p className="text-sm text-fg-muted mt-1 leading-relaxed">
                            {course.description}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Level & duration chips */}
                    <div className="flex flex-wrap items-center gap-2">
                      <Chip icon={Layers}>
                        {course.level || 'All levels'}
                      </Chip>
                      <Chip icon={Clock}>{toHours(course.duration_hours)}</Chip>
                    </div>

                    <ProgressBar
                      value={coveragePct}
                      label="Skill gap coverage"
                      valueLabel={`${coveragePct}%`}
                    />

                    {/* AI rationale — absent when no summary row was generated */}
                    {course.summary?.summary_text && (
                      <AiInsightBox label="Why This Course" labelAs="h5">
                        {course.summary.structured ? (
                          <SummarySections
                            sections={[
                              {
                                label: 'Why recommended',
                                text: course.summary.structured.why_recommended,
                              },
                              { label: 'How it helps', text: course.summary.structured.how_it_helps },
                              {
                                label: 'Key skills covered',
                                items: course.summary.structured.key_skills,
                                tone: 'brand',
                              },
                            ]}
                          />
                        ) : (
                          // Pre-structured summaries are a single paragraph.
                          course.summary.summary_text
                        )}
                      </AiInsightBox>
                    )}

                    {/* Corpus syllabus — absent for the pre-corpus courses */}
                    <CourseSyllabus syllabus={course.syllabus} />

                    {/* The way into the assessment. Only courses that carry a
                        question corpus (a syllabus) can be sat, so the button is
                        gated on that — a pre-corpus course would open a page with
                        no sections and no Start test, which reads as broken. */}
                    {course.course_id && course.syllabus?.length ? (
                      <div className="border-t border-line pt-4">
                        <Button
                          as={Link}
                          to={`/projects/${projectId}/courses/${course.course_id}`}
                          size="sm"
                          iconRight={ChevronRight}
                        >
                          Start assessment
                        </Button>
                      </div>
                    ) : null}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </PageShell>
  );
};

export default CourseRecommendationsPage;
