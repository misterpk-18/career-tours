import { useCallback, useState } from 'react';
import { apiErrorMessage } from '../lib/apiError';

/**
 * The submit shape shared by the auth forms and the create/upload modals:
 * clear error -> validate -> submitting -> try/catch/finally -> unwrap message.
 *
 * `fallbackError` is per call site on purpose — the four forms have four
 * distinct user-facing messages, and collapsing them into one generic string
 * would be a UX regression disguised as deduplication.
 *
 * `validate` returns a message string when invalid, or anything falsy when valid.
 */
export const useSubmit = (action, { validate, onSuccess, fallbackError = 'Something went wrong.' } = {}) => {
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(
    async (event) => {
      event?.preventDefault?.();
      setError('');

      const invalid = validate?.();
      if (invalid) {
        setError(invalid);
        return undefined;
      }

      setSubmitting(true);
      try {
        const result = await action();
        await onSuccess?.(result);
        return result;
      } catch (err) {
        console.error(fallbackError, err);
        setError(apiErrorMessage(err, fallbackError));
        return undefined;
      } finally {
        setSubmitting(false);
      }
    },
    [action, validate, onSuccess, fallbackError]
  );

  return { submit, submitting, error, setError, clearError: () => setError('') };
};

export default useSubmit;
