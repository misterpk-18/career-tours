import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderPlus,
  ArrowRight,
  UploadCloud,
  Eye,
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { projectsAPI } from '../services/api';
import CreateProjectModal from '../components/CreateProjectModal';
import ResumeUploadModal from '../components/ResumeUploadModal';
import ResumeViewerModal from '../components/ResumeViewerModal';
import Modal from '../components/ui/Modal';
import PageShell from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import StatTile from '../components/ui/StatTile';
import SectionHeading from '../components/ui/SectionHeading';
import { formatDate } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

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
  // The project pending a delete confirmation, and whether the request is in
  // flight.
  const [deletingProject, setDeletingProject] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  // Keyed on the id rather than the object: `student` is a new object identity
  // on every auth refresh, which refetched on each one.
  useEffect(() => {
    if (student?.student_id) {
      fetchProjects();
    }
  }, [student?.student_id]);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await projectsAPI.getByStudentId(student.student_id);
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch student projects:', err);
      setError(apiErrorMessage(err, 'Unable to load projects. Please try refreshing.'));
    } finally {
      setLoading(false);
    }
  };

  const handleProjectCreated = (newProject) => {
    // Clearing the error matters: the fetch failure message is stale the moment
    // a project is created locally, and it used to hide the grid entirely.
    setError('');
    setProjects((prev) => [newProject, ...prev]);
  };

  const handleResumeUploaded = async () => {
    fetchProjects();
  };

  const handleDeleteProject = async () => {
    if (!deletingProject) return;
    setDeleteBusy(true);
    setError('');
    try {
      await projectsAPI.delete(deletingProject.project_id);
      // The server soft-deletes, so the row survives; the UI just drops it from
      // the list. Removing it locally is instant and matches what a refetch
      // would return anyway.
      setProjects((prev) => prev.filter((p) => p.project_id !== deletingProject.project_id));
      setDeletingProject(null);
    } catch (err) {
      console.error('Failed to delete project:', err);
      setError(apiErrorMessage(err, 'Unable to delete this project. Please try again.'));
    } finally {
      setDeleteBusy(false);
    }
  };

  const resumeCount = projects.filter((p) => p.resume_id).length;

  return (
    <PageShell>
      {/* No eyebrow: the top bar's breadcrumb already says PORTAL / DASHBOARD
          two lines above, and repeating it made the page open on the same word
          three times. */}
      <HeroBanner
        title={
          <>
            Hello, {student?.full_name || 'Student'}
          </>
        }
        description="Upload a resume to a project, extract your skills, and see which careers they match."
        actions={
          <Button size="lg" icon={FolderPlus} onClick={() => setIsCreateModalOpen(true)}>
            Create New Project
          </Button>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 pt-6 border-t border-line">
          <StatTile
            value={projects.length}
            tone="brand"
            label="Total Projects"
            sublabel="Projects"
          />
          <StatTile
            value={resumeCount}
            tone="success"
            label="Resumes Uploaded"
            sublabel="Resumes"
          />
        </div>
      </HeroBanner>

      <SectionHeading
        as="h2"
        icon={Layers}
        iconClassName="text-brand-fg"
        right={
          <Button variant="ghost" size="xs" icon={FolderPlus} onClick={() => setIsCreateModalOpen(true)}>
            Add Project
          </Button>
        }
      >
        Your projects
      </SectionHeading>

      {/* Non-blocking: a project created after a failed fetch stays visible. */}
      {error ? (
        <Alert
          tone="error"
          action={
            <Button size="xs" variant="secondary" onClick={fetchProjects}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}

      {loading ? (
        <PageSpinner message="Loading your student projects…" className="py-16" />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderPlus}
          title="No projects created yet"
          titleAs="h3"
          description="Get started by creating your first student project. Then upload your resume to extract skills and view recommended careers."
          action={
            <Button icon={FolderPlus} onClick={() => setIsCreateModalOpen(true)}>
              Create First Project
            </Button>
          }
          className="max-w-xl mx-auto"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Card
              key={project.project_id}
              variant="interactive"
              className="flex flex-col justify-between group"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <Badge mono>ID: {project.project_id.substring(0, 8)}…</Badge>
                  {project.resume_id ? (
                    <Badge tone="success" icon={CheckCircle2}>
                      Resume Linked
                    </Badge>
                  ) : (
                    <Badge tone="warning" icon={Clock}>
                      Pending Resume
                    </Badge>
                  )}
                </div>

                <div>
                  <h3 className="text-lg font-bold text-fg group-hover:text-brand-fg transition-colors line-clamp-1">
                    {project.project_name}
                  </h3>
                  <p className="text-sm text-fg-muted mt-1.5 line-clamp-2 min-h-[42px]">
                    {project.description || 'No detailed description provided.'}
                  </p>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-fg-muted">
                  <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                  Created {formatDate(project.created_at)}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-line space-y-2.5">
                {project.resume_id ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    fullWidth
                    icon={Eye}
                    onClick={() => setViewResumeId(project.resume_id)}
                  >
                    View resume
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    fullWidth
                    icon={UploadCloud}
                    onClick={() => setUploadModalProject(project)}
                  >
                    Upload Resume
                  </Button>
                )}

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    className="flex-1"
                    iconRight={ArrowRight}
                    onClick={() => navigate(`/projects/${project.project_id}`)}
                  >
                    Open project
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    aria-label={`Delete ${project.project_name}`}
                    className="!text-fg-muted hover:!text-danger-fg"
                    onClick={() => setDeletingProject(project)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
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

      {/* key= remounts the viewer so the previous resume's text never bleeds
          through while the next one loads. Safe here (nothing to type). */}
      <ResumeViewerModal
        key={viewResumeId || 'none'}
        isOpen={!!viewResumeId}
        onClose={() => setViewResumeId(null)}
        resumeId={viewResumeId}
      />

      <Modal
        open={Boolean(deletingProject)}
        onClose={() => (deleteBusy ? null : setDeletingProject(null))}
        title="Delete this project?"
      >
        <div className="space-y-4">
          <p className="text-sm text-fg-secondary">
            <span className="font-semibold text-fg">{deletingProject?.project_name}</span> will be
            removed from your dashboard. You can’t undo this from here.
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={deleteBusy}
              onClick={() => setDeletingProject(null)}
            >
              Keep it
            </Button>
            <Button
              variant="danger"
              size="sm"
              icon={Trash2}
              loading={deleteBusy}
              onClick={handleDeleteProject}
            >
              Delete project
            </Button>
          </div>
        </div>
      </Modal>
    </PageShell>
  );
};

export default HomePage;
