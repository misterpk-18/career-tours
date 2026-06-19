from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Resume:
    resume_id: UUID
    student_id: UUID
    file_url: str
    raw_text: str | None
    parsed_at: datetime | None
    created_at: datetime