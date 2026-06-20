-- Name: occupations; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.occupations (
    occupation_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    occupation_name character varying(255) NOT NULL,
    description text,
    average_salary numeric(12,2),
    growth_outlook character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.occupations OWNER TO manojtungala;

--
-- Name: occupations occupations_occupation_name_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupations
    ADD CONSTRAINT occupations_occupation_name_key UNIQUE (occupation_name);


--
-- Name: occupations occupations_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupations
    ADD CONSTRAINT occupations_pkey PRIMARY KEY (occupation_id);


--
