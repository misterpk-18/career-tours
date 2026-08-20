-- What a student actually answered, per project.
--
-- 013 loaded the 2,560 questions; this is the other side of them. One row per
-- attempt at one question, holding the response as given and the marks it
-- earned. Per-section progress is deliberately NOT stored — it is
-- sum(marks_awarded) over a section, and a derived column that can disagree
-- with the rows it is derived from is a bug waiting for the first partial
-- submission. If aggregating ever becomes too slow for the syllabus view, the
-- fix is a view or a materialised one, not a column somebody has to remember
-- to update.
--
-- Scoped to project_id, not student_id. A project is the student's workspace —
-- it owns their resume, their extracted skills and their recommendations — and
-- a student may hold several. Storing student_id here too would let the two
-- disagree about who an attempt belongs to; the owner is reachable through
-- projects.student_id, and api/guards.owned_project is what enforces access.
--
-- attempt_number rather than one row per question: a learner who re-sits a
-- section has a history worth keeping, and overwriting the first attempt would
-- destroy the only evidence of what they improved on. The natural key is
-- (project_id, question_id, attempt_number), so a resubmission of the SAME
-- attempt is an upsert while a genuine re-sit is a new row.
--
-- Both response columns are nullable and neither is the "real" one: an mcq
-- carries selected_option, a scenario or practical carries response_text. The
-- CHECK below only requires that at least one is present, because this table
-- cannot see question_type — that lives in course_section_questions, and
-- Postgres has no cross-row CHECK. The repository resolves the question first
-- and rejects the mismatch there.
--
-- No schema_migrations table exists here, so every statement is re-runnable.
CREATE TABLE IF NOT EXISTS public.project_question_attempts (
    attempt_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    question_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,
    attempt_number integer NOT NULL DEFAULT 1,

    selected_option character(1),
    response_text text,

    is_correct boolean,
    marks_awarded integer,
    max_marks integer NOT NULL,

    -- 'auto' for mcqs, which grade themselves; 'assessor' for the scenarios and
    -- practical tasks, which do not. 'pending' is the honest state for a
    -- submitted scenario nobody has marked yet, and is why marks_awarded is
    -- nullable — zero would read as "marked, scored nothing".
    graded_by character varying(16) NOT NULL DEFAULT 'pending',
    assessor_note text,

    submitted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    graded_at timestamp without time zone,

    CONSTRAINT project_question_attempts_pkey PRIMARY KEY (attempt_id),

    CONSTRAINT project_question_attempts_attempt_number_check
        CHECK (attempt_number > 0),

    CONSTRAINT project_question_attempts_option_check
        CHECK (selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')),

    CONSTRAINT project_question_attempts_graded_by_check
        CHECK (graded_by IN ('pending', 'auto', 'assessor')),

    -- An attempt with no response at all is a row nobody can mark.
    CONSTRAINT project_question_attempts_response_check
        CHECK (selected_option IS NOT NULL OR response_text IS NOT NULL),

    -- Marks cannot exceed what the question is worth, and cannot be negative.
    CONSTRAINT project_question_attempts_marks_check
        CHECK (marks_awarded IS NULL OR (marks_awarded >= 0 AND marks_awarded <= max_marks)),

    -- Graded means scored, and ungraded means unscored. Without this a row can
    -- claim graded_by = 'assessor' while marks_awarded is still null, which the
    -- syllabus view would silently total as zero.
    CONSTRAINT project_question_attempts_grade_state_check
        CHECK (
            (graded_by = 'pending' AND marks_awarded IS NULL AND graded_at IS NULL)
            OR (graded_by <> 'pending' AND marks_awarded IS NOT NULL AND graded_at IS NOT NULL)
        )
);

-- The natural key. A resubmission of the same attempt updates it; a re-sit is a
-- new attempt_number and a new row.
CREATE UNIQUE INDEX IF NOT EXISTS project_question_attempts_natural_key
    ON public.project_question_attempts (project_id, question_id, attempt_number);

-- "How is this project doing on this section" — the read behind the syllabus
-- view, and the one that replaces a stored progress column.
CREATE INDEX IF NOT EXISTS project_question_attempts_section_idx
    ON public.project_question_attempts (project_id, section_code, attempt_number);

-- "What is waiting to be marked", across every project.
CREATE INDEX IF NOT EXISTS project_question_attempts_pending_idx
    ON public.project_question_attempts (graded_by, submitted_at)
    WHERE graded_by = 'pending';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'project_question_attempts_project_id_fkey'
    ) THEN
        ALTER TABLE public.project_question_attempts
            ADD CONSTRAINT project_question_attempts_project_id_fkey
            FOREIGN KEY (project_id) REFERENCES public.projects(project_id)
            ON DELETE CASCADE;
    END IF;

    -- ON DELETE RESTRICT, not CASCADE. Reloading the corpus upserts by natural
    -- key and deletes nothing, so this never fires in normal operation — but if
    -- someone ever prunes a question, a learner's marked answer to it must not
    -- disappear with it. Better a failed delete than a silently shortened
    -- transcript.
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'project_question_attempts_question_id_fkey'
    ) THEN
        ALTER TABLE public.project_question_attempts
            ADD CONSTRAINT project_question_attempts_question_id_fkey
            FOREIGN KEY (question_id)
            REFERENCES public.course_section_questions(question_id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'project_question_attempts_section_code_fkey'
    ) THEN
        ALTER TABLE public.project_question_attempts
            ADD CONSTRAINT project_question_attempts_section_code_fkey
            FOREIGN KEY (section_code)
            REFERENCES public.course_sections(section_code)
            ON DELETE CASCADE;
    END IF;
END
$$;
