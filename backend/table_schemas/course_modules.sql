-- Name: course_modules; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.course_modules (
    module_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_id uuid NOT NULL,
    module_number integer NOT NULL,
    title character varying(255) NOT NULL,
    objective text,
    observable_evidence text,
    topics jsonb DEFAULT '[]'::jsonb NOT NULL,
    section_code character varying(24),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT course_modules_module_number_check CHECK ((module_number > 0)),
    CONSTRAINT course_modules_topics_check CHECK ((jsonb_typeof(topics) = 'array'))
);


ALTER TABLE public.course_modules OWNER TO manojtungala;

--
-- Name: course_modules course_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_pkey PRIMARY KEY (module_id);


--
-- Name: course_modules course_modules_course_id_module_number_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_course_id_module_number_key UNIQUE (course_id, module_number);


--
-- Name: course_modules course_modules_course_id_idx; Type: INDEX; Schema: public; Owner: manojtungala
--

CREATE INDEX course_modules_course_id_idx ON public.course_modules USING btree (course_id, module_number);


--
-- Name: course_modules course_modules_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(course_id) ON DELETE CASCADE;


--
