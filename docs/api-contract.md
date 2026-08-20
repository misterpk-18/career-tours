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

**Every endpoint below requires a bearer token except the health checks (`GET /`, `GET /db-test`) and the unauthenticated auth endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/verify-email`, `POST /api/auth/resend-verification`, `POST /api/auth/otp/request`, `POST /api/auth/otp/verify`, `POST /api/auth/password/forgot`, and `POST /api/auth/password/reset`.**

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
7b. [Course Assessment API — the project-independent track](#7b-course-assessment-api--the-project-independent-track)
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

JWT-based authentication for students. A successful login returns a signed **JWT** (HS256) alongside the student profile. The token encodes the `student_id` in its `sub` claim and expires after `JWT_EXPIRY_HOURS` (default 24). Registered users are stored in the same `students` table; `email` and `phone` are both **unique**, and passwords are stored only as salted hashes (`werkzeug`), never returned in responses. The serialized student now carries an **`email_verified`** boolean.

There are two ways to sign in — password and passwordless email OTP — plus email verification and password reset. Every email is sent from `Nipuna Careers <no-reply@nipunacareers.com>` via Amazon SES; the emailed secrets (verify/reset links, OTP codes) are stored only as hashes, are single-use, and expire. See [architecture.md](architecture.md#email-ses) for the SES/sandbox caveat.

**No account enumeration.** `resend-verification`, `otp/request` and `password/forgot` always return `200` with the same generic message whether or not the address is registered (and whether or not the mail actually sent). Do not branch on their response to infer membership.

### **POST /api/auth/register**
Creates a new student and emails a verification link. **It does not log the student in** — a new account must confirm its email before it can sign in with a password. Only `full_name`, `email`, and `password` are required (min 8 chars); optional profile fields (`phone`, `college_name`, …) may be included; blank strings are stored as NULL. Accounts that existed before email verification shipped were grandfathered to verified.
- **Request Body**: `{ "full_name": "...", "email": "...", "password": "...", "phone": "..." }`
- **Response (201 Created)** — no token; the client should show a "check your email" state:
  ```json
  {
    "message": "Account created. Check your email for a link to verify your address.",
    "email": "manoj@example.com",
    "requires_verification": true
  }
  ```
- **Response (400)** — a required field is missing. **Response (409)** — `{"error": "email already registered"}`.

### **POST /api/auth/verify-email**
Consumes a verification link's token and marks the address verified.
- **Request Body**: `{ "token": "<from the emailed link>" }`
- **Response (200)**: `{ "message": "Email verified. You can now sign in." }`
- **Response (400)** — invalid/expired/used token.

### **POST /api/auth/resend-verification**
Re-sends the verification link (subject to a 30s per-account cooldown).
- **Request Body**: `{ "email": "..." }` → **200** generic message (enumeration-safe).

### **POST /api/auth/login**
Authenticates by email and password and returns an access token.
- **Request Body**: `{ "email": "...", "password": "..." }`
- **Response (200 OK)**: `{ "token": "...", "student": { …, "email_verified": true } }`
- **Response (400)** — `email` or `password` missing.
- **Response (401)** — `{"error": "invalid email or password"}`.
- **Response (403)** — correct credentials but the address is unverified:
  ```json
  { "error": "Please verify your email before signing in.", "code": "email_unverified" }
  ```
  Clients branch on `code: "email_unverified"` to offer "resend verification".

### **POST /api/auth/otp/request**
Starts a passwordless login: mails a 6-digit code (10-minute expiry, 30s cooldown).
- **Request Body**: `{ "email": "..." }` → **200** generic message (enumeration-safe).

### **POST /api/auth/otp/verify**
Finishes a passwordless login. A correct code both signs in and marks the address verified (a delivered code proves inbox control). The code is attempt-capped (5) and single-use.
- **Request Body**: `{ "email": "...", "code": "123456" }`
- **Response (200 OK)**: `{ "token": "...", "student": { … } }` — identical shape to password login.
- **Response (401)** — `{"error": "That code is incorrect or has expired."}`.

### **POST /api/auth/password/forgot**
Mails a one-time reset link (1-hour expiry).
- **Request Body**: `{ "email": "..." }` → **200** generic message (enumeration-safe).

### **POST /api/auth/password/reset**
Sets a new password from a reset link's token; also clears any verification gate.
- **Request Body**: `{ "token": "<from the emailed link>", "password": "<min 8 chars>" }`
- **Response (200)**: `{ "message": "Password updated. You can now sign in." }`
- **Response (400)** — invalid/expired token, or password shorter than 8.

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
- **Response (400 Bad Request)**: `{ "error": "project_name is required" }`
- **Response (409 Conflict)** — the student already has an active project with this exact name (case-sensitive; a soft-deleted name is free to reuse):
  ```json
  { "error": "You already have a project with this name." }
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
Updates attributes of an existing project (e.g., changing status, name, description). Renaming to a name the student already uses on another active project returns **409** with the same "already have a project with this name" error as create.
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
**Soft delete.** The project vanishes from every read (it 404s afterward and drops out of the student's list), but the row and everything that cascades off it — sittings, scores, recommendations, the resume row — stay in the database. A `deleted_at` timestamp is stamped rather than the row removed.
- **Path Parameters**:
  - `project_id` (string, required): The UUID of the project to delete.
- **Response (200 OK)**: `{ "message": "project deleted successfully" }`
- **Response (404 Not Found)** — the project doesn't exist, isn't the caller's, or was already deleted (a second delete returns 404).

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

## 7b. Course Assessment API — the project-independent track

The same sitting flow as section 7, but a sitting is owned by the **student** rather than a project, and lives in its own tables (`course_section_sittings` / `course_question_attempts`). The two tracks are completely independent: a section can be sat in both, and neither score affects the other. Reachable from the catalogue course page, with no project in scope. Ownership is taken from the token on every route.

Sitting behaviour (start/get/answer/pause/resume/submit, the clock, the shuffle, grading out of the MCQ total of 30, practice-after-submit) is identical to section 7 — only the URLs and the owner differ.

| Method & path | Purpose |
|---|---|
| `POST /api/course-assessments/<course_id>/sections/<section_code>/sittings` | Start (or resume) a course-track sitting. Body `{"mode":"graded"\|"practice", "restart":bool}`. `course_id` is for symmetry/navigation; the sitting is keyed on student + section. → `201`/`200` with `{ "sitting": {…, "student_id", "project_id": null}, "resumed": bool }` |
| `GET /api/course-sittings/<sitting_id>` | The paper in this sitting's shuffled layout plus answers so far. Withholds the key for a graded sitting in progress. |
| `POST /api/course-sittings/<sitting_id>/answers` | Save a batch of answers. Practice returns per-question `results`. |
| `POST /api/course-sittings/<sitting_id>/pause` · `/resume` · `/submit` | Clock control and the once-only graded submit. |
| `GET /api/course-assessments/<course_id>/progress?course_code=NT-C-023` | Per-section state for that course, this student. `course_code` (the section prefix) is required. |
| `GET /api/course-achievements` | XP / level / streak / badges for the **course track** — a separate pool from `/api/achievements`, derived only from course-track sittings. |

Every sitting id is scoped to the caller; a stray id from another account returns `404`.

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
