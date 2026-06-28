# Career Tours - Career Matching Engine

A Flask-based API application that powers an AI-driven career matching engine. The system manages student profiles, processes resumes, matches student skills to occupations, and provides intelligent career and course recommendations using natural language processing, vector embeddings, and LLM-powered summarization.

---

## Tech Stack

- **Framework**: Python 3, Flask, Flask-SQLAlchemy
- **Database**: PostgreSQL (with SQLAlchemy and `psycopg2`)
- **AI & ML & Tracing**: OpenAI API, `sentence-transformers` (pre-downloaded locally for offline use), `scikit-learn`, `langchain`, **LangSmith**
- **Document & Cloud Storage**: `pypdf`, `docx2txt`, **AWS S3** (`boto3`)

---

## Project Structure

- `api/`: API blueprints and route definitions (`students`, `resumes`, `recommendations`, `projects`)
- `config/`: Configuration files (e.g., database connection)
- `models/`: SQLAlchemy database models
- `repositories/`: Data access layer handling database interactions
- `services/`: Business logic, AI integration, and file processing
  - `resume/`: PDF/DOCX text parsing and OpenAI skill extraction pipelines
  - `skills/`: Skill normalization and mapping engines
  - `matching/`: Embedding-based skill matching and occupational ranking models
  - `reccomendations/`: Generation of student career tracks, skill gaps, and course recommenders
- `migrations/`: Database migrations
- `tests/`: Extensive test suite covering unit tests and live integration tests
- `uploads/`: Temporary local directory for processing resumes
- `utils/`: Helper functions and utilities

---

## API Reference

All requests and responses use the `application/json` content type unless specified otherwise. URL paths are relative to the root URL (e.g., `http://127.0.0.1:5000`).

### Table of Contents
1. [Base & Health Check](#1-base--health-check)
2. [Student Management API (`/api/students`)](#2-student-management-api-apistudents)
3. [Project Management API (`/api/projects`)](#3-project-management-api-apiprojects)
4. [Resume Parsing & Skill Extraction API (`/api/resumes`)](#4-resume-parsing--skill-extraction-api-apiresumes)
5. [Recommendation Engine API (`/api/recommendations`)](#5-recommendation-engine-api-apirecommendations)

---

### 1. Base & Health Check

#### **GET /**
Checks the operational health of the Flask application server.
- **Request Headers**: None
- **Response (200 OK)**:
  ```json
  {
    "status": "ok"
  }
  ```

#### **GET /db-test**
Tests active connectivity to the PostgreSQL database.
- **Request Headers**: None
- **Response (200 OK)**:
  ```json
  {
    "database": "career_tours"
  }
  ```
- **Response (500 Internal Server Error)**:
  ```json
  {
    "error": "database connection failed"
  }
  ```

---

### 2. Student Management API (`/api/students`)

#### **POST /api/students**
Registers a new student profile in the system.
- **Request Body**:
  ```json
  {
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
    "work_mode_preference": "Hybrid"
  }
  ```
- **Response (201 Created)**:
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
    "error": "full_name is required"
  }
  ```

#### **GET /api/students/<student_id>**
Retrieves details of an existing student profile by UUID.
- **Path Parameters**:
  - `student_id` (string, required): The UUID of the student.
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

### 3. Project Management API (`/api/projects`)

Projects represent specific career-matching tracks, goals, or workflows created for a student.

#### **POST /api/projects**
Creates a new project track for a student.
- **Request Body**:
  ```json
  {
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
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

#### **GET /api/projects/<project_id>**
Retrieves a project's details by its UUID.
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
    "created_at": "2026-06-24T14:35:00.111222",
    "updated_at": "2026-06-24T14:35:00.111222"
  }
  ```

#### **GET /api/projects/student/<student_id>**
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

#### **PUT /api/projects/<project_id>**
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

#### **DELETE /api/projects/<project_id>**
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

### 4. Resume Parsing & Skill Extraction API (`/api/resumes`)

Processes physical CV documents, uploads them to AWS S3, extracts the raw text, and triggers GenAI-powered skill extraction.

#### **POST /api/resumes/upload**
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

#### **GET /api/resumes/<resume_id>**
Retrieves an uploaded resume's metadata and its extracted raw text content.
- **Path Parameters**:
  - `resume_id` (string, required): The UUID of the resume.
- **Response (200 OK)**:
  ```json
  {
    "resume_id": "0d61fb19-6ab7-47b2-bd75-47e2a9b6b801",
    "student_id": "8fa134d1-c290-482a-89a1-6380cde5d2fe",
    "project_id": "90e66ad3-8b77-4c7b-a3ee-851f89bc101a",
    "file_url": "https://your-s3-bucket.s3.amazonaws.com/0d61fb19-6ab7-47b2-bd75-47e2a9b6b801.pdf",
    "raw_text": "Manoj Tungala\nCloud and GenAI Engineer...\n...",
    "parsed_at": "2026-06-24T14:42:00.123456",
    "created_at": "2026-06-24T14:41:55.789012"
  }
  ```

#### **POST /api/resumes/<resume_id>/extract-skills**
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

### 5. Recommendation Engine API (`/api/recommendations`)

Computes matching scores against active occupational profiles and suggests career paths, bridges gaps, and aligns courses.

#### **POST /api/recommendations/projects/<project_id>/generate**
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

#### **GET /api/recommendations/projects/<project_id>/careers**
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

#### **GET /api/recommendations/projects/<project_id>/courses**
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

#### **GET /api/recommendations/projects/<project_id>**
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

#### **GET /api/recommendations/projects/<project_id>/careers/<occupation_id>**
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

#### **GET /api/recommendations/projects/<project_id>/careers/<occupation_id>/courses**
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

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd career-tours
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file in the root directory and configure the necessary environment variables:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=career_tours
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password

   # OpenAI API Configuration
   OPENAI_API_KEY=your_openai_api_key

   # LangSmith Tracing Configuration
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=your_langsmith_api_key
   LANGSMITH_PROJECT=your_project_name

   # AWS S3 Storage Configuration
   AWS_ACCESS_KEY=your_aws_access_key
   AWS_SECRET_KEY=your_aws_secret_key
   AWS_REGION=your_aws_region
   AWS_BUCKET_NAME=your_s3_bucket_name
   ```

5. **Database Initialization**:
   Run the database migrations or setup SQL scripts to configure the schema.

6. **Run the application**:
   ```bash
   python app.py
   ```
   The application will run on `http://127.0.0.1:5000` by default.
