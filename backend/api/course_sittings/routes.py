"""The project-independent course assessment track.

The same sitting flow as ``api/projects`` — start, get the paper, answer,
pause, resume, submit, plus per-section progress — but a sitting is owned by
the authenticated STUDENT rather than a project. Ownership comes from the token
(``g.student_id``) on every route, never from the URL, so there is no
cross-account reach even without a project guard.

The heavy lifting (the seeded shuffle in ``present``, the clock arithmetic and
grading in ``CourseSittingRepository``, the serializers) is shared with the
project track; only the owner and the tables differ.
"""

from uuid import UUID

from flask import Blueprint, g, jsonify, request

from api.auth.utils import require_auth
from api.serializers import (
    serialize_attempt,
    serialize_section_state,
    serialize_sitting,
)
from config.database import db
from repositories.course_achievement_repository import CourseAchievementRepository
from repositories.course_sitting_repository import (
    DEFAULT_TIME_LIMIT_SECONDS,
    CourseSittingRepository,
)
from services.assessment.presentation import present

course_sittings_bp = Blueprint("course_sittings", __name__)

MAX_ANSWERS_PER_REQUEST = 50


def _clock(sitting: dict):
    """Resolve the clock, auto-submitting the sitting if time ran out."""
    remaining = CourseSittingRepository.clock(sitting)

    if sitting["status"] == "in_progress" and remaining <= 0:
        expired = CourseSittingRepository.submit(sitting["sitting_id"])
        if expired:
            db.session.commit()
            return expired, 0

    return sitting, remaining


def _sitting_or_error(sitting_id: str):
    """Load a sitting owned by the current student, with its clock resolved."""
    try:
        sitting_uuid = UUID(sitting_id)
    except ValueError:
        return None, 0, (jsonify({"error": "sitting_id must be a valid UUID"}), 400)

    sitting = CourseSittingRepository.get(sitting_uuid, g.student_id)
    if sitting is None:
        return None, 0, (jsonify({"error": "sitting not found"}), 404)

    sitting, remaining = _clock(sitting)
    return sitting, remaining, None


@course_sittings_bp.route(
    "/course-assessments/<course_id>/sections/<section_code>/sittings",
    methods=["POST"],
)
@require_auth
def start_sitting(course_id: str, section_code: str):
    """Start a course-track sitting, or hand back the one already open.

    Same contract as the project track: a graded run happens once, POSTing an
    open graded sitting resumes it, and ``restart: true`` discards and starts
    fresh. ``course_id`` is carried for symmetry and client navigation; the
    sitting itself is keyed on the student and the section.
    """
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "graded")

    if mode not in ("graded", "practice"):
        return jsonify({"error": "mode must be 'graded' or 'practice'"}), 400

    questions = CourseSittingRepository.mcqs_for_section(section_code)
    if not questions:
        return jsonify({"error": f"section {section_code} has no questions"}), 404

    graded = CourseSittingRepository.find(g.student_id, section_code, "graded")

    if mode == "graded":
        if graded and graded["status"] == "submitted":
            return jsonify({
                "error": "this section has already been submitted; start a practice sitting instead",
                "sitting": serialize_sitting(graded, 0),
            }), 409

        if graded and not data.get("restart"):
            sitting, remaining = _clock(graded)
            if sitting["status"] == "submitted":
                return jsonify({
                    "error": "the previous attempt ran out of time and was submitted",
                    "sitting": serialize_sitting(sitting, 0),
                }), 409
            return jsonify({"sitting": serialize_sitting(sitting, remaining),
                            "resumed": True}), 200

        if graded:
            CourseSittingRepository.discard(graded["sitting_id"])
    else:
        open_practice = CourseSittingRepository.find(
            g.student_id, section_code, "practice", open_only=True
        )
        if open_practice and not data.get("restart"):
            sitting, remaining = _clock(open_practice)
            if sitting["status"] != "submitted":
                return jsonify({"sitting": serialize_sitting(sitting, remaining),
                                "resumed": True}), 200
        elif open_practice:
            CourseSittingRepository.discard(open_practice["sitting_id"])

    try:
        sitting = CourseSittingRepository.start(
            g.student_id, section_code, mode,
            DEFAULT_TIME_LIMIT_SECONDS,
            CourseSittingRepository.marks_available(section_code),
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "failed to start the sitting"}), 500

    return jsonify({
        "sitting": serialize_sitting(sitting, sitting["seconds_remaining"]),
        "resumed": False,
    }), 201


