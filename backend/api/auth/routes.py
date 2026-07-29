from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from api.auth.utils import generate_token, serialize_student
from config.database import db
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
    except IntegrityError:
        # The checks above race: two concurrent signups with the same email or phone
        # both pass them and one loses at the unique index. Report it the same way.
        db.session.rollback()
        current_app.logger.warning("register: unique violation", exc_info=True)
        return jsonify({"error": "email or phone already registered"}), 409
    except Exception:
        # Roll back before returning, or this connection stays poisoned and every
        # later request served by the same worker fails on the aborted transaction.
        db.session.rollback()
        current_app.logger.exception("register: failed to create student")
        return jsonify({"error": "failed to register"}), 500

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
