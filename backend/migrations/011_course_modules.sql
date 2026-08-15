-- Give the corpus's eight-modules-per-course structure somewhere to live.
--
-- Every course PDF in the approved knowledge corpus is built from the same
-- template: four "Deep Knowledge" sections, two modules each, eight modules per
-- course, 320 across the catalog. Each module states a title, an objective and
-- the observable evidence a learner must produce. Until now all of it was read
-- and thrown away — extract_course_profiles.py sends the whole PDF to the model
-- and keeps five course-level fields plus a flat skill list, so a course could
-- say what it teaches but never what order it teaches it in.
--
-- topics is jsonb rather than a child table. The objective line *is* the topic
-- list ("Syntax, data types, control flow, functions"), so a topic has no
-- identity of its own, nothing points at one, and nothing joins on one — it is
-- a display array, and a table would buy foreign keys nobody needs. The raw
-- objective is kept alongside it as the source of truth, so a bad split stays a
-- cosmetic problem rather than data loss.
--
-- UNIQUE (course_id, module_number) is what makes the loader re-runnable: the
-- corpus numbers its own modules, so the upsert has a stable natural key and a
-- second run updates the same 320 rows instead of doubling them.
--
-- Constraints are inline rather than in trailing ALTER TABLE statements so that
-- CREATE TABLE IF NOT EXISTS covers the whole migration and re-running it is a
-- no-op. There is no schema_migrations table here; re-runnability is the only
-- thing standing between an operator and a duplicate-object error.
CREATE TABLE IF NOT EXISTS public.course_modules (
    module_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_id uuid NOT NULL,
    module_number integer NOT NULL,
    title character varying(255) NOT NULL,
    objective text,
    observable_evidence text,
    topics jsonb DEFAULT '[]'::jsonb NOT NULL,
    section_code character varying(24),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT course_modules_pkey PRIMARY KEY (module_id),
    CONSTRAINT course_modules_module_number_check CHECK ((module_number > 0)),
    CONSTRAINT course_modules_topics_check CHECK ((jsonb_typeof(topics) = 'array')),
    CONSTRAINT course_modules_course_id_module_number_key UNIQUE (course_id, module_number),
    CONSTRAINT course_modules_course_id_fkey FOREIGN KEY (course_id)
        REFERENCES public.courses(course_id) ON DELETE CASCADE
);

-- The syllabus read is always "every module of this course, in order", so the
-- index carries module_number and the ORDER BY comes for free.
CREATE INDEX IF NOT EXISTS course_modules_course_id_idx
    ON public.course_modules (course_id, module_number);
