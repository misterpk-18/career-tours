from uuid import UUID

from flask import Blueprint, g, jsonify, request

from api.auth.utils import require_auth
from api.guards import owned_project
from api.serializers import (
    serialize_attempt,
    serialize_job,
    serialize_project_skill,
    serialize_section_state,
    serialize_sitting,
)
from config.database import db
from repositories.job_repository import JobRepository
from repositories.project_repository import ProjectRepository
from repositories.project_skill_repository import ProjectSkillRepository
from repositories.section_sitting_repository import (
    DEFAULT_TIME_LIMIT_SECONDS,
    SectionSittingRepository,
)
from services.assessment.presentation import present


projects_bp = Blueprint(
    "projects",
    __name__,
)


def _serialize_project(project) -> dict:
    return {
        "project_id": str(project.project_id),
        "student_id": str(project.student_id),
        "project_name": project.project_name,
        "description": project.description,
        "status": project.status,
        "resume_id": str(project.resume_id) if project.resume_id else None,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


@projects_bp.route("", methods=["POST"])
@require_auth
def create_project():
    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    if not data.get("project_name"):
        return jsonify({"error": "project_name is required"}), 400

    # The owner comes from the token, never the body. Trusting a body-supplied
    # student_id would let any caller file a project under someone else's account.
    project_data = {**data, "student_id": g.student_id}

    try:
        project = ProjectRepository.create(project_data)
    except Exception:
        return jsonify({"error": "failed to create project"}), 500

    return jsonify(_serialize_project(project)), 201


@projects_bp.route("/<project_id>", methods=["GET"])
@require_auth
def get_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    return jsonify(_serialize_project(project))


@projects_bp.route("/<project_id>/skills", methods=["GET"])
@require_auth
def get_project_skills(project_id: str):
    """The stored skills for a project, or an empty list if none were extracted.

    The page needs this to decide which step of the pipeline the project is on.
    Without it the client had no way to ask, so it cached the extraction response
    in localStorage and guessed — which read as "no skills extracted" in any
    other browser.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    skills = ProjectSkillRepository.get_by_project_id(project.project_id)

    return jsonify([serialize_project_skill(skill) for skill in skills])


@projects_bp.route("/<project_id>/jobs/latest", methods=["GET"])
@require_auth
def get_latest_project_job(project_id: str):
    """The most recent job of a given type for this project, or null.

    This is how a page re-attaches to a run already in progress after a reload,
    a navigation, or a switch to another device — without the client having
    stored a job id anywhere. The same reasoning as `get_project_skills` above:
    if the server cannot be asked, the client caches and guesses, and the guess
    is wrong in every other browser.
    """
    job_type = request.args.get("type")

    if not job_type:
        return jsonify({"error": "type query parameter is required"}), 400

    project, error = owned_project(project_id)
    if error:
        return error

    # Same reasoning as GET /api/jobs/<id>: resolve dead workers before reading,
    # so a page reloaded after a deploy sees `failed` rather than a job stuck
    # `running` forever.
    JobRepository.reap_stale()

    job = JobRepository.get_latest(project.project_id, job_type)

    return jsonify({"job": serialize_job(job) if job else None})


@projects_bp.route("/student/<student_id>", methods=["GET"])
@require_auth
def get_student_projects(student_id: str):
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        return jsonify({"error": "student_id must be a valid UUID"}), 400

    if student_uuid != g.student_id:
        return jsonify({"error": "student not found"}), 404

    projects = ProjectRepository.get_by_student_id(student_uuid)

    return jsonify([_serialize_project(project) for project in projects])


@projects_bp.route("/<project_id>", methods=["PUT"])
@require_auth
def update_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    data = request.get_json()

    if not data:
        return jsonify({"error": "request body is required"}), 400

    # Ownership is not editable: a PUT carrying student_id must not reassign the
    # project, and project_id in the body must not redirect the update.
    payload = {key: value for key, value in data.items() if key not in ("student_id", "project_id")}

    updated = ProjectRepository.update(project.project_id, payload)

    if updated is None:
        return jsonify({"error": "project not found"}), 404

    return jsonify(_serialize_project(updated))


@projects_bp.route("/<project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id: str):
    project, error = owned_project(project_id)
    if error:
        return error

    deleted = ProjectRepository.delete(project.project_id)

    if not deleted:
        return jsonify({"error": "project not found"}), 404

    return jsonify({"message": "project deleted successfully"})


# ---------------------------------------------------------------- sittings
#
# These live on the projects blueprint because every route is scoped to a
# project the caller must own, and `owned_project` is what proves that. A
# separate blueprint would have to re-derive the same ownership check, and a
# second implementation of an access check is a second thing to get wrong.
#
# Only MCQs are offered. The scenarios and practical tasks stay in the corpus
# and are worth 70 of a section's 100 marks, but they need a human to mark and
# this system has no assessor role, so a sitting is scored out of the MCQ total.

MAX_ANSWERS_PER_REQUEST = 50


def _clock(sitting: dict):
    """A sitting with its clock resolved, auto-submitting it if time ran out.

    Called at the top of every route that touches a sitting. A timed sitting can
    expire while nobody is looking at it — the student closed the tab, the laptop
    slept — and nothing else would notice. Enforcing it lazily on read means the
    expiry is applied the moment anyone asks, without a sweeper process.

    Returns ``(sitting, seconds_remaining)``.
    """
    remaining = SectionSittingRepository.clock(sitting)

    if sitting["status"] == "in_progress" and remaining <= 0:
        expired = SectionSittingRepository.submit(sitting["sitting_id"])
        if expired:
            db.session.commit()
            return expired, 0

    return sitting, remaining


def _sitting_or_error(project, sitting_id: str):
    try:
        sitting_uuid = UUID(sitting_id)
    except ValueError:
        return None, 0, (jsonify({"error": "sitting_id must be a valid UUID"}), 400)

    sitting = SectionSittingRepository.get(sitting_uuid, project.project_id)
    if sitting is None:
        return None, 0, (jsonify({"error": "sitting not found"}), 404)

    sitting, remaining = _clock(sitting)
    return sitting, remaining, None


@projects_bp.route("/<project_id>/sections/<section_code>/sittings", methods=["POST"])
@require_auth
def start_sitting(project_id: str, section_code: str):
    """Start a sitting, or hand back the one already open.

    The graded run happens once. If it is already submitted the only thing left
    is practice, and this says so rather than silently starting a practice run
    the caller did not ask for — the button the student pressed and the thing
    that happens have to match.

    If a graded sitting is open, POSTing again returns it untouched: that is
    "continue previous attempt". Passing `"restart": true` deletes it and starts
    fresh, which is "start new" and is destructive, which is why it needs saying
    explicitly. The delete and the insert share one transaction so a section
    cannot end up with neither.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "graded")

    if mode not in ("graded", "practice"):
        return jsonify({"error": "mode must be 'graded' or 'practice'"}), 400

    questions = SectionSittingRepository.mcqs_for_section(section_code)
    if not questions:
        return jsonify({"error": f"section {section_code} has no questions"}), 404

    graded = SectionSittingRepository.find(project.project_id, section_code, "graded")

    if mode == "graded":
        if graded and graded["status"] == "submitted":
            return jsonify({
                "error": "this section has already been submitted; start a practice sitting instead",
                "sitting": serialize_sitting(graded, 0),
            }), 409

        if graded and not data.get("restart"):
            sitting, remaining = _clock(graded)
            # An expired sitting is submitted now, so a fresh graded run is no
            # longer possible — say that rather than returning it as resumable.
            if sitting["status"] == "submitted":
                return jsonify({
                    "error": "the previous attempt ran out of time and was submitted",
                    "sitting": serialize_sitting(sitting, 0),
                }), 409
            return jsonify({"sitting": serialize_sitting(sitting, remaining),
                            "resumed": True}), 200

        if graded:
            SectionSittingRepository.discard(graded["sitting_id"])
    else:
        open_practice = SectionSittingRepository.find(
            project.project_id, section_code, "practice", open_only=True
        )
        if open_practice and not data.get("restart"):
            sitting, remaining = _clock(open_practice)
            if sitting["status"] != "submitted":
                return jsonify({"sitting": serialize_sitting(sitting, remaining),
                                "resumed": True}), 200
        elif open_practice:
            SectionSittingRepository.discard(open_practice["sitting_id"])

    try:
        sitting = SectionSittingRepository.start(
            project.project_id, section_code, mode,
            DEFAULT_TIME_LIMIT_SECONDS,
            SectionSittingRepository.marks_available(section_code),
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "failed to start the sitting"}), 500

    return jsonify({
        "sitting": serialize_sitting(sitting, sitting["seconds_remaining"]),
        "resumed": False,
    }), 201


