-- Name: jobs; Type: TABLE; Schema: public; Owner: manojtungala
--
-- Backs long-running work that cannot fit in a request. See
-- migrations/007_jobs.sql for why it exists.

CREATE TABLE public.jobs (
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


ALTER TABLE public.jobs OWNER TO manojtungala;

--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: jobs jobs_status_check; Type: CHECK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_status_check CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled'));


--
-- Name: jobs_active_project_type_key; Type: INDEX; Schema: public; Owner: manojtungala
--
-- One active job per (project, type). Partial, so finished rows accumulate as
-- history while only queued/running rows contend — this is what makes a double
-- submit return the in-flight job instead of starting a second expensive run.

CREATE UNIQUE INDEX jobs_active_project_type_key ON public.jobs (project_id, job_type) WHERE status IN ('queued', 'running');


--
-- Name: jobs_project_type_created_idx; Type: INDEX; Schema: public; Owner: manojtungala
--

CREATE INDEX jobs_project_type_created_idx ON public.jobs (project_id, job_type, created_at DESC);


--
-- Name: jobs_status_heartbeat_idx; Type: INDEX; Schema: public; Owner: manojtungala
--

CREATE INDEX jobs_status_heartbeat_idx ON public.jobs (status, heartbeat_at);


--
-- Name: jobs jobs_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
-- Name: jobs jobs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
