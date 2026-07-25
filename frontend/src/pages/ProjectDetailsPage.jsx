import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { projectsAPI, resumesAPI, recommendationsAPI } from '../services/api';
import ResumeUploadModal from '../components/ResumeUploadModal';
import ResumeViewerModal from '../components/ResumeViewerModal';
import {
  Folder,
  FileText,
  UploadCloud,
  Eye,
  Sparkles,
  Compass,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Award,
  Zap,
  Tag,
  Star,
  ArrowRight,
  GraduationCap,
} from 'lucide-react';

// Helper: deduplicate skills by skill_name, keeping the latest entry
const deduplicateSkills = (skills) => {
  const map = new Map();
  for (const skill of skills) {
    const key = (skill.skill_name || '').toLowerCase().trim();
    if (!key) continue;
    // Overwrite with the latest occurrence (assumes array is ordered oldest→newest)
    map.set(key, skill);
  }
  return Array.from(map.values());
};

// localStorage helpers for caching extracted skills per project
const SKILLS_CACHE_KEY = (projectId) => `ct_skills_${projectId}`;

const getCachedSkills = (projectId) => {
  try {
    const raw = localStorage.getItem(SKILLS_CACHE_KEY(projectId));
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
};

const setCachedSkills = (projectId, skills) => {
  try {
    localStorage.setItem(SKILLS_CACHE_KEY(projectId), JSON.stringify(skills));
  } catch { /* ignore */ }
};

export const ProjectDetailsPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Skills state
  const [skills, setSkills] = useState([]);
  const [skillsAlreadyExtracted, setSkillsAlreadyExtracted] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractSuccess, setExtractSuccess] = useState('');

  // Career recommendation state
  const [careersAlreadyGenerated, setCareersAlreadyGenerated] = useState(false);
  const [recommending, setRecommending] = useState(false);

  // Modals state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [viewResumeId, setViewResumeId] = useState(null);

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId]);

  const fetchProjectData = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await projectsAPI.getById(projectId);
      setProject(data);

      // 1. Try loading cached skills from localStorage
      const cached = getCachedSkills(projectId);
      if (cached && cached.length > 0) {
        setSkills(deduplicateSkills(cached));
        setSkillsAlreadyExtracted(true);
      }

      // 2. Check if career recommendations already exist
      try {
        const overview = await recommendationsAPI.getProjectOverview(projectId);
        if (overview?.careers && overview.careers.length > 0) {
          setCareersAlreadyGenerated(true);
        }
      } catch (err) {
        // No recommendations yet — that's fine
      }
    } catch (err) {
      console.error('Failed to load project details:', err);
      setError('Unable to load project details.');
    } finally {
      setLoading(false);
    }
  };

  const handleExtractSkills = async () => {
    if (!project?.resume_id) {
      setError('Please upload a resume first before extracting skills.');
      return;
    }

    setExtracting(true);
    setError('');
    setExtractSuccess('');

    try {
      const res = await resumesAPI.extractSkills(project.resume_id);
      if (res.skills) {
        const unique = deduplicateSkills(res.skills);
        setSkills(unique);
        setSkillsAlreadyExtracted(true);
        setCachedSkills(projectId, unique);
        setExtractSuccess(`Successfully extracted ${unique.length} skills from resume!`);
      }
    } catch (err) {
      console.error('Skill extraction failed:', err);
      const apiError = err.response?.data?.error || err.response?.data?.detail || 'Failed to extract skills from resume.';
      setError(apiError);
    } finally {
      setExtracting(false);
    }
  };

  const handleRecommendCareers = async () => {
    setRecommending(true);
    setError('');
    try {
      await recommendationsAPI.generate(projectId);
      setCareersAlreadyGenerated(true);
      navigate(`/projects/${projectId}/careers`);
    } catch (err) {
      console.error('Failed to generate career recommendations:', err);
      const apiError = err.response?.data?.error || err.response?.data?.detail || 'Failed to generate recommendations.';
      setError(apiError);
    } finally {
      setRecommending(false);
    }
  };

  const handleViewCareers = () => {
    navigate(`/projects/${projectId}/careers`);
  };

  // Courses are produced by the same generate call as careers, so the careers
  // flag gates both destinations.
  const handleViewCourses = () => {
    navigate(`/projects/${projectId}/courses`);
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400">
        <Loader2 className="w-10 h-10 animate-spin text-brand-400 mb-4" />
        <p className="text-sm font-medium">Loading project workspace...</p>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="p-6 rounded-2xl bg-red-950/60 border border-red-800/60 text-red-200 text-sm">
          {error}
        </div>
        <Link to="/" className="inline-flex items-center gap-2 mt-4 text-xs font-semibold text-brand-400">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Projects Dashboard
        </Link>
        <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
          Project UUID: {project.project_id}
        </span>
      </div>

      {/* Project Header Banner */}
      <div className="glass-panel rounded-3xl p-8 relative overflow-hidden border border-slate-800">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
              <Folder className="w-3.5 h-3.5" /> Project Workspace
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">{project.project_name}</h1>
            <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
              {project.description || 'No description provided for this project.'}
            </p>
          </div>

          {/* Quick Resume Controls */}
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            {project.resume_id ? (
              <button
                onClick={() => setViewResumeId(project.resume_id)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-2 transition-all"
              >
                <Eye className="w-4 h-4 text-purple-400" />
                Review & Download Resume
              </button>
            ) : (
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-2 transition-all"
              >
                <UploadCloud className="w-4 h-4 text-brand-400" />
                Upload Resume
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Extract Skills & Career Actions Header */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              AI Skill Extraction Engine
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              {skillsAlreadyExtracted
                ? 'Skills have been successfully extracted from your resume'
                : 'Extract technical and domain skills from your uploaded resume to power career match recommendations'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Only show Extract Skills button if skills have NOT been extracted yet */}
            {!skillsAlreadyExtracted && (
              <button
                onClick={handleExtractSkills}
                disabled={extracting || !project.resume_id}
                className="gradient-button px-5 py-2.5 rounded-xl text-white font-semibold text-xs flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                {extracting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting Skills...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Extract Skills</span>
                  </>
                )}
              </button>
            )}

            {/* Show extracted badge when skills are done */}
            {skillsAlreadyExtracted && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/80 border border-emerald-800/60 text-emerald-300 text-xs font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                Skills Extracted
              </div>
            )}

            {/* Recommendation buttons. The "view" pair is gated on
                careersAlreadyGenerated (fetched from the API) rather than on
                `skills`, which is only ever hydrated from localStorage — on a
                fresh browser the cache is empty even though recommendations
                exist server-side, which used to hide these buttons entirely. */}
            {careersAlreadyGenerated ? (
              <>
                <button
                  onClick={handleViewCareers}
                  className="gradient-button-emerald px-6 py-2.5 rounded-xl text-white font-bold text-xs flex items-center gap-2 shadow-xl"
                >
                  <Compass className="w-4 h-4" />
                  <span>View Recommended Careers</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={handleViewCourses}
                  className="glass-card px-6 py-2.5 rounded-xl text-white font-bold text-xs flex items-center gap-2 border border-slate-700"
                >
                  <GraduationCap className="w-4 h-4" />
                  <span>View Recommended Courses</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </>
            ) : skills.length > 0 ? (
              <button
                onClick={handleRecommendCareers}
                disabled={recommending}
                className="gradient-button-emerald px-6 py-2.5 rounded-xl text-white font-bold text-xs flex items-center gap-2 shadow-xl"
              >
                {recommending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing Careers...</span>
                  </>
                ) : (
                  <>
                    <Compass className="w-4 h-4" />
                    <span>Recommend Careers ✨</span>
                  </>
                )}
              </button>
            ) : null}
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/60 border border-red-800/60 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <div>{error}</div>
          </div>
        )}

        {extractSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>{extractSuccess}</div>
          </div>
        )}

        {!project.resume_id && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/50 text-amber-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Please upload a resume file (PDF or DOCX) to enable AI Skill Extraction.</span>
            </div>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="text-amber-300 hover:text-white font-semibold underline text-xs shrink-0"
            >
              Upload Now
            </button>
          </div>
        )}
      </div>

      {/* Extracted Skills Showcase Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Tag className="w-4 h-4 text-brand-400" />
            Extracted Skills ({skills.length})
          </h3>
          {skills.length > 0 && (
            <button
              onClick={careersAlreadyGenerated ? handleViewCareers : handleRecommendCareers}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              {careersAlreadyGenerated ? 'View Career Recommendations' : 'Go to Career Page'} <Compass className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {skills.length === 0 ? (
          <div className="glass-panel rounded-2xl p-10 text-center border border-slate-800">
            <Sparkles className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h4 className="text-sm font-bold text-white">No skills extracted yet</h4>
            <p className="text-xs text-slate-400 mt-1 mb-4">
              Click the "Extract Skills" button above to run AI parsing on your uploaded resume.
            </p>
            {project.resume_id && !skillsAlreadyExtracted && (
              <button
                onClick={handleExtractSkills}
                disabled={extracting}
                className="gradient-button px-5 py-2.5 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2"
              >
                <Zap className="w-4 h-4 text-amber-300" />
                Extract Skills Now
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {skills.map((skill, index) => (
              <div
                key={skill.project_skill_id || index}
                className="glass-card p-4 rounded-xl border border-slate-800/80 flex flex-col justify-between hover:border-brand-500/40 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-bold text-white">{skill.skill_name}</div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-brand-950 text-brand-300 border border-brand-800/60 uppercase shrink-0">
                    {skill.source && skill.source.length <= 20 ? skill.source : 'Resume'}
                  </span>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1 text-slate-400">
                    <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                    <span>Level {skill.proficiency_level || 5}/10</span>
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    Conf: <span className="text-emerald-400 font-semibold">{Math.round((skill.confidence_score || 1) * 100)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <ResumeUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        project={project}
        onResumeUploaded={async () => {
          await fetchProjectData();
        }}
      />

      <ResumeViewerModal
        isOpen={!!viewResumeId}
        onClose={() => setViewResumeId(null)}
        resumeId={viewResumeId}
      />
    </div>
  );
};

export default ProjectDetailsPage;
