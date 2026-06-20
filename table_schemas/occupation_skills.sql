-- Name: occupation_skills; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.occupation_skills (
    occupation_skill_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    occupation_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    weight numeric(5,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT occupation_skills_weight_check CHECK (((weight >= (0)::numeric) AND (weight <= (100)::numeric)))
);


ALTER TABLE public.occupation_skills OWNER TO manojtungala;

--
-- Name: occupation_skills occupation_skills_occupation_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupation_skills
    ADD CONSTRAINT occupation_skills_occupation_id_skill_id_key UNIQUE (occupation_id, skill_id);


--
-- Name: occupation_skills occupation_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupation_skills
    ADD CONSTRAINT occupation_skills_pkey PRIMARY KEY (occupation_skill_id);


--
-- Name: occupation_skills occupation_skills_occupation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupation_skills
    ADD CONSTRAINT occupation_skills_occupation_id_fkey FOREIGN KEY (occupation_id) REFERENCES public.occupations(occupation_id) ON DELETE CASCADE;


--
-- Name: occupation_skills occupation_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.occupation_skills
    ADD CONSTRAINT occupation_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id) ON DELETE CASCADE;


--
