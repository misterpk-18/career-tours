# Career Tours - Career Matching Engine

An AI-driven career matching platform. It manages student profiles, processes resumes, matches student skills to occupations, and produces career and course recommendations using natural language processing, vector embeddings, and LLM-powered summarization.

It also runs the assessments: a generated corpus of **2,560 questions** across all 40 courses (160 sections × 10 MCQ + 4 scenario + 2 practical), sat as timed, pausable, once-graded **sittings** with an anonymous XP leaderboard on top. See [docs/api-contract.md](docs/api-contract.md#7-assessment-api--sittings).

The repository is a monorepo with two applications:

| App | Path | Stack |
|---|---|---|
| **Backend** — REST API and the matching engine | [`backend/`](backend/) | Python 3, Flask, PostgreSQL |
| **Frontend** — student-facing web client | [`frontend/`](frontend/) | React 18, Vite, Tailwind CSS |

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/frontend.md](docs/frontend.md) | Frontend guide: stack, routing, API layer, styling conventions, how to add a page |
| [docs/career-matching-engine.md](docs/career-matching-engine.md) | Product logic: the 10-step matching pipeline, scoring formulas, LLM vs. deterministic split |
| [docs/database_relationship_documentation.md](docs/database_relationship_documentation.md) | All 20 tables, ER diagram, relationship walkthrough, recommendation data flow, the assessment tables |
| [docs/data-pipelines.md](docs/data-pipelines.md) | How the catalog tables get filled: the course-corpus and ESCO career imports, the generated section-question corpus, and how to re-run them |
| [docs/architecture.md](docs/architecture.md) | **Current runtime**: CloudFront → API Gateway → Lambda (container image) → Neon + S3 + OpenAI. Live AWS inventory, request path, env vars, build & deploy |
| [docs/api-contract.md](docs/api-contract.md) | **API contract**: every endpoint, its request/response shapes and error cases |
| [docs/career-tours-auth.postman_collection.json](docs/career-tours-auth.postman_collection.json) | Postman collection for the auth and resume endpoints |

---

## Tech Stack

**Backend**
- **Framework**: Python 3, Flask
- **Runtime**: **AWS Lambda**, deployed as an arm64 container image from ECR — see [docs/architecture.md](docs/architecture.md). `backend/app.py` exposes `handler` for Lambda via Mangum. Mangum is an ASGI adapter and Flask is a WSGI app, so `asgiref.wsgi.WsgiToAsgi` bridges the two. The same module also exposes `app`, which is what the local `flask run` development server binds.
- **Database**: PostgreSQL hosted on **Neon** — every environment, local included, connects to that one endpoint over TLS. Accessed via raw SQL (`sqlalchemy.text`) in the repository layer — not an ORM. `flask-sqlalchemy` is only used to manage the `db.session`/engine; domain objects are plain `dataclasses`, not `db.Model` classes.
- **AI & ML & Tracing**: OpenAI API, skill embeddings from `sentence-transformers/all-MiniLM-L6-v2` via the **Hugging Face Inference API** (`huggingface-hub`; requires `HF_TOKEN`), `numpy` for the cosine similarity, `langchain`, **LangSmith**. Nothing runs a model in-process — there is no `torch` dependency.
- **Document & Cloud Storage**: `pypdf`, `docx2txt`, **AWS S3** (`boto3`)

