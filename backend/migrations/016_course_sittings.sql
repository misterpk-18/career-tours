-- A second, project-INDEPENDENT assessment track.
--
-- 015 gave a section its sittings scoped to a PROJECT: a score belongs to a
-- student's workspace, and the same student can hold several. This adds a
-- parallel track scoped to the STUDENT directly, reachable from the catalogue
-- course page with no project in sight. The two are deliberately separate
-- tables rather than one table with a nullable owner, because the whole point
-- is independence: a section's course-track score and its project-track score
-- must never touch, and separate relations make that structural rather than a
-- convention a query has to remember.
--
-- Everything else mirrors 015 exactly -- same clock model (stored REMAINING,
-- not a deadline), same "first graded submit locks the score" via a partial
-- unique index, same MCQ-only scoring out of 30. The only substantive
-- difference is the owner column: student_id here, project_id there.
--
-- No schema_migrations table exists here, so every statement is re-runnable.
CREATE TABLE IF NOT EXISTS public.course_section_sittings (
    sitting_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,

    mode character varying(8) NOT NULL DEFAULT 'graded',
    status character varying(12) NOT NULL DEFAULT 'in_progress',

    time_limit_seconds integer NOT NULL,
    seconds_remaining integer NOT NULL,
    resumed_at timestamp without time zone,

    marks_awarded integer,
    marks_available integer NOT NULL,

    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    submitted_at timestamp without time zone,

    CONSTRAINT course_section_sittings_pkey PRIMARY KEY (sitting_id),

    CONSTRAINT course_section_sittings_mode_check
        CHECK (mode IN ('graded', 'practice')),

    CONSTRAINT course_section_sittings_status_check
        CHECK (status IN ('in_progress', 'paused', 'submitted', 'abandoned')),

    CONSTRAINT course_section_sittings_clock_check
        CHECK (time_limit_seconds > 0 AND seconds_remaining >= 0
               AND seconds_remaining <= time_limit_seconds),

    CONSTRAINT course_section_sittings_running_check
        CHECK ((status = 'in_progress') = (resumed_at IS NOT NULL)),

    CONSTRAINT course_section_sittings_submitted_check
        CHECK (
            (status = 'submitted'
             AND submitted_at IS NOT NULL AND marks_awarded IS NOT NULL)
            OR (status <> 'submitted'
                AND submitted_at IS NULL AND marks_awarded IS NULL)
        ),

    CONSTRAINT course_section_sittings_marks_check
        CHECK (marks_awarded IS NULL
               OR (marks_awarded >= 0 AND marks_awarded <= marks_available))
);

-- One graded sitting per section per student, ever -- the constraint that makes
-- the course-track score final, exactly as the project track's does.
CREATE UNIQUE INDEX IF NOT EXISTS course_section_sittings_one_graded
    ON public.course_section_sittings (student_id, section_code)
    WHERE mode = 'graded';

-- At most one open practice run at a time, so "resume practice" is unambiguous.
CREATE UNIQUE INDEX IF NOT EXISTS course_section_sittings_one_open_practice
    ON public.course_section_sittings (student_id, section_code)
    WHERE mode = 'practice' AND status IN ('in_progress', 'paused');

CREATE INDEX IF NOT EXISTS course_section_sittings_student_idx
    ON public.course_section_sittings (student_id, section_code, started_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_section_sittings_student_id_fkey') THEN
        ALTER TABLE public.course_section_sittings
            ADD CONSTRAINT course_section_sittings_student_id_fkey
            FOREIGN KEY (student_id) REFERENCES public.students(student_id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_section_sittings_section_code_fkey') THEN
        ALTER TABLE public.course_section_sittings
            ADD CONSTRAINT course_section_sittings_section_code_fkey
            FOREIGN KEY (section_code) REFERENCES public.course_sections(section_code)
            ON DELETE CASCADE;
    END IF;
END
$$;


-- The answers inside a course-track sitting. Mirror of the project track's
-- attempts in its post-015 shape (sitting_id + presented_option, natural key
-- on the sitting, no attempt_number), with student_id as the owner column.
CREATE TABLE IF NOT EXISTS public.course_question_attempts (
    attempt_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    sitting_id uuid NOT NULL,
    student_id uuid NOT NULL,
    question_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,

    -- Canonical corpus letter. is_correct is decided against this.
    selected_option character(1),
    -- The letter the student actually clicked in their shuffled layout.
    presented_option character(1),
    response_text text,

    is_correct boolean,
    marks_awarded integer,
    max_marks integer NOT NULL,

    graded_by character varying(16) NOT NULL DEFAULT 'pending',
    assessor_note text,

    submitted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    graded_at timestamp without time zone,

    CONSTRAINT course_question_attempts_pkey PRIMARY KEY (attempt_id),

    CONSTRAINT course_question_attempts_option_check
        CHECK (selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')),

    CONSTRAINT course_question_attempts_graded_by_check
        CHECK (graded_by IN ('pending', 'auto', 'assessor')),

    CONSTRAINT course_question_attempts_response_check
        CHECK (selected_option IS NOT NULL OR response_text IS NOT NULL),

    CONSTRAINT course_question_attempts_marks_check
        CHECK (marks_awarded IS NULL OR (marks_awarded >= 0 AND marks_awarded <= max_marks)),

    CONSTRAINT course_question_attempts_grade_state_check
        CHECK (
            (graded_by = 'pending' AND marks_awarded IS NULL AND graded_at IS NULL)
            OR (graded_by <> 'pending' AND marks_awarded IS NOT NULL AND graded_at IS NOT NULL)
        )
);

-- One answer per question per sitting; revising an answer is an upsert.
CREATE UNIQUE INDEX IF NOT EXISTS course_question_attempts_natural_key
    ON public.course_question_attempts (sitting_id, question_id);

CREATE INDEX IF NOT EXISTS course_question_attempts_section_idx
    ON public.course_question_attempts (student_id, section_code);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_question_attempts_sitting_id_fkey') THEN
        ALTER TABLE public.course_question_attempts
            ADD CONSTRAINT course_question_attempts_sitting_id_fkey
            FOREIGN KEY (sitting_id)
            REFERENCES public.course_section_sittings(sitting_id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_question_attempts_student_id_fkey') THEN
        ALTER TABLE public.course_question_attempts
            ADD CONSTRAINT course_question_attempts_student_id_fkey
            FOREIGN KEY (student_id) REFERENCES public.students(student_id)
            ON DELETE CASCADE;
    END IF;

    -- ON DELETE RESTRICT for the question, same reasoning as the project track:
    -- pruning a question must not silently shorten a learner's transcript.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_question_attempts_question_id_fkey') THEN
        ALTER TABLE public.course_question_attempts
            ADD CONSTRAINT course_question_attempts_question_id_fkey
            FOREIGN KEY (question_id)
            REFERENCES public.course_section_questions(question_id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'course_question_attempts_section_code_fkey') THEN
        ALTER TABLE public.course_question_attempts
            ADD CONSTRAINT course_question_attempts_section_code_fkey
            FOREIGN KEY (section_code)
            REFERENCES public.course_sections(section_code)
            ON DELETE CASCADE;
    END IF;
END
$$;
