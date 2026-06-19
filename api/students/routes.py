from uuid import UUID

from flask import Blueprint, jsonify, request

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


@students_bp.route("", methods=["POST"])
def create_student():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("full_name"):
        return jsonify({"error": "full_name is required"}), 400

    if not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    try:
        student = StudentRepository.create(data)
    except Exception:
        return jsonify({"error": "failed to create student"}), 500

    return jsonify(_serialize_student(student)), 201


@students_bp.route("/<student_id>", methods=["GET"])
def get_student(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    student = StudentRepository.get_by_id(student_uuid)

    if student is None:
        return jsonify({"error": "student not found"}), 404

    return jsonify(_serialize_student(student))
