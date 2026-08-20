import React, { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, XCircle, LogIn } from 'lucide-react';
import AuthShell from '../components/ui/AuthShell';
import Button from '../components/ui/Button';
import PageSpinner from '../components/ui/PageSpinner';
import { authAPI } from '../services/api';
import { apiErrorMessage } from '../lib/apiError';

/**
 * The landing page for the verify-email link. Consumes ?token once on mount and
 * shows the result. Guarded against React 18 StrictMode's double-invoke so the
 * single-use token isn't spent twice (the second call would look like failure).
 */
export const VerifyEmailPage = () => {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [status, setStatus] = useState('working'); // working | ok | error
  const [message, setMessage] = useState('');
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    if (!token) {
      setStatus('error');
      setMessage('This link is missing its token.');
      return;
    }
    authAPI
      .verifyEmail(token)
      .then((data) => {
        setStatus('ok');
        setMessage(data?.message || 'Email verified. You can now sign in.');
      })
      .catch((err) => {
        setStatus('error');
        setMessage(apiErrorMessage(err, 'This verification link is invalid or has expired.'));
      });
  }, [token]);

  if (status === 'working') {
    return <PageSpinner message="Verifying your email…" className="py-24" />;
  }

  const ok = status === 'ok';
  return (
    <AuthShell
      title={ok ? 'Email verified' : 'Verification failed'}
      description={ok ? 'Your account is ready.' : 'We couldn’t verify this link.'}
    >
      <div className="space-y-5 text-center">
        <div
          className={`mx-auto grid h-14 w-14 place-items-center rounded-full ${
            ok ? 'bg-success-subtle' : 'bg-danger-subtle'
          }`}
        >
          {ok ? (
            <CheckCircle2 className="h-7 w-7 text-success-fg" aria-hidden="true" />
          ) : (
            <XCircle className="h-7 w-7 text-danger-fg" aria-hidden="true" />
          )}
        </div>
        <p className="text-sm text-fg-secondary">{message}</p>
        <Button as={Link} to="/login" size="lg" fullWidth icon={LogIn}>
          Go to sign in
        </Button>
      </div>
    </AuthShell>
  );
};

export default VerifyEmailPage;
