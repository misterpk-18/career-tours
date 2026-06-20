-- Name: questionnaires; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.questionnaires (
    question_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    question_text text NOT NULL,
    question_type character varying(50) NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.questionnaires OWNER TO manojtungala;

--
-- Name: questionnaires questionnaires_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.questionnaires
    ADD CONSTRAINT questionnaires_pkey PRIMARY KEY (question_id);


--
