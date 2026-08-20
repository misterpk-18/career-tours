# API Contract

The complete REST contract for the Career Tours backend: every endpoint, its
request and response shapes, and its error cases. This is the reference the
frontend's `frontend/src/services/api.js` is written against.

Requests and responses are `application/json` unless stated otherwise. Paths
are relative to the API root:

| Environment | Root |
|---|---|
| Local development | `http://127.0.0.1:5001` — the port the Vite dev proxy expects |
| Production | `https://nipunacareers.com` — CloudFront routes `/api/*` to the HTTP API, so `/api` is same-origin and needs no base URL |

For the runtime that serves these endpoints, see [architecture.md](architecture.md).

---

## Authentication

**Every endpoint below requires a bearer token except `GET /`, `GET /db-test`, `POST /api/auth/register` and `POST /api/auth/login`.**

```http
Authorization: Bearer <token>
```

The token comes from `register` or `login`. Missing or malformed → `401 {"error": "authorization token required"}`; expired → `401 {"error": "token expired"}`; invalid signature → `401 {"error": "invalid token"}`.

### Database pressure is a 503, not a 500

Two failures are reported as `503` with a `Retry-After` header and `"retryable": true` in the body, because both are transient and the request itself was fine:

| Cause | Body | Retry-After |
|---|---|---|
| Connection pool exhausted under load | `The server is busy. Your request was not lost — try again in a moment.` | `2` |
| Neon compute waking, or the connection dropped | `The database is waking up. Your request was not lost — try again in a moment.` | `3` |

This matters to any client: a `500` means "this request is broken, do not retry", so a caller that believed it would discard work that nothing was wrong with. Measured at 64 concurrent sittings, the pool (`pool_size: 1, max_overflow: 2` — correct for Lambda, where concurrency comes from more invocations) produced 40 of these. Only `POST .../answers` retries automatically, because it is the one request where giving up costs a student a graded answer.

Authentication alone is not the whole check. Every id in this API is a UUID in a URL, and UUIDs travel — they show up in the UI, in logs and in shared links — so each route also verifies that the row belongs to the caller (`backend/api/guards.py`):

- A project, resume, student or recommendation belonging to **another** student returns **`404`, not `403`**. A 403 would confirm the id exists, which is the one thing an enumerating caller wants.
- The owner is always taken from the token, never the request body. `POST /api/projects` ignores a body-supplied `student_id`, and `PUT /api/projects/<id>` cannot reassign ownership.

> Prior to this, only `GET /api/resumes/mine` and `GET /api/resumes/<id>/preview` enforced auth. Every other route served any caller who knew an id, including student PII, resume-derived profiles, project deletion, and the billed LLM endpoints.

