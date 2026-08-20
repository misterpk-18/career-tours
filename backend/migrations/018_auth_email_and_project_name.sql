-- Email verification, passwordless OTP login, password reset — plus the
-- project-name uniqueness rule.
--
-- Three independent pieces bundled because they landed together:
--
--   1. students.email_verified — new signups must confirm their address before
--      password login; the accounts that already exist are grandfathered in.
--   2. auth_email_challenges — one table for every emailed secret: the
--      verify-email link, the reset-password link, and the login OTP code. Each
--      is stored only as a SHA-256 hash, is single-use (consumed_at), expires,
--      and (for the OTP) counts attempts.
--   3. a per-student unique project name among ACTIVE projects.
--
-- No schema_migrations table exists here, so every statement is re-runnable.

-- 1. email_verified, grandfathering every account that exists right now ---------
--
-- Added nullable first so the backfill can tell "already existed" (NULL) from
-- "created since" (non-null, because new inserts default to false). That makes
-- the grandfather step safe to re-run: on a second run every row is already
-- non-null, so the UPDATE touches nothing and cannot re-verify a genuinely
-- unverified new account.
ALTER TABLE public.students
    ADD COLUMN IF NOT EXISTS email_verified boolean;

UPDATE public.students
    SET email_verified = true
    WHERE email_verified IS NULL;

ALTER TABLE public.students
    ALTER COLUMN email_verified SET DEFAULT false;

ALTER TABLE public.students
    ALTER COLUMN email_verified SET NOT NULL;


-- 2. auth_email_challenges -----------------------------------------------------
CREATE TABLE IF NOT EXISTS public.auth_email_challenges (
    challenge_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    purpose character varying(20) NOT NULL,

    -- SHA-256 of the raw token (link) or code (OTP). The raw value is emailed
    -- and never stored, so a database read cannot reconstruct a live link.
    secret_hash text NOT NULL,

    expires_at timestamp without time zone NOT NULL,
    consumed_at timestamp without time zone,
    -- Only meaningful for login_otp: caps guesses at the 6-digit code.
    attempts integer NOT NULL DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT auth_email_challenges_pkey PRIMARY KEY (challenge_id),

    CONSTRAINT auth_email_challenges_purpose_check
        CHECK (purpose IN ('verify_email', 'reset_password', 'login_otp'))
);

CREATE INDEX IF NOT EXISTS auth_email_challenges_lookup
    ON public.auth_email_challenges (student_id, purpose, created_at DESC);

-- Link tokens are looked up by their hash directly (the link carries no id).
CREATE INDEX IF NOT EXISTS auth_email_challenges_secret
    ON public.auth_email_challenges (secret_hash);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'auth_email_challenges_student_id_fkey') THEN
        ALTER TABLE public.auth_email_challenges
            ADD CONSTRAINT auth_email_challenges_student_id_fkey
            FOREIGN KEY (student_id) REFERENCES public.students(student_id)
            ON DELETE CASCADE;
    END IF;
END
$$;


-- 3. one project name per student, among active projects ----------------------
--
-- Exact match (case-sensitive), and scoped to WHERE deleted_at IS NULL so a
-- deleted project's name is free to reuse. A partial unique index makes this a
-- database guarantee, not just an application check; the API also checks first
-- to return a friendly 409 rather than a raw integrity error.
CREATE UNIQUE INDEX IF NOT EXISTS projects_unique_active_name_per_student
    ON public.projects (student_id, project_name)
    WHERE deleted_at IS NULL;
