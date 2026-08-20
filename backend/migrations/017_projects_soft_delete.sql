-- Soft delete for projects.
--
-- A student can now delete a project, but "delete" here means hide, not
-- destroy: the row and everything that cascades off it (sittings, scores,
-- recommendations, skill gaps) stay in the database. A hard DELETE would take
-- all of that with it via ON DELETE CASCADE, and a deleted project's history is
-- worth keeping — for the student who changes their mind and for any later
-- analysis.
--
-- deleted_at NULL means active and visible; a timestamp means hidden and when.
-- A dedicated column rather than a status value because status is already used
-- for the project's own lifecycle and a soft-delete flag must not be something
-- an ordinary status update can clear by accident.
--
-- No schema_migrations table exists here, so every statement is re-runnable.
ALTER TABLE public.projects
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone;

-- The list read is "this student's active projects, newest first". A partial
-- index on the active rows keeps that fast and skips the deleted ones entirely.
CREATE INDEX IF NOT EXISTS projects_active_by_student
    ON public.projects (student_id, created_at DESC)
    WHERE deleted_at IS NULL;
