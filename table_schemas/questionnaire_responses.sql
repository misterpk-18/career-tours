-- Name: questionnaire_responses; Type: TABLE; Schema: public; Owner: manojtungala
--

CREATE TABLE public.questionnaire_responses (
    response_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    student_id uuid NOT NULL,
    question_id uuid NOT NULL,
    answer_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.questionnaire_responses OWNER TO manojtungala;

--
-- Name: questionnaire_responses questionnaire_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.questionnaire_responses
    ADD CONSTRAINT questionnaire_responses_pkey PRIMARY KEY (response_id);


--
-- Name: questionnaire_responses questionnaire_responses_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.questionnaire_responses
    ADD CONSTRAINT questionnaire_responses_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questionnaires(question_id) ON DELETE CASCADE;


--
-- Name: questionnaire_responses questionnaire_responses_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: manojtungala
--

ALTER TABLE ONLY public.questionnaire_responses
    ADD CONSTRAINT questionnaire_responses_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id) ON DELETE CASCADE;


--
