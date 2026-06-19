from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Student:
    student_id: UUID
    full_name: str
    email: str
    phone: str | None
    college_name: str | None
    degree_name: str | None
    branch_name: str | None
    current_year_semester: str | None
    graduation_year: int | None
    preferred_job_location: str | None
    target_role: str | None
    career_interest: str | None
    learning_hours_per_week: int | None
    internship_preference: str | None
    work_mode_preference: str | None
    created_at: datetime
    updated_at: datetime