@course_sittings_bp.route("/course-sittings/<sitting_id>", methods=["GET"])
@require_auth
def get_sitting(sitting_id: str):
    """The paper as this sitting shows it, plus whatever has been answered."""
    sitting, remaining, error = _sitting_or_error(sitting_id)
    if error:
        return error

    questions = CourseSittingRepository.mcqs_for_section(sitting["section_code"])
    by_id = {q["question_id"]: q for q in questions}
    presented = present(sitting["sitting_id"], questions)

    answers = {a["question_id"]: a for a in CourseSittingRepository.answers_for(
        sitting["sitting_id"]
    )}

    reveal = sitting["mode"] == "practice" or sitting["status"] == "submitted"

    paper = []
    for item in presented:
        answer = answers.get(item["question_id"])
        entry = {
            "position": item["position"],
            "question_id": str(item["question_id"]),
            "stem": item["stem"],
            "options": item["options"],
            "marks": item["marks"],
            "answered_option": answer["presented_option"] if answer else None,
        }

        if reveal and answer:
            source = by_id[item["question_id"]]
            correct_display = next(
                shown for shown, stored in item["answer_map"].items()
                if stored == source["correct_option"]
            )
            entry.update({
                "is_correct": answer["is_correct"],
                "correct_option": correct_display,
                "explanation": source["explanation"],
                "distractor_rationale": source["distractor_rationale"],
            })

        paper.append(entry)

    return jsonify({
        "sitting": serialize_sitting(sitting, remaining),
        "questions": paper,
    })


@course_sittings_bp.route("/course-sittings/<sitting_id>/answers", methods=["POST"])
@require_auth
def save_answers(sitting_id: str):
    """Record answers. Accepts a batch; revising an answer overwrites it."""
    sitting, remaining, error = _sitting_or_error(sitting_id)
    if error:
        return error

    if sitting["status"] == "submitted":
        return jsonify({"error": "this sitting has been submitted and cannot be changed"}), 409

    if sitting["status"] == "paused":
        return jsonify({"error": "this sitting is paused; resume it before answering"}), 409

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "request body is required"}), 400

    answers = data.get("answers")
    if not isinstance(answers, list) or not answers:
        return jsonify({"error": "answers must be a non-empty list"}), 400

    if len(answers) > MAX_ANSWERS_PER_REQUEST:
        return jsonify({
            "error": f"at most {MAX_ANSWERS_PER_REQUEST} answers per request, got {len(answers)}"
        }), 400

    questions = CourseSittingRepository.mcq_keys_for_section(sitting["section_code"])
    presented = {item["question_id"]: item for item in present(sitting["sitting_id"], questions)}
    by_id = {q["question_id"]: q for q in questions}

    resolved = []
    seen = set()

    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return jsonify({"error": f"answers[{index}] must be an object"}), 400

        try:
            question_uuid = UUID(str(answer.get("question_id")))
        except (ValueError, TypeError):
            return jsonify({"error": f"answers[{index}].question_id must be a valid UUID"}), 400

        if question_uuid in seen:
            return jsonify({"error": f"answers[{index}] repeats question_id {question_uuid}"}), 400
        seen.add(question_uuid)

        if question_uuid not in presented:
            return jsonify({
                "error": f"answers[{index}]: question {question_uuid} is not in this sitting"
            }), 404

        chosen = answer.get("selected_option")
        if chosen not in ("A", "B", "C", "D"):
            return jsonify({
                "error": f"answers[{index}].selected_option must be one of A, B, C, D"
            }), 400

        resolved.append((by_id[question_uuid], chosen,
                         presented[question_uuid]["answer_map"][chosen]))

    try:
        recorded = [
            CourseSittingRepository.save_answer(sitting, question, chosen, stored)
            for question, chosen, stored in resolved
        ]
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "failed to save answers"}), 500

    payload = {
        "sitting": serialize_sitting(sitting, remaining),
        "saved": len(recorded),
    }

    if sitting["mode"] == "practice":
        prose = {
            q["question_id"]: q
            for q in CourseSittingRepository.mcqs_for_section(sitting["section_code"])
        }
        results = []
        for attempt, (question, _, _) in zip(recorded, resolved):
            item = presented[question["question_id"]]
            correct_display = next(
                shown for shown, stored in item["answer_map"].items()
                if stored == question["correct_option"]
            )
            source = prose[question["question_id"]]
            results.append({
                **serialize_attempt(attempt),
                "correct_option": correct_display,
                "explanation": source["explanation"],
                "distractor_rationale": source["distractor_rationale"],
            })
        payload["results"] = results

    return jsonify(payload), 200


