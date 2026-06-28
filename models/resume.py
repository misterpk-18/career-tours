from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Resume:
    resume_id: UUID
    student_id: UUID
    project_id: UUID
    file_url: str
    raw_text: Optional[str]
    parsed_at: Optional[datetime]
    created_at: datetime