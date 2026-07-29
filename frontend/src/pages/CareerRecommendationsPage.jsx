import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Compass,
  Award,
  TrendingUp,
  DollarSign,
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  GraduationCap,
  ChevronRight,
} from 'lucide-react';
import { recommendationsAPI, projectsAPI } from '../services/api';
import PageShell, { NarrowShell } from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import PaneSpinner from '../components/ui/PaneSpinner';
import HeroBanner from '../components/ui/HeroBanner';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Chip from '../components/ui/Chip';
import EmptyState from '../components/ui/EmptyState';
import MetricTile from '../components/ui/MetricTile';
import ProgressBar from '../components/ui/ProgressBar';
import RankBadge from '../components/ui/RankBadge';
import SectionHeading from '../components/ui/SectionHeading';
import SectionLabel from '../components/ui/SectionLabel';
import AiInsightBox from '../components/ui/AiInsightBox';
import SummarySections from '../components/ui/SummarySections';
import SelectableCard, { SelectableList } from '../components/ui/SelectableCard';
import { toPct, formatCurrency } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

export const CareerRecommendationsPage = () => {
  const { projectId } = useParams();

  const [project, setProject] = useState(null);
  const [careers, setCareers] = useState([]);
  const [selectedCareer, setSelectedCareer] = useState(null);
  const [careerDetail, setCareerDetail] = useState(null);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');
  // Detail failures used to be swallowed into a console.warn, leaving the pane
  // on the "select a career" placeholder after the user had already clicked one.
  const [detailError, setDetailError] = useState('');
  const [selectedOccupationId, setSelectedOccupationId] = useState(null);

  useEffect(() => {
    if (projectId) {
      fetchRecommendations();
    }
  }, [projectId]);

  const fetchRecommendations = async () => {
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

      if (careerList.length > 0) {
        const firstId = careerList[0].occupation_id;
        setSelectedOccupationId(firstId);
        loadCareerDetail(firstId);
      }
    } catch (err) {
      console.error('Failed to load career recommendations:', err);
      setError(apiErrorMessage(err, 'Unable to load career recommendations right now.'));
    } finally {
      setLoading(false);
    }
  };

  const loadCareerDetail = async (occupationId) => {
    setDetailLoading(true);
    setDetailError('');
    try {
      const detail = await recommendationsAPI.getCareerDetails(projectId, occupationId);
      setCareerDetail(detail);
      setSelectedCareer(detail.career);
    } catch (err) {
      console.error('Failed to load career detail breakdown:', err);
      setDetailError(apiErrorMessage(err, 'Unable to load the breakdown for this career.'));
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSelectCareer = (occupationId) => {
    setSelectedOccupationId(occupationId);
    loadCareerDetail(occupationId);
  };

  if (loading) {
    return <PageSpinner message="Computing top 5 career match percentages…" />;
  }

  // A real failure and "nothing generated yet" were previously the same branch,
  // so a network error was reported as "you haven't extracted skills".
  if (error) {
    return (
      <NarrowShell>
        <EmptyState
          icon={AlertTriangle}
          iconTone="danger"
          title="Could Not Load Career Recommendations"
          titleAs="h1"
          description={error}
          action={
            <>
              <Button icon={RefreshCw} onClick={fetchRecommendations}>
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

  if (careers.length === 0) {
    return (
      <NarrowShell>
        <EmptyState
          icon={Compass}
          title="No Career Recommendations Yet"
          titleAs="h1"
          description="Run skill extraction on your project resume first, then generate recommendations to see your top career matches."
          action={
            <Button as={Link} to={`/projects/${projectId}`} icon={ArrowLeft}>
              Return to Project &amp; Extract Skills
            </Button>
          }
        />
      </NarrowShell>
    );
  }

  return (
    <PageShell>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Button as={Link} to={`/projects/${projectId}`} variant="ghost" size="xs" icon={ArrowLeft}>
          Back to Project Workspace
        </Button>
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            as={Link}
            to={`/projects/${projectId}/courses`}
            variant="ghost"
            size="xs"
            icon={GraduationCap}
            iconRight={ChevronRight}
          >
            View Recommended Courses
          </Button>
          <Badge tone="success" mono>
            AI Career Matching Complete
          </Badge>
        </div>
      </div>

      <HeroBanner
        eyebrow="Recommended Careers Summary"
        eyebrowIcon={Compass}
        eyebrowTone="success"
        orbTone="success"
        title={
          <>
            Top 5 Career Matches for{' '}
            <span className="text-gradient">{project?.project_name}</span>
          </>
        }
        description="Based on your extracted project skills, experience and domain profile, these are the five highest-fitting career paths."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: ranked careers */}
        <div className="lg:col-span-5 space-y-4">
          <SectionHeading as="h2" icon={Award} iconClassName="text-warning-fg" right="Sorted by match score">
            Top 5 Ranked Careers
          </SectionHeading>

          <SelectableList label="Recommended careers">
            {careers.slice(0, 5).map((item, idx) => {
              const rank = item.rank_position || idx + 1;
              const matchPct = toPct(item.match_percentage);
              const isSelected = selectedOccupationId === item.occupation_id;

              return (
                <SelectableCard
                  key={item.match_id || item.occupation_id || idx}
                  selected={isSelected}
                  onSelect={() => handleSelectCareer(item.occupation_id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
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

                  <div className="mt-4 pt-3 border-t border-line">
                    <ProgressBar
                      value={matchPct}
                      label="Match compatibility"
                      valueLabel={`${matchPct}% Match`}
                    />
                  </div>
                </SelectableCard>
              );
            })}
          </SelectableList>
        </div>

        {/* Right: selected career detail */}
        <div className="lg:col-span-7 space-y-6">
          {detailLoading ? (
            <PaneSpinner message="Loading career breakdown & skill gaps…" />
          ) : detailError ? (
            <Alert
              tone="error"
              action={
                <Button
                  size="xs"
                  variant="secondary"
                  icon={RefreshCw}
                  onClick={() => loadCareerDetail(selectedOccupationId)}
                >
                  Retry
                </Button>
              }
            >
              {detailError}
            </Alert>
          ) : selectedCareer ? (
            <Card radius="3xl" padding="lg" className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-line">
                <div>
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-success-fg uppercase tracking-wider mb-1">
                    <CheckCircle2 className="w-4 h-4" aria-hidden="true" /> Recommendation #
                    {selectedCareer.rank_position || 1}
                  </div>
                  <h3 className="text-2xl font-extrabold text-fg">{selectedCareer.occupation_name}</h3>
                </div>

                <div className="px-4 py-2 rounded-2xl bg-success-subtle border border-success-fg/40 text-success-fg font-extrabold text-lg text-center shrink-0">
                  {toPct(selectedCareer.match_percentage)}% Match
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricTile
                  icon={DollarSign}
                  iconTone="success"
                  label="Average Salary"
                  value={`${formatCurrency(selectedCareer.average_salary)} / yr`}
                />
                <MetricTile
                  icon={TrendingUp}
                  iconTone="accent"
                  label="Growth Outlook"
                  value={selectedCareer.growth_outlook || 'High demand'}
                  valueTone="text-success-fg"
                />
              </div>

              <div>
                <SectionLabel>Occupation Overview</SectionLabel>
                <p className="text-sm text-fg-secondary leading-relaxed bg-surface-3 p-4 rounded-xl border border-line">
                  {selectedCareer.description}
                </p>
              </div>

              {careerDetail?.summary ? (
                <AiInsightBox>
                  {careerDetail.summary.structured ? (
                    <SummarySections
                      sections={[
                        { label: 'Why this fits', text: careerDetail.summary.structured.why_it_fits },
                        {
                          label: 'Strengths',
                          items: careerDetail.summary.structured.strengths,
                          tone: 'success',
                        },
                        {
                          label: 'Skill gaps',
                          items: careerDetail.summary.structured.skill_gaps,
                          tone: 'warning',
                        },
                        { label: 'Career outlook', text: careerDetail.summary.structured.outlook },
                      ]}
                    />
                  ) : (
                    // Summaries generated before the output was structured are prose.
                    careerDetail.summary.summary_text
                  )}
                </AiInsightBox>
              ) : null}

              {careerDetail?.skill_gaps?.length > 0 ? (
                <div>
                  <SectionLabel icon={BookOpen} iconClassName="text-brand-fg">
                    Skill Gaps to Bridge
                  </SectionLabel>
                  <div className="flex flex-wrap gap-2">
                    {careerDetail.skill_gaps.map((gap, gIdx) => (
                      <Chip key={gap.gap_id || gIdx} tone="warning" dot>
                        {gap.skill_name || `Gap skill #${gIdx + 1}`}
                      </Chip>
                    ))}
                  </div>
                </div>
              ) : null}
            </Card>
          ) : (
            <Card radius="3xl" padding="lg" className="text-center text-fg-muted">
              Select a career from the list to inspect salary metrics and skill gaps.
            </Card>
          )}
        </div>
      </div>
    </PageShell>
  );
};

export default CareerRecommendationsPage;
