-- Name: project_skills; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.project_skills (
    project_skill_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    skill_id uuid,
    skill_name character varying(255),
    proficiency_level integer,
    confidence_score numeric(5,2),
    source character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.project_skills OWNER TO manojtungala;

--
-- Name: project_skills project_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.project_skills
    ADD CONSTRAINT project_skills_pkey PRIMARY KEY (project_skill_id);


--
-- Name: project_skills project_skills_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.project_skills
    ADD CONSTRAINT project_skills_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(project_id) ON DELETE CASCADE;


--
-- Name: project_skills project_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.project_skills
    ADD CONSTRAINT project_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(skill_id);


--
-- Name: project_skills_project_id_name_key; Type: INDEX; Schema: public; Owner: manojtungala
--
-- One row per skill name per project. On lower(skill_name) because the
-- normalizer only canonicalises names it has an alias for, so "Flask" and
-- "flask" can both arrive. Partial because a NULL name has no identity to
-- deduplicate on. This is the conflict target ProjectSkillRepository.bulk_create
-- upserts against; without it every re-extraction appended a duplicate set.

CREATE UNIQUE INDEX project_skills_project_id_name_key ON public.project_skills (project_id, lower(skill_name)) WHERE skill_name IS NOT NULL;


--
