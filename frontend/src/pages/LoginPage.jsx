import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, ArrowRight, UserPlus, KeyRound, Lock } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TextField from '../components/ui/TextField';
import PasswordField from '../components/ui/PasswordField';
import { authAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';

/**
 * Two ways in, one screen:
 *  - password: email + password (the original flow), with a clear path when the
 *    account exists but hasn't verified its email yet.
 *  - code: passwordless — email a 6-digit code, then enter it.
 */
export const LoginPage = () => {
  const { login, establishSession } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState('password'); // 'password' | 'code'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [unverified, setUnverified] = useState(false); // show the resend path

  const resetMessages = () => {
    setError('');
    setNotice('');
    setUnverified(false);
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    resetMessages();
    if (!email.trim() || !password.trim()) {
      setError('Please fill in both email and password.');
      return;
    }
    setBusy(true);
    try {
      await login({ email: email.trim(), password });
      navigate('/');
    } catch (err) {
      if (err?.response?.data?.code === 'email_unverified') {
        setUnverified(true);
        setError('Your email isn’t verified yet. Check your inbox, or resend the link below.');
      } else {
        setError(apiErrorMessage(err, 'Invalid email or password. Please try again.'));
      }
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    resetMessages();
    setBusy(true);
    try {
      await authAPI.resendVerification(email.trim());
      setNotice('If that email is registered and unverified, a new link is on its way.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not resend right now. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  const handleRequestCode = async (e) => {
    e.preventDefault();
    resetMessages();
    if (!email.trim()) {
      setError('Enter your email to get a code.');
      return;
    }
    setBusy(true);
    try {
      await authAPI.requestOtp(email.trim());
      setCodeSent(true);
      setNotice('If that email is registered, a 6-digit code is on its way. It expires in 10 minutes.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not send a code. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    resetMessages();
    if (!/^\d{6}$/.test(code.trim())) {
      setError('Enter the 6-digit code from your email.');
      return;
    }
    setBusy(true);
    try {
      const data = await authAPI.verifyOtp(email.trim(), code.trim());
      establishSession(data);
      navigate('/');
    } catch (err) {
      setError(apiErrorMessage(err, 'That code is incorrect or has expired.'));
    } finally {
      setBusy(false);
    }
  };

  const switchTo = (next) => {
    setMode(next);
    resetMessages();
    setCodeSent(false);
    setCode('');
  };

  return (
    <AuthShell
      title="Welcome Back to CareerTours"
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
      {/* Mode toggle */}
      <div className="mb-6 grid grid-cols-2 gap-2 rounded-xl bg-surface-2 p-1">
        <button
          type="button"
          onClick={() => switchTo('password')}
          className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-colors ${
            mode === 'password' ? 'bg-surface text-fg shadow-sm' : 'text-fg-muted hover:text-fg'
          }`}
        >
          <Lock className="h-4 w-4" aria-hidden="true" /> Password
        </button>
        <button
          type="button"
          onClick={() => switchTo('code')}
          className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-colors ${
            mode === 'code' ? 'bg-surface text-fg shadow-sm' : 'text-fg-muted hover:text-fg'
          }`}
        >
          <KeyRound className="h-4 w-4" aria-hidden="true" /> Email code
        </button>
      </div>

      {error ? <Alert tone="error" className="mb-6">{error}</Alert> : null}
      {notice ? <Alert tone="info" className="mb-6">{notice}</Alert> : null}

      {unverified ? (
        <div className="mb-6">
          <Button variant="secondary" size="sm" fullWidth loading={busy} onClick={handleResend}>
            Resend verification email
          </Button>
        </div>
      ) : null}

      {mode === 'password' ? (
        <form onSubmit={handlePasswordLogin} noValidate className="space-y-5">
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
          <PasswordField
            label="Password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            disabled={busy}
          />
          <div className="flex justify-end -mt-2">
            <Link to="/forgot-password" className="text-sm font-medium text-brand-fg hover:underline">
              Forgot password?
            </Link>
          </div>
          <Button
            type="submit"
            size="lg"
            fullWidth
            loading={busy}
            loadingText="Signing in…"
            iconRight={ArrowRight}
          >
            Sign in
          </Button>
        </form>
      ) : !codeSent ? (
        <form onSubmit={handleRequestCode} noValidate className="space-y-5">
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
            loadingText="Sending code…"
            iconRight={ArrowRight}
          >
            Email me a code
          </Button>
        </form>
      ) : (
        <form onSubmit={handleVerifyCode} noValidate className="space-y-5">
          <TextField
            label="6-digit code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="123456"
            icon={KeyRound}
            disabled={busy}
          />
          <Button
            type="submit"
            size="lg"
            fullWidth
            loading={busy}
            loadingText="Verifying…"
            iconRight={ArrowRight}
          >
            Sign in
          </Button>
          <button
            type="button"
            onClick={handleRequestCode}
            disabled={busy}
            className="w-full text-sm font-medium text-fg-muted hover:text-fg"
          >
            Resend code
          </button>
        </form>
      )}
    </AuthShell>
  );
};

export default LoginPage;
