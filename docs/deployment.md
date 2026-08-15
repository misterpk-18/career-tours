# Production Deployment Guide (EC2 & Nginx)

This guide documents the complete step-by-step process used to deploy **Career Tours** on an Amazon Linux 2023 EC2 instance: the Flask API behind **Gunicorn**, the React frontend as a static build, both fronted by an **Nginx** reverse proxy with a Let's Encrypt certificate.

> **The API now runs on AWS Lambda.** See **[docs/architecture.md](architecture.md)** for the
> current runtime shape, the live AWS inventory, and the build-and-deploy commands. That
> document is the source of truth; this one is the EC2 procedure it replaced.
>
> `backend/app.py` exports both entrypoints from the same code — `app` for a WSGI server and
> `handler` for Lambda via Mangum — so the steps below still work against an instance. Keep
> them only for as long as the EC2 box exists. Postgres is fully migrated either way: it is
> hosted on Neon and no longer runs on the instance.

Live deployment: **https://career-tours.duckdns.org** (instance `3.110.122.199`).
Always use the hostname — the certificate cannot cover a bare IP. Nginx `301`s
everything on port 80, the bare IP included, to that hostname, so a `curl` against
`http://3.110.122.199` needs `-L` or it returns only the redirect body and looks
broken.

> The instance has **no Elastic IP**: stopping and starting it changes the public
> address, which then has to be repointed at DuckDNS and is why earlier hosts
> (`13.203.206.148`, `13.204.83.160`) appear in this document's history.

### Repository layout on the server

The repo is a monorepo. Paths matter for the systemd unit and Nginx config:

```text
/home/ec2-user/career-tours/
├── requirements.txt        # Python deps — at the REPO ROOT
├── .env                    # runtime config — at the REPO ROOT
├── .venv/                  # virtualenv — at the REPO ROOT
├── backend/                # Flask app lives here; app.py is backend/app.py
│   └── table_schemas/      # SQL DDL
├── frontend/               # React + Vite source
│   └── dist/               # built static assets served by Nginx
└── docs/
```

The Python packages use bare imports (`from api.auth.routes import auth_bp`), so Gunicorn **must run with `backend/` as its working directory**.

---

## Architecture Overview

**The current architecture is documented in [docs/architecture.md](architecture.md)** —
API Gateway → Lambda (container image) → Neon + S3 + OpenAI. Read that first.

The diagram below is the **EC2 architecture**, kept because the instance still exists. Note
that Postgres no longer runs on it; even here, the database is Neon.

```text
[Client / Web Browser]
          │ https://career-tours.duckdns.org  (Port 443, Let's Encrypt)
          │ Port 80 → 301 redirect to HTTPS
          ▼
   [Nginx]
     ├── /            → static files from frontend/dist (SPA fallback)
     └── /api, /db-test → proxy to Gunicorn
                          │
                          ▼
              [Gunicorn WSGI Server] (Port 5000)
                          │ (Flask Application)
                          ▼
              [Neon PostgreSQL] (TLS, off-instance)
```

> **Port note:** production Gunicorn listens on **5000**. Local development is different — see `docs/frontend.md`; the Vite dev proxy targets **5001**.
>
> **On Lambda there is no port at all** — the function is invoked, not listened to. Anything
> below that tunes Gunicorn workers, Nginx timeouts or systemd is EC2-only.

---

## Prerequisites

Ensure your EC2 Security Group permits incoming traffic on:
- **Port 22** (SSH)
- **Port 80** (HTTP) — also required permanently for TLS certificate renewal, see Step 8
- **Port 443** (HTTPS) — see Step 8

For HTTPS you need a **hostname**: public certificate authorities will not issue
for a bare IP address. A free DuckDNS subdomain works (the current deployment uses
`career-tours.duckdns.org`); so does any domain you own.

