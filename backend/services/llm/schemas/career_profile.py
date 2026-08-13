from typing import List, Literal

from pydantic import BaseModel


class CareerSkillWeight(BaseModel):
    """One skill a career needs, how central it is, and how strongly.

    ``skill_id`` is always an id the caller supplied in the candidate list — the
    model picks from a closed vocabulary rather than naming skills freely. That
    is what keeps ``career_skills.csv`` referentially valid against
    ``skills.csv`` and, downstream, keeps ``occupation_skills`` joinable to the
    same ``skills`` rows student extraction produces.
    """

    skill_id: str
    relation_type: Literal["essential", "optional"]
    weight: int


class CareerProfile(BaseModel):
    career_title: str
    skills: List[CareerSkillWeight]
