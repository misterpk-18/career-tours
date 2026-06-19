from pydantic import BaseModel
from typing import List

from services.llm.schemas.skill import Skill


class StudentProfile(BaseModel):
    technical_skills: List[Skill]
    soft_skills: List[Skill]
    domain_skills: List[Skill]
    summary: str