@course_sittings_bp.route("/course-sittings/<sitting_id>/pause", methods=["POST"])
@require_auth
def pause_sitting(sitting_id: str):
    """Stop the clock. The time left is banked on the row."""
    sitting, _, error = _sitting_or_error(sitting_id)
    if error:
        return error

    paused = CourseSittingRepository.pause(sitting["sitting_id"])
    if paused is None:
        return jsonify({
            "error": f"only a sitting in progress can be paused; this one is {sitting['status']}"
        }), 409

    db.session.commit()
    return jsonify({"sitting": serialize_sitting(paused, paused["seconds_remaining"])})


@course_sittings_bp.route("/course-sittings/<sitting_id>/resume", methods=["POST"])
@require_auth
def resume_sitting(sitting_id: str):
    """Restart the clock on a paused sitting."""
    sitting, _, error = _sitting_or_error(sitting_id)
    if error:
        return error

    resumed = CourseSittingRepository.resume(sitting["sitting_id"])
    if resumed is None:
        if sitting["status"] == "paused" and sitting["seconds_remaining"] <= 0:
            return jsonify({"error": "no time remains on this sitting; submit it"}), 409
        return jsonify({
            "error": f"only a paused sitting can be resumed; this one is {sitting['status']}"
        }), 409

    db.session.commit()
    return jsonify({
        "sitting": serialize_sitting(resumed, CourseSittingRepository.clock(resumed)),
    })


@course_sittings_bp.route("/course-sittings/<sitting_id>/submit", methods=["POST"])
@require_auth
def submit_sitting(sitting_id: str):
    """Close the sitting and lock its score."""
    sitting, _, error = _sitting_or_error(sitting_id)
    if error:
        return error

    if sitting["status"] == "submitted":
        return jsonify({
            "error": "this sitting has already been submitted",
            "sitting": serialize_sitting(sitting, 0),
        }), 409

    submitted = CourseSittingRepository.submit(sitting["sitting_id"])
    if submitted is None:
        return jsonify({"error": "failed to submit the sitting"}), 500

    db.session.commit()

    answers = CourseSittingRepository.answers_for(submitted["sitting_id"])

    return jsonify({
        "sitting": serialize_sitting(submitted, 0),
        "answered": len(answers),
        "total_questions": len(
            CourseSittingRepository.mcqs_for_section(submitted["section_code"])
        ),
    })


@course_sittings_bp.route("/course-assessments/<course_id>/progress", methods=["GET"])
@require_auth
def get_progress(course_id: str):
    """Per-section state for this course, for the authenticated student.

    ``course_id`` is a UUID in the URL, but sittings are keyed by section code,
    whose eight-character prefix is the course code. The client already knows
    the course's sections from the catalogue, so it passes the course code it
    wants scoped to via the ``course_code`` query parameter; absent, nothing is
    filtered and the student's whole course-track history comes back.
    """
    course_code = request.args.get("course_code")
    if not course_code:
        return jsonify({"error": "course_code query parameter is required"}), 400

    return jsonify([
        serialize_section_state(row)
        for row in CourseSittingRepository.section_overview(g.student_id, course_code)
    ])


@course_sittings_bp.route("/course-achievements", methods=["GET"])
@require_auth
def get_course_achievements():
    """XP, level, streak and badges for the COURSE track, this student's own.

    A separate pool from ``/api/achievements`` (the project track) by design —
    derived only from course-track sittings, so the two never move each other.
    """
    return jsonify(CourseAchievementRepository.profile(g.student_id))
