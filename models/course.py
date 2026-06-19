from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Course:
    course_id: UUID
    course_name: str
    description: str | None
    duration_hours: int | None
    level: str | None
    is_active: bool
    created_at: datetime