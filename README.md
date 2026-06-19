# Career Tours - Career Matching Engine

A Flask-based API application that powers an AI-driven career matching engine. The system manages student profiles, processes resumes, and provides intelligent career recommendations using natural language processing and vector embeddings.

## Tech Stack

- **Framework**: Python 3, Flask
- **Database**: PostgreSQL (with SQLAlchemy and `psycopg2`)
- **AI & ML**: OpenAI API, `sentence-transformers`, `scikit-learn`, `langchain`
- **Document Processing**: `pypdf`, `docx2txt`

## Project Structure

- `api/`: API blueprints and route definitions (`students`, `resumes`, `recommendations`)
- `config/`: Configuration files (e.g., database connection)
- `models/`: SQLAlchemy database models
- `repositories/`: Data access layer handling database interactions
- `services/`: Business logic, AI integration, and file processing
- `migrations/`: Database migrations
- `tests/`: Test suite
- `uploads/`: Storage for uploaded resumes
- `utils/`: Helper functions and utilities
- `storage/` & `jobs/`: Background job handling and file storage

## Endpoints

- **`GET /`**: Health check.
- **`GET /db-test`**: Database connection test.
- **`/api/students`**: Endpoints for managing student profiles.
- **`/api/resumes`**: Endpoints for uploading and processing resumes (PDF/DOCX).
- **`/api/recommendations`**: Endpoints for generating and retrieving career recommendations based on profiles and resumes.

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
   Create a `.env` file in the root directory and configure the necessary environment variables (e.g., `DATABASE_URL`, `OPENAI_API_KEY`).

5. **Database Initialization**:
   Run the database migrations to set up the schema.

6. **Run the application**:
   ```bash
   python app.py
   ```
   The application will run on `http://127.0.0.1:5000` by default.