@projects_bp.route("/<project_id>/sittings/<sitting_id>", methods=["GET"])
@require_auth
def get_sitting(project_id: str, sitting_id: str):
    """The paper as this sitting shows it, plus whatever has been answered.

    The layout is recomputed from the sitting id rather than stored, so a reload,
    a different device and a later review all produce the identical arrangement.
    `answer_map` is deliberately NOT sent: it would tell the client which option
    is the corpus answer, and for an MCQ that is the answer itself.

    A submitted sitting includes the explanations, because at that point there
    is nothing left to protect and the explanation is the whole value.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    sitting, remaining, error = _sitting_or_error(project, sitting_id)
    if error:
        return error

    questions = SectionSittingRepository.mcqs_for_section(sitting["section_code"])
    by_id = {q["question_id"]: q for q in questions}
    presented = present(sitting["sitting_id"], questions)

    answers = {a["question_id"]: a for a in SectionSittingRepository.answers_for(
        sitting["sitting_id"]
    )}

    # Practice reveals as you go; a graded sitting reveals nothing until it is
    # submitted. Either way the reveal is assembled here rather than trusted to
    # the client, which would otherwise need the key in order to show it.
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


@projects_bp.route("/<project_id>/sittings/<sitting_id>/answers", methods=["POST"])
@require_auth
def save_answers(project_id: str, sitting_id: str):
    """Record answers. Accepts a batch, and revising an answer overwrites it.

    The letters arriving here are the letters the student saw, which are not the
    corpus letters — the options were shuffled. The mapping back is recomputed
    from the sitting id, never taken from the request: a client that could send
    its own mapping could mark itself correct.

    A batch is validated in full before anything is written, and commits once,
    so a paper submitted in one request cannot land half-saved.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    sitting, remaining, error = _sitting_or_error(project, sitting_id)
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

    # The key projection, not the full rows: this path only needs to rebuild the
    # shuffle and compare the answer, and the prose is several KB per question
    # fetched cross-region for nothing.
    questions = SectionSittingRepository.mcq_keys_for_section(sitting["section_code"])
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
            SectionSittingRepository.save_answer(sitting, question, chosen, stored)
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

    # Practice tells you immediately; a graded sitting tells you nothing until
    # submit. Sending is_correct here for a graded run would leak the key one
    # question at a time.
    #
    # The reveal has to carry the explanation as well as the verdict. The GET
    # payload only includes explanations for questions that are ALREADY
    # answered, so a client that learned the verdict from here and nothing else
    # showed a tick with no explanation beneath it until the page was reloaded —
    # which is the whole point of practice mode missing.
    if sitting["mode"] == "practice":
        prose = {
            q["question_id"]: q
            for q in SectionSittingRepository.mcqs_for_section(sitting["section_code"])
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


@projects_bp.route("/<project_id>/sittings/<sitting_id>/pause", methods=["POST"])
@require_auth
def pause_sitting(project_id: str, sitting_id: str):
    """Stop the clock. The time left is banked on the row."""
    project, error = owned_project(project_id)
    if error:
        return error

    sitting, _, error = _sitting_or_error(project, sitting_id)
    if error:
        return error

    paused = SectionSittingRepository.pause(sitting["sitting_id"])
    if paused is None:
        return jsonify({
            "error": f"only a sitting in progress can be paused; this one is {sitting['status']}"
        }), 409

    db.session.commit()
    return jsonify({"sitting": serialize_sitting(paused, paused["seconds_remaining"])})


@projects_bp.route("/<project_id>/sittings/<sitting_id>/resume", methods=["POST"])
@require_auth
def resume_sitting(project_id: str, sitting_id: str):
    """Restart the clock on a paused sitting."""
    project, error = owned_project(project_id)
    if error:
        return error

    sitting, _, error = _sitting_or_error(project, sitting_id)
    if error:
        return error

    resumed = SectionSittingRepository.resume(sitting["sitting_id"])
    if resumed is None:
        # Distinguish the two ways this fails, because the fix differs: one is
        # "you are already running", the other is "there is no time left".
        if sitting["status"] == "paused" and sitting["seconds_remaining"] <= 0:
            return jsonify({"error": "no time remains on this sitting; submit it"}), 409
        return jsonify({
            "error": f"only a paused sitting can be resumed; this one is {sitting['status']}"
        }), 409

    db.session.commit()
    return jsonify({
        "sitting": serialize_sitting(resumed, SectionSittingRepository.clock(resumed)),
    })


@projects_bp.route("/<project_id>/sittings/<sitting_id>/submit", methods=["POST"])
@require_auth
def submit_sitting(project_id: str, sitting_id: str):
    """Close the sitting and lock its score.

    For a graded sitting this is the irreversible one: the score is written onto
    the row and the unique index means no second graded sitting can ever exist
    for this section, so nothing can overwrite it. Unanswered questions score
    nothing rather than blocking the submit — a student who runs out of time and
    submits eight of ten answers should get the eight.
    """
    project, error = owned_project(project_id)
    if error:
        return error

    sitting, _, error = _sitting_or_error(project, sitting_id)
    if error:
        return error

    if sitting["status"] == "submitted":
        return jsonify({
            "error": "this sitting has already been submitted",
            "sitting": serialize_sitting(sitting, 0),
        }), 409

    submitted = SectionSittingRepository.submit(sitting["sitting_id"])
    if submitted is None:
        return jsonify({"error": "failed to submit the sitting"}), 500

    db.session.commit()

    answers = SectionSittingRepository.answers_for(submitted["sitting_id"])

    return jsonify({
        "sitting": serialize_sitting(submitted, 0),
        "answered": len(answers),
        "total_questions": len(
            SectionSittingRepository.mcqs_for_section(submitted["section_code"])
        ),
    })


@projects_bp.route("/<project_id>/progress", methods=["GET"])
@require_auth
def get_progress(project_id: str):
    """Per-section state, which is what decides the button on each section.

    Absent means Start. `graded_status` of in_progress or paused means
    "continue previous attempt or start new". Submitted means Practice, and
    `marks_awarded` is the locked score.

    Sections the student has not touched are absent rather than returned with
    zeros: the syllabus already knows every section, and inventing rows here
    would make "not started" indistinguishable from "scored nothing".
    """
    project, error = owned_project(project_id)
    if error:
        return error

    return jsonify([
        serialize_section_state(row)
        for row in SectionSittingRepository.section_overview(project.project_id)
    ])
