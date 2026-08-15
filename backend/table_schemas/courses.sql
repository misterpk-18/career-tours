-- Name: courses; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.courses (
    course_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_code character varying(16),
    course_name character varying(255) NOT NULL,
    description text,
    duration_hours integer,
    level character varying(50),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.courses OWNER TO manojtungala;

--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (course_id);


--
-- Name: courses_course_code_key; Type: INDEX; Schema: public; Owner: manojtungala
--
-- Partial: the pre-corpus courses have no code, and several NULLs must coexist.

CREATE UNIQUE INDEX courses_course_code_key
    ON public.courses (course_code)
    WHERE course_code IS NOT NULL;


--
