from typing import List, Literal

from pydantic import BaseModel


class RubricCriterion(BaseModel):
    """One line of the grading rubric for a question that a human marks.

    The MCQs grade themselves; the scenarios and practical tasks do not, and a
    marks-only total ("this is worth 8") gives a grader nothing to be
    consistent about. Each criterion is one thing the grader looks for and the
    marks it is worth, and the criteria must sum to the question's own marks.
    """

    criterion: str
    marks: int


class ConceptMCQ(BaseModel):
    """One of the ten concept MCQs. Auto-gradable, four options, one correct.

    ``distractor_rationale`` is not decoration. A hard MCQ is hard because the
    wrong options are things a half-learned student actually believes, and
    making the model say why each distractor is tempting is what stops it
    shipping three obviously-absurd options around one correct answer.
    """

    question_number: int
    stem: str
    options: List[str]
    correct_option: Literal["A", "B", "C", "D"]
    explanation: str
    distractor_rationale: str
    skills_covered: List[str]
    modules_covered: List[int]
    marks: int


class ScenarioQuestion(BaseModel):
    """One of the four code/design scenarios. Written answer, graded on a rubric."""

    question_number: int
    scenario: str
    task: str
    expected_answer: str
    rubric: List[RubricCriterion]
    skills_covered: List[str]
    modules_covered: List[int]
    marks: int


class PracticalTask(BaseModel):
    """One of the two practical tasks — something the learner builds and submits.

    ``deliverable`` is what lands in the assessor's hands, and it should match
    the section's own ``completion_evidence`` rather than inventing a new
    artefact type.
    """

    task_number: int
    title: str
    brief: str
    deliverable: str
    acceptance_criteria: List[str]
    rubric: List[RubricCriterion]
    skills_covered: List[str]
    modules_covered: List[int]
    marks: int


class SectionAssessment(BaseModel):
    """The full question set for one section — i.e. one pair of modules.

    The shape is not a choice: every section in the corpus already declares
    ``assessment`` as "10 concept MCQ (30 marks) + 4 code/design scenarios (30)
    + 2 practical tasks (40)", and this is that promise made concrete.

    ``skills_assessed`` is the model's answer to which of the course's skills
    this pair of modules actually covers. The course corpus carries skills only
    at course level, so this field is also how the skill-to-section map gets
    built.
    """

    section_code: str
    skills_assessed: List[str]
    concept_mcqs: List[ConceptMCQ]
    scenario_questions: List[ScenarioQuestion]
    practical_tasks: List[PracticalTask]
