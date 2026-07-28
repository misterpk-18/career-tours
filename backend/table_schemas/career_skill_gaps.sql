-- Name: career_skill_gaps; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.career_skill_gaps (
    gap_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    occupation_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    gap_percentage numeric(5,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    project_id uuid,
    CONSTRAINT career_skill_gaps_gap_percentage_check CHECK (((gap_percentage >= (0)::numeric) AND (gap_percentage <= (100)::numeric)))
);


ALTER TABLE public.career_skill_gaps OWNER TO manojtungala;

--
-- Name: career_skill_gaps career_skill_gaps_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_pkey PRIMARY KEY (gap_id);


--
-- Name: career_skill_gaps career_skill_gaps_student_id_occupation_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_student_id_occupation_id_skill_id_key UNIQUE (student_id, occupation_id, skill_id);


--
-- Name: career_skill_gaps career_skill_gaps_occupation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_occupation_id_fkey FOREIGN KEY (occupation_id) REFERENCES public.occupations(occupation_id) ON DELETE CASCADE;


--
-- Name: career_skill_gaps career_skill_gaps_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
-- Name: career_skill_gaps career_skill_gaps_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id) ON DELETE CASCADE;


--
-- Name: career_skill_gaps career_skill_gaps_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.career_skill_gaps
    ADD CONSTRAINT career_skill_gaps_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
