from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from api.auth.utils import generate_token, serialize_student
from repositories.student_repository import StudentRepository

auth_bp = Blueprint(
    "auth",
    __name__,
)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("full_name"):
        return jsonify({"error": "full_name is required"}), 400

    if not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    if not data.get("password"):
        return jsonify({"error": "password is required"}), 400

    if StudentRepository.get_by_email(data["email"]) is not None:
        return jsonify({"error": "email already registered"}), 409

    if data.get("phone") and StudentRepository.get_by_phone(data["phone"]) is not None:
        return jsonify({"error": "phone already registered"}), 409

    try:
        student = StudentRepository.create(data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": "failed to register", "detail": str(e)}), 500

    token = generate_token(student.student_id)
    return jsonify({"token": token, "student": serialize_student(student)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    if not data.get("password"):
        return jsonify({"error": "password is required"}), 400

    student = StudentRepository.get_by_email(data["email"])

    if student is None or not student.password_hash or not check_password_hash(
        student.password_hash, data["password"]
    ):
        return jsonify({"error": "invalid email or password"}), 401

    token = generate_token(student.student_id)
    return jsonify({"token": token, "student": serialize_student(student)}), 200
