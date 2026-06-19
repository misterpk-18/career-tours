from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Skill:
    skill_id: UUID
    skill_name: str
    skill_category: str | None
    description: str | None
    created_at: datetime