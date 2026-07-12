from datetime import datetime, timedelta, timezone
from functools import wraps
from uuid import UUID

import jwt
from flask import g, jsonify, request

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


def require_auth(view):
    """Protect a route: require a valid Bearer JWT and expose the student id.

    On success, sets ``g.student_id`` (a UUID) for the wrapped view. On any
    failure, returns a 401 JSON error consistent with the app's error shape.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")

        if not header.startswith("Bearer "):
            return jsonify({"error": "authorization token required"}), 401

        token = header[len("Bearer "):].strip()

        try:
            claims = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.PyJWTError:
            return jsonify({"error": "invalid token"}), 401

        try:
            g.student_id = UUID(claims["sub"])
        except (KeyError, ValueError):
            return jsonify({"error": "invalid token"}), 401

        return view(*args, **kwargs)

    return wrapper


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
