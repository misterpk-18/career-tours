-- Name: skill_aliases; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.skill_aliases (
    alias_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    skill_id uuid NOT NULL,
    alias_name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.skill_aliases OWNER TO manojtungala;

--
-- Name: skill_aliases skill_aliases_alias_name_key; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.skill_aliases
    ADD CONSTRAINT skill_aliases_alias_name_key UNIQUE (alias_name);


--
-- Name: skill_aliases skill_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.skill_aliases
    ADD CONSTRAINT skill_aliases_pkey PRIMARY KEY (alias_id);


--
-- Name: skill_aliases skill_aliases_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.skill_aliases
    ADD CONSTRAINT skill_aliases_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id) ON DELETE CASCADE;


--
