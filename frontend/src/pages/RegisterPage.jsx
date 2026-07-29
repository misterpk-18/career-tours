import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Phone, GraduationCap, Target, ArrowRight, LogIn } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TextField from '../components/ui/TextField';
import PasswordField from '../components/ui/PasswordField';
import { useSubmit } from '../hooks/useSubmit';

const INITIAL_FORM = {
  full_name: '',
  email: '',
  password: '',
  phone: '',
  college_name: '',
  degree_name: '',
  branch_name: '',
  target_role: '',
};

export const RegisterPage = () => {
  const [formData, setFormData] = useState(INITIAL_FORM);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const { submit, submitting, error } = useSubmit(() => register(formData), {
    validate: () => {
      if (!formData.full_name.trim()) return 'Please enter your full name.';
      if (!formData.email.trim()) return 'Please enter your email address.';
      if (!formData.password.trim()) return 'Please choose a password.';
      // Per-field messages rather than one merged string, so the user knows
      // which field to fix.
      if (formData.password.length < 8) return 'Password must be at least 8 characters.';
      return null;
    },
    onSuccess: () => navigate('/'),
    fallbackError: 'Failed to create student account.',
  });

  return (
    <AuthShell
      width="xl"
      title={
        <>
          Join CareerTours
        </>
      }
      description="Create your student account to analyse resumes and discover matching career paths."
      footer={
        <>
          <p className="text-sm text-fg-muted mb-3">Already have an account?</p>
          <Button as={Link} to="/login" variant="secondary" size="md" icon={LogIn}>
            Sign in instead
          </Button>
        </>
      }
    >
      {error ? (
        <Alert tone="error" className="mb-6">
          {error}
        </Alert>
      ) : null}

      <form onSubmit={submit} noValidate className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextField
            label="Full name"
            name="full_name"
            autoComplete="name"
            required
            value={formData.full_name}
            onChange={handleChange}
            placeholder="Sarah Chen"
            icon={User}
            disabled={submitting}
          />
          <TextField
            label="Email address"
            type="email"
            name="email"
            autoComplete="email"
            inputMode="email"
            required
            value={formData.email}
            onChange={handleChange}
            placeholder="student@college.edu"
            icon={Mail}
            disabled={submitting}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <PasswordField
            label="Password"
            name="password"
            autoComplete="new-password"
            required
            value={formData.password}
            onChange={handleChange}
            placeholder="At least 8 characters"
            hint="Use at least 8 characters."
            disabled={submitting}
          />
          <TextField
            label="Phone"
            type="tel"
            name="phone"
            autoComplete="tel"
            inputMode="tel"
            value={formData.phone}
            onChange={handleChange}
            placeholder="+91 90000 00000"
            icon={Phone}
            disabled={submitting}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextField
            label="College"
            name="college_name"
            autoComplete="organization"
            value={formData.college_name}
            onChange={handleChange}
            placeholder="NIT Silchar"
            icon={GraduationCap}
            disabled={submitting}
          />
          <TextField
            label="Degree"
            name="degree_name"
            value={formData.degree_name}
            onChange={handleChange}
            placeholder="B.Tech"
            icon={GraduationCap}
            disabled={submitting}
          />
        </div>

        <TextField
          label="Target role"
          name="target_role"
          value={formData.target_role}
          onChange={handleChange}
          placeholder="Backend Developer"
          icon={Target}
          // Hint rather than a long placeholder: placeholders truncate on narrow
          // screens and vanish as soon as the user types.
          hint="For example: Software Engineer, Data Scientist, Full Stack Developer."
          disabled={submitting}
        />

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          loadingText="Creating account…"
          iconRight={ArrowRight}
          className="mt-2"
        >
          Create account
        </Button>
      </form>
    </AuthShell>
  );
};

export default RegisterPage;
