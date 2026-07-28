-- Name: skills; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.skills (
    skill_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    skill_name character varying(255) NOT NULL,
    skill_category character varying(100),
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.skills OWNER TO manojtungala;

--
-- Name: skills skills_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.skills
    ADD CONSTRAINT skills_pkey PRIMARY KEY (skill_id);


--
-- Name: skills skills_skill_name_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.skills
    ADD CONSTRAINT skills_skill_name_key UNIQUE (skill_name);


--
