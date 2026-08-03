-- Scope the three recommendation tables' unique constraints to the project, not
-- the student.
--
-- All three repositories upsert with `ON CONFLICT (project_id, ...)`, but these
-- tables were created with `UNIQUE (student_id, ...)`. Postgres matches an
-- ON CONFLICT target against an actual constraint, so on a database built from
-- table_schemas/ the first insert of a generate run failed with
-- "there is no unique or exclusion constraint matching the ON CONFLICT
-- specification" and POST /recommendations/projects/<id>/generate returned 500.
-- The local development database had been corrected by hand, so the mismatch was
-- invisible until a fresh instance was provisioned.
--
-- Project scoping is the intended behaviour: a student may run several projects,
-- and each project gets its own independent set of matches, gaps and course
-- recommendations. Keying on student_id capped a student at one row per
-- occupation across all of their projects, so a second project would overwrite
-- the first project's results instead of recording its own.
--
-- Rewriting the constraint cannot introduce a conflict: the old constraint made
-- (student_id, occupation_id) unique, and a project belongs to exactly one
-- student, so (project_id, occupation_id) is already distinct in existing rows.

ALTER TABLE public.student_career_matches
    DROP CONSTRAINT IF EXISTS student_career_matches_student_id_occupation_id_key;

ALTER TABLE public.career_skill_gaps
    DROP CONSTRAINT IF EXISTS career_skill_gaps_student_id_occupation_id_skill_id_key;

ALTER TABLE public.course_recommendations
    DROP CONSTRAINT IF EXISTS course_recommendations_student_id_occupation_id_course_id_key;

-- ADD CONSTRAINT has no IF NOT EXISTS, so each add is guarded to keep this file
-- re-runnable against a database that already has the project-scoped version.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.student_career_matches'::regclass
          AND conname = 'student_career_matches_project_id_occupation_id_key'
    ) THEN
        ALTER TABLE public.student_career_matches
            ADD CONSTRAINT student_career_matches_project_id_occupation_id_key
            UNIQUE (project_id, occupation_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.career_skill_gaps'::regclass
          AND conname = 'career_skill_gaps_project_id_occupation_id_skill_id_key'
    ) THEN
        ALTER TABLE public.career_skill_gaps
            ADD CONSTRAINT career_skill_gaps_project_id_occupation_id_skill_id_key
            UNIQUE (project_id, occupation_id, skill_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.course_recommendations'::regclass
          AND conname = 'course_recommendations_project_id_occupation_id_course_id_key'
    ) THEN
        ALTER TABLE public.course_recommendations
            ADD CONSTRAINT course_recommendations_project_id_occupation_id_course_id_key
            UNIQUE (project_id, occupation_id, course_id);
    END IF;
END $$;
