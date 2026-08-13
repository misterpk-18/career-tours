import os
from typing import Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai

from services.llm.schemas.career_profile import CareerProfile
from services.llm.schemas.career_summary import CareerSummary
from services.llm.schemas.course_profile import CourseProfile
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

    def extract_course_profile(self, course_code: str, course_text: str) -> CourseProfile:
        """Turn one course's knowledge-corpus pages into a storable profile.

        One call per course, deliberately: the 40 profiles are independent
        documents, and batching them would make a single bad parse cost 40
        courses' worth of tokens. Extraction runs on gpt-5 for the same reason
        resume extraction does — it is a one-off cost per document, not a
        per-request one, so the cheaper sibling's weaker structure-following is
        not worth the saving.
        """

        prompt = f"""
You are reading one course profile from the Nipuna CareerTours approved knowledge
corpus (course code {course_code}). The full text of that course's pages follows.

{course_text}

Extract exactly these fields.

course_name: the course title as printed in the page header, next to the course
code. Use it verbatim — do not expand abbreviations or re-word it.

description: 2-3 sentences describing what the course covers and what a learner
can do at the end of it. Draw on the "Category", "Target learners" and "Final
outcome" entries. Plain prose, no markdown, no bullet points.

duration_hours: the LOWER bound of the approved guided-hours range. If the
corpus gives "240-300 guided hours", return 240. If it gives only weeks, convert
at the corpus's own stated hours-per-week; if neither is stated, return 0.

level: the difficulty band, phrased as one of "Beginner", "Beginner to
Intermediate", "Intermediate", "Intermediate to Advanced", or "Advanced". Infer
it from the prerequisites and target learners.

skills: the skills the course actually teaches, drawn from the approved tools,
module objectives, section competencies and per-concept knowledge statements.
Aim for 8-15. Prefer the specific and nameable ("Django REST Framework", "SQL",
"Responsive Web Design") over the vague ("programming", "problem solving"). Do
not invent skills the corpus never mentions.

For each skill:
- skill_name: the common industry name for it, in its usual casing.
- coverage_weight: 0-100, how thoroughly THIS course covers it. A core skill the
  course is built around sits around 80-95; a skill that is taught but
  peripheral sits around 50-70. These are independent judgements, not a
  distribution — they do not need to sum to anything.
- category: "technical" for tools, languages and platforms; "soft" for
  communication, teamwork and workplace behaviour; "domain" for
  industry/business knowledge such as accounting, marketing or compliance.

Return structured data.
"""

        response = self.client.responses.parse(model="gpt-5", input=prompt, text_format=CourseProfile)

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"Failed to parse course profile for {course_code} from LLM response")

        return parsed

    def extract_career_skills(
        self,
        career_title: str,
        candidates: List[str],
        description: str = "",
        fixed_relations: bool = False,
    ) -> CareerProfile:
        """Pick and weight the skills one career needs, from a closed vocabulary.

        Two callers, one prompt. Authored careers (modern market titles ESCO has
        no code for) get the whole curated vocabulary to choose from. The ESCO
        careers that were never weighted get only their own upstream relations
        as candidates and ``fixed_relations=True``, because
        ``data/imports/esco/validate.py`` refuses any ESCO pair that is not in
        the upstream ESCO data — so for those the model is choosing weights, not
        skills.

        ``candidates`` are pre-formatted "id | name | category" lines; building
        them is the caller's job because the two modes source them differently.
        """

        # Stated as hard rules because validate.py enforces every one of them as
        # a build failure. Left implicit, the model reliably produces a flat
        # 80/85/90 spread that trips the distinct-weights and >80 caps.
        shape_rules = """
- Choose at least 8 skills, and never fewer than 5.
- At least 3 must be relation_type "essential". Essential means the career
  cannot be practised without it; optional means it is common but not required.
- weight is an integer 1-100 measuring how central the skill is to this career.
- Use at least 4 DISTINCT weight values. Do not cluster everything at 80-90.
- At least one weight must be 70 or above.
- At most 40% of the weights may be above 80. Be sparing at the top.
- The average weight of the essential skills must be clearly higher than the
  average weight of the optional ones.
"""

        if fixed_relations:
            task = f"""
Below is the approved skill list for this career, taken from ESCO. Use EXACTLY
these skills — every one, and nothing else. Keep each skill's given
relation_type. Your job is only to assign each one a weight.
"""
        else:
            task = f"""
Below is the approved skill vocabulary. Choose the skills that a
{career_title} genuinely needs, and return each with a relation_type and a
weight. You may ONLY use skill_id values from this list — never invent one, and
never return a skill this career does not actually need just to pad the count.
"""

        prompt = f"""
You are building a skills profile for the career "{career_title}".
{f"About this career: {description}" if description.strip() else ""}
{task}
{chr(10).join(candidates)}

Rules:
{shape_rules}

Return career_title exactly as "{career_title}", and the skills list.
"""

        response = self.client.responses.parse(model="gpt-5", input=prompt, text_format=CareerProfile)

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"Failed to parse career skills for {career_title} from LLM response")

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
