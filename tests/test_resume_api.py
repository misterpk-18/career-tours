"""
Mocked unit tests for Resume API endpoints.

Endpoints covered:
  POST /api/resumes/upload              - upload_resume
  GET  /api/resumes/<id>                - get_resume
  POST /api/resumes/<id>/extract-skills - extract_skills

All external dependencies (DB, S3, OpenAI) are mocked.
"""

import io
import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app import app
from models.resume import Resume
from models.project import Project  # used for project mock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESUME_ID   = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PROJECT_ID  = "cccccccc-cccc-cccc-cccc-cccccccccccc"
STUDENT_ID  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

RESUME_REPO  = "api.resumes.routes.ResumeRepository"
PROJECT_REPO = "api.resumes.routes.ProjectRepository"
PARSER       = "api.resumes.routes.ResumeParser"
S3           = "api.resumes.routes.S3Service"
EXTRACTOR    = "api.resumes.routes.ResumeSkillExtractor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(**overrides):
    defaults = dict(
        project_id=uuid.UUID(PROJECT_ID),
        student_id=uuid.UUID(STUDENT_ID),
        project_name="Test Project",
        status="active",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_resume(**overrides) -> Resume:
    defaults = dict(
        resume_id=uuid.UUID(RESUME_ID),
        student_id=uuid.UUID(STUDENT_ID),
        project_id=uuid.UUID(PROJECT_ID),
        file_url="https://s3.example.com/resumes/test.pdf",
        raw_text="Python, Flask, SQL, Machine Learning",
        parsed_at=datetime(2024, 6, 1, 12, 0, 0),
        created_at=datetime(2024, 6, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    return Resume(**defaults)


def _pdf_file(name="resume.pdf", content=b"%PDF-1.4 fake pdf content here"):
    """Return a (file-object, filename, mimetype) tuple for multipart upload."""
    return (io.BytesIO(content), name, "application/pdf")


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ===========================================================================
# POST /api/resumes/upload
# ===========================================================================

class TestUploadResume:

    def _post(self, client, data):
        return client.post(
            "/api/resumes/upload",
            data=data,
            content_type="multipart/form-data",
        )

    def test_upload_success(self, client):
        """201 returned with resume metadata on a valid upload."""
        mock_project = _make_project()
        mock_resume  = _make_resume()

        with (
            patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project),
            patch(f"{PARSER}.extract_text", return_value="Python Flask SQL"),
            patch(f"{S3}.upload_file",       return_value="https://s3.example.com/r.pdf"),
            patch(f"{RESUME_REPO}.create",   return_value=mock_resume),
        ):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(),
            })

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["resume_id"]  == RESUME_ID
        assert data["project_id"] == PROJECT_ID
        assert data["student_id"] == STUDENT_ID
        assert "file_url" in data
        assert "text_length" in data

    def test_upload_missing_project_id(self, client):
        """400 when project_id form field is absent."""
        resp = self._post(client, {"resume_file": _pdf_file()})
        assert resp.status_code == 400
        assert "project_id" in resp.get_json()["error"]

    def test_upload_missing_file(self, client):
        """400 when resume_file is absent."""
        resp = self._post(client, {"project_id": PROJECT_ID})
        assert resp.status_code == 400
        assert "resume_file" in resp.get_json()["error"]

    def test_upload_invalid_project_uuid(self, client):
        """400 when project_id is not a valid UUID."""
        resp = self._post(client, {
            "project_id":  "not-a-uuid",
            "resume_file": _pdf_file(),
        })
        assert resp.status_code == 400
        assert "UUID" in resp.get_json()["error"]

    def test_upload_project_not_found(self, client):
        """404 when project doesn't exist."""
        with patch(f"{PROJECT_REPO}.get_by_id", return_value=None):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(),
            })
        assert resp.status_code == 404
        assert "project not found" in resp.get_json()["error"]

    def test_upload_unsupported_file_type(self, client):
        """400 when file extension is not .pdf or .docx."""
        mock_project = _make_project()
        with patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": (io.BytesIO(b"hello"), "resume.txt", "text/plain"),
            })
        assert resp.status_code == 400
        assert "unsupported file type" in resp.get_json()["error"]

    def test_upload_empty_file(self, client):
        """400 when uploaded file is empty."""
        mock_project = _make_project()
        with patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(content=b""),
            })
        assert resp.status_code == 400
        assert "empty" in resp.get_json()["error"]

    def test_upload_parser_failure(self, client):
        """400 when text extraction raises a ValueError."""
        mock_project = _make_project()
        with (
            patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project),
            patch(f"{PARSER}.extract_text", side_effect=ValueError("bad pdf")),
        ):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(),
            })
        assert resp.status_code == 400
        assert "bad pdf" in resp.get_json()["error"]

    def test_upload_s3_failure(self, client):
        """500 when S3 upload raises an exception."""
        mock_project = _make_project()
        with (
            patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project),
            patch(f"{PARSER}.extract_text",   return_value="some text"),
            patch(f"{S3}.upload_file", side_effect=Exception("S3 down")),
        ):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(),
            })
        assert resp.status_code == 500
        assert "S3" in resp.get_json()["error"]

    def test_upload_db_failure(self, client):
        """500 when database create raises an exception."""
        mock_project = _make_project()
        with (
            patch(f"{PROJECT_REPO}.get_by_id", return_value=mock_project),
            patch(f"{PARSER}.extract_text",    return_value="some text"),
            patch(f"{S3}.upload_file",         return_value="https://s3.example.com/r.pdf"),
            patch(f"{RESUME_REPO}.create",     side_effect=Exception("DB error")),
            patch("api.resumes.routes.db.session.rollback"),
        ):
            resp = self._post(client, {
                "project_id":  PROJECT_ID,
                "resume_file": _pdf_file(),
            })
        assert resp.status_code == 500
        assert "failed to save resume record" in resp.get_json()["error"]


