-- Name: course_recommendations; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.course_recommendations (
    recommendation_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    occupation_id uuid NOT NULL,
    course_id uuid NOT NULL,
    coverage_percentage numeric(5,2) NOT NULL,
    recommendation_rank integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    project_id uuid,
    CONSTRAINT course_recommendations_coverage_percentage_check CHECK (((coverage_percentage >= (0)::numeric) AND (coverage_percentage <= (100)::numeric)))
);


ALTER TABLE public.course_recommendations OWNER TO manojtungala;

--
-- Name: course_recommendations course_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_pkey PRIMARY KEY (recommendation_id);


--
-- Name: course_recommendations course_recommendations_student_id_occupation_id_course_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_student_id_occupation_id_course_id_key UNIQUE (student_id, occupation_id, course_id);


--
-- Name: course_recommendations course_recommendations_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(course_id) ON DELETE CASCADE;


--
-- Name: course_recommendations course_recommendations_occupation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_occupation_id_fkey FOREIGN KEY (occupation_id) REFERENCES public.occupations(occupation_id) ON DELETE CASCADE;


--
-- Name: course_recommendations course_recommendations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
-- Name: course_recommendations course_recommendations_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_recommendations
    ADD CONSTRAINT course_recommendations_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
