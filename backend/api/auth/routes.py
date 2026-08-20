"""Authentication: password login, email verification, passwordless OTP login,
and password reset.

Three principles run through the email flows:

* **No enumeration.** The endpoints that take just an email (OTP request, forgot
  password, resend verification) always answer 200 with the same message whether
  or not the address is registered, and whether or not the mail actually sent.
  A different answer for a known vs unknown address is a membership oracle.
* **Secrets are hashed and single-use.** Links and codes are stored only as
  hashes, expire, and are consumed on first use — see AuthChallengeRepository.
* **Verification gates password login, not OTP login.** A new account must
  confirm its address before signing in with a password; signing in by OTP
  proves the address on the spot, so it both logs in and marks it verified.
"""

import secrets

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from api.auth.utils import generate_token, serialize_student
from config.database import db
from repositories.auth_challenge_repository import AuthChallengeRepository
from repositories.student_repository import StudentRepository
from services.email.mailer import (
    EmailSendError,
    send_login_otp,
    send_reset_email,
    send_verification_email,
)

auth_bp = Blueprint(
    "auth",
    __name__,
)

# Lifetimes. A verification link is generous (a day); a reset link is tight
# (an hour) because it changes a credential; an OTP is short (ten minutes)
# because it is only six digits.
VERIFY_TTL_SECONDS = 24 * 60 * 60
RESET_TTL_SECONDS = 60 * 60
OTP_TTL_SECONDS = 10 * 60

# Don't re-send the same kind of mail more than once every 30s per account.
RESEND_COOLDOWN_SECONDS = 30

# The generic answer for every enumeration-safe endpoint.
_GENERIC_EMAIL_MSG = "If that email is registered, we've sent it a message."


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_and_mail(student, purpose, ttl, mailer, secret):
    """Store a challenge and send its mail, respecting the resend cooldown.

    Swallows a send failure by design: the callers are enumeration-safe and must
    not reveal, via an error, that the address exists. The failure is logged.
    """
    since = AuthChallengeRepository.seconds_since_last(student.student_id, purpose)
    if since is not None and since < RESEND_COOLDOWN_SECONDS:
        return  # too soon; the previous mail is still the live one

    AuthChallengeRepository.issue(student.student_id, purpose, secret, ttl)
    try:
        mailer(student.email, secret)
    except EmailSendError:
        current_app.logger.warning("auth: %s email to student failed", purpose, exc_info=True)


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
        db.session.rollback()
        current_app.logger.warning("register: unique violation", exc_info=True)
        return jsonify({"error": "email or phone already registered"}), 409
    except Exception:
        db.session.rollback()
        current_app.logger.exception("register: failed to create student")
        return jsonify({"error": "failed to register"}), 500

    # New accounts start unverified and are NOT logged in: they must confirm the
    # address first. No token is returned here, unlike the pre-verification flow.
    _issue_and_mail(
        student, "verify_email", VERIFY_TTL_SECONDS, send_verification_email, _new_token()
    )

    return jsonify({
        "message": "Account created. Check your email for a link to verify your address.",
        "email": student.email,
        "requires_verification": True,
    }), 201


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

    # Correct credentials but an unconfirmed address: refuse, and say why with a
    # code the client can branch on to offer "resend". Existing accounts were
    # grandfathered to verified, so only new, unconfirmed signups hit this.
    if not student.email_verified:
        return jsonify({
            "error": "Please verify your email before signing in.",
            "code": "email_unverified",
        }), 403

    token = generate_token(student.student_id)
    return jsonify({"token": token, "student": serialize_student(student)}), 200


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not token:
        return jsonify({"error": "token is required"}), 400

    student_id = AuthChallengeRepository.consume_by_token("verify_email", token)
    if student_id is None:
        return jsonify({"error": "This verification link is invalid or has expired."}), 400

    StudentRepository.mark_email_verified(student_id)
    return jsonify({"message": "Email verified. You can now sign in."}), 200


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "email is required"}), 400

    student = StudentRepository.get_by_email(email)
    # Only send for a real, still-unverified account; answer the same either way.
    if student is not None and not student.email_verified:
        _issue_and_mail(
            student, "verify_email", VERIFY_TTL_SECONDS, send_verification_email, _new_token()
        )

    return jsonify({"message": _GENERIC_EMAIL_MSG}), 200


@auth_bp.route("/otp/request", methods=["POST"])
def otp_request():
    """Start a passwordless login: mail a 6-digit code to the address."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "email is required"}), 400

    student = StudentRepository.get_by_email(email)
    if student is not None:
        _issue_and_mail(student, "login_otp", OTP_TTL_SECONDS, send_login_otp, _new_otp())

    return jsonify({"message": _GENERIC_EMAIL_MSG}), 200


@auth_bp.route("/otp/verify", methods=["POST"])
def otp_verify():
    """Finish a passwordless login: a correct code logs in AND verifies the
    address (a delivered code proves the student controls the inbox)."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    code = data.get("code")

    if not email or not code:
        return jsonify({"error": "email and code are required"}), 400

    student = StudentRepository.get_by_email(email)
    if student is None or not AuthChallengeRepository.verify_otp(student.student_id, str(code)):
        return jsonify({"error": "That code is incorrect or has expired."}), 401

    if not student.email_verified:
        StudentRepository.mark_email_verified(student.student_id)
        student.email_verified = True

    token = generate_token(student.student_id)
    return jsonify({"token": token, "student": serialize_student(student)}), 200


@auth_bp.route("/password/forgot", methods=["POST"])
def password_forgot():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "email is required"}), 400

    student = StudentRepository.get_by_email(email)
    if student is not None:
        _issue_and_mail(
            student, "reset_password", RESET_TTL_SECONDS, send_reset_email, _new_token()
        )

    return jsonify({"message": _GENERIC_EMAIL_MSG}), 200


@auth_bp.route("/password/reset", methods=["POST"])
def password_reset():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_password = data.get("password")

    if not token or not new_password:
        return jsonify({"error": "token and password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    student_id = AuthChallengeRepository.consume_by_token("reset_password", token)
    if student_id is None:
        return jsonify({"error": "This reset link is invalid or has expired."}), 400

    StudentRepository.set_password(student_id, new_password)
    # A completed reset proves inbox control too, so clear any verification gate.
    StudentRepository.mark_email_verified(student_id)

    return jsonify({"message": "Password updated. You can now sign in."}), 200
