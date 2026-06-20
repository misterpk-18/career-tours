-- Name: course_skills; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.course_skills (
    course_skill_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    coverage_weight numeric(5,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT course_skills_coverage_weight_check CHECK (((coverage_weight >= (0)::numeric) AND (coverage_weight <= (100)::numeric)))
);


ALTER TABLE public.course_skills OWNER TO manojtungala;

--
-- Name: course_skills course_skills_course_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_skills
    ADD CONSTRAINT course_skills_course_id_skill_id_key UNIQUE (course_id, skill_id);


--
-- Name: course_skills course_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_skills
    ADD CONSTRAINT course_skills_pkey PRIMARY KEY (course_skill_id);


--
-- Name: course_skills course_skills_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_skills
    ADD CONSTRAINT course_skills_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(course_id) ON DELETE CASCADE;


--
-- Name: course_skills course_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_skills
    ADD CONSTRAINT course_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id) ON DELETE CASCADE;


--
