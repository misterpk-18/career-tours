import os
from typing import Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai

from services.llm.schemas.career_summary import CareerSummary
from services.llm.schemas.course_summary import CourseSummary
from services.llm.schemas.student_profile import StudentProfile

load_dotenv()

# Model for the recommendation summaries. These were on gpt-4o-mini while returning
# free prose; structured output is a harder ask, so they run a tier up. Extraction
# stays on gpt-5 (a single call per resume); summaries are many calls per project,
# so they use the cheaper sibling.
SUMMARY_MODEL = "gpt-5-mini"


class OpenAIService:
    def __init__(self):
        self.client = wrap_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))

    def extract_skills(self, resume_text: str, questionnaire_answers: Optional[Dict] = None) -> StudentProfile:
        questionnaire_answers = questionnaire_answers or {}

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

        response = self.client.responses.parse(model="gpt-5", input=prompt, text_format=StudentProfile)

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Failed to parse student profile from LLM response")

        return parsed

    def generate_career_summary(
        self, occupation: str, score: float, matched_skills: List[str], missing_skills: List[str]
    ) -> CareerSummary:
        prompt = f"""
You are a career guidance expert advising a student.

Occupation: {occupation}

Match Score: {score}

Matched Skills:
{matched_skills}

Missing Skills:
{missing_skills}

Produce:

- why_it_fits: 2-3 sentences on why this career suits the student, grounded in the
  matched skills above. Address the student as "you".
- strengths: the specific strengths that support this career, one short phrase each.
- skill_gaps: what the student still needs, one short phrase each. Draw these from
  the missing skills.
- outlook: 1-2 sentences on demand for this role and the likely next step up.

Keep the tone professional and student-friendly. Do not repeat the section names
inside the values, and do not use markdown.
"""

        response = self.client.responses.parse(
            model=SUMMARY_MODEL,
            input=prompt,
            text_format=CareerSummary,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Failed to parse career summary from LLM response")

        return parsed

    def generate_course_summary(
        self,
        course_name: str,
        occupation_name: str,
        covered_skills: List[str],
    ) -> CourseSummary:
        skills_text = ", ".join(covered_skills[:10])

        prompt = f"""
You are a career guidance expert advising a student.

Target Career:
{occupation_name}

Recommended Course:
{course_name}

Skills Covered:
{skills_text}

Produce:

- why_recommended: 1-2 sentences on why this course is recommended, referring to the
  gap it closes. Address the student as "you".
- how_it_helps: 1-2 sentences on how it moves you closer to the target career.
- key_skills: the important skills it covers, drawn from the list above, one short
  phrase each.

Keep the tone professional and student-friendly. Do not repeat the section names
inside the values, and do not use markdown.
"""

        response = self.client.responses.parse(
            model=SUMMARY_MODEL,
            input=prompt,
            text_format=CourseSummary,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Failed to parse course summary from LLM response")

        return parsed
