from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Project:
    project_id: UUID
    student_id: UUID
    project_name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime