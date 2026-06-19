import os

from openai import OpenAI
from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai

from services.llm.schemas.student_profile import (
    StudentProfile
)

load_dotenv()


class OpenAIService:

    def __init__(self):
        self.client = wrap_openai(OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY"
            )
        ))

    def extract_skills(
        self,
        resume_text: str,
        questionnaire_answers: dict | None = None
    ) -> StudentProfile:

        questionnaire_answers = (
            questionnaire_answers or {}
        )

        prompt = f"""
Analyze the student's profile.

Resume:
{resume_text}

Questionnaire:
{questionnaire_answers}

Extract:

1. Technical Skills
2. Soft Skills
3. Domain Skills
4. Student Summary

For each skill return:
- skill_name
- confidence (0-1)
- proficiency (1-10)
- source

Return structured data.
"""

        response = self.client.responses.parse(
            model="gpt-5",
            input=prompt,
            text_format=StudentProfile
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Failed to parse student profile from LLM response")

        return parsed

    def generate_career_summary(
        self,
        occupation: str,
        score: float,
        matched_skills: list[str],
        missing_skills: list[str]
    ) -> str:

        prompt = f"""
Occupation: {occupation}

Match Score: {score}

Matched Skills:
{matched_skills}

Missing Skills:
{missing_skills}

Generate:

- Why this career fits
- Strengths
- Skill gaps
- Career outlook

Return plain text only.
"""

        response = self.client.responses.create(
            model="gpt-5",
            input=prompt
        )

        return response.output_text