import os
from typing import Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai

from services.llm.schemas.career_profile import CareerProfile
from services.llm.schemas.career_summary import CareerSummary
from services.llm.schemas.course_profile import CourseProfile
from services.llm.schemas.course_summary import CourseSummary
from services.llm.schemas.section_assessment import SectionAssessment
from services.llm.schemas.student_profile import StudentProfile

load_dotenv()

# Model for the recommendation summaries. These were on gpt-4o-mini while returning
# free prose; structured output is a harder ask, so they run a tier up. Extraction
# stays on gpt-5 (a single call per resume); summaries are many calls per project,
# so they use the cheaper sibling.
SUMMARY_MODEL = "gpt-5-mini"



def section_assessment_prompt(course: Dict, section: Dict, modules: List[Dict]) -> str:
    """The instructions for writing one section's question set.

    Module scope, not a method, because the corpus is being trialled against
    more than one generator and both have to be handed the SAME text. A
    paraphrase would make the comparison a measure of the paraphrase.
    """

    module_block = "\n\n".join(
        f"""Module {m['module_number']} - {m['title']}
Objective: {m['objective']}
Topics: {', '.join(m['topics'])}
Observable evidence: {m['observable_evidence']}"""
        for m in modules
    )

    skill_lines = "\n".join(
        f"- {s['skill_name']} (course-level coverage {int(s['coverage_weight'])}/100, {s['category']})"
        for s in course["skills"]
    )

    module_numbers = sorted(m["module_number"] for m in modules)

    return f"""
You are writing the end-of-section assessment for section {section['section_code']}
of the Nipuna CareerTours course "{course['course_name']}" ({course['course_code']}).

The learner has just finished the two modules below and nothing after them.

{module_block}

Section competency: {section['competency']}
Completion evidence the learner must produce: {section['completion_evidence']}
This section is worth {section['weight_pct']}% of the course.

Here are ALL the skills the course teaches, across all eight modules:

{skill_lines}

First decide which of those skills these two modules genuinely cover, and return
them in skills_assessed using the skill names EXACTLY as written above. Do not
include a skill the learner has not been taught yet — a question about a skill
from a later module is a broken question, not a hard one. Do not coin new names.

Then write the assessment. It must contain exactly:

- 10 concept MCQs, 3 marks each (30 total)
- 4 scenario questions, 7 or 8 marks each, summing to exactly 30
- 2 practical tasks, 20 marks each (40 total)

Draw each question's skills_covered from skills_assessed only, and set
modules_covered to the module numbers ({" and/or ".join(str(n) for n in module_numbers)})
the question draws on. Prefer questions that need BOTH modules over questions
that sit inside one.

You do NOT have to reach every skill in skills_assessed. Sixteen questions cannot
go deep on nine skills at once, and a set that covers everything shallowly is
worse than one that goes properly hard on the skills at the centre of these two
modules. Spend the questions where the difficulty is, and let the peripheral
skills go unasked.

Make these HARD. This is the standard:

- A question a learner can answer by recalling a definition is too easy. Ask what
  happens, why it happens, which of two correct-looking approaches is right here,
  or what breaks under a stated condition.
- These MCQ forms are BANNED outright, however well written. Do not produce them:
  "What is X?", "Which of the following best describes X?", "What is the purpose
  of X?", "What is the primary difference between X and Y?", "Which of these is a
  benefit of X?". Every one is answerable from a glossary, which makes it worth
  nothing here. Replace each with a specific situation that has an outcome: show
  the state, the call, or the command, and ask what results and why. If a stem
  could be answered by someone who had read about the topic but never used it,
  it is the wrong question.
- Prefer stems built on a concrete artefact — a snippet, a query, a schema, a
  command with its output, a report extract — over stems that are pure prose.
  At least seven of the ten MCQs must contain such an artefact.
- Give each scenario and practical task at least 4 rubric criteria. Two or three
  coarse lines cannot be marked consistently by different assessors.
- MCQ distractors must be beliefs a half-learned student actually holds — the
  near-miss, the right idea applied in the wrong place, the answer that is true
  in general but false in this case. Never pad with an obviously absurd option.
  Say in distractor_rationale why each wrong option is tempting.
- Scenarios must give concrete context and ask for a judgement plus its
  justification. "Explain X" is not a scenario. Where this course teaches
  programming, that context is real code, a real schema or a real API contract.
  Where it does not, it is the equivalent artefact in ITS OWN domain and you
  must not reach for code to manufacture difficulty: a trial balance that will
  not tie, a period that will not close, a campaign whose cost per acquisition
  moved the wrong way, a layout whose logo fails at 16px, a subnet plan that
  collides. Difficulty comes from the judgement the situation demands, not from
  the notation it is written in.
- Practical tasks must produce the section's stated completion evidence, be
  finishable in 2-4 hours, and have acceptance criteria an assessor can check by
  looking at the submission rather than by forming an opinion.
- Each rubric's criterion marks must sum to that question's marks.

Return section_code exactly as "{section['section_code']}". Write options as four
plain strings in A, B, C, D order — no "A)" prefixes. Ground everything in the two
modules' topics.

FORMATTING. The interface renders these fields as restricted markdown, so:

- Put every piece of code, query, schema, markup, config, terminal output or
  report extract in a fenced block with a language tag, like ```python ... ```
  or ```sql ... ```. Use the tag that matches what is inside: python, sql,
  javascript, jsx, typescript, tsx, html, css, scss, java, csharp, cpp, c, go,
  rust, ruby, php, kotlin, swift, r, abap, bash, powershell, dockerfile, nginx,
  apache, terraform, makefile, http, json, yaml, toml, ini, xml, csv, graphql,
  markdown, diff, dax, mdx, powerquery, vba. Use ```text for anything with no language — ledger extracts,
  trial balances, report output, directory trees, plain tabular data.
- Keep real newlines and indentation inside the fence. Do not collapse a
  multi-line program onto one line.
- Close every fence you open.
- Use `single backticks` for an identifier mentioned mid-sentence — a column
  name, a function name, a menu path, a flag.
- Use NO other markdown. No headings, no bold, no italics, no bullet or numbered
  lists, no tables. Prose is plain sentences.

This applies to every text field, including the four MCQ options: an option that
is a query or a snippet gets its own fenced block, exactly like the stem.
"""

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

    def extract_course_profile(
        self,
        course_code: str,
        course_text: str,
        vocabulary: Optional[List[str]] = None,
    ) -> CourseProfile:
        """Turn one course's knowledge-corpus pages into a storable profile.

        One call per course, deliberately: the 40 profiles are independent
        documents, and batching them would make a single bad parse cost 40
        courses' worth of tokens. Extraction runs on gpt-5 for the same reason
        resume extraction does — it is a one-off cost per document, not a
        per-request one, so the cheaper sibling's weaker structure-following is
        not worth the saving.

        ``vocabulary`` is the list of skill names the rest of the system already
        speaks, and passing it is what makes the output useful. Course
        recommendation joins a student's gap skills — which come from
        ``occupation_skills`` — to ``course_skills`` on ``skill_id``, exactly.
        Extracted without a vocabulary, this prompt produces faithful syllabus
        phrasing ("Aggregation with GROUP BY and HAVING") that no occupation
        ever names, and the join finds nothing.
        """

        if vocabulary:
            # Deliberately not a hard constraint. A course can legitimately teach
            # something no occupation lists — Tally, GST filing — and forcing
            # those onto a near-miss from the list would be worse than admitting
            # a new name. The instruction is "prefer", and the loader
            # canonicalizes whatever comes back.
            vocabulary_rule = f"""
Wherever one of these approved skill names fits, use it EXACTLY as written
rather than inventing your own wording. This is how the course is linked to the
careers that need it, so a near-match in your own words is worse than a slightly
broader name from this list. Coin a new name only when nothing here genuinely
covers the skill.

{chr(10).join(vocabulary)}
"""
        else:
            vocabulary_rule = ""

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
{vocabulary_rule}

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

    def generate_section_assessment(
        self,
        course: Dict,
        section: Dict,
        modules: List[Dict],
    ) -> SectionAssessment:
        """Write the end-of-section question set for one pair of modules.

        The prompt lives in ``section_assessment_prompt`` at module scope rather
        than inline, because it is not only used here — the same text has to be
        handed verbatim to any other generator the corpus is trialled against,
        and a second copy would quietly drift.

        One call per section, 160 in the corpus. Sections are the unit rather
        than modules or topics because the corpus already treats them as one:
        each owns exactly two consecutive modules, declares its own
        ``assessment`` split, and carries the ``completion_evidence`` the
        practical tasks have to produce. A per-module set would have to invent
        all three.

        The whole course's skills go into the prompt but only some come back.
        The corpus carries skills at course level only — there is no skill to
        module mapping anywhere — so the model is asked to pick the ones these
        two modules actually teach, and ``skills_assessed`` is what builds that
        map. Passing only the section's own topics instead would be cheaper and
        useless: the topics are syllabus phrasing ("data types", "functions")
        that no ``course_skills`` row is named after, so nothing downstream
        could join to the result.

        Withholding later modules' skills is the load-bearing instruction. Given
        the full list with no scoping rule, the model writes a Django question
        for module 1 — hard, correct, and unanswerable by a learner who has
        reached the end of module 2.
        """

        prompt = section_assessment_prompt(course, section, modules)

        response = self.client.responses.parse(
            model="gpt-5",
            input=prompt,
            text_format=SectionAssessment,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"Failed to parse assessment for {section['section_code']} from LLM response")

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
