from datetime import datetime, timedelta, timezone

import jwt

from config.database import JWT_EXPIRY_HOURS, SECRET_KEY

_ALGORITHM = "HS256"


def generate_token(student_id) -> str:
    """Create a signed JWT for the given student id."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(student_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[_ALGORITHM])


def serialize_student(student) -> dict:
    """Serialize a Student, never exposing the password hash."""
    return {
        "student_id": str(student.student_id),
        "full_name": student.full_name,
        "email": student.email,
        "phone": student.phone,
        "college_name": student.college_name,
        "degree_name": student.degree_name,
        "branch_name": student.branch_name,
        "current_year_semester": student.current_year_semester,
        "graduation_year": student.graduation_year,
        "preferred_job_location": student.preferred_job_location,
        "target_role": student.target_role,
        "career_interest": student.career_interest,
        "learning_hours_per_week": student.learning_hours_per_week,
        "internship_preference": student.internship_preference,
        "work_mode_preference": student.work_mode_preference,
        "created_at": student.created_at.isoformat(),
        "updated_at": student.updated_at.isoformat(),
    }
