from typing import List

from pydantic import BaseModel


class CourseSummary(BaseModel):
    """Per-course rationale, split into the three things the prompt asks for."""

    why_recommended: str
    how_it_helps: str
    key_skills: List[str]
