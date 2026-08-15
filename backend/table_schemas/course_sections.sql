-- Name: course_sections; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.course_sections (
    section_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    course_id uuid NOT NULL,
    section_code character varying(24) NOT NULL,
    module_from integer NOT NULL,
    module_to integer NOT NULL,
    competency text,
    completion_evidence text,
    weight_pct integer,
    assessment text,
    remediation text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT course_sections_module_range_check CHECK (((module_from > 0) AND (module_to >= module_from))),
    CONSTRAINT course_sections_weight_pct_check CHECK (((weight_pct IS NULL) OR ((weight_pct >= 0) AND (weight_pct <= 100))))
);


ALTER TABLE public.course_sections OWNER TO manojtungala;

--
-- Name: course_sections course_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_sections
    ADD CONSTRAINT course_sections_pkey PRIMARY KEY (section_id);


--
-- Name: course_sections course_sections_section_code_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_sections
    ADD CONSTRAINT course_sections_section_code_key UNIQUE (section_code);


--
-- Name: course_sections course_sections_course_id_idx; Type: INDEX; Schema: public; Owner: manojtungala
--

CREATE INDEX course_sections_course_id_idx ON public.course_sections USING btree (course_id, module_from);


--
-- Name: course_sections course_sections_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.course_sections
    ADD CONSTRAINT course_sections_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(course_id) ON DELETE CASCADE;


--
