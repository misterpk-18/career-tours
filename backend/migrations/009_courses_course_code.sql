-- Give courses the corpus's own identifier, so the knowledge-corpus loader has
-- something stable to upsert on.
--
-- The 40 courses now come from Nipuna's approved knowledge corpus, where each
-- one is identified by a code (NT-C-001 .. NT-C-040) printed on every page. The
-- loader has to be re-runnable, which means matching an incoming profile to the
-- row it already wrote. course_name is the only other candidate and it is a
-- poor one: it is what the corpus is most likely to re-word between versions
-- ("Web Development / Web Designing" is already carrying a slash for exactly
-- that reason), and re-wording it would silently insert a duplicate course
-- rather than update the existing one.
--
-- Nullable, because the 20 pre-corpus courses have no code and are not getting
-- invented ones. The unique index is partial for the same reason — several
-- NULLs are fine, two NT-C-001s are not.
ALTER TABLE public.courses
    ADD COLUMN IF NOT EXISTS course_code character varying(16);

CREATE UNIQUE INDEX IF NOT EXISTS courses_course_code_key
    ON public.courses (course_code)
    WHERE course_code IS NOT NULL;
