
from pathlib import Path
from uuid import UUID, uuid4

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from api.auth.utils import require_auth
from api.guards import owned_project
from api.serializers import serialize_project_skill
from config.database import db
from repositories.project_repository import ProjectRepository
from repositories.resume_repository import ResumeRepository
from services.resume.extractor import ResumeSkillExtractor
from services.resume.parser import ResumeParser
from services.storage.s3_service import S3Service

resume_bp = Blueprint(
    "resume",
    __name__,
)

# Scratch space for an upload between `file.save()` and the S3 upload — every
# code path below removes the file again. On Lambda only /tmp is writable, and a
# relative path would resolve under the read-only /var/task and fail this mkdir
# at import time, taking the whole app down with it.
UPLOAD_DIR = Path("/tmp/uploads/resumes")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _remove_file(file_path: Path) -> None:
    if file_path.exists():
        file_path.unlink()


_serialize_skill = serialize_project_skill


def _serialize_resume(resume) -> dict:
    return {
        "resume_id": str(resume.resume_id),
        "student_id": str(resume.student_id),
        "project_id": str(resume.project_id),
        "file_name": resume.file_name,
        "file_url": resume.file_url,
        "raw_text": resume.raw_text,
        "parsed_at": resume.parsed_at.isoformat() if resume.parsed_at else None,
        "created_at": resume.created_at.isoformat(),
    }


def _serialize_resume_list_item(resume, preview_url) -> dict:
    return {
        "resume_id": str(resume.resume_id),
        "project_id": str(resume.project_id) if resume.project_id else None,
        "file_name": resume.file_name,
        "file_url": resume.file_url,
        "preview_url": preview_url,
        "parsed_at": resume.parsed_at.isoformat() if resume.parsed_at else None,
        "created_at": resume.created_at.isoformat(),
    }


@resume_bp.route("/upload", methods=["POST"])
@require_auth
def upload_resume():
    project_id = request.form.get("project_id")
    file = request.files.get("resume_file")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    if not file:
        return jsonify({"error": "resume_file is required"}), 400

    project, error = owned_project(project_id)
    if error:
        return error

    project_uuid = project.project_id

    if not file.filename:
        return jsonify({"error": "resume_file must have a filename"}), 400

    original_name = secure_filename(file.filename)

    if not original_name:
        return jsonify({"error": "resume_file has an invalid filename"}), 400

    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(
            {
                "error": "unsupported file type",
                "allowed_types": sorted(ALLOWED_EXTENSIONS),
            }
        ), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        return jsonify(
            {
                "error": f"file size exceeds {MAX_FILE_SIZE_MB}MB limit",
            }
        ), 400

    if file_size == 0:
        return jsonify({"error": "resume_file is empty"}), 400

    stored_name = f"{uuid4()}{extension}"
    file_path = UPLOAD_DIR / stored_name

    try:
        file.save(file_path)
    except OSError:
        return jsonify({"error": "failed to save uploaded file"}), 500

    try:
        raw_text = ResumeParser.extract_text(str(file_path))
    except ValueError as exc:
        _remove_file(file_path)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        _remove_file(file_path)
        return jsonify({"error": "failed to parse resume file"}), 400

    try:
        s3_service = S3Service()
        s3_url = s3_service.upload_file(str(file_path), stored_name)
    except Exception as exc:
        _remove_file(file_path)
        return jsonify({"error": f"failed to upload file to S3: {str(exc)}"}), 500

    try:
        resume = ResumeRepository.create(
            student_id=project.student_id,
            project_id=project.project_id,
            file_url=s3_url,
            raw_text=raw_text,
            file_name=original_name,
        )
    except Exception:
        db.session.rollback()
        _remove_file(file_path)
        current_app.logger.exception("upload_resume: failed to save resume record")
        return jsonify({"error": "failed to save resume record"}), 500

    # Point the project at its (current) resume. Non-fatal if it fails: the
    # resume is already saved and reachable via resumes.project_id.
    try:
        ProjectRepository.set_resume_id(project.project_id, resume.resume_id)
    except Exception:
        import traceback
        traceback.print_exc()
        db.session.rollback()

    _remove_file(file_path)

    return jsonify(
        {
            "resume_id": str(resume.resume_id),
            "student_id": str(resume.student_id),
            "project_id": str(resume.project_id),
            "file_url": resume.file_url,
            "text_length": len(raw_text),
        }
    ), 201


@resume_bp.route("/mine", methods=["GET"])
@require_auth
def list_my_resumes():
    resumes = ResumeRepository.get_by_student_id(g.student_id)

    s3_service = S3Service()
    items = []
    for resume in resumes:
        preview_url = None
        try:
            key = S3Service.key_from_url(resume.file_url)
            preview_url = s3_service.generate_presigned_url(key)
        except (ValueError, RuntimeError):
            preview_url = None
        items.append(_serialize_resume_list_item(resume, preview_url))

    return jsonify({"resumes": items})


