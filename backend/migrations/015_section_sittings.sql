-- A sitting: one run at a section's questions, from Start to Submit.
--
-- 014 recorded individual answers but had no notion of the run they belong to,
-- so it could not express any of what the flow actually needs -- start, pause,
-- resume, a score that locks on first submit, or practice afterwards. This adds
-- that run as a row, and re-points the answers at it.
--
-- MCQs only, deliberately. The scenarios and practical tasks stay in
-- course_section_questions untouched, but they are worth 70 of the 100 marks and
-- cannot be scored without a human, and this system has no assessor role. So a
-- sitting is scored out of the MCQ total (30) and marks_available records that
-- explicitly rather than assuming it -- when written questions do enter the UI,
-- old sittings must not silently start claiming to be out of 100.
--
-- The clock is server-side and stored as REMAINING, not as a deadline. Pause
-- stops it, which a deadline column cannot express: on pause the elapsed time
-- since resumed_at is subtracted and resumed_at is cleared; on resume it is set
-- again. The client is never trusted with the number, because the client is
-- where a student would change it.
--
-- Question and option order are NOT stored. Both are a deterministic
-- SHA-256-seeded permutation of sitting_id, so any process can recompute the
-- exact layout a student saw -- resume, review, and grading all derive it rather
-- than sharing state. The correct option is dealt from a balanced pool by the
-- same algorithm the corpus generator uses, so a shuffled sitting still gets
-- exactly 3/3/2/2 across its ten questions instead of a random spread.
--
-- No schema_migrations table exists here, so every statement is re-runnable.
CREATE TABLE IF NOT EXISTS public.project_section_sittings (
    sitting_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,

    -- 'graded' is the one that counts and happens once. 'practice' never
    -- touches the score and may be repeated.
    mode character varying(8) NOT NULL DEFAULT 'graded',
    status character varying(12) NOT NULL DEFAULT 'in_progress',

    time_limit_seconds integer NOT NULL,
    seconds_remaining integer NOT NULL,
    -- When the clock last started running. NULL exactly when it is not running.
    resumed_at timestamp without time zone,

    marks_awarded integer,
    marks_available integer NOT NULL,

    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    submitted_at timestamp without time zone,

    CONSTRAINT project_section_sittings_pkey PRIMARY KEY (sitting_id),

    CONSTRAINT project_section_sittings_mode_check
        CHECK (mode IN ('graded', 'practice')),

    CONSTRAINT project_section_sittings_status_check
        CHECK (status IN ('in_progress', 'paused', 'submitted', 'abandoned')),

    CONSTRAINT project_section_sittings_clock_check
        CHECK (time_limit_seconds > 0 AND seconds_remaining >= 0
               AND seconds_remaining <= time_limit_seconds),

    -- The clock runs if and only if the sitting is in progress. Without this a
    -- paused sitting could keep a resumed_at and quietly bleed time away while
    -- the student is not even looking at it.
    CONSTRAINT project_section_sittings_running_check
        CHECK ((status = 'in_progress') = (resumed_at IS NOT NULL)),

    -- Submitted means scored and stamped; anything else means neither. This is
    -- what makes "the first submit decides the score" enforceable rather than
    -- merely intended.
    CONSTRAINT project_section_sittings_submitted_check
        CHECK (
            (status = 'submitted'
             AND submitted_at IS NOT NULL AND marks_awarded IS NOT NULL)
            OR (status <> 'submitted'
                AND submitted_at IS NULL AND marks_awarded IS NULL)
        ),

    CONSTRAINT project_section_sittings_marks_check
        CHECK (marks_awarded IS NULL
               OR (marks_awarded >= 0 AND marks_awarded <= marks_available))
);

