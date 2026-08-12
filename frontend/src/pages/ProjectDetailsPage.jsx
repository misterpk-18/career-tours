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
import JobProgress from '../components/ui/JobProgress';
import useJob from '../hooks/useJob';
import { JOB_GENERATE_RECOMMENDATIONS } from '../lib/jobStages';
import { deduplicateSkills } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

export const ProjectDetailsPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Skills state
  const [skills, setSkills] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [extractSuccess, setExtractSuccess] = useState('');

  // Career recommendation state. The run itself lives in useJob, which also
  // re-attaches to one already in progress when this page mounts — so a reload
  // or a second tab picks the same run back up with nothing stored client-side.
  const [careersAlreadyGenerated, setCareersAlreadyGenerated] = useState(false);
  const {
    job: generateJob,
    start: startGenerate,
    starting: submittingGenerate,
    error: generateError,
    active: generateActive,
  } = useJob({
    projectId,
    jobType: JOB_GENERATE_RECOMMENDATIONS,
    // Only a succeeded run has recommendations to show. A failed one must not
    // set this flag: the generator clears the old recommendations before
    // writing new ones, so the project genuinely has none to view.
    onSucceeded: () => setCareersAlreadyGenerated(true),
  });

  const recommending = submittingGenerate || generateActive;

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

      // Which pipeline step this project is on is decided here, from the server.
      // Both of these must resolve before the action buttons render, otherwise
      // the page briefly offers a step the project has already completed.
      try {
        const stored = await projectsAPI.getSkills(projectId);
        setSkills(deduplicateSkills(stored || []));
      } catch (err) {
        console.error('Failed to load stored project skills:', err);
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
        // The API returns stored skills instead of re-running the extraction when
        // this project already has them, so don't claim a fresh parse.
        setExtractSuccess(
          res.reused
            ? `Loaded ${unique.length} skills already extracted from this resume.`
            : `Extracted ${unique.length} skills from your resume.`
        );
      }
    } catch (err) {
      console.error('Skill extraction failed:', err);
      setError(apiErrorMessage(err, 'Failed to extract skills from resume.'));
    } finally {
      setExtracting(false);
    }
  };

  // Submit and poll rather than await. Generation takes ~2 minutes, which is far
  // longer than any HTTP request should be held open, and it used to be spent
  // behind a spinning button that said nothing.
  //
  // Deliberately does NOT navigate on success any more: the user has been on
  // this page for two minutes and may well have started reading something else.
  // Yanking them to another route at an unpredictable moment is worse than
  // showing them a button. The double-click guard is gone too — the server now
  // returns the in-flight job for a second submit, which also holds across
  // browser tabs, which no client-side flag could.
  const handleRecommendCareers = () =>
    startGenerate(() => recommendationsAPI.generateAsync(projectId));

  const handleViewCareers = () => navigate(`/projects/${projectId}/careers`);

  // Courses are produced by the same generate call as careers, so the careers
  // flag gates both destinations.
  const handleViewCourses = () => navigate(`/projects/${projectId}/courses`);

  // The pipeline is strictly sequential: upload a resume, extract skills from it,
  // then generate recommendations. Each step's control appears only once the step
  // before it is done and disappears once the step itself is, so the page never
  // offers an action that cannot succeed. All three flags come from the server.
  const hasResume = Boolean(project?.resume_id);
  const hasSkills = skills.length > 0;
  const canExtractSkills = hasResume && !hasSkills;
  const canRecommendCareers = hasSkills && !careersAlreadyGenerated;

  if (loading) {
    return <PageSpinner message="Loading project workspace…" />;
  }

  if (error && !project) {
    return (
      <NarrowShell>
        <EmptyState
          icon={AlertTriangle}
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
              View resume
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

      <Card className="space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="min-w-0">
            <SectionHeading as="h2" size="sm" icon={Zap} iconClassName="text-warning-fg">
              Skills from your resume
            </SectionHeading>
            <p className="text-sm text-fg-muted mt-1">
              {!hasResume
                ? 'Upload a resume to this project to extract the skills that power career matching.'
                : hasSkills
                  ? 'Skills have been successfully extracted from your resume.'
                  : 'Extract technical and domain skills from your uploaded resume to power career match recommendations.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* No resume means no step to offer here: the upload control lives in
                the banner and the warning below, so rendering a dead "Extract
                skills" button as well only invited the click it then refused. */}
            {canExtractSkills ? (
              <Button
                icon={Sparkles}
                onClick={handleExtractSkills}
                loading={extracting}
                loadingText="Extracting skills…"
              >
                Extract skills
              </Button>
            ) : hasSkills ? (
              <Badge tone="success" icon={CheckCircle2}>
                Skills Extracted
              </Badge>
            ) : null}

            {careersAlreadyGenerated ? (
              <>
                <Button icon={Compass} onClick={handleViewCareers}>
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
            ) : canRecommendCareers ? (
              <Button
                icon={Compass}
                onClick={handleRecommendCareers}
                loading={recommending}
                loadingText="Analysing…"
              >
                Recommend Careers
              </Button>
            ) : null}
          </div>
        </div>

        {error ? <Alert tone="error">{error}</Alert> : null}
        {generateError ? <Alert tone="error">{generateError}</Alert> : null}
        {extractSuccess ? <Alert tone="success">{extractSuccess}</Alert> : null}

        {/* Renders the live bar while running and the reason on failure. Returns
            null once the run has succeeded, at which point the buttons above
            have already switched to the View actions. */}
        <JobProgress job={generateJob} />

        {generateJob?.status === 'succeeded' ? (
          <Alert
            tone="success"
            action={
              <Button variant="ghost" size="xs" iconRight={ArrowRight} onClick={handleViewCareers}>
                View Careers
              </Button>
            }
          >
            Your career recommendations are ready.
          </Alert>
        ) : null}

        {!hasResume ? (
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
            hasSkills ? (
              <Button
                variant="ghost"
                size="xs"
                iconRight={Compass}
                onClick={careersAlreadyGenerated ? handleViewCareers : handleRecommendCareers}
                loading={recommending}
                loadingText="Analysing…"
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
            icon={Tag}
            size="sm"
            title="No skills extracted yet"
            titleAs="h3"
            description={
              hasResume
                ? 'Use the "Extract Skills" button above to run AI parsing on your uploaded resume.'
                : 'Upload a resume to this project first — skill extraction runs on the uploaded file.'
            }
            action={
              canExtractSkills ? (
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
