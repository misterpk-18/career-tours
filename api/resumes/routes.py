from pathlib import Path
from uuid import UUID, uuid4

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

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

UPLOAD_DIR = Path("uploads/resumes")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _remove_file(file_path: Path) -> None:
    if file_path.exists():
        file_path.unlink()


def _serialize_skill(skill: dict) -> dict:
    return {
        "student_skill_id": str(skill["student_skill_id"]),
        "student_id": str(skill["student_id"]),
        "skill_id": str(skill["skill_id"]),
        "skill_name": skill["skill_name"],
        "proficiency_level": skill["proficiency_level"],
        "confidence_score": float(skill["confidence_score"]),
        "source": skill["source"],
        "created_at": skill["created_at"].isoformat(),
    }


def _serialize_resume(resume) -> dict:
    return {
        "resume_id": str(resume.resume_id),
        "student_id": str(resume.student_id),
        "project_id": str(resume.project_id),
        "file_url": resume.file_url,
        "raw_text": resume.raw_text,
        "parsed_at": resume.parsed_at.isoformat() if resume.parsed_at else None,
        "created_at": resume.created_at.isoformat(),
    }


@resume_bp.route("/upload", methods=["POST"])
def upload_resume():
    project_id = request.form.get("project_id")
    file = request.files.get("resume_file")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    if not file:
        return jsonify({"error": "resume_file is required"}), 400

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return jsonify({"error": "project_id must be a valid UUID"}), 400

    project = ProjectRepository.get_by_id(project_uuid)

    if project is None:
        return jsonify({"error": "project not found"}), 404

    if not file.filename:
        return jsonify({"error": "resume_file must have a filename"}), 400

    original_name = secure_filename(file.filename)

    if not original_name:
        return jsonify({"error": "resume_file has an invalid filename"}), 400

    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "unsupported file type",
            "allowed_types": sorted(ALLOWED_EXTENSIONS),
        }), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        return jsonify({
            "error": f"file size exceeds {MAX_FILE_SIZE_MB}MB limit",
        }), 400

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
        )
    except Exception:
        db.session.rollback()
        _remove_file(file_path)
        return jsonify({"error": "failed to save resume record"}), 500

    _remove_file(file_path)

    return jsonify({
        "resume_id": str(resume.resume_id),
        "student_id": str(resume.student_id),
        "project_id": str(resume.project_id),
        "file_url": resume.file_url,
        "text_length": len(raw_text),
    }), 201


@resume_bp.route("/<resume_id>", methods=["GET"])
def get_resume(resume_id: str):
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        return jsonify({"error": "resume_id must be a valid UUID"}), 400

    resume = ResumeRepository.get_by_id(resume_uuid)

    if resume is None:
        return jsonify({"error": "resume not found"}), 404

    return jsonify(_serialize_resume(resume))


@resume_bp.route("/<resume_id>/extract-skills", methods=["POST"])
def extract_skills(resume_id: str):
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        return jsonify({"error": "resume_id must be a valid UUID"}), 400

    resume = ResumeRepository.get_by_id(resume_uuid)

    if resume is None:
        return jsonify({"error": "resume not found"}), 404

    if not resume.raw_text:
        return jsonify({"error": "resume has no parsed text"}), 400

    payload = request.get_json(silent=True) or {}
    questionnaire_answers = payload.get("questionnaire_answers")

    try:
        result = ResumeSkillExtractor.extract_and_save(
            resume.project_id,
            resume.raw_text,
            questionnaire_answers,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception:
        db.session.rollback()
        return jsonify({"error": "failed to extract skills"}), 500

    return jsonify({
        "resume_id": str(resume.resume_id),
        "student_id": str(resume.student_id),
        "summary": result["summary"],
        "skills_saved": result["skills_saved"],
        "skills_skipped": result["skills_skipped"],
        "skills": [
            _serialize_skill(skill)
            for skill in result["skills"]
        ],
    })