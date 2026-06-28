from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Student:
    student_id: UUID
    full_name: str
    email: str
    phone: Optional[str]
    college_name: Optional[str]
    degree_name: Optional[str]
    branch_name: Optional[str]
    current_year_semester: Optional[str]
    graduation_year: Optional[int]
    preferred_job_location: Optional[str]
    target_role: Optional[str]
    career_interest: Optional[str]
    learning_hours_per_week: Optional[int]
    internship_preference: Optional[str]
    work_mode_preference: Optional[str]
    created_at: datetime
    updated_at: datetime