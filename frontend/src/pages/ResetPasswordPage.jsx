import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, LogIn, CheckCircle2 } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import PasswordField from '../components/ui/PasswordField';
import { authAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';

/**
 * The landing page for the reset-password link. Reads ?token, takes a new
 * password, and posts both. The token is single-use and validated server-side.
 */
export const ResetPasswordPage = () => {
  const [params] = useSearchParams();
  const token = params.get('token');

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!token) {
      setError('This reset link is missing its token.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('The two passwords don’t match.');
      return;
    }
    setBusy(true);
    try {
      await authAPI.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'This reset link is invalid or has expired.'));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <AuthShell title="Password updated" description="You can sign in with your new password.">
        <div className="space-y-5 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-success-subtle">
            <CheckCircle2 className="h-7 w-7 text-success-fg" aria-hidden="true" />
          </div>
          <Button as={Link} to="/login" size="lg" fullWidth icon={LogIn}>
            Go to sign in
          </Button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Set a new password"
      description="Choose a password you haven’t used here before."
      footer={
        <Button as={Link} to="/login" variant="secondary" size="md" icon={LogIn}>
          Back to sign in
        </Button>
      }
    >
      {error ? <Alert tone="error" className="mb-6">{error}</Alert> : null}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <PasswordField
          label="New password"
          name="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
          hint="Use at least 8 characters."
          disabled={busy}
        />
        <PasswordField
          label="Confirm new password"
          name="confirm"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Re-enter your new password"
          disabled={busy}
        />
        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={busy}
          loadingText="Updating…"
          iconRight={ArrowRight}
        >
          Update password
        </Button>
      </form>
    </AuthShell>
  );
};

export default ResetPasswordPage;
