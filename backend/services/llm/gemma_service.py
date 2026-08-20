"""Generate section assessments with Gemma 4 31B via the HuggingFace router.

Interface-compatible with ``OpenAIService.generate_section_assessment`` so the
generator script can swap backends with a flag, and deliberately reuses
``section_assessment_prompt`` so the two backends are asked for the same thing.

The difference that matters is structured output. ``responses.parse`` forces
gpt-5 to emit schema-conforming JSON and retries inside the API call; the router
exposes an OpenAI-compatible chat endpoint with no such guarantee, so the schema
has to be described in the prompt and enforced here on the way back. That means
three things this module does and the gpt-5 path does not need:

* **Fence stripping.** Asked for raw JSON, the model still wraps the document in
  a ```json fence perhaps half the time. Stripping it is cheaper than another
  round trip.
* **Pydantic validation as the parse step.** ``SectionAssessment`` is the same
  model gpt-5 is held to, so validating against it here buys identical field and
  type guarantees rather than a hand-rolled subset.
* **A repair round trip.** When the JSON is malformed or a field is missing, the
  error is handed back with the original response and one correction is
  requested. A fresh generation would throw away a mostly-good 4,000-token
  answer over a trailing comma.
"""

import json
import os
import re
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from services.llm.openai_service import section_assessment_prompt
from services.llm.schemas.section_assessment import (
    ConceptMCQ,
    PracticalTask,
    ScenarioQuestion,
    SectionAssessment,
)


class SkillSelection(BaseModel):
    """Just the skill scoping decision, made once before any questions exist."""

    skills_assessed: List[str]


class MCQBatch(BaseModel):
    concept_mcqs: List[ConceptMCQ]


class ScenarioBatch(BaseModel):
    scenario_questions: List[ScenarioQuestion]


class PracticalBatch(BaseModel):
    practical_tasks: List[PracticalTask]

load_dotenv()

MODEL = "google/gemma-4-31B-it"

ROUTER_BASE_URL = "https://router.huggingface.co/v1"

# Long enough for the whole document. The observed answer is ~4,600 tokens, but a
# section with several fenced code blocks runs longer, and a response truncated
# by the cap is unrecoverable — it fails to parse and the repair pass has nothing
# to work with.
MAX_TOKENS = 16000

# The model has no native schema enforcement, so the shape is described in the
# prompt. Kept terse: Gemma follows a compact contract more reliably than a long
# one, and every field here is re-checked against the Pydantic model anyway.
JSON_CONTRACT = """
Return ONE raw JSON object and nothing else. No prose before or after it, and do
not wrap the object itself in a code fence. Fenced blocks belong INSIDE the
string values, where the formatting rules above call for them.

{
  "section_code": "string",
  "skills_assessed": ["string"],
  "concept_mcqs": [
    {"question_number": 1, "stem": "string", "options": ["a","b","c","d"],
     "correct_option": "A", "explanation": "string", "distractor_rationale": "string",
     "skills_covered": ["string"], "modules_covered": [1], "marks": 3}
  ],
  "scenario_questions": [
    {"question_number": 1, "scenario": "string", "task": "string",
     "expected_answer": "string", "rubric": [{"criterion": "string", "marks": 4}],
     "skills_covered": ["string"], "modules_covered": [1], "marks": 8}
  ],
  "practical_tasks": [
    {"task_number": 1, "title": "string", "brief": "string", "deliverable": "string",
     "acceptance_criteria": ["string"], "rubric": [{"criterion": "string", "marks": 8}],
     "skills_covered": ["string"], "modules_covered": [1], "marks": 20}
  ]
}

Exactly 10 concept_mcqs, 4 scenario_questions, 2 practical_tasks. Every field
above is required on every item.
"""

SYSTEM = (
    "You are an assessment author. You reply with one raw JSON object and no other text. "
    "You follow the requested schema exactly and you do not soften the difficulty bar you are given."
)

