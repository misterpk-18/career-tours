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
  Loader2,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  ChevronRight
} from 'lucide-react';

// Postgres numeric columns come back as JSON strings ("85.00"), so everything
// numeric has to be coerced before arithmetic or inline width styling.
const toPct = (val) => Math.max(0, Math.min(100, Math.round(Number(val) || 0)));
const toHours = (val) => (Number(val) ? `${Number(val)} hrs` : 'Self-paced');

// `courses.level` is free-form text and includes spanning phrases such as
// "Beginner to Intermediate", so match on substrings rather than exact keys.
// Checked high-to-low: a span is colored by the highest level it reaches.
const LEVEL_STYLES = [
  ['advanced', 'bg-purple-950/60 border-purple-800/60 text-purple-300'],
  ['intermediate', 'bg-amber-950/60 border-amber-800/60 text-amber-300'],
  ['beginner', 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'],
];

const levelStyle = (level) => {
  const normalized = String(level || '').toLowerCase();
  const match = LEVEL_STYLES.find(([keyword]) => normalized.includes(keyword));
  return match ? match[1] : 'bg-slate-900/60 border-slate-700 text-slate-300';
};

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
      setError(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          'Unable to load course recommendations right now.'
      );
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
      setCoursesError(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          'Unable to load courses for this career path.'
      );
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
  const totalHours = activeCourses.reduce((sum, c) => sum + (Number(c.duration_hours) || 0), 0);
  const noCoursesAnywhere =
    careers.length > 0 && careers.every((c) => !courseCountByCareer[c.occupation_id]);

  // 1. Page-level loading
  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400">
        <Loader2 className="w-10 h-10 animate-spin text-brand-400 mb-4" />
        <p className="text-sm font-medium">Loading your personalized course roadmap...</p>
      </div>
    );
  }

  // 2. Page-level error — distinct from "nothing generated yet"
  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="glass-panel rounded-3xl p-8 text-center border border-slate-800">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white">Could Not Load Course Recommendations</h2>
          <p className="text-xs text-slate-400 mt-2 mb-6">{error}</p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={fetchInitial}
              className="gradient-button px-6 py-3 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" /> Try Again
            </button>
            <Link
              to={`/projects/${projectId}`}
              className="glass-card px-6 py-3 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2 border border-slate-700"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Project
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 3. Nothing generated yet
  if (careers.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="glass-panel rounded-3xl p-8 text-center border border-slate-800">
          <GraduationCap className="w-12 h-12 text-brand-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white">No Course Recommendations Yet</h2>
          <p className="text-xs text-slate-400 mt-2 mb-6">
            Courses are generated alongside your career matches. Head back to the project workspace,
            extract your resume skills, and run the recommendation engine first.
          </p>
          <Link
            to={`/projects/${projectId}`}
            className="gradient-button px-6 py-3 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Project & Generate
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Link
          to={`/projects/${projectId}`}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Project Workspace
        </Link>
        <Link
          to={`/projects/${projectId}/careers`}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <Compass className="w-4 h-4" /> View Career Matches <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Hero Banner */}
      <div className="glass-panel rounded-3xl p-8 relative overflow-hidden border border-slate-800">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
            <GraduationCap className="w-3.5 h-3.5" /> Recommended Learning Path
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Courses to Close Your Gaps in{' '}
            <span className="gradient-text">{project?.project_name}</span>
          </h1>
          <p className="text-slate-300 text-sm max-w-3xl leading-relaxed">
            For every career we matched you with, these are the courses that cover the skills you are
            missing — ranked by how much of the gap each one closes.
          </p>
        </div>
      </div>

      {/* 4. Careers exist, but the engine produced no courses at all */}
      {noCoursesAnywhere && (
        <div className="glass-panel rounded-3xl p-8 text-center border border-amber-900/50">
          <BookOpen className="w-10 h-10 text-amber-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white">No Courses Matched Your Skill Gaps</h2>
          <p className="text-xs text-slate-400 mt-2">
            Your career matches were generated, but the course catalog has nothing mapped to the
            missing skills yet. Check back once more courses are added.
          </p>
        </div>
      )}

      {/* Master / Detail: careers on the left, their courses on the right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: recommended careers */}
        <div className="lg:col-span-5 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" /> Matched Careers
            </span>
            <span className="text-xs text-slate-400 font-normal">Select to see courses</span>
          </h2>

          <div className="space-y-3">
            {careers.slice(0, 5).map((item, idx) => {
              const rank = item.rank_position || idx + 1;
              const matchPct = toPct(item.match_percentage);
              const courseCount = courseCountByCareer[item.occupation_id] || 0;
              const isSelected = selectedOccupationId === item.occupation_id;

              return (
                <div
                  key={item.match_id || item.occupation_id || idx}
                  onClick={() => handleSelectCareer(item.occupation_id)}
                  className={`glass-card p-5 rounded-2xl cursor-pointer border transition-all ${
                    isSelected
                      ? 'border-brand-500 bg-slate-800/90 shadow-xl scale-[1.01]'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-brand-500/20 text-brand-400 font-extrabold text-sm flex items-center justify-center border border-brand-500/30 shrink-0">
                        #{rank}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-white">{item.occupation_name}</h3>
                        <p className="text-xs text-slate-400 line-clamp-1">{item.description}</p>
                      </div>
                    </div>

                    <ChevronRight
                      className={`w-5 h-5 shrink-0 transition-transform ${
                        isSelected ? 'text-brand-400 translate-x-1' : 'text-slate-600'
                      }`}
                    />
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-semibold">
                    <span className="inline-flex items-center gap-1.5 text-brand-300">
                      <BookOpen className="w-3.5 h-3.5" />
                      {courseCount} {courseCount === 1 ? 'course' : 'courses'}
                    </span>
                    <span className="text-emerald-400 font-bold">{matchPct}% Match</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: courses for the selected career */}
        <div className="lg:col-span-7 space-y-6">
          {/* 5. Right-pane loading — also covers the gap between selecting a
              career and the request registering, so the header never flashes
              with an empty course list. */}
          {coursesLoading || (selectedCareer && !coursesLoaded && !coursesError) ? (
            <div className="glass-panel rounded-3xl p-16 text-center text-slate-400 border border-slate-800">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-brand-400 mb-3" />
              <p className="text-sm">Loading courses &amp; AI summaries...</p>
            </div>
          ) : /* 6. Right-pane error, with retry */
          coursesError ? (
            <div className="p-6 rounded-3xl bg-red-950/60 border border-red-800/60 text-center">
              <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
              <p className="text-xs text-red-200 mb-4">{coursesError}</p>
              <button
                onClick={() => loadCareerCourses(selectedOccupationId)}
                className="gradient-button px-5 py-2.5 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          ) : /* 8. Nothing selected */
          !selectedCareer ? (
            <div className="glass-panel rounded-3xl p-12 text-center text-slate-400 border border-slate-800">
              Select a career from the list to view its recommended courses.
            </div>
          ) : /* 7. Loaded, but this career has no courses */
          coursesLoaded && activeCourses.length === 0 ? (
            <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800">
              <BookOpen className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white">No Courses for This Career Yet</h3>
              <p className="text-xs text-slate-400 mt-2">
                We could not map any catalog courses to the skill gaps for{' '}
                {selectedCareer.occupation_name}.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Selected career header */}
              <div className="glass-panel rounded-3xl p-6 border border-slate-800">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-300 uppercase tracking-wider mb-1">
                      <Compass className="w-4 h-4" /> Career #
                      {selectedCareer.rank_position || 1}
                    </div>
                    <h2 className="text-2xl font-extrabold text-white">
                      {selectedCareer.occupation_name}
                    </h2>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <div className="px-4 py-2 rounded-2xl bg-slate-900/60 border border-slate-800 text-center">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase">
                        Courses
                      </div>
                      <div className="text-base font-bold text-white">{activeCourses.length}</div>
                    </div>
                    <div className="px-4 py-2 rounded-2xl bg-slate-900/60 border border-slate-800 text-center">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase">
                        Total Time
                      </div>
                      <div className="text-base font-bold text-white">
                        {totalHours ? `${totalHours} hrs` : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Course cards, in the rank order the backend returned */}
              {activeCourses.map((course, idx) => {
                const coveragePct = toPct(course.coverage_percentage);
                const rank = course.recommendation_rank || idx + 1;

                return (
                  <div
                    key={course.recommendation_id || course.course_id || idx}
                    className="glass-card p-5 rounded-2xl border border-slate-800 space-y-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-xl bg-brand-500/20 text-brand-400 font-extrabold text-sm flex items-center justify-center border border-brand-500/30 shrink-0">
                        #{rank}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-base font-bold text-white">{course.course_name}</h3>
                        {course.description && (
                          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                            {course.description}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Level & duration chips */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium inline-flex items-center gap-1.5 ${levelStyle(
                          course.level
                        )}`}
                      >
                        <Layers className="w-3.5 h-3.5" />
                        {course.level || 'All levels'}
                      </span>
                      <span className="px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-700 text-slate-300 text-xs font-medium inline-flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {toHours(course.duration_hours)}
                      </span>
                    </div>

                    {/* Skill gap coverage bar */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-semibold">
                        <span className="text-slate-400">Skill Gap Coverage</span>
                        <span className="text-emerald-400 font-bold">{coveragePct}%</span>
                      </div>
                      <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                        <div
                          className="bg-gradient-to-r from-brand-500 via-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                          style={{ width: `${coveragePct}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* AI rationale — absent when no summary row was generated */}
                    {course.summary?.summary_text && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Why This Course
                        </h4>
                        <div className="text-xs text-slate-300 leading-relaxed bg-brand-950/30 p-4 rounded-xl border border-brand-800/40">
                          {course.summary.summary_text}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CourseRecommendationsPage;
