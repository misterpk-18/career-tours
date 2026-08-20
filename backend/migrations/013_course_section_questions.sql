-- The end-of-section question sets, one row per question.
--
-- 012 gave every section its assessment SPEC — "10 concept MCQ (30 marks) + 4
-- code/design scenarios (30) + 2 practical tasks (40)" — as a line of prose.
-- This is that spec made concrete: 2,560 rows, sixteen per section, generated
-- from the corpus and validated before they ever reached here.
--
-- One table, not three, with a question_type discriminator. The three kinds
-- share more than they differ (marks, skills, modules, a rubric for the two
-- that a human grades) and every reader wants them together and in order — a
-- section's paper is all sixteen, not three separate fetches the caller has to
-- interleave. The cost is type-specific columns that are null for the other two
-- types, which the CHECK constraints below make honest rather than merely
-- conventional: an mcq row without options, or a practical without a
-- deliverable, is rejected by the database rather than discovered by a learner.
--
-- section_code is the FK, matching the choice 012 made deliberately: it embeds
-- the course code (NT-C-001-S01), is globally unique on its own, and means this
-- table needs no uuid backfill to point at a real parent.
--
-- options / acceptance_criteria / rubric are jsonb because they are ordered
-- lists the application renders whole and never queries into. skills_covered is
-- text[] instead, because it IS queried — "which questions exercise this skill"
-- is the entire reason the generator recorded skill names per question, and
-- names have to match public.skills.skill_name exactly for that join to find
-- anything. The loader verifies that before writing; the database cannot, since
-- the names arrive as an array rather than as foreign keys.
--
-- No schema_migrations table exists here, so every statement is re-runnable.
CREATE TABLE IF NOT EXISTS public.course_section_questions (
    question_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    section_code character varying(24) NOT NULL,
    question_type character varying(12) NOT NULL,
    question_number integer NOT NULL,
    marks integer NOT NULL,

    -- concept mcq
    stem text,
    options jsonb,
    correct_option character(1),
    explanation text,
    distractor_rationale text,

    -- scenario question
    scenario text,
    task text,
    expected_answer text,

    -- practical task
    title text,
    brief text,
    deliverable text,
    acceptance_criteria jsonb,

    -- shared
    rubric jsonb,
    skills_covered text[] NOT NULL DEFAULT '{}',
    modules_covered integer[] NOT NULL DEFAULT '{}',
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT course_section_questions_pkey PRIMARY KEY (question_id),

    CONSTRAINT course_section_questions_type_check
        CHECK (question_type IN ('mcq', 'scenario', 'practical')),

    CONSTRAINT course_section_questions_marks_check
        CHECK (marks > 0),

    CONSTRAINT course_section_questions_number_check
        CHECK (question_number > 0),

    -- Each type carries its own fields and only its own. Without these the
    -- nullable columns would let a half-populated row of any shape in.
    CONSTRAINT course_section_questions_mcq_shape CHECK (
        question_type <> 'mcq' OR (
            stem IS NOT NULL
            AND options IS NOT NULL
            AND jsonb_array_length(options) = 4
            AND correct_option IN ('A', 'B', 'C', 'D')
            AND explanation IS NOT NULL
        )
    ),

    CONSTRAINT course_section_questions_scenario_shape CHECK (
        question_type <> 'scenario' OR (
            scenario IS NOT NULL
            AND task IS NOT NULL
            AND expected_answer IS NOT NULL
            AND rubric IS NOT NULL
        )
    ),

    CONSTRAINT course_section_questions_practical_shape CHECK (
        question_type <> 'practical' OR (
            title IS NOT NULL
            AND brief IS NOT NULL
            AND deliverable IS NOT NULL
            AND acceptance_criteria IS NOT NULL
            AND rubric IS NOT NULL
        )
    )
);

-- The natural key. The corpus numbers its own questions within each type, so a
-- re-run updates the same 2,560 rows rather than appending a second set — the
-- same mistake 03d3285 had to go back and fix for project skills.
CREATE UNIQUE INDEX IF NOT EXISTS course_section_questions_natural_key
    ON public.course_section_questions (section_code, question_type, question_number);

-- Every read starts "give me this section's paper", in order.
CREATE INDEX IF NOT EXISTS course_section_questions_section_idx
    ON public.course_section_questions (section_code, question_type, question_number);

-- "Which questions exercise this skill" — the reason skill names are stored
-- per question at all.
CREATE INDEX IF NOT EXISTS course_section_questions_skills_idx
    ON public.course_section_questions USING gin (skills_covered);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'course_section_questions_section_code_fkey'
    ) THEN
        ALTER TABLE public.course_section_questions
            ADD CONSTRAINT course_section_questions_section_code_fkey
            FOREIGN KEY (section_code)
            REFERENCES public.course_sections(section_code)
            ON DELETE CASCADE;
    END IF;
END
$$;
