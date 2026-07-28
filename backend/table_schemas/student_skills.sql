-- Name: student_skills; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.student_skills (
    student_skill_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    proficiency_level integer,
    confidence_score numeric(5,2),
    source character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT student_skills_confidence_score_check CHECK (((confidence_score >= (0)::numeric) AND (confidence_score <= (1)::numeric))),
    CONSTRAINT student_skills_proficiency_level_check CHECK (((proficiency_level >= 1) AND (proficiency_level <= 10)))
);


ALTER TABLE public.student_skills OWNER TO manojtungala;

--
-- Name: student_skills student_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_skills
    ADD CONSTRAINT student_skills_pkey PRIMARY KEY (student_skill_id);


--
-- Name: student_skills student_skills_student_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_skills
    ADD CONSTRAINT student_skills_student_id_skill_id_key UNIQUE (student_id, skill_id);


--
-- Name: student_skills student_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_skills
    ADD CONSTRAINT student_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id) ON DELETE CASCADE;


--
-- Name: student_skills student_skills_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.student_skills
    ADD CONSTRAINT student_skills_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