**Frontend**
- **Framework**: React 18 with plain JSX (no TypeScript), built by Vite 5
- **Routing / HTTP**: `react-router-dom` v6, `axios`
- **Styling**: Tailwind CSS 3 driven entirely by CSS custom properties. **One theme — Solarized Dark**; no light mode and no toggle. The accent ramp is adapted for text contrast, and the reasoning is in [docs/frontend.md](docs/frontend.md#the-colour-contract)
- **Question rendering**: `react-markdown` + `remark-gfm` + `lowlight` with 18 registered grammars — restricted markdown for the 2,560-question assessment corpus
- **Icons**: `lucide-react`

---

## Project Structure

```text
career-tours/
├── backend/                  # Flask API and matching engine
│   ├── app.py                # app factory, blueprint registration, health endpoints, Lambda handler
│   ├── api/                  # blueprints: auth, students, resumes, recommendations, projects
│   ├── config/               # database connection configuration
│   ├── models/               # plain dataclass DTOs representing domain entities
│   ├── repositories/         # data access layer — raw-SQL database interactions
│   ├── services/             # business logic, AI integration, file processing
│   │   ├── resume/           # PDF/DOCX text parsing and OpenAI skill extraction
│   │   ├── skills/           # skill normalization and mapping engines
│   │   ├── matching/         # embedding-based skill matching and occupation ranking
│   │   ├── recommendations/  # career tracks, skill gaps, course recommendations
│   │   └── storage/          # AWS S3 upload/retrieval for resume files
│   ├── scripts/              # one-off catalog imports — see docs/data-pipelines.md
│   ├── data/                 # reference data the matching engine reads
│   │   ├── lms/              # course knowledge corpus: 40 split PDFs + extracted profiles/modules
│   │   ├── imports/esco/     # careers.csv, skills.csv, career_skills.csv + validate.py
│   │   └── skill_taxonomy.json  # canonical skill vocabulary (repo-owned)
│   ├── migrations/           # incremental schema migrations
│   └── table_schemas/        # SQL DDL for each table (source of truth for the schema)
│                             # (no uploads/ dir — resumes are staged in /tmp, then S3)
│
├── frontend/                 # React + Vite web client
│   ├── src/
│   │   ├── App.jsx           # all routes + auth route guards
│   │   ├── pages/            # Login, Register, Home, ProjectDetails, Career/Course recs
│   │   ├── components/       # Navbar and modals
│   │   ├── context/          # AuthContext (JWT + student in localStorage)
│   │   ├── services/api.js   # the single axios module — every API call lives here
│   │   └── index.css         # Tailwind directives + shared .glass-* / .gradient-* classes
│   └── dist/                 # production build output (synced to S3, served by CloudFront)
│
├── docs/                     # all project documentation
├── Dockerfile                # arm64 Lambda container image
└── requirements.txt          # Python dependencies (repo root, not backend/)
```

> The Python packages use bare imports (`from api.auth.routes import auth_bp`), so the backend must be run with `backend/` as the working directory or on `sys.path`.

---

## Frontend

| Route | Access | Page |
|---|---|---|
| `/login`, `/register` | public | Authentication |
| `/` | protected | Dashboard — project list |
| `/projects/:projectId` | protected | Project workspace — resume upload, skill extraction, generate recommendations |
| `/projects/:projectId/careers` | protected | Top 5 career matches with AI insights and skill gaps |
| `/projects/:projectId/courses` | protected | Gap-filling course recommendations, grouped by career |

See [docs/frontend.md](docs/frontend.md) for the full guide.

---

## API

Every endpoint, with its request and response shapes and error cases, is documented in **[docs/api-contract.md](docs/api-contract.md)**.

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- Access to the project's Neon Postgres database (no local Postgres server is
  needed; the `psql` client is still useful for applying DDL by hand)

### 1. Clone the repository

```bash
git clone <repository-url>
cd career-tours
```

### Backend

1. **Set up a virtual environment** (at the repo root, not inside `backend/`):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**:
   Create a `.env` file in the repo root and configure the necessary environment variables:
   ```env
   # Database Configuration (Neon-hosted Postgres — see your Neon project's
   # connection details. There is no local Postgres; every environment,
   # including local development, talks to Neon.)
   DB_HOST=ep-your-endpoint.region.aws.neon.tech
   DB_PORT=5432
   DB_NAME=neondb
   DB_USER=neondb_owner
   DB_PASSWORD=your_neon_password
   DB_SSLMODE=require   # Neon rejects plaintext connections

   # Authentication (JWT)
   SECRET_KEY=your_long_random_secret   # e.g. python -c "import secrets; print(secrets.token_urlsafe(32))"
   JWT_EXPIRY_HOURS=24

   # OpenAI API Configuration
   OPENAI_API_KEY=your_openai_api_key

   # Hugging Face Inference API — required: skill embeddings come from
   # sentence-transformers/all-MiniLM-L6-v2 over the API. Without this,
   # recommendation generation fails.
   HF_TOKEN=your_hugging_face_token

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

4. **Database Initialization**:
   Apply the SQL DDL in `backend/table_schemas/` in dependency order, then the incremental scripts in `backend/migrations/`. How the catalog tables are then populated is in [docs/data-pipelines.md](docs/data-pipelines.md).

5. **Run the API** on port 5001, which is what the frontend dev proxy expects:
   ```bash
   cd backend && flask --app app run --port 5001 --debug
   ```
   `python backend/app.py` also works but binds Flask's default port **5000** — on macOS that port is already taken by the AirPlay Receiver, and the frontend proxy does not point there. See the note under [Frontend](#frontend-1) below.

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The dev server proxies `/api` to `http://127.0.0.1:5001`, so the backend must be listening on **5001**. Note that `python backend/app.py` starts Flask on its default port **5000**, which on macOS is also occupied by the AirPlay Receiver — use the `flask --app app run --port 5001` command above, or change the proxy `target` in `frontend/vite.config.js` to match whatever port you run.

To produce a production bundle:

```bash
npm run build                    # emits frontend/dist/
npm run preview                  # serve the built bundle locally
```

There is no linter or test suite configured in the frontend; a successful `npm run build` is the quality gate.

For production — building the arm64 image, pushing it to ECR, updating the Lambda, and syncing `frontend/dist` to S3 behind CloudFront — see [docs/architecture.md](docs/architecture.md). The live deployment is **https://nipunacareers.com**.
