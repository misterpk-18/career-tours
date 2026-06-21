from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Project:
    project_id: UUID
    student_id: UUID
    project_name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime