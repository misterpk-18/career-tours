-- Allow additional skills (not in the master `skills` catalog) to be stored
-- against a project. For these rows skill_id is NULL and the raw extracted
-- name is kept in skill_name. student_skills is unchanged: it still requires
-- a non-NULL skill_id (only catalog-matched skills are persisted there).

ALTER TABLE public.project_skills
    ALTER COLUMN skill_id DROP NOT NULL;

ALTER TABLE public.project_skills
    ADD COLUMN IF NOT EXISTS skill_name character varying(255);
