import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { projectsAPI } from '../services/api';
import CreateProjectModal from '../components/CreateProjectModal';
import ResumeUploadModal from '../components/ResumeUploadModal';
import ResumeViewerModal from '../components/ResumeViewerModal';
import {
  FolderPlus,
  FileText,
  Sparkles,
  ArrowRight,
  UploadCloud,
  Eye,
  Download,
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  Compass,
  Briefcase
} from 'lucide-react';

export const HomePage = () => {
  const { student } = useAuth();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [uploadModalProject, setUploadModalProject] = useState(null);
  const [viewResumeId, setViewResumeId] = useState(null);

  useEffect(() => {
    if (student?.student_id) {
      fetchProjects();
    }
  }, [student]);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await projectsAPI.getByStudentId(student.student_id);
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch student projects:', err);
      setError('Unable to load projects. Please try refreshing.');
    } finally {
      setLoading(false);
    }
  };

  const handleProjectCreated = (newProject) => {
    setProjects([newProject, ...projects]);
  };

  const handleResumeUploaded = async () => {
    fetchProjects();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8">
      {/* Welcome Banner */}
      <div className="glass-panel rounded-3xl p-8 relative overflow-hidden border border-slate-800">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" /> Student Career Dashboard
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
              Hello, <span className="gradient-text">{student?.full_name || 'Student'}</span> 👋
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
              Create student projects, upload your resumes, extract AI skill insights, and get match percentages for top career paths.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="gradient-button px-6 py-3.5 rounded-2xl text-white font-bold text-sm flex items-center justify-center gap-2 shrink-0 shadow-xl"
          >
            <FolderPlus className="w-5 h-5" />
            <span>Create New Project</span>
          </button>
        </div>

        {/* Dashboard Quick Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 pt-6 border-t border-slate-800/80">
          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xl">
              {projects.length}
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Total Projects</div>
              <div className="text-lg font-bold text-white">Active Portfolios</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xl">
              {projects.filter(p => p.resume_id).length}
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Resumes Uploaded</div>
              <div className="text-lg font-bold text-white">Ready for Extraction</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xl">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">AI Recommendation Engine</div>
              <div className="text-lg font-bold text-white">Top 5 Matching</div>
            </div>
          </div>
        </div>
      </div>

      {/* Projects Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-brand-400" />
            My Student Projects
          </h2>
          <p className="text-xs text-slate-400 mt-1">Select a project to review resumes, extract skills, and view career recommendations</p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          + Add Project
        </button>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-400">
          <Clock className="w-8 h-8 animate-spin mx-auto text-brand-400 mb-3" />
          <p className="text-sm">Loading your student projects...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-2xl bg-red-950/50 border border-red-800/60 text-red-200 text-sm">
          {error}
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800 max-w-xl mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center mx-auto mb-4">
            <FolderPlus className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white">No projects created yet</h3>
          <p className="text-slate-400 text-xs mt-2 mb-6">
            Get started by creating your first student project. Then upload your resume to extract skills and view recommended careers.
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="gradient-button px-6 py-3 rounded-xl text-white font-semibold text-xs inline-flex items-center gap-2 shadow-lg"
          >
            <FolderPlus className="w-4 h-4" />
            Create First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.project_id}
              className="glass-card rounded-2xl p-6 flex flex-col justify-between relative group"
            >
              <div className="space-y-4">
                {/* Status & ID */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    ID: {project.project_id.substring(0, 8)}...
                  </span>
                  {project.resume_id ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Resume Linked
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/60">
                      <Clock className="w-3 h-3 text-amber-400" /> Pending Resume
                    </span>
                  )}
                </div>

                {/* Title & Description */}
                <div>
                  <h3 className="text-lg font-bold text-white group-hover:text-brand-300 transition-colors line-clamp-1">
                    {project.project_name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 min-h-[36px]">
                    {project.description || 'No detailed description provided.'}
                  </p>
                </div>

                {/* Date */}
                <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                  <Calendar className="w-3.5 h-3.5" />
                  Created {new Date(project.created_at).toLocaleDateString()}
                </div>
              </div>

              {/* Action Buttons Container */}
              <div className="mt-6 pt-4 border-t border-slate-800/80 space-y-2.5">
                {/* Resume Action row */}
                <div>
                  {project.resume_id ? (
                    <button
                      onClick={() => setViewResumeId(project.resume_id)}
                      className="w-full py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700/80 flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5 text-purple-400" />
                      Review & Download Resume
                    </button>
                  ) : (
                    <button
                      onClick={() => setUploadModalProject(project)}
                      className="w-full py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700/80 flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <UploadCloud className="w-3.5 h-3.5 text-brand-400" />
                      Upload Resume
                    </button>
                  )}
                </div>

                {/* Primary Navigate to Project Page */}
                <button
                  onClick={() => navigate(`/projects/${project.project_id}`)}
                  className="w-full py-2.5 px-4 rounded-xl gradient-button text-white font-semibold text-xs flex items-center justify-center gap-2 group-hover:shadow-lg transition-all"
                >
                  <span>Open Project Page & Extract Skills</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />

      <ResumeUploadModal
        isOpen={!!uploadModalProject}
        onClose={() => setUploadModalProject(null)}
        project={uploadModalProject}
        onResumeUploaded={handleResumeUploaded}
      />

      <ResumeViewerModal
        isOpen={!!viewResumeId}
        onClose={() => setViewResumeId(null)}
        resumeId={viewResumeId}
      />
    </div>
  );
};

export default HomePage;
