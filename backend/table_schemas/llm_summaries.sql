-- Name: llm_summaries; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.llm_summaries (
    summary_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    occupation_id uuid,
    summary_type character varying(100) NOT NULL,
    summary_text text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    project_id uuid NOT NULL,
    course_id uuid
);


ALTER TABLE public.llm_summaries OWNER TO manojtungala;

--
-- Name: llm_summaries llm_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.llm_summaries
    ADD CONSTRAINT llm_summaries_pkey PRIMARY KEY (summary_id);


--
-- Name: llm_summaries llm_summaries_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.llm_summaries
    ADD CONSTRAINT llm_summaries_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(course_id) ON DELETE CASCADE;


--
-- Name: llm_summaries llm_summaries_occupation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.llm_summaries
    ADD CONSTRAINT llm_summaries_occupation_id_fkey FOREIGN KEY (occupation_id) REFERENCES public.occupations(occupation_id) ON DELETE CASCADE;


--
-- Name: llm_summaries llm_summaries_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.llm_summaries
    ADD CONSTRAINT llm_summaries_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
-- Name: llm_summaries llm_summaries_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.llm_summaries
    ADD CONSTRAINT llm_summaries_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