@resume_bp.route("/<resume_id>", methods=["GET"])
@require_auth
def get_resume(resume_id: str):
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        return jsonify({"error": "resume_id must be a valid UUID"}), 400

    resume = ResumeRepository.get_by_id(resume_uuid)

    # 404 rather than 403 for another student's resume — see api/guards.py. This
    # response carries raw_text, i.e. the entire contents of the CV.
    if resume is None or resume.student_id != g.student_id:
        return jsonify({"error": "resume not found"}), 404

    return jsonify(_serialize_resume(resume))


@resume_bp.route("/<resume_id>/preview", methods=["GET"])
@require_auth
def preview_resume(resume_id: str):
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        return jsonify({"error": "resume_id must be a valid UUID"}), 400

    resume = ResumeRepository.get_by_id(resume_uuid)

    # 404 (not 403) when the resume belongs to another student, so we don't
    # reveal that a resume with that id exists.
    if resume is None or resume.student_id != g.student_id:
        return jsonify({"error": "resume not found"}), 404

    try:
        expires_in = min(int(request.args.get("expires_in", 3600)), 3600)
    except ValueError:
        expires_in = 3600

    try:
        key = S3Service.key_from_url(resume.file_url)
        preview_url = S3Service().generate_presigned_url(key, expires_in=expires_in)
    except (ValueError, RuntimeError):
        return jsonify({"error": "failed to generate preview url"}), 500

    return jsonify(
        {
            "resume_id": str(resume.resume_id),
            "file_name": resume.file_name,
            "file_url": resume.file_url,
            "preview_url": preview_url,
            "expires_in": expires_in,
            "raw_text": resume.raw_text,
            "parsed_at": resume.parsed_at.isoformat() if resume.parsed_at else None,
        }
    )


@resume_bp.route("/<resume_id>/extract-skills", methods=["POST"])
@require_auth
def extract_skills(resume_id: str):
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        return jsonify({"error": "resume_id must be a valid UUID"}), 400

    resume = ResumeRepository.get_by_id(resume_uuid)

    # Unauthenticated, this endpoint let anyone with a resume id spend money on
    # the OpenAI account and read the extracted profile back.
    if resume is None or resume.student_id != g.student_id:
        return jsonify({"error": "resume not found"}), 404

    if not resume.raw_text:
        return jsonify({"error": "resume has no parsed text"}), 400

    payload = request.get_json(silent=True) or {}
    questionnaire_answers = payload.get("questionnaire_answers")

    if not resume.project_id:
        return jsonify({"error": "resume has no associated project"}), 400

    # Check the database before parsing anything: if this project's skills are
    # already stored, return them instead of paying for another LLM extraction.
    # Pass {"force": true} to re-extract deliberately.
    if not payload.get("force"):
        try:
            existing = ResumeSkillExtractor.existing_result(
                resume.project_id,
                resume.student_id,
            )
        except Exception:
            db.session.rollback()
            current_app.logger.exception("extract_skills: failed to read stored skills")
            return jsonify({"error": "failed to extract skills"}), 500

        if existing is not None:
            return jsonify(
                {
                    "resume_id": str(resume.resume_id),
                    "student_id": str(resume.student_id),
                    "summary": existing["summary"],
                    "skills_saved": existing["skills_saved"],
                    "additional_skills_saved": existing["additional_skills_saved"],
                    "skills": [
                        _serialize_skill(skill) for skill in existing["skills"]
                    ],
                    "reused": True,
                }
            )

    try:
        result = ResumeSkillExtractor.extract_and_save(
            resume.project_id,
            resume.student_id,
            resume.raw_text,
            questionnaire_answers,
        )
    except RuntimeError as exc:
        db.session.rollback()
        current_app.logger.exception("extract_skills: extraction failed")
        return jsonify({"error": str(exc)}), 500
    except Exception:
        # Never echo the exception back: SQLAlchemy errors carry the full statement
        # and bound parameters, which is user data.
        db.session.rollback()
        current_app.logger.exception("extract_skills: failed to extract skills")
        return jsonify({"error": "failed to extract skills"}), 500

    return jsonify(
        {
            "resume_id": str(resume.resume_id),
            "student_id": str(resume.student_id),
            "summary": result["summary"],
            "skills_saved": result["skills_saved"],
            "additional_skills_saved": result["additional_skills_saved"],
            "skills": [_serialize_skill(skill) for skill in result["skills"]],
            "reused": False,
        }
    )