Node.js 18+ is also required on the instance to build the frontend (Step 6). Alternatively, build `frontend/dist` locally and rsync it up — the live instance has neither Node nor Git installed, so it is deployed that way (see [Redeploying](#redeploying)).

---

## Step 1: System Optimization (Swap Space) — *optional*

This step existed because `sentence-transformers` loaded an embedding model
in-process and would OOM on a 1GB instance. Embeddings now come from the Hugging
Face Inference API and no model is loaded locally, so **swap is no longer
required**. It is still harmless insurance on a `t2.micro`/`t3.micro`; skip it
otherwise.

```bash
# Allocate 2GB file
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048

# Secure the permissions
sudo chmod 600 /swapfile

# Set up swap space
sudo mkswap /swapfile

# Enable swap
sudo swapon /swapfile

# Persist swap across system reboots
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

---

## Step 2: Install System Packages

Install Git, Nginx, and the PostgreSQL **client**. The server package is not
needed — Postgres is hosted on Neon, not on this instance — but `psql` is still
required for applying DDL and inspecting the database:

```bash
sudo dnf install -y nginx git postgresql15
```

---

## Step 3: Connect to Neon Postgres

There is no Postgres server on this instance. The database is hosted on Neon, and
every environment — local development, EC2, Lambda — connects to that same
endpoint over TLS.

1. **Collect the connection details** from the Neon console (Project → Connection
   Details). Export them for the rest of this guide; these are the same five
   values that go into the server's `.env`, plus the required SSL mode:
   ```bash
   export DB_HOST=ep-your-endpoint.region.aws.neon.tech
   export DB_PORT=5432
   export DB_NAME=neondb
   export DB_USER=neondb_owner
   read -rs DB_PASSWORD && export DB_PASSWORD
   export PGSSLMODE=require
   ```

   Neon **rejects plaintext connections** — a client with `sslmode=disable` fails
   to connect at all. `PGSSLMODE` above covers the `psql` commands in this guide;
   the application reads `DB_SSLMODE` from `.env` instead.

2. **Verify connectivity and enable the UUID extension**. Neon provisions the
   database and owner role for you, so there is no user or database to create —
   but `uuid-ossp` is not enabled by default and every table's primary key
   default depends on it:
   ```bash
   PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
     -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";' \
     -c 'SELECT current_database(), current_user;'
   ```

3. **Initialize Database Tables**:
   Import the SQL tables under `backend/table_schemas/` in their dependency order:
   ```bash
   cd /home/ec2-user/career-tours/backend/table_schemas
   for f in students.sql skills.sql occupations.sql questionnaires.sql courses.sql projects.sql resumes.sql skill_aliases.sql student_skills.sql occupation_skills.sql questionnaire_responses.sql course_skills.sql course_modules.sql student_career_matches.sql career_skill_gaps.sql course_recommendations.sql llm_summaries.sql project_skills.sql; do
       PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$f"
   done
   ```

4. **Apply Migrations**:
   `backend/table_schemas/` holds the original DDL; every schema change made since
   then lives in `backend/migrations/`, applied in filename order. They are
   idempotent enough to re-run, except `002` which fails if the constraint already
   exists — harmless:
   ```bash
   cd /home/ec2-user/career-tours/backend/migrations
   for f in $(ls *.sql | sort); do
       PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$f"
   done
   ```

5. **Seed the reference tables** — *required; the app is not functional without this.*

   Steps 3 and 4 create empty tables. Five of them are **reference (catalog) data**
   rather than user data, and nothing in the app ever writes them: `skills`,
   `courses`, `occupations`, `course_skills`, `occupation_skills`.

   Because all environments share the one Neon database, this seeding is done
   **once** — not per deploy. Check the counts below before re-running any of it.

   The matching engine scores a student's skills against `occupation_skills`. With no
   occupations, `POST /recommendations/projects/<id>/generate` **succeeds and returns
   zero matches**, which the UI renders as "No Career Recommendations Yet" — the same
   screen it shows when no skills have been extracted. There is no error anywhere, in
   any log. Verify with a row count before blaming anything else:

   ```bash
   PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
     SELECT 'courses' t, count(*) FROM courses
     UNION ALL SELECT 'occupations', count(*) FROM occupations
     UNION ALL SELECT 'skills', count(*) FROM skills
     UNION ALL SELECT 'course_skills', count(*) FROM course_skills
     UNION ALL SELECT 'occupation_skills', count(*) FROM occupation_skills ORDER BY 1;"
   ```

   If the counts come back zero, copy the rows in from a populated database (for
   the initial Neon load this was the old local `career_tours` database). `skills`
   is not optional even if only the other four are wanted — `course_skills` and
   `occupation_skills` have `NOT NULL` FKs to it.

   ```bash
   # Dump as column-level INSERTs, NOT -Fc: a version-specific archive is fragile
   # across servers, and plain INSERTs let you add ON CONFLICT below.
   pg_dump -h "$SOURCE_HOST" -U "$SOURCE_USER" -d "$SOURCE_DB" \
       --data-only --column-inserts --no-owner --no-privileges \
       -t public.skills -t public.courses -t public.occupations \
       -t public.course_skills -t public.occupation_skills > ref_data.sql
   ```

   Neon runs PostgreSQL 18, so the old `SET transaction_timeout` strip needed for
   the PostgreSQL 15 server on EC2 no longer applies — Neon accepts it. If the
   source is *newer* than the target you will still need that kind of workaround;
   check the server versions before assuming.

   Then rewrite each `INSERT` to end `ON CONFLICT DO NOTHING` before loading, so the
   file is additive and re-runnable. **Do not `TRUNCATE` to re-seed:**
   `course_recommendations`, `career_skill_gaps` and `student_career_matches` cascade
   off these tables and would take real user output with them. Copy the UUIDs
   verbatim rather than regenerating, so the FK graph stays intact and ids line up
   across environments.

   Neon is reachable from anywhere, so load it directly — no `scp` to the instance
   and no SSH hop:

   ```bash
   PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
       -v ON_ERROR_STOP=1 --single-transaction -f ref_data.sql
   ```

   `pg_dump` emits these five tables parent-before-child already, so no manual
   ordering is needed. Confirm afterwards that the counts are non-zero and that no
   orphan rows exist in the two junction tables.

---

## Step 4: Python Environment Setup

1. **Copy Application Code**:
   Sync or clone the project directory to `/home/ec2-user/career-tours/`. (Make sure to exclude `.venv`, `.git`, `node_modules`, and private SSH key files).

2. **Initialize Python Virtual Environment**:
   The virtualenv lives at the **repo root**, not inside `backend/`:
   ```bash
   cd /home/ec2-user/career-tours
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip --no-cache-dir
   ```

3. **Install Packages**:
   Install Gunicorn and other requirements (`requirements.txt` is at the repo root):
   ```bash
   .venv/bin/pip install --no-cache-dir -r requirements.txt
   ```

   There is no longer a separate CPU-only PyTorch step. `sentence-transformers`
   pulled in `torch` (~900MB of transitive dependencies) purely to embed skills
   in-process; that now goes through the Hugging Face Inference API, and the
   whole dependency set installs to ~220MB.

4. **Environment Configuration**:
   Create `/home/ec2-user/career-tours/.env` (repo root — the systemd unit loads it via `EnvironmentFile`) and add:
   ```env
   DB_HOST=ep-your-endpoint.region.aws.neon.tech
   DB_PORT=5432
   DB_NAME=neondb
   DB_USER=neondb_owner
   DB_PASSWORD=your_neon_password
   DB_SSLMODE=require

   # Auth
   SECRET_KEY=your_jwt_signing_secret
   JWT_EXPIRY_HOURS=24

   # External Integrations
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=your_langsmith_api_key
   LANGSMITH_PROJECT=your_project_name

   OPENAI_API_KEY=your_openai_key

   # Required — skill embeddings come from the Hugging Face Inference API.
   # Recommendation generation fails without it.
   HF_TOKEN=your_hugging_face_token

   AWS_ACCESS_KEY=your_aws_access_key
   AWS_SECRET_KEY=your_aws_secret_key
   AWS_REGION=ap-south-1
   AWS_BUCKET_NAME=career-tours-data
   ```

   > systemd's `EnvironmentFile` parser is not a shell: write `KEY=value` with no
   > `export`, and quote any value containing spaces. A value that happens to be
   > valid-looking shell will still break `source .env` in bash even though systemd
   > accepts it, so prefer quoting throughout.

---

## Step 5: Configure Gunicorn Service

Create the systemd service file `/etc/systemd/system/career-tours.service`:

```ini
[Unit]
Description=Gunicorn instance for Career Tours Flask API
After=network.target postgresql.service

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/career-tours/backend
Environment="PATH=/home/ec2-user/career-tours/.venv/bin"
EnvironmentFile=/home/ec2-user/career-tours/.env
ExecStart=/home/ec2-user/career-tours/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 --timeout 300 --access-logfile /var/log/career-tours/access.log --error-logfile /var/log/career-tours/error.log --capture-output app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Important:** `WorkingDirectory` must be `.../career-tours/backend` (not the repo root). `app.py` lives in `backend/` and imports its packages with bare names (`from api.auth.routes import auth_bp`), so `app:app` only resolves when Gunicorn is started from inside `backend/`. The virtualenv, `.env`, and log paths still point at the repo root.
>
> The same bare-import constraint applies to Lambda: the handler is `app.handler`,
> and `backend/` must be the root of the deployment package (or the Docker
> `WORKDIR`) or the import fails the same way.
>
> If you are upgrading an existing deployment that predates the `backend/` restructure, this line is the one change that will otherwise break the service with `ModuleNotFoundError: No module named 'app'`.

Create logging folders and enable the service:
```bash
sudo mkdir -p /var/log/career-tours
sudo chown ec2-user:ec2-user /var/log/career-tours

sudo systemctl daemon-reload
sudo systemctl enable career-tours --now
```

> **No upload directory is needed.** `UPLOAD_DIR = Path("/tmp/uploads/resumes")` in
> `backend/api/resumes/routes.py`, and it is created at import time. It is an absolute path
> on both runtimes — Lambda's `/tmp` is the only writable filesystem there, and a relative
> path would resolve under the read-only `/var/task` and kill the app before it served a
> request. Earlier versions of this guide told you to `mkdir backend/uploads/resumes`; that
> directory is no longer used by anything. The file is deleted after being pushed to S3 on
> every code path, so `/tmp` does not accumulate.

---

## Step 6: Build the Frontend

The React app is a static bundle — there is no Node process in production. Build it once per release:

```bash
cd /home/ec2-user/career-tours/frontend
npm ci
npm run build          # emits frontend/dist/
```

The bundle calls the API at the relative path `/api` (see `frontend/src/services/api.js`), so no build-time environment variables are needed — Nginx routes `/api` to Gunicorn on the same origin.

Nginx (running as the `nginx` user) must be able to traverse into the directory:

```bash
sudo chmod o+x /home/ec2-user /home/ec2-user/career-tours /home/ec2-user/career-tours/frontend
```

On a low-memory instance the Vite build can be OOM-killed. If that happens, build on your workstation and sync the output instead:

```bash
# from your local machine
cd frontend && npm run build
rsync -avz --delete dist/ ec2-user@<host>:/home/ec2-user/career-tours/frontend/dist/
```

---

## Step 7: Configure Nginx (static frontend + API proxy)

1. **Delete Default Conf**:
   Clean up the default server block from `/etc/nginx/nginx.conf` by removing or commenting out the `server { ... }` block inside the `http { ... }` context.

2. **Add Custom Server Block**:
   Create a new file at `/etc/nginx/conf.d/career-tours.conf`. The frontend is served as static files with an SPA fallback; only API paths are proxied to Gunicorn:
   ```nginx
   server {
       listen 80 default_server;
       listen [::]:80 default_server;
       server_name career-tours.duckdns.org 3.110.122.199; # your hostname, then the public IP

       # Allow large payloads (resume file uploads up to 10MB)
       client_max_body_size 10M;

       access_log /var/log/nginx/career_tours_access.log;
       error_log  /var/log/nginx/career_tours_error.log info;

       root /home/ec2-user/career-tours/frontend/dist;
       index index.html;

       # React Router owns client-side routes (e.g. /projects/<id>/courses).
       # Serve the file if it exists, otherwise hand back index.html so a deep
       # link or a browser refresh does not 404.
       location / {
           try_files $uri $uri/ /index.html;
       }

       # Hashed Vite assets are immutable — cache them hard.
       location /assets/ {
           expires 1y;
           add_header Cache-Control "public, immutable";
           try_files $uri =404;
       }

       # Never cache the app shell, or clients pin to a stale bundle.
       location = /index.html {
           add_header Cache-Control "no-store";
       }

       # Flask API + health endpoints
       location ~ ^/(api|db-test)(/|$) {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;

           # Increase timeouts to accommodate heavy LLM processing times
           proxy_read_timeout 300s;
           proxy_connect_timeout 75s;
       }
   }
   ```

   > The Flask `GET /` health check is no longer reachable at `/` — that path now serves the frontend. Use `/db-test` for health checks, or query Gunicorn directly on the instance with `curl -i http://127.0.0.1:5000/`.

   The repo-root `nginx.conf` mirrors what is actually deployed, including the
   Certbot-managed TLS lines added in Step 8. Certbot rewrites those on the server
   during renewal, so treat the instance as the source of truth and copy changes
   back into `nginx.conf`, not the other way round.

3. **Start Nginx**:
   ```bash
   sudo nginx -t # Validate syntax
   sudo systemctl enable nginx --now
   ```

---

## Step 8: Enable HTTPS (Let's Encrypt)

Served over plain HTTP, browsers mark the site "Not secure" and login passwords
cross the network in cleartext. Fixing that needs a **hostname** — Let's Encrypt
will not issue a certificate for a bare IP, so `https://3.110.122.199` can never
be trusted no matter what is configured.

1. **Point a hostname at the instance.** The deployment uses DuckDNS: register a
   subdomain at [duckdns.org](https://www.duckdns.org) and set its IP to the
   instance's public address. DuckDNS pre-fills the IP of whatever machine you are
   browsing from, so this almost always needs correcting. Verify before continuing —
   certbot's HTTP-01 challenge must reach *this* server:
   ```bash
   dig +short career-tours.duckdns.org      # must print the instance's public IP
   ```

2. **Add the hostname to `server_name`** in `/etc/nginx/conf.d/career-tours.conf`
   (Step 7) and reload, so the certbot nginx plugin can find the right block.

3. **Issue and install the certificate.** Port 443 must be open in the security
   group first:
   ```bash
   sudo dnf install -y certbot python3-certbot-nginx

   sudo certbot --nginx -d career-tours.duckdns.org \
       --agree-tos -m you@example.com --no-eff-email \
       --redirect --non-interactive
   ```
   Certbot rewrites the Nginx block in place: it adds the `listen 443 ssl` server,
   wires in the certificate paths, and (from `--redirect`) adds a port-80 server
   that 301s the hostname to HTTPS. Keep port 80 open — renewals validate over it.

   Certbot's generated port-80 block ends in `return 404` for any Host it does not
   recognise, which **breaks existing links that used the bare IP**. Replace the
   generated `if ($host = ...)` / `return 404` pair with an unconditional redirect
   to the canonical origin (see the repo-root `nginx.conf`):
   ```nginx
   return 301 https://career-tours.duckdns.org$request_uri;
   ```

4. **Enable the renewal timer — certbot does not do this for you.** On Amazon
   Linux 2023 the package ships `certbot-renew.timer` but leaves it disabled, while
   certbot's success message still claims "Certbot has set up a scheduled task to
   automatically renew this certificate." It has not. Unless you enable the timer,
   the certificate expires 90 days later with no warning:
   ```bash
   sudo systemctl enable --now certbot-renew.timer
   systemctl list-timers certbot-renew.timer   # must list one timer
   sudo certbot renew --dry-run                # must report success
   ```
   The renewal config records `installer = nginx`, so Nginx is reloaded
   automatically once a renewal lands.

> **The DNS record is static.** Stopping and starting an EC2 instance assigns a new
> public IP, and the hostname will keep pointing at the old one — breaking the site
> and every future renewal. Attach an **Elastic IP**, or run a DuckDNS updater on
> the box (`curl "https://www.duckdns.org/update?domains=<sub>&token=<token>&ip="`
> on a timer; an empty `ip=` makes DuckDNS use the caller's address).

---

## Redeploying

> **Deploying the Lambda is a different procedure entirely** — `docker buildx` for arm64,
> push to ECR, `aws lambda update-function-code`. It is in
> [docs/architecture.md § Deploying](architecture.md#deploying). The rsync flow below only
> updates the EC2 instance.

If the instance has Git and Node:

```bash
cd /home/ec2-user/career-tours
git pull

# backend
.venv/bin/pip install --no-cache-dir -r requirements.txt   # only if deps changed
sudo systemctl restart career-tours

# frontend
cd frontend && npm ci && npm run build
# static files are picked up immediately; no Nginx reload needed
```

**The live instance has neither**, so it is deployed by pushing from a workstation.
Build the bundle locally and rsync both halves up:

```bash
# from a local clone, at the repo root
cd frontend && npm ci && npm run build && cd ..

HOST=ec2-user@3.110.122.199
KEY=~/Downloads/my_first_key_pair_ct.pem   # the older career_tours_key_pair.pem is NOT valid on this instance

# backend code — never sync uploads/ (server-owned user data) or the venv/.env.
# data/imports is untracked local staging (~4MB) and the box has little free disk.
rsync -az --delete -e "ssh -i $KEY" \
    --exclude __pycache__ --exclude '*.pyc' --exclude uploads --exclude 'data/imports' \
    backend/ $HOST:/home/ec2-user/career-tours/backend/

# built frontend
rsync -az --delete -e "ssh -i $KEY" \
    frontend/dist/ $HOST:/home/ec2-user/career-tours/frontend/dist/

rsync -az -e "ssh -i $KEY" requirements.txt README.md docs $HOST:/home/ec2-user/career-tours/

ssh -i $KEY $HOST 'sudo systemctl restart career-tours'
```

`--delete` is scoped to `backend/` and `frontend/dist/` deliberately: the repo-root
`.env`, `.venv/`, and `backend/uploads/` live only on the server and must survive a
deploy. Apply any new `backend/migrations/*.sql` before restarting.

---

## Verification Commands

- **Check Service Status**:
  ```bash
  sudo systemctl status career-tours
  sudo systemctl status nginx
  ```

- **Inspect Logs**:
  ```bash
  # Gunicorn error log — application tracebacks land here only because of
  # --capture-output (Step 5). Without that flag Gunicorn leaves the app's
  # stdout/stderr alone and tracebacks go to the journal instead, so this file
  # shows nothing but worker lifecycle noise.
  tail -f /var/log/career-tours/error.log

  # Everything the service wrote, regardless of Gunicorn's log routing
  sudo journalctl -u career-tours -f

  # Nginx access log
  tail -f /var/log/nginx/career_tours_access.log
  ```

- **Open a psql session against Neon** (from the instance or any workstation —
  Neon is not instance-local, so there is nothing special about running this on
  EC2):
  ```bash
  # There is no local Postgres and no local socket: host/user must always be
  # given explicitly. Source the .env instead of hardcoding credentials anywhere.
  set -a; . /home/ec2-user/career-tours/.env; set +a
  PGPASSWORD="$DB_PASSWORD" PGSSLMODE="${DB_SSLMODE:-require}" \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
  ```

- **Query Endpoints** (on the instance):
  ```bash
  # Frontend shell (should return HTML, not JSON)
  curl -i http://localhost/

  # Flask app health, bypassing Nginx
  curl -i http://127.0.0.1:5000/

  # Check PostgreSQL connection status (proxied through Nginx)
  curl -i http://localhost/db-test

  # SPA deep link must return 200 + HTML, not 404
  curl -i -o /dev/null -w '%{http_code}\n' http://localhost/projects/abc/courses
  ```

- **Verify TLS from outside** (from any machine). `ssl_verify_result` must be `0` —
  anything else means browsers will still warn:
  ```bash
  D=career-tours.duckdns.org
  curl -s -o /dev/null -w '%{http_code} verify=%{ssl_verify_result}\n' https://$D/
  curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://$D/   # expect 301
  curl -s https://$D/db-test

  # Certificate subject and expiry
  echo | openssl s_client -connect $D:443 -servername $D 2>/dev/null \
      | openssl x509 -noout -subject -dates
  ```

- **Common failure modes**:

  | Symptom | Cause |
  |---|---|
  | `ModuleNotFoundError: No module named 'app'` in the Gunicorn error log | `WorkingDirectory` is not `.../career-tours/backend` (Step 5) |
  | Nginx `403 Forbidden` on `/` | `nginx` user cannot traverse into `/home/ec2-user/...` (see the `chmod o+x` in Step 6) |
  | Deep links 404 but `/` works | `try_files ... /index.html` fallback missing from the `location /` block |
  | Frontend loads but every API call 404s | requests are hitting the static `root` instead of the proxy — check the `location ~ ^/(api|db-test)` regex block |
  | "Not secure" in the browser | the site was opened over `http://`, or by IP — the certificate only covers the hostname (Step 8) |
  | Certificate expired unnoticed | `certbot-renew.timer` was never enabled; certbot's success message wrongly claims it was (Step 8.4) |
  | Renewal fails with a challenge error | port 80 was closed after setup, or the hostname now resolves to a stale IP (see the Elastic IP note in Step 8) |
  | `password authentication failed for user "manojtungala"` | the real password is `DB_PASSWORD` in the server's `.env`; no password is committed to this repo |
