/**
 * Unwrap an axios error into a user-facing message.
 *
 * The Flask API returns `{"error": "..."}` for handled failures and
 * `{"error": ..., "detail": "..."}` for unexpected ones. This chain was
 * duplicated across eight call sites, and LoginPage was missing the `detail`
 * branch — so a 500 there produced the generic fallback instead of the reason.
 */
export const apiErrorMessage = (err, fallback = 'Something went wrong. Please try again.') =>
  err?.response?.data?.error || err?.response?.data?.detail || fallback;

export default apiErrorMessage;
