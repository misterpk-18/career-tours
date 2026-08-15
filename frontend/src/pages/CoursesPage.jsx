import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, BookOpen, Clock, GraduationCap, Layers, Search } from 'lucide-react';
import { catalogueAPI } from '../services/api';
import PageShell from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import SearchField from '../components/ui/SearchField';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { apiErrorMessage } from '../lib/apiError';

// How many skill chips a card shows before collapsing the rest into a count.
// A full-stack course teaches ~15 skills; printing all of them makes every card
// a different height and buries the course name.
const SKILL_CHIPS = 5;

export const CoursesPage = () => {
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    setLoading(true);
    setError('');
    try {
      setCourses(await catalogueAPI.listCourses());
    } catch (err) {
      console.error('Failed to load the course catalogue:', err);
      setError(apiErrorMessage(err, 'Unable to load courses. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Every term must match, but each may match any field.
   *
   * Searching the skills as well as the name is the point: someone looking for
   * "django" wants the Python Full Stack course, whose title never says Django.
   */
  const results = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);

    if (!terms.length) return courses;

    return courses.filter((course) => {
      const haystack = [
        course.course_name,
        course.course_code,
        course.description,
        course.level,
        ...(course.skills || []),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return terms.every((term) => haystack.includes(term));
    });
  }, [courses, query]);

  return (
    <PageShell>
      <HeroBanner
        title="Course catalogue"
        description="Every course in the library. Search by name, level, or a skill you want to learn, then open a course to see the journey it takes you through."
      >
        <div className="mt-8 border-t border-line pt-6">
          <SearchField
            value={query}
            onChange={setQuery}
            label="Search courses"
            placeholder="Search by course, level or skill — try “python” or “cloud”"
            count={results.length}
            total={courses.length}
            className="max-w-2xl"
          />
        </div>
      </HeroBanner>

      {error ? (
        <Alert
          tone="error"
          action={
            <Button size="xs" variant="secondary" onClick={fetchCourses}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}

      {loading ? (
        <PageSpinner message="Loading the course catalogue…" className="py-16" />
      ) : results.length === 0 ? (
        <EmptyState
          icon={query ? Search : GraduationCap}
          title={query ? `No courses match “${query}”` : 'No courses in the catalogue'}
          titleAs="h3"
          description={
            query
              ? 'Try a broader term — a skill name, or part of the course title.'
              : 'The catalogue is empty. Load the course corpus and this page will fill up.'
          }
          action={
            query ? (
              <Button variant="secondary" onClick={() => setQuery('')}>
                Clear search
              </Button>
            ) : null
          }
          className="max-w-xl mx-auto"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {results.map((course) => {
            const extraSkills = (course.skills?.length || 0) - SKILL_CHIPS;

            return (
              <Card
                key={course.course_id}
                variant="interactive"
                as="article"
                className="flex flex-col justify-between group"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    {course.course_code ? <Badge mono>{course.course_code}</Badge> : <span />}
                    {course.level ? <Badge>{course.level}</Badge> : null}
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-fg transition-colors group-hover:text-brand-fg">
                      {course.course_name}
                    </h3>
                    <p className="mt-1.5 line-clamp-3 text-sm text-fg-muted">
                      {course.description || 'No description available for this course.'}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-fg-muted">
                    {course.duration_hours ? (
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                        {course.duration_hours} hours
                      </span>
                    ) : null}
                    {course.module_count ? (
                      <span className="flex items-center gap-1.5">
                        <Layers className="h-3.5 w-3.5" aria-hidden="true" />
                        {course.module_count} modules
                      </span>
                    ) : null}
                    {course.skills?.length ? (
                      <span className="flex items-center gap-1.5">
                        <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
                        {course.skills.length} skills
                      </span>
                    ) : null}
                  </div>

                  {course.skills?.length ? (
                    <div className="flex flex-wrap gap-1.5">
                      {course.skills.slice(0, SKILL_CHIPS).map((skill) => (
                        <Badge key={skill}>{skill}</Badge>
                      ))}
                      {extraSkills > 0 ? (
                        <span className="self-center text-2xs text-fg-muted">
                          +{extraSkills} more
                        </span>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                <div className="mt-6 border-t border-line pt-4">
                  <Button
                    size="sm"
                    fullWidth
                    iconRight={ArrowRight}
                    onClick={() => navigate(`/courses/${course.course_id}`)}
                  >
                    View learning journey
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </PageShell>
  );
};

export default CoursesPage;
