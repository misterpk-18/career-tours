import React, { useEffect, useMemo, useState } from 'react';
import { Compass, Search, TrendingUp } from 'lucide-react';
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

export const CareersPage = () => {
  const [careers, setCareers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetchCareers();
  }, []);

  const fetchCareers = async () => {
    setLoading(true);
    setError('');
    try {
      setCareers(await catalogueAPI.listCareers());
    } catch (err) {
      console.error('Failed to load the career catalogue:', err);
      setError(apiErrorMessage(err, 'Unable to load careers. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Matches on the career's name, description and its listed skills.
   *
   * The skills the API sends are the heaviest few essential ones, not the whole
   * set, so a search for a niche skill can miss a career that does require it.
   * That is a deliberate trade against a several-hundred-KB response; the full
   * list belongs to a career detail view, which does not exist yet.
   */
  const results = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);

    if (!terms.length) return careers;

    return careers.filter((career) => {
      const haystack = [career.occupation_name, career.description, ...(career.skills || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return terms.every((term) => haystack.includes(term));
    });
  }, [careers, query]);

  return (
    <PageShell>
      <HeroBanner
        title="Career directory"
        description="Every career in the catalogue, with the skills each one is built on. Upload a resume to a project to see which of these you already match."
      >
        <div className="mt-8 border-t border-line pt-6">
          <SearchField
            value={query}
            onChange={setQuery}
            label="Search careers"
            placeholder="Search by role or skill — try “data” or “kubernetes”"
            count={results.length}
            total={careers.length}
            className="max-w-2xl"
          />
        </div>
      </HeroBanner>

      {error ? (
        <Alert
          tone="error"
          action={
            <Button size="xs" variant="secondary" onClick={fetchCareers}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}

      {loading ? (
        <PageSpinner message="Loading the career directory…" className="py-16" />
      ) : results.length === 0 ? (
        <EmptyState
          icon={query ? Search : Compass}
          title={query ? `No careers match “${query}”` : 'No careers in the catalogue'}
          titleAs="h3"
          description={
            query
              ? 'Try a broader term — a role family such as “engineer”, or a skill name.'
              : 'The catalogue is empty. Load the careers corpus and this page will fill up.'
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
        // items-start, so a card is only as tall as its content. 87 of the 267
        // careers have no description at all, and stretching those to match a
        // neighbour's opened a blank band above their skills.
        <div className="grid grid-cols-1 items-start md:grid-cols-2 xl:grid-cols-3 gap-6">
          {results.map((career) => (
            <Card key={career.occupation_id} as="article" className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-bold leading-snug text-fg">
                  {career.occupation_name}
                </h3>
                {career.description ? (
                  <p className="mt-1.5 line-clamp-3 text-sm text-fg-muted">{career.description}</p>
                ) : null}
              </div>

              {/* Essential and optional are counted apart on purpose: 5,150 of
                  the 8,114 catalogue pairs are optional, so one combined number
                  would describe a job by things nobody has to know. */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-fg-muted">
                <span>
                  <span className="font-semibold text-fg-secondary">
                    {career.essential_skill_count}
                  </span>{' '}
                  essential
                </span>
                {career.optional_skill_count ? (
                  <span>
                    <span className="font-semibold text-fg-secondary">
                      {career.optional_skill_count}
                    </span>{' '}
                    optional
                  </span>
                ) : null}
                {career.growth_outlook ? (
                  <span className="flex items-center gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                    {career.growth_outlook} growth
                  </span>
                ) : null}
              </div>

              {career.skills?.length ? (
                <div className="border-t border-line pt-4">
                  <p className="mb-2 text-2xs font-bold uppercase tracking-widest text-fg-muted">
                    Core skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {career.skills.map((skill) => (
                      <Badge key={skill}>{skill}</Badge>
                    ))}
                  </div>
                </div>
              ) : null}
            </Card>
          ))}
        </div>
      )}
    </PageShell>
  );
};

export default CareersPage;
