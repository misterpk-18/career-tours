-- Add the jobs table backing long-running work.
--
-- Recommendation generation takes ~73 seconds and skill extraction ~30. Both
-- currently run inside the request, which works only because a Lambda Function
-- URL has no integration timeout. API Gateway's HTTP API caps at 30 seconds and
-- cannot be raised, so the request path has to become: write a job row, return
-- 202, do the work out of band, and let the client poll. This table is where
-- that job lives.
--
-- Nothing writes to it yet. This migration and the read-only endpoints that
-- accompany it are deliberately inert, so they can be applied to a live database
-- ahead of the worker without changing any existing behaviour.
--
-- The partial unique index below is the load-bearing part. A double-click on
-- "generate" must not spend a second 73 seconds of OpenAI budget, and the guard
-- cannot live in Python: concurrent requests land in different Lambda sandboxes
-- that share no memory. Postgres is the only thing both of them can agree on.

CREATE TABLE IF NOT EXISTS public.jobs (
    job_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    project_id uuid,
    job_type character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'queued'::character varying NOT NULL,
    stage character varying(50),
    stage_done integer,
    stage_total integer,
    percent integer DEFAULT 0 NOT NULL,
    message text,
    error text,
    result jsonb,
    cancel_requested boolean DEFAULT false NOT NULL,
    attempt smallint DEFAULT 0 NOT NULL,
    request_id text,
    heartbeat_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp without time zone,
    finished_at timestamp without time zone
);

-- ADD CONSTRAINT has no IF NOT EXISTS, so each add is guarded to keep this file
-- re-runnable — the same idiom as 006.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.jobs'::regclass
          AND conname = 'jobs_pkey'
    ) THEN
        ALTER TABLE ONLY public.jobs
            ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.jobs'::regclass
          AND conname = 'jobs_student_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.jobs
            ADD CONSTRAINT jobs_student_id_fkey FOREIGN KEY (student_id)
            REFERENCES public.students(student_id) ON DELETE CASCADE;
    END IF;

    -- project_id is nullable so a job type that is not scoped to a project stays
    -- possible. CASCADE matches resumes_project_id_fkey: deleting a project
    -- should not leave its jobs behind as orphans.
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.jobs'::regclass
          AND conname = 'jobs_project_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.jobs
            ADD CONSTRAINT jobs_project_id_fkey FOREIGN KEY (project_id)
            REFERENCES public.projects(project_id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.jobs'::regclass
          AND conname = 'jobs_status_check'
    ) THEN
        ALTER TABLE ONLY public.jobs
            ADD CONSTRAINT jobs_status_check CHECK (
                status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
            );
    END IF;
END $$;

-- One active job per (project, type). Partial, so completed rows accumulate
-- freely as history and only queued/running rows contend. A second submit hits
-- this and the route returns the job already in flight.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_active_project_type_key
    ON public.jobs (project_id, job_type)
    WHERE status IN ('queued', 'running');

-- "the most recent run of this type for this project", for re-attaching a
-- progress bar after a page reload.
CREATE INDEX IF NOT EXISTS jobs_project_type_created_idx
    ON public.jobs (project_id, job_type, created_at DESC);

-- Finding jobs whose worker died without writing a terminal status. A worker
-- that is OOM-killed or hits the Lambda timeout writes nothing at all, so the
-- only evidence is a heartbeat that stopped advancing.
CREATE INDEX IF NOT EXISTS jobs_status_heartbeat_idx
    ON public.jobs (status, heartbeat_at);
