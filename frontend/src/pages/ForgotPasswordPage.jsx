import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowRight, ArrowLeft, MailCheck } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TextField from '../components/ui/TextField';
import { authAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';

/**
 * Enter an email to be sent a one-time reset link. The response is deliberately
 * the same whether or not the address is registered — the server does not
 * confirm membership, and neither does this screen.
 */
export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) {
      setError('Enter your email address.');
      return;
    }
    setBusy(true);
    try {
      await authAPI.forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'Something went wrong. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Reset your password"
      description="We’ll email you a link to set a new one."
      footer={
        <Button as={Link} to="/login" variant="secondary" size="md" icon={ArrowLeft}>
          Back to sign in
        </Button>
      }
    >
      {error ? <Alert tone="error" className="mb-6">{error}</Alert> : null}

      {sent ? (
        <div className="space-y-5 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-brand-subtle">
            <MailCheck className="h-7 w-7 text-brand-subtle-fg" aria-hidden="true" />
          </div>
          <p className="text-sm text-fg-secondary">
            If <span className="font-semibold text-fg">{email}</span> is registered, a reset link is
            on its way. It expires in one hour.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
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
            disabled={busy}
          />
          <Button
            type="submit"
            size="lg"
            fullWidth
            loading={busy}
            loadingText="Sending…"
            iconRight={ArrowRight}
          >
            Email me a reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
};

export default ForgotPasswordPage;
