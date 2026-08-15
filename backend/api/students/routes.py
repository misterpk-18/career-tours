from uuid import UUID

from flask import Blueprint, g, jsonify, request

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


# Everything a student may change about themselves.
#
# `email` is absent on purpose: it is the login identity and the unique key, so
# changing it here would silently invalidate the session's own credentials and
# could collide with another account. `password` is absent for the same class of
# reason — a password change needs the current password, which is a different
# endpoint with a different check. `student_id`, `created_at` and `updated_at`
# are not the caller's to set.
EDITABLE_FIELDS = (
    "full_name",
    "phone",
    "college_name",
    "degree_name",
    "branch_name",
    "current_year_semester",
    "graduation_year",
    "preferred_job_location",
    "target_role",
    "career_interest",
    "learning_hours_per_week",
    "internship_preference",
    "work_mode_preference",
)

INTEGER_FIELDS = ("graduation_year", "learning_hours_per_week")

# Mirrors the CHECK constraints on `students`. Validating here turns a bad value
# into a 400 naming the field; without it Postgres raises a CheckViolation and
# the caller gets a 500 that says nothing about which field was wrong.
#
# Empty means "no answer" and is stored as NULL — the constraints permit NULL,
# since a CHECK passes unless it evaluates to false.
ENUM_FIELDS = {
    "work_mode_preference": ("office", "remote", "hybrid"),
    "internship_preference": ("free", "paid", "both"),
}


@students_bp.route("/<student_id>", methods=["PUT"])
@require_auth
def update_student(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    # Same 404-not-403 rule as the GET above: a 403 would confirm that the id
    # names a real account, which is the one bit an enumerating caller wants.
    if student_uuid != g.student_id:
        return jsonify({"error": "student not found"}), 404

    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "request body is required"}), 400

    # Allow-list rather than filtering out the dangerous keys: the repository's
    # update() merges whatever it is handed over the existing row, so an unknown
    # key here would be a way to write a column no one meant to expose.
    updates = {field: data[field] for field in EDITABLE_FIELDS if field in data}

    if not updates:
        return jsonify({"error": "no editable fields in request body"}), 400

    if "full_name" in updates and not str(updates["full_name"] or "").strip():
        return jsonify({"error": "full_name cannot be empty"}), 400

    for field in INTEGER_FIELDS:
        if field not in updates:
            continue

        value = updates[field]

        # An empty number input posts "", which means "cleared", not zero.
        if value is None or (isinstance(value, str) and not value.strip()):
            updates[field] = None
            continue

        try:
            updates[field] = int(value)
        except (TypeError, ValueError):
            return jsonify({"error": f"{field} must be a whole number"}), 400

    for field, allowed in ENUM_FIELDS.items():
        if field not in updates:
            continue

        value = updates[field]

        if value is None or (isinstance(value, str) and not value.strip()):
            updates[field] = None
            continue

        if value not in allowed:
            return (
                jsonify({"error": f"{field} must be one of: {', '.join(allowed)}"}),
                400,
            )

    student = StudentRepository.update(student_uuid, updates)

    if student is None:
        return jsonify({"error": "student not found"}), 404

    return jsonify(_serialize_student(student))
