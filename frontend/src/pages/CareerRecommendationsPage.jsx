import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { recommendationsAPI, projectsAPI } from '../services/api';
import {
  Compass,
  Award,
  TrendingUp,
  DollarSign,
  ArrowLeft,
  Loader2,
  Sparkles,
  CheckCircle2,
  BookOpen,
  Briefcase,
  Layers,
  GraduationCap,
  ChevronRight
} from 'lucide-react';

export const CareerRecommendationsPage = () => {
  const { projectId } = useParams();

  const [project, setProject] = useState(null);
  const [careers, setCareers] = useState([]);
  const [selectedCareer, setSelectedCareer] = useState(null);
  const [careerDetail, setCareerDetail] = useState(null);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (projectId) {
      fetchRecommendations();
    }
  }, [projectId]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch project info
      const projData = await projectsAPI.getById(projectId);
      setProject(projData);

      // Fetch career recommendations overview
      const overview = await recommendationsAPI.getProjectOverview(projectId);
      const careerList = overview.careers || [];

      setCareers(careerList);

      if (careerList.length > 0) {
        // Automatically inspect top #1 career recommendation
        loadCareerDetail(projectId, careerList[0].occupation_id);
      }
    } catch (err) {
      console.error('Failed to load career recommendations:', err);
      setError('Unable to load career recommendations. Ensure skill extraction was performed.');
    } finally {
      setLoading(false);
    }
  };

  const loadCareerDetail = async (projId, occupationId) => {
    setDetailLoading(true);
    try {
      const detail = await recommendationsAPI.getCareerDetails(projId, occupationId);
      setCareerDetail(detail);
      setSelectedCareer(detail.career);
    } catch (err) {
      console.warn('Failed to load career detail breakdown:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const formatCurrency = (val) => {
    if (!val) return 'Competitive';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400">
        <Loader2 className="w-10 h-10 animate-spin text-brand-400 mb-4" />
        <p className="text-sm font-medium">Computing top 5 career match percentages...</p>
      </div>
    );
  }

  if (error || careers.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="glass-panel rounded-3xl p-8 text-center border border-slate-800">
          <Compass className="w-12 h-12 text-brand-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white">No Career Recommendations Found</h2>
          <p className="text-xs text-slate-400 mt-2 mb-6">
            Please run skill extraction on your project resume first to compute top career matches.
          </p>
          <Link
            to={`/projects/${projectId}`}
            className="gradient-button px-6 py-3 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Project & Extract Skills
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
        <div className="flex items-center gap-4">
          <Link
            to={`/projects/${projectId}/courses`}
            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
          >
            <GraduationCap className="w-4 h-4" /> View Recommended Courses
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
          <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
            AI Career Matching Complete
          </span>
        </div>
      </div>

      {/* Hero Banner */}
      <div className="glass-panel rounded-3xl p-8 relative overflow-hidden border border-slate-800">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-semibold">
            <Compass className="w-3.5 h-3.5" /> Recommended Careers Summary
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Top 5 Career Matches for <span className="gradient-text">{project?.project_name}</span>
          </h1>
          <p className="text-slate-300 text-sm max-w-3xl leading-relaxed">
            Based on your extracted project skills, experience, and domain profiles, our AI engine has matched you with the top 5 highest-fitting career paths.
          </p>
        </div>
      </div>

      {/* Main Grid Layout: Left List of Top 5, Right Detail View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Top 5 Careers Cards */}
        <div className="lg:col-span-5 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" /> Top 5 Ranked Careers
            </span>
            <span className="text-xs text-slate-400 font-normal">Sorted by Match Score</span>
          </h2>

          <div className="space-y-3">
            {careers.slice(0, 5).map((item, idx) => {
              const rank = item.rank_position || idx + 1;
              const matchPct = Math.round(item.match_percentage || 0);
              const isSelected = selectedCareer?.occupation_id === item.occupation_id;

              return (
                <div
                  key={item.match_id || item.occupation_id || idx}
                  onClick={() => loadCareerDetail(projectId, item.occupation_id)}
                  className={`glass-card p-5 rounded-2xl cursor-pointer border transition-all ${
                    isSelected
                      ? 'border-brand-500 bg-slate-800/90 shadow-xl scale-[1.01]'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-brand-500/20 text-brand-400 font-extrabold text-sm flex items-center justify-center border border-brand-500/30">
                        #{rank}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-white">{item.occupation_name}</h3>
                        <p className="text-xs text-slate-400 line-clamp-1">{item.description}</p>
                      </div>
                    </div>

                    <ChevronRight className={`w-5 h-5 transition-transform ${isSelected ? 'text-brand-400 translate-x-1' : 'text-slate-600'}`} />
                  </div>

                  {/* Match Percentage Progress Bar */}
                  <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-slate-400">Match Compatibility</span>
                      <span className="text-emerald-400 font-bold">{matchPct}% Match</span>
                    </div>
                    <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="bg-gradient-to-r from-brand-500 via-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${matchPct}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Active Selected Career Detail & Skill Gaps */}
        <div className="lg:col-span-7 space-y-6">
          {detailLoading ? (
            <div className="glass-panel rounded-3xl p-16 text-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-brand-400 mb-3" />
              <p className="text-sm">Loading career breakdown & skill gaps...</p>
            </div>
          ) : selectedCareer ? (
            <div className="glass-panel rounded-3xl p-8 border border-slate-800 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                <div>
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1">
                    <CheckCircle2 className="w-4 h-4" /> Top Recommendation #{selectedCareer.rank_position || 1}
                  </div>
                  <h2 className="text-2xl font-extrabold text-white">{selectedCareer.occupation_name}</h2>
                </div>

                <div className="px-4 py-2 rounded-2xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-extrabold text-lg text-center shrink-0">
                  {Math.round(selectedCareer.match_percentage || 0)}% Match
                </div>
              </div>

              {/* Key Salary & Growth Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <DollarSign className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 uppercase">Average Salary</div>
                    <div className="text-base font-bold text-white">{formatCurrency(selectedCareer.average_salary)} / yr</div>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 uppercase">Growth Outlook</div>
                    <div className="text-base font-bold text-emerald-400">{selectedCareer.growth_outlook || 'High Demand'}</div>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Occupation Overview</h4>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                  {selectedCareer.description}
                </p>
              </div>

              {/* AI Strategic Summary */}
              {careerDetail?.summary && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" /> AI Strategic Insights
                  </h4>
                  <div className="text-xs text-slate-300 leading-relaxed bg-brand-950/30 p-4 rounded-xl border border-brand-800/40">
                    {careerDetail.summary.summary_text}
                  </div>
                </div>
              )}

              {/* Skill Gap Analysis */}
              {careerDetail?.skill_gaps && careerDetail.skill_gaps.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-brand-400" /> Skill Gaps to Bridge
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {careerDetail.skill_gaps.map((gap, gIdx) => (
                      <span
                        key={gIdx}
                        className="px-3 py-1.5 rounded-lg bg-amber-950/60 border border-amber-800/60 text-amber-300 text-xs font-medium flex items-center gap-1.5"
                      >
                        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                        {gap.skill_name || `Gap Skill #${gIdx + 1}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="glass-panel rounded-3xl p-12 text-center text-slate-400">
              Select a career from the top 5 list to inspect salary metrics and skill gaps.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CareerRecommendationsPage;
