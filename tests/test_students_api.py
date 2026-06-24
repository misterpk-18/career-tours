"""
Tests for the Student API endpoints.

Endpoints covered:
  POST  /api/students           - create_student
  GET   /api/students/<id>      - get_student

Uses Flask's test client and mocks StudentRepository so no
live database connection is required.
"""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass
from unittest.mock import patch, MagicMock

import pytest

from app import app
from models.student import Student


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_student(**overrides) -> Student:
    """Return a Student dataclass instance with sensible defaults."""
    defaults = dict(
        student_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="9876543210",
        college_name="MIT",
        degree_name="B.Tech",
        branch_name="Computer Science",
        current_year_semester="3rd Year",
        graduation_year=2026,
        preferred_job_location="Remote",
        target_role="Software Engineer",
        career_interest="AI/ML",
        learning_hours_per_week=10,
        internship_preference="Yes",
        work_mode_preference="Remote",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 6, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    return Student(**defaults)


STUDENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
REPO_PATH  = "api.students.routes.StudentRepository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/students
# ---------------------------------------------------------------------------

class TestCreateStudent:

    def test_create_student_success(self, client):
        """201 returned with serialized student on valid payload."""
        mock_student = _make_student()
        payload = {"full_name": "Ada Lovelace", "email": "ada@example.com"}

        with patch(f"{REPO_PATH}.create", return_value=mock_student):
            resp = client.post(
                "/api/students",
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["student_id"] == STUDENT_ID
        assert data["full_name"] == "Ada Lovelace"
        assert data["email"] == "ada@example.com"

    def test_create_student_missing_body(self, client):
        """400 returned when no JSON body is sent."""
        resp = client.post(
            "/api/students",
            data="",
            content_type="application/json",
        )
        # Flask's get_json() returns None for empty body → route returns 400
        assert resp.status_code == 400
        body = resp.get_json()
        if body:
            assert "required" in body["error"]

    def test_create_student_missing_full_name(self, client):
        """400 returned when full_name is absent."""
        payload = {"email": "ada@example.com"}
        resp = client.post(
            "/api/students",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "full_name" in resp.get_json()["error"]

    def test_create_student_missing_email(self, client):
        """400 returned when email is absent."""
        payload = {"full_name": "Ada Lovelace"}
        resp = client.post(
            "/api/students",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "email" in resp.get_json()["error"]

    def test_create_student_repo_exception(self, client):
        """500 returned when the repository raises an exception."""
        payload = {"full_name": "Ada Lovelace", "email": "ada@example.com"}

        with patch(f"{REPO_PATH}.create", side_effect=Exception("DB error")):
            resp = client.post(
                "/api/students",
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert resp.status_code == 500
        assert "failed to create student" in resp.get_json()["error"]

    def test_create_student_all_optional_fields(self, client):
        """201 returned with all optional fields present in response."""
        mock_student = _make_student()
        payload = {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "9876543210",
            "college_name": "MIT",
            "degree_name": "B.Tech",
            "branch_name": "Computer Science",
            "current_year_semester": "3rd Year",
            "graduation_year": 2026,
            "preferred_job_location": "Remote",
            "target_role": "Software Engineer",
            "career_interest": "AI/ML",
            "learning_hours_per_week": 10,
            "internship_preference": "Yes",
            "work_mode_preference": "Remote",
        }

        with patch(f"{REPO_PATH}.create", return_value=mock_student):
            resp = client.post(
                "/api/students",
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["college_name"] == "MIT"
        assert data["graduation_year"] == 2026
        assert data["work_mode_preference"] == "Remote"


# ---------------------------------------------------------------------------
# GET /api/students/<student_id>
# ---------------------------------------------------------------------------

class TestGetStudent:

    def test_get_student_success(self, client):
        """200 returned with serialized student for a valid UUID."""
        mock_student = _make_student()

        with patch(f"{REPO_PATH}.get_by_id", return_value=mock_student):
            resp = client.get(f"/api/students/{STUDENT_ID}")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["student_id"] == STUDENT_ID
        assert data["full_name"] == "Ada Lovelace"
        assert data["email"] == "ada@example.com"

    def test_get_student_not_found(self, client):
        """404 returned when repository returns None."""
        with patch(f"{REPO_PATH}.get_by_id", return_value=None):
            resp = client.get(f"/api/students/{STUDENT_ID}")

        assert resp.status_code == 404
        assert "not found" in resp.get_json()["error"]

    def test_get_student_invalid_uuid(self, client):
        """400 returned for a non-UUID student_id path param."""
        resp = client.get("/api/students/not-a-valid-uuid")
        assert resp.status_code == 400
        assert "UUID" in resp.get_json()["error"]

    def test_get_student_response_has_timestamps(self, client):
        """Response includes ISO-formatted created_at and updated_at."""
        mock_student = _make_student()

        with patch(f"{REPO_PATH}.get_by_id", return_value=mock_student):
            resp = client.get(f"/api/students/{STUDENT_ID}")

        data = resp.get_json()
        assert data["created_at"] == "2024-01-01T12:00:00"
        assert data["updated_at"] == "2024-06-01T12:00:00"

    def test_get_student_optional_fields_none(self, client):
        """Response correctly serializes None optional fields."""
        mock_student = _make_student(
            phone=None,
            college_name=None,
            graduation_year=None,
        )

        with patch(f"{REPO_PATH}.get_by_id", return_value=mock_student):
            resp = client.get(f"/api/students/{STUDENT_ID}")

        data = resp.get_json()
        assert data["phone"] is None
        assert data["college_name"] is None
        assert data["graduation_year"] is None
