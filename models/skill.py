from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Skill:
    skill_id: UUID
    skill_name: str
    skill_category: Optional[str]
    description: Optional[str]
    created_at: datetime