## Table of Contents
1. [Base & Health Check](#1-base--health-check)
2. [Authentication API (`/api/auth`)](#2-authentication-api-apiauth)
3. [Student Management API (`/api/students`)](#3-student-management-api-apistudents)
4. [Project Management API (`/api/projects`)](#4-project-management-api-apiprojects)
5. [Resume Parsing & Skill Extraction API (`/api/resumes`)](#5-resume-parsing--skill-extraction-api-apiresumes)
6. [Recommendation Engine API (`/api/recommendations`)](#6-recommendation-engine-api-apirecommendations)
7. [Assessment API — sittings (`/api/projects/.../sittings`)](#7-assessment-api--sittings)
8. [Achievements API (`/api/achievements`)](#8-achievements-api-apiachievements)

---

## 1. Base & Health Check

### **GET /**
Checks the operational health of the Flask application server.
- **Request Headers**: None
- **Response (200 OK)**:
  ```json
  {
    "status": "ok"
  }
  ```

### **GET /db-test**
Tests active connectivity to the PostgreSQL database.
- **Request Headers**: None
- **Response (200 OK)**:
  ```json
  {
    "database": "neondb"
  }
  ```
- **Response (500 Internal Server Error)**:
  ```json
  {
    "error": "database connection failed"
  }
  ```

---

## 2. Authentication API (`/api/auth`)

JWT-based authentication for students. On success, both endpoints return a signed **JWT** (HS256) alongside the student profile. The token encodes the `student_id` in its `sub` claim and expires after `JWT_EXPIRY_HOURS` (default 24). Registered users are stored in the same `students` table; `email` and `phone` are both **unique**, and passwords are stored only as salted hashes (`werkzeug`), never returned in responses.

### **POST /api/auth/register**
Registers a new student and returns an access token. Optional profile fields (`phone`, `college_name`, `degree_name`, `target_role`, …) may be included; only `full_name`, `email`, and `password` are required. Blank strings are stored as NULL.
- **Request Body**:
  ```json
  {
    "full_name": "Manoj Tungala",
    "email": "manoj@example.com",
    "password": "s3cret-passphrase",
    "phone": "+1234567890"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "student": {
      "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
      "full_name": "Manoj Tungala",
      "email": "manoj@example.com",
      "phone": "+1234567890",
      "created_at": "2026-07-12T14:32:10.123456",
      "updated_at": "2026-07-12T14:32:10.123456"
    }
  }
  ```
- **Response (400 Bad Request)** — a required field is missing:
  ```json
  {
    "error": "password is required"
  }
  ```
- **Response (409 Conflict)** — the email or phone is already registered:
  ```json
  {
    "error": "email already registered"
  }
  ```

### **POST /api/auth/login**
Authenticates a student by email and password and returns an access token.
- **Request Body**:
  ```json
  {
    "email": "manoj@example.com",
    "password": "s3cret-passphrase"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "student": {
      "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
      "full_name": "Manoj Tungala",
      "email": "manoj@example.com",
      "phone": "+1234567890",
      "created_at": "2026-07-12T14:32:10.123456",
      "updated_at": "2026-07-12T14:32:10.123456"
    }
  }
  ```
- **Response (400 Bad Request)** — `email` or `password` missing.
- **Response (401 Unauthorized)** — invalid credentials:
  ```json
  {
    "error": "invalid email or password"
  }
  ```

---

## 3. Student Management API (`/api/students`)

> `POST /api/students` has been **removed**. It was an unauthenticated second way
> to create an account that skipped the password rules in `POST /api/auth/register`,
> so it could create a student with no password and therefore no way to sign in.
> Registration has exactly one entry point: `POST /api/auth/register`.

### **GET /api/students/<student_id>**
Retrieves a student profile by UUID. Only the authenticated student's own profile is
reachable — any other `student_id` returns `404`.
- **Headers**: `Authorization: Bearer <token>` (required).
- **Path Parameters**:
  - `student_id` (string, required): The UUID of the student. Must match the token.
- **Response (200 OK)**:
  ```json
  {
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "full_name": "Manoj Tungala",
    "email": "manoj@example.com",
    "phone": "+1234567890",
    "college_name": "State University",
    "degree_name": "Bachelor of Science",
    "branch_name": "Computer Science",
    "current_year_semester": "4th Year / 8th Semester",
    "graduation_year": 2026,
    "preferred_job_location": "San Francisco, CA",
    "target_role": "GenAI / Cloud Data Engineer",
    "career_interest": "Software Development, Machine Learning",
    "learning_hours_per_week": 15,
    "internship_preference": "Remote/Hybrid",
    "work_mode_preference": "Hybrid",
    "created_at": "2026-06-24T14:32:10.123456",
    "updated_at": "2026-06-24T14:32:10.123456"
  }
  ```
- **Response (400 Bad Request)**:
  ```json
  {
    "error": "student_id must be a valid UUID"
  }
  ```
- **Response (404 Not Found)**:
  ```json
  {
    "error": "student not found"
  }
  ```

---

## 4. Project Management API (`/api/projects`)

Projects represent specific career-matching tracks, goals, or workflows created for a student.

Every project response includes a **`resume_id`** field — the project's linked resume. It is `null` when a project is first created and is populated automatically once a resume is uploaded for that project via `POST /api/resumes/upload` (see the Resume API). This gives each project a direct pointer to its current resume. Deleting the linked resume resets `resume_id` back to `null`.

### **POST /api/projects**
Creates a new project track for a student. The project starts with `resume_id: null`.
- **Headers**: `Authorization: Bearer <token>` (required). The project owner is taken from the token; a `student_id` in the body is ignored.
- **Request Body**:
  ```json
  {
    "project_name": "Summer Internship 2026 prep",
    "description": "Matching resume skills to Cloud Data Engineering and GenAI roles",
    "status": "active"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_name": "Summer Internship 2026 prep",
    "description": "Matching resume skills to Cloud Data Engineering and GenAI roles",
    "status": "active",
    "resume_id": null,
    "created_at": "2026-06-24T14:35:00.111222",
    "updated_at": "2026-06-24T14:35:00.111222"
  }
  ```
- **Response (400 Bad Request)**:
  ```json
  {
    "error": "project_name is required"
  }
  ```

### **GET /api/projects/<project_id>**
Retrieves a project's details by its UUID. After a resume has been uploaded, `resume_id` points to it.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_name": "Summer Internship 2026 prep",
    "description": "Matching resume skills to Cloud Data Engineering and GenAI roles",
    "status": "active",
    "resume_id": "0d61fb19-6ab7-47b2-bd75-47e2a9b6b801",
    "created_at": "2026-06-24T14:35:00.111222",
    "updated_at": "2026-06-24T14:35:00.111222"
  }
  ```

### **GET /api/projects/student/<student_id>**
Retrieves all projects associated with a specific student.
- **Path Parameters**:
  - `student_id` (string, required): The UUID of the student.
- **Response (200 OK)**:
  ```json
  [
    {
      "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
      "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
      "project_name": "Summer Internship 2026 prep",
      "description": "Matching resume skills to Cloud Data Engineering and GenAI roles",
      "status": "active",
      "created_at": "2026-06-24T14:35:00.111222",
      "updated_at": "2026-06-24T14:35:00.111222"
    }
  ]
  ```

### **PUT /api/projects/<project_id>**
Updates attributes of an existing project (e.g., changing status, name, description).
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project to update.
- **Request Body**:
  ```json
  {
    "project_name": "Summer Internship 2026 preparation (Updated)",
    "description": "Refining skills for technical placement",
    "status": "completed"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_name": "Summer Internship 2026 preparation (Updated)",
    "description": "Refining skills for technical placement",
    "status": "completed",
    "created_at": "2026-06-24T14:35:00.111222",
    "updated_at": "2026-06-24T14:40:00.444555"
  }
  ```

### **DELETE /api/projects/<project_id>**
Deletes a project record from the database.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project to delete.
- **Response (200 OK)**:
  ```json
  {
    "message": "project deleted successfully"
  }
  ```

---

## 5. Resume Parsing & Skill Extraction API (`/api/resumes`)

Processes physical CV documents, uploads them to AWS S3, extracts the raw text, and triggers GenAI-powered skill extraction.

### **POST /api/resumes/upload**
Uploads a resume file (PDF or DOCX), extracts text, uploads it to S3, and creates a database record.
- **Content-Type**: `multipart/form-data`
- **Form Data Fields**:
  - `project_id` (string, required): The UUID of the project.
  - `resume_file` (file, required): The physical document (binary). Max size: 10MB. Allowed extensions: `.pdf`, `.docx`.
- **Response (201 Created)**:
  ```json
  {
    "resume_id": "0d61fb19-6ab7-47b2-bd75-47e2a9b6b801",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "file_url": "https://your-s3-bucket.s3.amazonaws.com/0d61fb19-6ab7-47b2-bd75-47e2a9b6b801.pdf",
    "text_length": 4850
  }
  ```
- **Response (400 Bad Request)**:
  - If the project ID is missing or invalid.
  - If the file is missing, empty, or exceeds the size limit.
  - If the file type is unsupported (e.g., `.txt`, `.png`).
  ```json
  {
    "error": "unsupported file type",
    "allowed_types": [".docx", ".pdf"]
  }
  ```

### **GET /api/resumes/mine**
Returns the resumes uploaded by the **currently authenticated student**, newest first. The student is identified from the JWT, so a student can only ever see their own resumes. Each resume includes a `preview_url` — a time-limited (1 hour) presigned S3 link the browser can open to view/download the actual document (the stored `file_url` itself is private and not directly accessible).
- **Request Headers**:
  - `Authorization: Bearer <token>` (required) — the JWT from `/api/auth/login` or `/api/auth/register`.
- **Response (200 OK)**:
  ```json
  {
    "resumes": [
      {
        "resume_id": "a9d6bbd1-1fdc-4223-820a-3db7e3ab5ad8",
        "project_id": "0d4988d6-0e82-4717-bb9f-ae3f9f783a1c",
        "file_name": "manoj_resume.pdf",
        "file_url": "https://your-s3-bucket.s3.ap-south-1.amazonaws.com/6edb7eff-....docx",
        "preview_url": "https://your-s3-bucket.s3.amazonaws.com/6edb7eff-....docx?X-Amz-Algorithm=...&X-Amz-Signature=...",
        "parsed_at": "2026-07-12T10:07:11.384250",
        "created_at": "2026-07-12T10:07:11.384250"
      }
    ]
  }
  ```
  Note: `file_name` is `null` for resumes uploaded before filename tracking was added. `preview_url` may be `null` if a signed link could not be generated for that row.
- **Response (401 Unauthorized)** — missing, invalid, or expired token:
  ```json
  {
    "error": "authorization token required"
  }
  ```

### **GET /api/resumes/<resume_id>**
Retrieves an uploaded resume's metadata and its extracted raw text content.
- **Path Parameters**:
  - `resume_id` (string, required): The UUID of the resume.
- **Response (200 OK)**:
  ```json
  {
    "resume_id": "0d61fb19-6ab7-47b2-bd75-47e2a9b6b801",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "file_name": "manoj_resume.pdf",
    "file_url": "https://your-s3-bucket.s3.amazonaws.com/0d61fb19-6ab7-47b2-bd75-47e2a9b6b801.pdf",
    "raw_text": "Manoj Tungala\nCloud and GenAI Engineer...\n...",
    "parsed_at": "2026-06-24T14:42:00.123456",
    "created_at": "2026-06-24T14:41:55.789012"
  }
  ```

### **GET /api/resumes/<resume_id>/preview**
Returns a fresh presigned `preview_url` (plus the extracted `raw_text`) for a single resume owned by the authenticated student. Use this to re-open a resume after an earlier `preview_url` has expired.
- **Request Headers**:
  - `Authorization: Bearer <token>` (required).
- **Path Parameters**:
  - `resume_id` (string, required): The UUID of the resume.
- **Query Parameters**:
  - `expires_in` (integer, optional): Seconds until the link expires. Default and maximum `3600`.
- **Response (200 OK)**:
  ```json
  {
    "resume_id": "a9d6bbd1-1fdc-4223-820a-3db7e3ab5ad8",
    "file_name": "manoj_resume.pdf",
    "file_url": "https://your-s3-bucket.s3.ap-south-1.amazonaws.com/6edb7eff-....docx",
    "preview_url": "https://your-s3-bucket.s3.amazonaws.com/6edb7eff-....docx?X-Amz-Signature=...",
    "expires_in": 3600,
    "raw_text": "Manoj Tungala\nCloud and GenAI Engineer...\n...",
    "parsed_at": "2026-07-12T10:07:11.384250"
  }
  ```
- **Response (401 Unauthorized)** — missing/invalid/expired token.
- **Response (404 Not Found)** — the resume does not exist, or belongs to another student.

### **POST /api/resumes/<resume_id>/extract-skills**
Triggers OpenAI to extract technical, soft, and domain skills from the resume text. It maps them to master database skills, checks for existing associations, saves them, and returns a structured profile.
- **Path Parameters**:
  - `resume_id` (string, required): The UUID of the resume.
- **Request Body (JSON, Optional)**:
  - `questionnaire_answers` (object, optional): Key-value responses to profile questions to help improve OpenAI extraction relevance.
  ```json
  {
    "questionnaire_answers": {
      "experience_level": "Mid-Level",
      "primary_focus": "GenAI and Data Lakehouses"
    }
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "resume_id": "0d61fb19-6ab7-47b2-bd75-47e2a9b6b801",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "summary": "Cloud and GenAI engineer with 2+ years building production-grade data platforms, LLM/agentic systems, and cloud-native services.",
    "skills_saved": 64,
    "skills_skipped": 1,
    "skills": [
      {
        "student_skill_id": "1a62d385-48b4-4b5c-b179-88ab89f76a1c",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "skill_id": "db60c283-9bfa-4340-9a3b-280fb5c09e3e",
        "skill_name": "Python",
        "proficiency_level": "advanced",
        "confidence_score": 0.98,
        "source": "resume",
        "created_at": "2026-06-24T14:45:10.555666"
      },
      {
        "student_skill_id": "9f88a2b5-e63d-4c31-89be-02ff48e244cd",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "skill_id": "eb32bb11-d1fa-4b8c-8f9d-14a0dbbcbe8d",
        "skill_name": "Databricks",
        "proficiency_level": "advanced",
        "confidence_score": 0.95,
        "source": "resume",
        "created_at": "2026-06-24T14:45:10.558777"
      }
    ]
  }
  ```

---

## 6. Recommendation Engine API (`/api/recommendations`)

Computes matching scores against active occupational profiles and suggests career paths, bridges gaps, and aligns courses.

### **POST /api/recommendations/projects/<project_id>/generate**
Analyzes a student's extracted skills, matches them to database occupations using NLP/vector search, identifies missing skills (gaps), ranks the top 5 fitting careers, searches for course mappings, generates AI summaries for why those careers and courses fit, and persists everything to the database.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "careers_generated": 5
  }
  ```

### **GET /api/recommendations/projects/<project_id>/careers**
Retrieves the ranked list of career matches calculated for the project.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "careers": [
      {
        "match_id": "5f6ba89d-4c12-4eb5-ba81-11d27f8a9ee2",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
        "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
        "occupation_name": "Data Engineer",
        "description": "Design, build, and maintain data pipeline architectures.",
        "average_salary": 115000.00,
        "growth_outlook": "Very Strong",
        "match_percentage": 88.5,
        "rank_position": 1,
        "generated_at": "2026-06-24T14:48:30.123456"
      }
    ]
  }
  ```

### **GET /api/recommendations/projects/<project_id>/courses**
Retrieves all course recommendations linked to the missing skills discovered across all recommended occupations for the project.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "courses": [
      {
        "recommendation_id": "c138da01-8fb7-44a3-ad65-27a3b3a726cd",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
        "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
        "course_id": "01b22ff3-99ab-48c0-8aef-41dcd9912cd3",
        "course_name": "Big Data Fundamentals on AWS",
        "description": "Learn to manage big data architectures using AWS EMR, Athena, and Redshift.",
        "duration_hours": 32.0,
        "level": "Intermediate",
        "coverage_percentage": 95.0,
        "recommendation_rank": 1,
        "created_at": "2026-06-24T14:48:35.789012"
      }
    ]
  }
  ```

### **GET /api/recommendations/projects/<project_id>**
A composite endpoint that returns both career and course recommendations in a single response payload.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "careers": [ ... ],
    "courses": [ ... ]
  }
  ```

### **GET /api/recommendations/projects/<project_id>/careers/<occupation_id>**
Retrieves details for a specific career match, including its score, a deep-dive AI-generated summary of fit, and a detailed breakdown of all missing skills (the skill gaps).
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
  - `occupation_id` (string, required): The UUID of the target occupation.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
    "career": {
      "match_id": "5f6ba89d-4c12-4eb5-ba81-11d27f8a9ee2",
      "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
      "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
      "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
      "occupation_name": "Data Engineer",
      "description": "Design, build, and maintain data pipeline architectures.",
      "average_salary": 115000.00,
      "growth_outlook": "Very Strong",
      "match_percentage": 88.5,
      "rank_position": 1,
      "generated_at": "2026-06-24T14:48:30.123456"
    },
    "summary": {
      "id": 42,
      "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
      "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
      "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
      "course_id": null,
      "summary_type": "career_summary",
      "summary_text": "The candidate shows an exceptional match for the Data Engineer role, possessing strong Python, SQL, and Databricks capabilities. To maximize readiness, bridging the 100% gap on Apache Spark and Kubernetes is highly recommended.",
      "created_at": "2026-06-24T14:48:32.444555"
    },
    "skill_gaps": [
      {
        "gap_id": "d0e14cb1-f5bc-4889-b789-99ab9c182def",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
        "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
        "occupation_name": "Data Engineer",
        "skill_id": "2b31ff11-1a3b-488d-ba7d-31ad18cce1a9",
        "skill_name": "Apache Spark",
        "gap_percentage": 100.0,
        "created_at": "2026-06-24T14:48:31.999888"
      }
    ]
  }
  ```

### **GET /api/recommendations/projects/<project_id>/careers/<occupation_id>/courses**
Retrieves the list of recommended courses targeting the skill gaps for a specific occupation, containing an embedded AI-generated analysis explaining exactly how each course bridges the student's gaps.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project.
  - `occupation_id` (string, required): The UUID of the occupation.
- **Response (200 OK)**:
  ```json
  {
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
    "courses": [
      {
        "recommendation_id": "c138da01-8fb7-44a3-ad65-27a3b3a726cd",
        "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
        "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
        "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
        "course_id": "01b22ff3-99ab-48c0-8aef-41dcd9912cd3",
        "course_name": "Big Data Fundamentals on AWS",
        "description": "Learn to manage big data architectures using AWS EMR, Athena, and Redshift.",
        "duration_hours": 32.0,
        "level": "Intermediate",
        "coverage_percentage": 95.0,
        "recommendation_rank": 1,
        "created_at": "2026-06-24T14:48:35.789012",
        "summary": {
          "id": 43,
          "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
          "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
          "occupation_id": "4ab2cdd3-2e21-4d30-bfa3-02f89cb211da",
          "course_id": "01b22ff3-99ab-48c0-8aef-41dcd9912cd3",
          "summary_type": "course_summary",
          "summary_text": "This course covers Apache Spark integration with AWS services which perfectly targets your missing skill in Spark.",
          "created_at": "2026-06-24T14:48:36.123456"
        }
      }
    ]
  }
  ```


---

## 7. Assessment API — sittings

A **sitting** is one run at a section's questions, from Start to Submit. Every route is scoped to a project the caller owns; a sitting id belonging to another project returns `404`.

**Only MCQs are served.** A section's 4 scenarios and 2 practical tasks exist in `course_section_questions` and are worth 70 of its 100 marks, but they need a human to mark and the system has no assessor role — so a sitting is scored out of the MCQ total (30) and `marks_available` states that on the row.

### **POST /api/projects/<project_id>/sections/<section_code>/sittings**
Start a sitting, or hand back the one already open.
- **Body**: `{"mode": "graded" | "practice", "restart": false}` — `mode` defaults to `graded`.
- **Response (201 Created)** — a new sitting:
  ```json
  {
    "sitting": {
      "sitting_id": "8fd8a924-af1e-473e-af3b-8608d7abe794",
      "project_id": "15f70153-ab03-4fba-8518-0bff41ae1053",
      "section_code": "NT-C-023-S01",
      "mode": "graded",
      "status": "in_progress",
      "time_limit_seconds": 1200,
      "seconds_remaining": 1200,
      "marks_awarded": null,
      "marks_available": 30,
      "started_at": "2026-08-20T02:18:14.221031",
      "submitted_at": null
    },
    "resumed": false
  }
  ```
- **Response (200 OK)** — a graded sitting was already open, so this is *continue previous attempt*. Identical shape with `"resumed": true`.
- **`"restart": true`** DELETES the unsubmitted sitting and its answers and starts fresh — this is *start new*, and it cannot be undone.
- **409** if the section's graded sitting is already submitted (`start a practice sitting instead`) or if the previous attempt expired and was auto-submitted. The response includes the existing `sitting`.
- **404** if the section code has no questions.

**One graded sitting per section, ever.** A unique index enforces it, which is what makes the score final: a second graded row cannot be inserted, so nothing can overwrite the first. At most one *open* practice sitting exists at a time; submitted practice runs accumulate as history.

### **GET /api/projects/<project_id>/sittings/<sitting_id>**
The paper as this sitting presents it, plus whatever has been answered.
- **Response (200 OK)**:
  ```json
  {
    "sitting": { "...": "as above" },
    "questions": [
      {
        "position": 1,
        "question_id": "c1bfdf84-73be-40a0-ae20-0764b79ddc7e",
        "stem": "Given a table:\n\n```sql\nCREATE TABLE person(...)\n```\nWhich rows are returned?",
        "options": ["...", "...", "...", "..."],
        "marks": 3,
        "answered_option": "B"
      }
    ]
  }
  ```
- **Question and option order are shuffled per sitting**, and nothing about the ordering is stored: both are a deterministic SHA-256 permutation of `sitting_id`, so a reload, another device and a later review all recompute the identical layout. The correct option is dealt from a balanced pool, so every sitting still gets exactly 3/3/2/2 across its ten questions.
- **`correct_option` and `explanation` are absent** for a graded sitting in progress — the server withholds them, so the client has nothing to leak. They appear once the sitting is `submitted`, and immediately per answered question in `practice` mode.

### **POST /api/projects/<project_id>/sittings/<sitting_id>/answers**
Record or revise answers. Accepts a batch; the whole batch commits once.
- **Body**: `{"answers": [{"question_id": "...", "selected_option": "A"}]}` — max 50 per request.
- **`selected_option` is the letter the student SAW.** The server maps it back through the sitting's shuffle; a client-supplied mapping is never accepted, because a client that could send one could mark itself correct.
- **Response (200 OK)**: `{"sitting": {...}, "saved": 1}`. In `practice` mode a `results` array is also returned, carrying `is_correct`, the displayed `correct_option`, `explanation` and `distractor_rationale`. A graded sitting returns no verdict at all.
- **409** if the sitting is `submitted` (cannot be changed) or `paused` (resume first).
- **400** for a repeated `question_id` in one batch, an option outside `A–D`, or a malformed body. **404** if the question is not in this sitting.
- **This is the only endpoint the frontend retries** — twice, on `503`/`429`/no-response. Safe by construction: a save is an upsert on `(sitting_id, question_id)`.

### **POST /api/projects/<project_id>/sittings/<sitting_id>/pause**
Stops the clock and banks the remaining seconds. `409` unless the sitting is `in_progress`.

### **POST /api/projects/<project_id>/sittings/<sitting_id>/resume**
Restarts the clock. `409` if the sitting is not `paused`, or if no time remains (the message distinguishes the two).

### **POST /api/projects/<project_id>/sittings/<sitting_id>/submit**
Closes the sitting and locks its score.
- **Response (200 OK)**: `{"sitting": {...}, "answered": 6, "total_questions": 10}` — the sitting now has `status: "submitted"`, a `submitted_at`, and a `marks_awarded` that will never change.
- Unanswered questions score nothing rather than blocking the submit.
- **409** if already submitted.

**The clock is enforced server-side, lazily.** `seconds_remaining` is only current as of the last pause; while a sitting runs, the elapsed time is subtracted by the database in the same query that reads the row. Every route resolves the clock first and **auto-submits an expired sitting**, so expiry applies the moment anyone asks and no sweeper process is needed.

### **GET /api/projects/<project_id>/progress**
Per-section state — what the syllabus button should say.
- **Response (200 OK)**:
  ```json
  [
    {
      "section_code": "NT-C-023-S01",
      "graded_status": "submitted",
      "marks_awarded": 27,
      "marks_available": 30,
      "submitted_at": "2026-08-20T02:10:02.114900",
      "open_practice_sitting_id": null,
      "practice_runs": 2
    }
  ]
  ```
- **Sections the student has not touched are absent**, not returned with zeros. The syllabus already knows every section, and inventing rows would make "not started" indistinguishable from "scored nothing". Absent → **Start**, `in_progress`/`paused` → **Continue or start new**, `submitted` → **Practice**.

---

## 8. Achievements API (`/api/achievements`)

XP, levels, streaks, badges and the leaderboard. **Everything is derived from submitted sittings on request** — there are no achievement tables and nothing to backfill, so a section submitted a second ago already counts.

**The XP rule**, stated once: a submitted **graded** sitting earns its marks (0–30) plus a flat **20** for clearing the section; a submitted **practice** sitting earns **5**, once per section however many times it is run. Practice is unlimited by design, so XP that scaled with it would be farmable. Graded sittings are capped at one per section, so the total is bounded by construction — 8,000 XP for the whole 160-section corpus, reaching level 13.

Levels lengthen: level *n* needs `100 × n` XP, so 100 / 300 / 600 / 1000 cumulative.

### **GET /api/achievements**
Always the caller's own, taken from the token. There is deliberately no id in the path.
- **Response (200 OK)**:
  ```json
  {
    "xp": 175,
    "level": 2,
    "xp_into_level": 75,
    "xp_for_level": 200,
    "streak": 4,
    "longest_streak": 4,
    "sections_submitted": 4,
    "courses_completed": 1,
    "marks_total": 90,
    "badges": [
      {
        "code": "perfect_section",
        "name": "Perfect 30",
        "icon": "💯",
        "criterion": "Score 30/30 in one section",
        "earned": true
      }
    ]
  }
  ```
- **Streaks count active days**, practice included, computed with a gaps-and-islands query over `DATE(submitted_at)`. A run counts as *current* if it reaches yesterday — a student mid-streak who has not opened the app today has not broken it.
- Eight badges, each carrying its own `criterion` text so the rule a student reads and the condition that awards it cannot drift.

### **GET /api/achievements/leaderboard?limit=10**
- **Response (200 OK)**: `{"entries": [{"position": 1, "xp": 175, "is_me": true}], "total_ranked": 1}`
- **Ranks and numbers only — never names.** A named board publishes one student's academic standing to another, which cannot be unseen. The caller's own row is always included even when it falls outside the top *n*.
- `limit` is clamped to 3–25.
