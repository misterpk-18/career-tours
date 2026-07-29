import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, ArrowRight, UserPlus } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TextField from '../components/ui/TextField';
import PasswordField from '../components/ui/PasswordField';
import { useSubmit } from '../hooks/useSubmit';

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  const { submit, submitting, error } = useSubmit(
    () => login({ email: email.trim(), password }),
    {
      validate: () =>
        (!email.trim() || !password.trim()) && 'Please fill in both email and password.',
      onSuccess: () => navigate('/'),
      fallbackError: 'Invalid email or password. Please try again.',
    }
  );

  return (
    <AuthShell
      title={
        <>
          Welcome Back to CareerTours
        </>
      }
      description="Sign in to manage your projects, analyse skills, and discover top career paths."
      footer={
        <>
          <p className="text-sm text-fg-muted mb-3">Don&apos;t have a student account yet?</p>
          <Button as={Link} to="/register" variant="secondary" size="md" icon={UserPlus}>
            Create an account
          </Button>
        </>
      }
    >
      {error ? (
        <Alert tone="error" className="mb-6">
          {error}
        </Alert>
      ) : null}

      {/* noValidate: the custom validate() message is the one users should see.
          Without it the browser's own bubble fires first and setError never runs. */}
      <form onSubmit={submit} noValidate className="space-y-5">
        <TextField
          label="Email address"
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="student@college.edu"
          icon={Mail}
          disabled={submitting}
        />

        <PasswordField
          label="Password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          disabled={submitting}
        />

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          loadingText="Signing in…"
          iconRight={ArrowRight}
          className="mt-2"
        >
          Sign in
        </Button>
      </form>
    </AuthShell>
  );
};

export default LoginPage;