# Per-batch shapes. The batched path cannot reuse JSON_CONTRACT because each call
# returns only one of the three lists, and handing over the whole document shape
# invites the model to fill in the other two. Every field is spelled out because
# omitting them is exactly what went wrong when the batch prompts carried no
# shape at all — Gemma invented its own field names and dropped ``title``.
MCQ_SHAPE = """
{"concept_mcqs": [
  {"question_number": 1, "stem": "string", "options": ["a","b","c","d"],
   "correct_option": "A", "explanation": "string", "distractor_rationale": "string",
   "skills_covered": ["string"], "modules_covered": [1], "marks": 3}
]}
"""

SCENARIO_SHAPE = """
{"scenario_questions": [
  {"question_number": 1, "scenario": "string", "task": "string",
   "expected_answer": "string",
   "rubric": [{"criterion": "string", "marks": 2}],
   "skills_covered": ["string"], "modules_covered": [1], "marks": 8}
]}
"""

PRACTICAL_SHAPE = """
{"practical_tasks": [
  {"task_number": 1, "title": "string", "brief": "string", "deliverable": "string",
   "acceptance_criteria": ["string"],
   "rubric": [{"criterion": "string", "marks": 5}],
   "skills_covered": ["string"], "modules_covered": [1], "marks": 20}
]}
"""


def strip_document_fence(text: str) -> str:
    """Unwrap a ```json fence around the whole document, if there is one.

    Only touches a fence at the very start of the response. A fence that opens
    mid-string belongs to a code block inside a question and must survive.
    """
    body = text.strip()

    if not body.startswith("```"):
        return body

    body = re.sub(r"^```[A-Za-z0-9]*[ \t]*\r?\n?", "", body)
    return re.sub(r"\r?\n?```\s*$", "", body.strip())


