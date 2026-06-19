from pydantic import BaseModel


class Skill(BaseModel):
    skill_name: str
    confidence: float
    proficiency: int
    source: str