# ===========================================================================
# GET /api/resumes/<resume_id>
# ===========================================================================

class TestGetResume:

    def test_get_resume_success(self, client):
        """200 with full serialized resume."""
        mock_resume = _make_resume()
        with patch(f"{RESUME_REPO}.get_by_id", return_value=mock_resume):
            resp = client.get(f"/api/resumes/{RESUME_ID}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["resume_id"]  == RESUME_ID
        assert data["student_id"] == STUDENT_ID
        assert data["project_id"] == PROJECT_ID
        assert data["raw_text"] == "Python, Flask, SQL, Machine Learning"

    def test_get_resume_not_found(self, client):
        """404 when resume doesn't exist."""
        with patch(f"{RESUME_REPO}.get_by_id", return_value=None):
            resp = client.get(f"/api/resumes/{RESUME_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["error"]

    def test_get_resume_invalid_uuid(self, client):
        """400 for invalid UUID path param."""
        resp = client.get("/api/resumes/not-a-uuid")
        assert resp.status_code == 400
        assert "UUID" in resp.get_json()["error"]

    def test_get_resume_parsed_at_iso(self, client):
        """parsed_at is returned as ISO string."""
        mock_resume = _make_resume()
        with patch(f"{RESUME_REPO}.get_by_id", return_value=mock_resume):
            resp = client.get(f"/api/resumes/{RESUME_ID}")
        data = resp.get_json()
        assert data["parsed_at"] == "2024-06-01T12:00:00"

    def test_get_resume_parsed_at_null(self, client):
        """parsed_at is None when resume hasn't been parsed."""
        mock_resume = _make_resume(parsed_at=None)
        with patch(f"{RESUME_REPO}.get_by_id", return_value=mock_resume):
            resp = client.get(f"/api/resumes/{RESUME_ID}")
        assert resp.get_json()["parsed_at"] is None


# ===========================================================================
# POST /api/resumes/<resume_id>/extract-skills
# ===========================================================================

class TestExtractSkills:

    def _mock_skill(self, name="Python"):
        return {
            "student_skill_id": str(uuid.uuid4()),
            "student_id":       STUDENT_ID,
            "skill_id":         str(uuid.uuid4()),
            "skill_name":       name,
            "proficiency_level": "intermediate",
            "confidence_score": 0.9,
            "source":           "resume",
            "created_at":       datetime(2024, 6, 1, 12, 0, 0),
        }

    def _mock_extractor_result(self, skills=None):
        skills = skills or [self._mock_skill("Python"), self._mock_skill("Flask")]
        return {
            "summary":       "Experienced Python developer.",
            "skills_saved":  len(skills),
            "skills_skipped": 0,
            "skills":        skills,
        }

    def test_extract_skills_success(self, client):
        """200 with skills list on successful extraction."""
        mock_resume = _make_resume()
        result      = self._mock_extractor_result()

        with (
            patch(f"{RESUME_REPO}.get_by_id",      return_value=mock_resume),
            patch(f"{EXTRACTOR}.extract_and_save", return_value=result),
        ):
            resp = client.post(
                f"/api/resumes/{RESUME_ID}/extract-skills",
                data=json.dumps({}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["resume_id"]    == RESUME_ID
        assert data["skills_saved"] == 2
        assert len(data["skills"])  == 2
        assert data["skills"][0]["skill_name"] == "Python"

    def test_extract_skills_resume_not_found(self, client):
        """404 when resume doesn't exist."""
        with patch(f"{RESUME_REPO}.get_by_id", return_value=None):
            resp = client.post(f"/api/resumes/{RESUME_ID}/extract-skills")
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["error"]

    def test_extract_skills_invalid_uuid(self, client):
        """400 for invalid UUID."""
        resp = client.post("/api/resumes/bad-uuid/extract-skills")
        assert resp.status_code == 400
        assert "UUID" in resp.get_json()["error"]

    def test_extract_skills_no_raw_text(self, client):
        """400 when resume has no parsed text."""
        mock_resume = _make_resume(raw_text=None)
        with patch(f"{RESUME_REPO}.get_by_id", return_value=mock_resume):
            resp = client.post(f"/api/resumes/{RESUME_ID}/extract-skills")
        assert resp.status_code == 400
        assert "no parsed text" in resp.get_json()["error"]

    def test_extract_skills_extractor_runtime_error(self, client):
        """500 when extractor raises RuntimeError."""
        mock_resume = _make_resume()
        with (
            patch(f"{RESUME_REPO}.get_by_id",      return_value=mock_resume),
            patch(f"{EXTRACTOR}.extract_and_save", side_effect=RuntimeError("LLM failed")),
        ):
            resp = client.post(f"/api/resumes/{RESUME_ID}/extract-skills")
        assert resp.status_code == 500
        assert "LLM failed" in resp.get_json()["error"]

    def test_extract_skills_extractor_generic_error(self, client):
        """500 on unexpected extractor error."""
        mock_resume = _make_resume()
        with (
            patch(f"{RESUME_REPO}.get_by_id",      return_value=mock_resume),
            patch(f"{EXTRACTOR}.extract_and_save", side_effect=Exception("boom")),
            patch("api.resumes.routes.db.session.rollback"),
        ):
            resp = client.post(f"/api/resumes/{RESUME_ID}/extract-skills")
        assert resp.status_code == 500
        assert "failed to extract skills" in resp.get_json()["error"]

    def test_extract_skills_with_questionnaire(self, client):
        """Questionnaire answers are accepted and passed through."""
        mock_resume = _make_resume()
        result      = self._mock_extractor_result()
        payload     = {"questionnaire_answers": {"experience": "2 years"}}

        with (
            patch(f"{RESUME_REPO}.get_by_id",      return_value=mock_resume),
            patch(f"{EXTRACTOR}.extract_and_save", return_value=result) as mock_ext,
        ):
            resp = client.post(
                f"/api/resumes/{RESUME_ID}/extract-skills",
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert resp.status_code == 200
        # Verify questionnaire was forwarded to the extractor
        _, kwargs = mock_ext.call_args
        passed_answers = mock_ext.call_args[0][2] if mock_ext.call_args[0] else kwargs.get("questionnaire_answers")
        assert passed_answers == {"experience": "2 years"}