class GemmaService:
    """Same one-call-per-section contract as OpenAIService, different backend."""

    def __init__(self, model: str = MODEL, provider: str | None = None, mcq_batch: int = 5):
        token = os.getenv("HF_TOKEN")
        if not token:
            raise RuntimeError("HF_TOKEN is not set; the router needs it to authenticate")

        # A provider suffix pins which host serves the request. Left off, the
        # router picks, and consecutive calls can land on hosts with different
        # speeds and different tokenizer quirks.
        self.model = f"{model}:{provider}" if provider else model
        self.mcq_batch = mcq_batch
        self.client = OpenAI(base_url=ROUTER_BASE_URL, api_key=token)

    def _complete(self, messages: list) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    def generate_section_assessment(
        self,
        course: Dict,
        section: Dict,
        modules: List[Dict],
    ) -> SectionAssessment:
        if self.mcq_batch < 10:
            return self.generate_section_assessment_batched(
                course, section, modules, mcq_batch=self.mcq_batch
            )

        prompt = f"{section_assessment_prompt(course, section, modules)}\n{JSON_CONTRACT}"

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ]

        raw = self._complete(messages)

        try:
            return SectionAssessment.model_validate_json(strip_document_fence(raw))
        except (ValidationError, json.JSONDecodeError) as first_error:
            # One repair attempt, with the model shown its own output and the
            # specific complaint. Cheaper and more likely to succeed than
            # regenerating from scratch.
            messages += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"That response could not be parsed against the schema:\n\n{first_error}\n\n"
                        "Return the corrected, complete JSON object. Raw JSON only, no prose, "
                        "no fence around the object. Keep the question content you already wrote — "
                        "fix only the structure."
                    ),
                },
            ]

            repaired = self._complete(messages)

            try:
                return SectionAssessment.model_validate_json(strip_document_fence(repaired))
            except (ValidationError, json.JSONDecodeError) as second_error:
                raise RuntimeError(
                    f"{section['section_code']}: unparseable after repair — {second_error}"
                ) from second_error

    # ------------------------------------------------------------------ batched

    def _batch(self, context: str, instruction: str, model_cls, already: list) -> BaseModel:
        """One batch call, parsed into ``model_cls``, with one repair attempt.

        ``already`` is the stems written so far for this section. Passing them is
        what stops batch two rewriting batch one's question in different words —
        each call is stateless, so without this the model has no way to know what
        it has already covered.
        """
        avoid = ""
        if already:
            listed = "\n".join(f"- {re.sub(r'\\s+', ' ', s)[:160]}" for s in already)
            avoid = (
                "\nThese questions are ALREADY written for this section. Do not repeat any of "
                f"them, and do not ask the same thing in different words:\n{listed}\n"
            )

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{context}\n{avoid}\n{instruction}"},
        ]

        raw = self._complete(messages)

        try:
            return model_cls.model_validate_json(strip_document_fence(raw))
        except (ValidationError, json.JSONDecodeError) as error:
            messages += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"That could not be parsed:\n\n{error}\n\nReturn the corrected complete "
                        "JSON object. Raw JSON only, no prose, no fence around the object. Keep "
                        "the question content — fix only the structure."
                    ),
                },
            ]
            for _ in range(2):
                try:
                    return model_cls.model_validate_json(strip_document_fence(self._complete(messages)))
                except (ValidationError, json.JSONDecodeError) as retry_error:
                    error = retry_error
            raise RuntimeError(f"batch unparseable after two repairs — {error}")

    def generate_section_assessment_batched(
        self,
        course: Dict,
        section: Dict,
        modules: List[Dict],
        mcq_batch: int = 5,
    ) -> SectionAssessment:
        """The same section, assembled from several small calls instead of one.

        Gemma returned all sixteen questions in ~4,600 tokens, and it showed:
        six of the ten MCQs were glossary questions of the exact form the brief
        bans. Asking for five at a time gives each question room and removes the
        incentive to pad the count, which is where the shallow ones came from.

        The cost is call volume — five calls per section rather than one, so 800
        for the corpus instead of 160 — and the need to serialize within a
        section so later batches can be told what the earlier ones asked.
        Sections still run concurrently, so wall clock scales with workers.

        ``skills_assessed`` is chosen first, in its own cheap call, and then held
        fixed for every batch. Deciding it per batch would let each one scope the
        section differently, and the union of four disagreeing answers is not a
        skill map.
        """
        code = section["section_code"]
        context = section_assessment_prompt(course, section, modules)

        selection = self._batch(
            context,
            "Do ONLY the skill scoping step. Do not write any questions. Return raw JSON: "
            '{"skills_assessed": ["exact skill name", "..."]}',
            SkillSelection,
            already=[],
        )
        skills = selection.skills_assessed

        fixed = (
            f"\nUse EXACTLY these skills for this section, and draw every skills_covered "
            f"from this list only: {', '.join(skills)}\n"
        )

        mcqs: List[ConceptMCQ] = []
        stems: List[str] = []

        # Two batches of five for ten MCQs; the loop handles any batch size that
        # divides ten, so mcq_batch=10 collapses back to a single call.
        for start in range(0, 10, mcq_batch):
            count = min(mcq_batch, 10 - start)
            batch = self._batch(
                context + fixed,
                f"Produce ONLY the next {count} concept MCQs, numbered "
                f"{start + 1} to {start + count}, each worth 3 marks. Every one must clear "
                "the difficulty bar above — none of the banned glossary forms. Return raw "
                f"JSON in EXACTLY this shape, with every field present on every item:\n{MCQ_SHAPE}",
                MCQBatch,
                already=stems,
            )
            for i, mcq in enumerate(batch.concept_mcqs[:count]):
                mcq.question_number = start + i + 1
                mcq.marks = 3
                mcqs.append(mcq)
                stems.append(mcq.stem)

        scenarios = self._batch(
            context + fixed,
            "Produce ONLY the 4 scenario questions. Marks must be 7 or 8 each and sum to "
            "exactly 30. At least 4 rubric criteria each, summing to that question's own marks. "
            f"Return raw JSON in EXACTLY this shape, every field present:\n{SCENARIO_SHAPE}",
            ScenarioBatch,
            already=stems,
        )

        practicals = self._batch(
            context + fixed,
            "Produce ONLY the 2 practical tasks, 20 marks each. At least 4 rubric criteria "
            "each, summing to exactly 20. Both need a short 'title'. Return raw JSON in EXACTLY "
            f"this shape, every field present:\n{PRACTICAL_SHAPE}",
            PracticalBatch,
            already=stems + [s.scenario for s in scenarios.scenario_questions],
        )

        return SectionAssessment(
            section_code=code,
            skills_assessed=skills,
            concept_mcqs=mcqs,
            scenario_questions=scenarios.scenario_questions,
            practical_tasks=practicals.practical_tasks,
        )
