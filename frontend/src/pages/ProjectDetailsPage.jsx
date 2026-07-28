import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Folder,
  UploadCloud,
  Eye,
  Sparkles,
  Compass,
  ArrowLeft,
  AlertTriangle,
  Zap,
  Tag,
  Star,
  ArrowRight,
  GraduationCap,
  CheckCircle2,
} from 'lucide-react';
import { projectsAPI, resumesAPI, recommendationsAPI } from '../services/api';
import ResumeUploadModal from '../components/ResumeUploadModal';
import ResumeViewerModal from '../components/ResumeViewerModal';
import PageShell, { NarrowShell } from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import SectionHeading from '../components/ui/SectionHeading';
import { deduplicateSkills } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

// localStorage cache of extracted skills per project. Temporary: it exists only
// because there is no GET endpoint for a project's skills yet, and it is the one
// place the client stores server data. Removed once
// GET /api/projects/<id>/skills lands.
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

      const cached = getCachedSkills(projectId);
      if (cached && cached.length > 0) {
        setSkills(deduplicateSkills(cached));
        setSkillsAlreadyExtracted(true);
      }

      try {
        const overview = await recommendationsAPI.getProjectOverview(projectId);
        if (overview?.careers && overview.careers.length > 0) {
          setCareersAlreadyGenerated(true);
        }
      } catch (err) {
        // No recommendations yet — that's fine.
      }
    } catch (err) {
      console.error('Failed to load project details:', err);
      setError(apiErrorMessage(err, 'Unable to load project details.'));
    } finally {
      setLoading(false);
    }
  };

  const handleExtractSkills = async () => {
    if (extracting) return;
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
      setError(apiErrorMessage(err, 'Failed to extract skills from resume.'));
    } finally {
      setExtracting(false);
    }
  };

  // Guarded: this handler is reachable from two triggers, and without the
  // early return a fast double-click fired two concurrent generate requests.
  const handleRecommendCareers = async () => {
    if (recommending) return;

    setRecommending(true);
    setError('');
    try {
      await recommendationsAPI.generate(projectId);
      setCareersAlreadyGenerated(true);
      navigate(`/projects/${projectId}/careers`);
    } catch (err) {
      console.error('Failed to generate career recommendations:', err);
      setError(apiErrorMessage(err, 'Failed to generate recommendations.'));
    } finally {
      setRecommending(false);
    }
  };

  const handleViewCareers = () => navigate(`/projects/${projectId}/careers`);

  // Courses are produced by the same generate call as careers, so the careers
  // flag gates both destinations.
  const handleViewCourses = () => navigate(`/projects/${projectId}/courses`);

  if (loading) {
    return <PageSpinner message="Loading project workspace…" />;
  }

  if (error && !project) {
    return (
      <NarrowShell>
        <EmptyState
          icon={AlertTriangle}
          iconTone="danger"
          title="Could Not Load This Project"
          titleAs="h1"
          description={error}
          action={
            <>
              <Button onClick={fetchProjectData}>Try Again</Button>
              <Button as={Link} to="/" variant="secondary" icon={ArrowLeft}>
                Back to Dashboard
              </Button>
            </>
          }
        />
      </NarrowShell>
    );
  }

  return (
    <PageShell>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Button as={Link} to="/" variant="ghost" size="xs" icon={ArrowLeft}>
          Back to Projects Dashboard
        </Button>
        {/* break-all: a full UUID overflowed its pill on narrow screens. */}
        <Badge mono className="whitespace-normal break-all max-w-full">
          Project UUID: {project.project_id}
        </Badge>
      </div>

      <HeroBanner
        eyebrow="Project Workspace"
        eyebrowIcon={Folder}
        title={project.project_name}
        description={project.description || 'No description provided for this project.'}
        actions={
          project.resume_id ? (
            <Button
              variant="secondary"
              size="sm"
              icon={Eye}
              onClick={() => setViewResumeId(project.resume_id)}
            >
              Review &amp; Download Resume
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              icon={UploadCloud}
              onClick={() => setIsUploadModalOpen(true)}
            >
              Upload Resume
            </Button>
          )
        }
      />

      <Card radius="2xl" className="space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="min-w-0">
            <SectionHeading as="h2" size="sm" icon={Zap} iconClassName="text-warning-fg">
              AI Skill Extraction Engine
            </SectionHeading>
            <p className="text-sm text-fg-muted mt-1">
              {skillsAlreadyExtracted
                ? 'Skills have been successfully extracted from your resume.'
                : 'Extract technical and domain skills from your uploaded resume to power career match recommendations.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {!skillsAlreadyExtracted ? (
              <Button
                icon={Sparkles}
                onClick={handleExtractSkills}
                loading={extracting}
                loadingText="Extracting Skills…"
                disabled={!project.resume_id}
              >
                Extract Skills
              </Button>
            ) : (
              <Badge tone="success" icon={CheckCircle2}>
                Skills Extracted
              </Badge>
            )}

            {/* The "view" pair is gated on careersAlreadyGenerated (from the API)
                rather than on `skills`, which is only ever hydrated from
                localStorage — on a fresh browser the cache is empty even though
                recommendations exist server-side, which used to hide these
                buttons entirely. */}
            {careersAlreadyGenerated ? (
              <>
                <Button variant="success" icon={Compass} iconRight={ArrowRight} onClick={handleViewCareers}>
                  View Recommended Careers
                </Button>
                <Button
                  variant="secondary"
                  icon={GraduationCap}
                  iconRight={ArrowRight}
                  onClick={handleViewCourses}
                >
                  View Recommended Courses
                </Button>
              </>
            ) : skills.length > 0 ? (
              <Button
                variant="success"
                icon={Compass}
                onClick={handleRecommendCareers}
                loading={recommending}
                loadingText="Analyzing Careers…"
              >
                Recommend Careers
              </Button>
            ) : null}
          </div>
        </div>

        {error ? <Alert tone="error">{error}</Alert> : null}
        {extractSuccess ? <Alert tone="success">{extractSuccess}</Alert> : null}

        {!project.resume_id ? (
          <Alert
            tone="warning"
            action={
              <Button variant="ghost" size="xs" onClick={() => setIsUploadModalOpen(true)}>
                Upload Now
              </Button>
            }
          >
            Please upload a resume file (PDF or DOCX) to enable AI skill extraction.
          </Alert>
        ) : null}
      </Card>

      <div className="space-y-4">
        <SectionHeading
          as="h2"
          size="sm"
          icon={Tag}
          iconClassName="text-brand-fg"
          right={
            skills.length > 0 ? (
              <Button
                variant="ghost"
                size="xs"
                iconRight={Compass}
                onClick={careersAlreadyGenerated ? handleViewCareers : handleRecommendCareers}
                loading={recommending}
                loadingText="Analyzing…"
              >
                {careersAlreadyGenerated ? 'View Career Recommendations' : 'Go to Career Page'}
              </Button>
            ) : null
          }
        >
          Extracted Skills ({skills.length})
        </SectionHeading>

        {skills.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            iconTone="neutral"
            size="sm"
            title="No skills extracted yet"
            titleAs="h3"
            description='Use the "Extract Skills" button above to run AI parsing on your uploaded resume.'
            action={
              project.resume_id && !skillsAlreadyExtracted ? (
                <Button icon={Zap} onClick={handleExtractSkills} loading={extracting} loadingText="Extracting…">
                  Extract Skills Now
                </Button>
              ) : null
            }
          />
        ) : (
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 list-none">
            {skills.map((skill, index) => (
              <Card
                as="li"
                key={skill.project_skill_id || index}
                variant="solid"
                radius="xl"
                padding="sm"
                className="flex flex-col justify-between"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-bold text-fg">{skill.skill_name}</div>
                  <Badge tone="brand" className="uppercase">
                    {skill.source && skill.source.length <= 20 ? skill.source : 'Resume'}
                  </Badge>
                </div>

                <div className="mt-4 pt-3 border-t border-line flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-1 text-fg-muted">
                    <Star className="w-3.5 h-3.5 text-warning-fg fill-current" aria-hidden="true" />
                    <span>Level {skill.proficiency_level || 5}/10</span>
                  </div>
                  <div className="text-fg-muted">
                    Conf:{' '}
                    <span className="text-success-fg font-semibold">
                      {Math.round((skill.confidence_score || 1) * 100)}%
                    </span>
                  </div>
                </div>
              </Card>
            ))}
          </ul>
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
        key={viewResumeId || 'none'}
        isOpen={!!viewResumeId}
        onClose={() => setViewResumeId(null)}
        resumeId={viewResumeId}
      />
    </PageShell>
  );
};

export default ProjectDetailsPage;
