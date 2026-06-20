-- Name: students; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.students (
    student_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    full_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    phone character varying(20),
    college_name character varying(255),
    degree_name character varying(255),
    branch_name character varying(255),
    current_year_semester character varying(50),
    graduation_year integer,
    preferred_job_location character varying(255),
    target_role character varying(255),
    career_interest character varying(255),
    learning_hours_per_week integer,
    internship_preference character varying(20),
    work_mode_preference character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT students_internship_preference_check CHECK (((internship_preference)::text = ANY ((ARRAY['free'::character varying, 'paid'::character varying, 'both'::character varying])::text[]))),
    CONSTRAINT students_work_mode_preference_check CHECK (((work_mode_preference)::text = ANY ((ARRAY['office'::character varying, 'remote'::character varying, 'hybrid'::character varying])::text[])))
);


ALTER TABLE public.students OWNER TO manojtungala;

--
-- Name: students students_email_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_email_key UNIQUE (email);


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (student_id);


--
