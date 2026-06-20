-- Name: student_career_matches; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.student_career_matches (
    match_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    occupation_id uuid NOT NULL,
    match_percentage numeric(5,2) NOT NULL,
    rank_position integer NOT NULL,
    generated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    project_id uuid NOT NULL,
    CONSTRAINT student_career_matches_match_percentage_check CHECK (((match_percentage >= (0)::numeric) AND (match_percentage <= (100)::numeric)))
);


ALTER TABLE public.student_career_matches OWNER TO manojtungala;

--
-- Name: student_career_matches student_career_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_career_matches
    ADD CONSTRAINT student_career_matches_pkey PRIMARY KEY (match_id);


--
-- Name: student_career_matches student_career_matches_student_id_occupation_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_career_matches
    ADD CONSTRAINT student_career_matches_student_id_occupation_id_key UNIQUE (student_id, occupation_id);


--
-- Name: student_career_matches student_career_matches_occupation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_career_matches
    ADD CONSTRAINT student_career_matches_occupation_id_fkey FOREIGN KEY (occupation_id) REFERENCES public.occupations(occupation_id) ON DELETE CASCADE;


--
-- Name: student_career_matches student_career_matches_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_career_matches
    ADD CONSTRAINT student_career_matches_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
-- Name: student_career_matches student_career_matches_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_career_matches
    ADD CONSTRAINT student_career_matches_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