-- One graded sitting per section, ever. This is the constraint that makes the
-- score final: a second graded run cannot be inserted, so it cannot overwrite
-- the first. "Start new" before submitting deletes the unsubmitted row rather
-- than adding a second, which is why 'abandoned' is not excluded here -- an
-- abandoned graded sitting would still occupy the slot, so the API deletes.
CREATE UNIQUE INDEX IF NOT EXISTS project_section_sittings_one_graded
    ON public.project_section_sittings (project_id, section_code)
    WHERE mode = 'graded';

-- At most one practice run open at a time, so "resume practice" is unambiguous.
-- Submitted practice runs accumulate freely as history.
CREATE UNIQUE INDEX IF NOT EXISTS project_section_sittings_one_open_practice
    ON public.project_section_sittings (project_id, section_code)
    WHERE mode = 'practice' AND status IN ('in_progress', 'paused');

CREATE INDEX IF NOT EXISTS project_section_sittings_project_idx
    ON public.project_section_sittings (project_id, section_code, started_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'project_section_sittings_project_id_fkey') THEN
        ALTER TABLE public.project_section_sittings
            ADD CONSTRAINT project_section_sittings_project_id_fkey
            FOREIGN KEY (project_id) REFERENCES public.projects(project_id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'project_section_sittings_section_code_fkey') THEN
        ALTER TABLE public.project_section_sittings
            ADD CONSTRAINT project_section_sittings_section_code_fkey
            FOREIGN KEY (section_code) REFERENCES public.course_sections(section_code)
            ON DELETE CASCADE;
    END IF;
END
$$;


-- Re-point the answers at their sitting.
--
-- 014's attempt_number tried to express re-runs on the answer itself, which is
-- the wrong place: a re-run is a property of the sitting, and every answer in
-- one belongs to the same run by construction. The sitting owns it now, so the
-- column goes and the natural key becomes (sitting_id, question_id) -- revising
-- an answer inside a sitting is an upsert, and a new sitting is new rows.
--
-- Safe to restructure rather than migrate data: the table is empty. The guard
-- below still checks, because "it was empty when I wrote this" is not something
-- a migration can assume about when it runs.
ALTER TABLE public.project_question_attempts
    ADD COLUMN IF NOT EXISTS sitting_id uuid;

-- What the student actually clicked, in the shuffled layout they were shown.
-- selected_option stays canonical -- the letter as stored in the corpus -- so
-- is_correct means what it says and review can show both.
ALTER TABLE public.project_question_attempts
    ADD COLUMN IF NOT EXISTS presented_option character(1);

DO $$
DECLARE
    orphans bigint;
BEGIN
    SELECT count(*) INTO orphans
      FROM public.project_question_attempts WHERE sitting_id IS NULL;

    IF orphans > 0 THEN
        RAISE EXCEPTION
            'project_question_attempts holds % row(s) with no sitting; '
            'assign them before re-running this migration', orphans;
    END IF;

    ALTER TABLE public.project_question_attempts
        ALTER COLUMN sitting_id SET NOT NULL;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'project_question_attempts_sitting_id_fkey') THEN
        ALTER TABLE public.project_question_attempts
            ADD CONSTRAINT project_question_attempts_sitting_id_fkey
            FOREIGN KEY (sitting_id)
            REFERENCES public.project_section_sittings(sitting_id)
            ON DELETE CASCADE;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_constraint
               WHERE conname = 'project_question_attempts_attempt_number_check') THEN
        ALTER TABLE public.project_question_attempts
            DROP CONSTRAINT project_question_attempts_attempt_number_check;
    END IF;
END
$$;

DROP INDEX IF EXISTS public.project_question_attempts_natural_key;
DROP INDEX IF EXISTS public.project_question_attempts_section_idx;

ALTER TABLE public.project_question_attempts
    DROP COLUMN IF EXISTS attempt_number;

CREATE UNIQUE INDEX IF NOT EXISTS project_question_attempts_natural_key
    ON public.project_question_attempts (sitting_id, question_id);

CREATE INDEX IF NOT EXISTS project_question_attempts_section_idx
    ON public.project_question_attempts (project_id, section_code);
