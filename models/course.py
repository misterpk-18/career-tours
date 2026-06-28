from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Course:
    course_id: UUID
    course_name: str
    description: Optional[str]
    duration_hours: Optional[int]
    level: Optional[str]
    is_active: bool
    created_at: datetime