import React, { useEffect, useState } from 'react';
import { Award, BarChart3, GraduationCap, Save, Target, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { studentsAPI } from '../services/api';
import PageShell from '../components/ui/PageShell';
import PageSpinner from '../components/ui/PageSpinner';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TextField from '../components/ui/TextField';
import SelectField from '../components/ui/SelectField';
import SectionHeading from '../components/ui/SectionHeading';
import XpBar from '../components/motion/XpBar';
import BadgeShelf from '../components/motion/BadgeShelf';
import Leaderboard from '../components/motion/Leaderboard';
import { achievementsAPI } from '../services/api';
import useSubmit from '../hooks/useSubmit';

// Values are the ones the CHECK constraints on `students` accept — not labels.
// Anything else is rejected by Postgres, so these lists must track the database
// (see ENUM_FIELDS in api/students/routes.py, which mirrors the same sets).
const WORK_MODES = [
  { value: 'office', label: 'On-site' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'remote', label: 'Remote' },
];

// The column records which kind of internship the student will take, not
// whether they are looking — 'free' means unpaid is acceptable too. Selecting
// nothing stores NULL, which is how "not looking right now" is represented.
const INTERNSHIP_OPTIONS = [
  { value: 'paid', label: 'Paid internships only' },
  { value: 'free', label: 'Unpaid internships too' },
  { value: 'both', label: 'Either paid or unpaid' },
];

// Exactly the fields PUT /api/students/<id> allows. Kept in one list so the form
// state, the reset and the payload cannot drift apart from each other.
const FIELDS = [
  'full_name',
  'phone',
  'target_role',
  'college_name',
  'degree_name',
  'branch_name',
  'current_year_semester',
  'graduation_year',
  'career_interest',
  'preferred_job_location',
  'learning_hours_per_week',
  'work_mode_preference',
  'internship_preference',
];

/** Server nulls become '' so every input stays controlled for its whole life. */
const toForm = (student) =>
  Object.fromEntries(FIELDS.map((field) => [field, student?.[field] ?? '']));

const Section = ({ icon, title, children }) => (
  <section className="space-y-5">
    <SectionHeading as="h2" size="sm" icon={icon} iconClassName="text-brand-fg">
      {title}
    </SectionHeading>
    <div className="grid grid-cols-1 gap-x-6 gap-y-5 md:grid-cols-2">{children}</div>
  </section>
);

export const ProfilePage = () => {
  // Achievements load separately from the profile form and never block it: a
  // failed XP fetch must not stop someone editing their phone number.
  const [achievements, setAchievements] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      achievementsAPI.mine().catch(() => null),
      achievementsAPI.leaderboard(8).catch(() => null),
    ]).then(([mine, board]) => {
      if (cancelled) return;
      setAchievements(mine);
      setLeaderboard(board);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const { student, updateStudent } = useAuth();

  const [form, setForm] = useState(() => toForm(student));
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saved, setSaved] = useState(false);

  /**
   * The session copy is seeded from login and can be months stale, so the
   * authoritative profile is re-read on mount. The cached copy still populates
   * the form first, which is why the fields are not empty while this runs.
   */
  useEffect(() => {
    if (!student?.student_id) return undefined;

    let cancelled = false;

    const fetchProfile = async () => {
      setLoadError('');
      try {
        const fresh = await studentsAPI.getById(student.student_id);
        if (!cancelled) {
          setForm(toForm(fresh));
          updateStudent(fresh);
        }
      } catch (err) {
        console.error('Failed to load the profile:', err);
        if (!cancelled) {
          // Non-fatal: the form is already populated from the session copy, so
          // this is a staleness warning rather than a dead page.
          setLoadError('Could not refresh your profile from the server. Showing your last known details.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchProfile();

    return () => {
      cancelled = true;
    };
    // Keyed on the id: `student` is a fresh object on every auth refresh, and
    // this effect calls updateStudent, so depending on it would re-run forever.
  }, [student?.student_id]);

  const setField = (field) => (event) => {
    setSaved(false);
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const { submit, submitting, error } = useSubmit(
    () => studentsAPI.update(student.student_id, form),
    {
      validate: () => (form.full_name.trim() ? '' : 'Full name is required.'),
      onSuccess: (updated) => {
        updateStudent(updated);
        setForm(toForm(updated));
        setSaved(true);
      },
      fallbackError: 'Could not save your profile. Please try again.',
    }
  );

  if (loading) {
    return <PageSpinner message="Loading your profile…" className="py-24" />;
  }

  return (
    <PageShell>
      {/* Achievements sit above the form because they are the reason a student
          opens this page more than once. The form is why they opened it the
          first time. */}
      {achievements ? (
        <div className="mb-6 space-y-4">
          <XpBar
            xp={achievements.xp}
            level={achievements.level}
            xpIntoLevel={achievements.xp_into_level}
            xpForLevel={achievements.xp_for_level}
            streak={achievements.streak}
          />

          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card padding="lg" className="space-y-4">
              <SectionHeading as="h2" size="sm" icon={Award} iconClassName="text-accent-fg">
                Badges
              </SectionHeading>
              <BadgeShelf badges={achievements.badges} />
            </Card>

            <Card padding="lg" className="space-y-4">
              <SectionHeading as="h2" size="sm" icon={BarChart3} iconClassName="text-accent-fg">
                Where you rank
              </SectionHeading>
              {leaderboard?.entries?.length ? (
                <>
                  <Leaderboard entries={leaderboard.entries} />
                  <p className="text-2xs text-fg-muted">
                    Ranked by XP. Other students are never named.
                  </p>
                </>
              ) : (
                <p className="text-sm text-fg-muted">
                  Submit a section to appear on the board.
                </p>
              )}
            </Card>
          </div>
        </div>
      ) : null}

      <form onSubmit={submit} className="space-y-6">
        <Card padding="lg" className="space-y-8">
          <Section icon={User} title="Basic identity & contact">
            <TextField
              label="Full name"
              required
              value={form.full_name}
              onChange={setField('full_name')}
              placeholder="Your name as it should appear"
            />

            <TextField
              label="Email address"
              type="email"
              value={student?.email || ''}
              readOnly
              disabled
              hint="Your email is your sign-in identity and cannot be changed here."
              inputClassName="cursor-not-allowed opacity-70"
            />

            <TextField
              label="Phone number"
              type="tel"
              value={form.phone}
              onChange={setField('phone')}
              placeholder="e.g. +91 98765 43210"
            />

            <TextField
              label="Target career role"
              value={form.target_role}
              onChange={setField('target_role')}
              placeholder="e.g. Backend Engineer"
            />
          </Section>

          <Section icon={GraduationCap} title="Academic profile">
            <TextField
              label="College / university"
              value={form.college_name}
              onChange={setField('college_name')}
              placeholder="e.g. IIT Hyderabad"
              className="md:col-span-2"
            />

            <TextField
              label="Degree"
              value={form.degree_name}
              onChange={setField('degree_name')}
              placeholder="e.g. B.Tech, M.Tech, BCA"
            />

            <TextField
              label="Branch / specialisation"
              value={form.branch_name}
              onChange={setField('branch_name')}
              placeholder="e.g. Computer Science"
            />

            <TextField
              label="Current year / semester"
              value={form.current_year_semester}
              onChange={setField('current_year_semester')}
              placeholder="e.g. IV Year / I Semester"
            />

            <TextField
              label="Graduation year"
              type="number"
              inputMode="numeric"
              min="1950"
              max="2100"
              value={form.graduation_year}
              onChange={setField('graduation_year')}
              placeholder="e.g. 2027"
            />
          </Section>

          <Section icon={Target} title="Career preferences">
            <TextField
              label="Career interests / tech stack"
              value={form.career_interest}
              onChange={setField('career_interest')}
              placeholder="e.g. AWS, Cloud Engineering, React, LLMs"
              className="md:col-span-2"
            />

            <TextField
              label="Preferred job location"
              value={form.preferred_job_location}
              onChange={setField('preferred_job_location')}
              placeholder="e.g. Hyderabad, Bengaluru"
            />

            <TextField
              label="Learning commitment"
              type="number"
              inputMode="numeric"
              min="0"
              max="168"
              value={form.learning_hours_per_week}
              onChange={setField('learning_hours_per_week')}
              placeholder="e.g. 15"
              hint="Hours per week you can give to study."
            />

            <SelectField
              label="Work mode preference"
              options={WORK_MODES}
              placeholder="No preference"
              value={form.work_mode_preference}
              onChange={setField('work_mode_preference')}
            />

            <SelectField
              label="Internship preference"
              options={INTERNSHIP_OPTIONS}
              placeholder="Not looking right now"
              hint="Leave unset if you are not looking for an internship."
              value={form.internship_preference}
              onChange={setField('internship_preference')}
            />
          </Section>
        </Card>

        {loadError ? <Alert tone="warning">{loadError}</Alert> : null}
        {error ? <Alert tone="error">{error}</Alert> : null}
        {saved && !error ? <Alert tone="success">Your profile has been saved.</Alert> : null}

        <div className="flex flex-wrap items-center justify-end gap-3">
          {/* Reset, not navigate away: this page is reached from the rail, so
              there is no "previous screen" to cancel back to. */}
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setForm(toForm(student));
              setSaved(false);
            }}
            disabled={submitting}
          >
            Discard changes
          </Button>

          <Button type="submit" icon={Save} loading={submitting} loadingText="Saving…">
            Save profile
          </Button>
        </div>
      </form>
    </PageShell>
  );
};

export default ProfilePage;
