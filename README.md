# Career Tours - Career Matching Engine

A Flask-based API application that powers an AI-driven career matching engine. The system manages student profiles, processes resumes, and provides intelligent career recommendations using natural language processing and vector embeddings.

## Tech Stack

- **Framework**: Python 3, Flask
- **Database**: PostgreSQL (with SQLAlchemy and `psycopg2`)
- **AI & ML & Tracing**: OpenAI API, `sentence-transformers`, `scikit-learn`, `langchain`, **LangSmith**
- **Document & Cloud Storage**: `pypdf`, `docx2txt`, **AWS S3** (`boto3`)

## Project Structure

- `api/`: API blueprints and route definitions (`students`, `resumes`, `recommendations`)
- `config/`: Configuration files (e.g., database connection)
- `models/`: SQLAlchemy database models
- `repositories/`: Data access layer handling database interactions
- `services/`: Business logic, AI integration, and file processing
- `migrations/`: Database migrations
- `tests/`: Test suite
- `uploads/`: Temporary local directory for processing resumes
- `utils/`: Helper functions and utilities
- `storage/` & `jobs/`: Background job handling and file storage

## Endpoints

- **`GET /`**: Health check.
- **`GET /db-test`**: Database connection test.
- **`/api/students`**: Endpoints for managing student profiles.
- **`/api/resumes`**: Endpoints for uploading and processing resumes (PDF/DOCX). Resumes are uploaded to AWS S3.
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
   Run the database migrations to set up the schema.

6. **Run the application**:
   ```bash
   python app.py
   ```
   The application will run on `http://127.0.0.1:5000` by default.
