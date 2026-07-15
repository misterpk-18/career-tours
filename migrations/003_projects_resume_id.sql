-- Add a back-pointer from a project to its resume. A project is created with
-- resume_id = NULL; it is populated once a resume is uploaded for that project.
-- resumes.project_id already links the other direction; the two nullable FKs
-- form a harmless circular reference. ON DELETE SET NULL clears the pointer if
-- the referenced resume is deleted (deleting a project still cascade-deletes
-- its resumes via resumes.project_id).

ALTER TABLE public.projects
    ADD COLUMN IF NOT EXISTS resume_id uuid;

ALTER TABLE public.projects
    ADD CONSTRAINT projects_resume_id_fkey
    FOREIGN KEY (resume_id) REFERENCES public.resumes(resume_id) ON DELETE SET NULL;
