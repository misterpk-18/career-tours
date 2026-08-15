-- Store the assessment structure the modules hang off.
--
-- 011 gave each course its eight modules but left section_code as a bare
-- string, pointing at nothing. The corpus puts real content in the section
-- header: the competency the pair of modules builds, the evidence that closes
-- them out, the section's share of the weighted mock-test average
-- (20/25/25/30) and the assessment split that produces it, plus the remediation
-- path for a learner who fails it. A syllabus view that shows modules without
-- their weight is showing eight equal-looking blocks that are not equal.
--
-- section_code is the natural key and is globally unique on its own, because it
-- embeds the course code (NT-C-001-S01). That is what lets course_modules keep
-- pointing at a plain string and still gain a real foreign key, rather than
-- needing a uuid backfilled into all 320 rows.
--
-- The FK is added separately below and guarded, because course_modules already
-- exists and ALTER TABLE ... ADD CONSTRAINT has no IF NOT EXISTS form. Same
-- reason as always here: there is no schema_migrations table, so re-running the
-- file has to be a no-op.
CREATE TABLE IF NOT EXISTS public.course_sections (
    section_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,
    module_from integer NOT NULL,
    module_to integer NOT NULL,
    competency text,
    completion_evidence text,
    weight_pct integer,
    assessment text,
    remediation text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT course_sections_pkey PRIMARY KEY (section_id),
    CONSTRAINT course_sections_section_code_key UNIQUE (section_code),
    CONSTRAINT course_sections_module_range_check CHECK ((module_from > 0 AND module_to >= module_from)),
    CONSTRAINT course_sections_weight_pct_check CHECK ((weight_pct IS NULL OR (weight_pct >= 0 AND weight_pct <= 100))),
    CONSTRAINT course_sections_course_id_fkey FOREIGN KEY (course_id)
        REFERENCES public.courses(course_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS course_sections_course_id_idx
    ON public.course_sections (course_id, module_from);

-- ON DELETE SET NULL rather than CASCADE: a section going away is a corpus
-- revision, and it should orphan the module's grouping, not delete the module
-- and take its topics with it.
--
-- Added NOT VALID, then validated separately below. On an existing database 011
-- has already written 320 module rows whose section_code points at a table that
-- is empty until load_course_modules.py runs, so a checked constraint could
-- never be added at this point in the sequence. NOT VALID still enforces the
-- key on every future insert and update; it only declines to re-check the rows
-- already there.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'course_modules_section_code_fkey'
    ) THEN
        ALTER TABLE public.course_modules
            ADD CONSTRAINT course_modules_section_code_fkey FOREIGN KEY (section_code)
            REFERENCES public.course_sections(section_code) ON DELETE SET NULL
            NOT VALID;
    END IF;
END
$$;

-- Promote it to fully validated once the rows can actually satisfy it, which is
-- immediately on a fresh database (no module rows yet) and on the next run of
-- this file after the loader has populated course_sections. Re-running the
-- migration is the documented recovery, so making it the thing that finishes
-- the job keeps the operator instructions to "apply migrations, load data".
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'course_modules_section_code_fkey' AND NOT convalidated
    ) AND NOT EXISTS (
        SELECT 1 FROM public.course_modules cm
        LEFT JOIN public.course_sections cs ON cs.section_code = cm.section_code
        WHERE cm.section_code IS NOT NULL AND cs.section_code IS NULL
    ) THEN
        ALTER TABLE public.course_modules VALIDATE CONSTRAINT course_modules_section_code_fkey;
        RAISE NOTICE 'course_modules_section_code_fkey validated';
    END IF;
END
$$;
