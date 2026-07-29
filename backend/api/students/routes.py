from uuid import UUID

from flask import Blueprint, g, jsonify

from api.auth.utils import require_auth
from repositories.student_repository import StudentRepository

students_bp = Blueprint(
    "students",
    __name__,
)


def _serialize_student(student) -> dict:
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


# NOTE: `POST /api/students` used to live here. It was an unauthenticated second
# way to create an account that skipped the password requirement enforced by
# `POST /api/auth/register`, so a student could be created with no password at
# all and no way to sign in. Registration has exactly one entry point now:
# api/auth/routes.py:register.


@students_bp.route("/<student_id>", methods=["GET"])
@require_auth
def get_student(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    # This response is the student's full profile — name, email, phone, college.
    # Unauthenticated it was a PII endpoint keyed on a guessable id.
    if student_uuid != g.student_id:
        return jsonify({"error": "student not found"}), 404

    student = StudentRepository.get_by_id(student_uuid)

    if student is None:
        return jsonify({"error": "student not found"}), 404

    return jsonify(_serialize_student(student))
