# Production Deployment Guide (EC2 & Nginx)

This guide documents the complete step-by-step process used to deploy the **Career Tours - Career Matching Engine** Flask API on an Amazon Linux 2023 EC2 instance with **Gunicorn** and **Nginx** reverse proxy.

---

## Architecture Overview

```text
[Client / Web Browser] 
          │ (Port 80 / HTTP)
          ▼
   [Nginx Reverse Proxy]
          │ (Internal Proxy)
          ▼
   [Gunicorn WSGI Server] (Port 5000)
          │ (Flask Application)
          ▼
   [PostgreSQL Database] (Port 5432)
```

---

## Prerequisites

Ensure your EC2 Security Group permits incoming traffic on:
- **Port 22** (SSH)
- **Port 80** (HTTP)

---

## Step 1: System Optimization (Swap Space)

To run NLP embedding models (`sentence-transformers`) on a resource-constrained instance (like a `t2.micro` or `t3.micro` with 1GB RAM), configure a **2GB swap file** to prevent Out Of Memory (OOM) crashes:

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

Install Git, Nginx, PostgreSQL 15 server, and the PostgreSQL contrib extensions:

```bash
sudo dnf install -y nginx git postgresql15-server postgresql15-contrib
```

---

## Step 3: Configure Local PostgreSQL

1. **Initialize the Database**:
   ```bash
   sudo postgresql-setup --initdb
   ```

2. **Configure Authentication Method**:
   By default, loopback TCP connections use `ident` matching which requires OS users to match DB users. We change this to password-based authentication (`scram-sha-256`):
   ```bash
   # Update pg_hba.conf
   sudo sed -i 's/ident/scram-sha-256/g' /var/lib/pgsql/data/pg_hba.conf
   ```

3. **Start and Enable PostgreSQL**:
   ```bash
   sudo systemctl enable postgresql --now
   ```

4. **Create Users and Databases**:
   Log in as the superuser `postgres` and set up the application roles:
   ```bash
   # Create database user and set superuser permissions
   sudo -u postgres psql -c "CREATE USER manojtungala WITH PASSWORD '12345678' SUPERUSER;"
   
   # Create the database owned by the application user
   sudo -u postgres psql -c "CREATE DATABASE career_tours OWNER manojtungala;"
   
   # Enable the UUID extension in the target database
   sudo -u postgres psql -d career_tours -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
   ```

5. **Initialize Database Tables**:
   Import the SQL tables under `table_schemas/` in their dependency order:
   ```bash
   cd /home/ec2-user/career-tours/table_schemas
   for f in students.sql skills.sql occupations.sql questionnaires.sql courses.sql projects.sql resumes.sql skill_aliases.sql student_skills.sql occupation_skills.sql questionnaire_responses.sql course_skills.sql student_career_matches.sql career_skill_gaps.sql course_recommendations.sql llm_summaries.sql project_skills.sql; do
       PGPASSWORD=12345678 psql -h 127.0.0.1 -U manojtungala -d career_tours -f "$f"
   done
   ```

---

## Step 4: Python Environment Setup

1. **Copy Application Code**:
   Sync or clone the project directory to `/home/ec2-user/career-tours/`. (Make sure to exclude `.venv`, `.git`, and private SSH key files).

2. **Initialize Python Virtual Environment**:
   ```bash
   cd /home/ec2-user/career-tours
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip --no-cache-dir
   ```

3. **Install CPU-only PyTorch**:
   To fit inside typical EC2 disk space limits, install the lightweight, CPU-only PyTorch wheel (~200MB vs the standard ~900MB CUDA wheel):
   ```bash
   .venv/bin/pip install --no-cache-dir torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
   ```

4. **Install Remaining Packages**:
   Install Gunicorn and other requirements:
   ```bash
   .venv/bin/pip install --no-cache-dir -r requirements.txt
   ```

5. **Environment Configuration**:
   Create `/home/ec2-user/career-tours/.env` and add:
   ```env
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_NAME=career_tours
   DB_USER=manojtungala
   DB_PASSWORD=12345678

   # External Integrations
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=your_langsmith_api_key
   LANGSMITH_PROJECT=your_project_name

   OPENAI_API_KEY=your_openai_key
   AWS_ACCESS_KEY=your_aws_access_key
   AWS_SECRET_KEY=your_aws_secret_key
   AWS_REGION=ap-south-1
   AWS_BUCKET_NAME=career-tours-data
   ```

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
WorkingDirectory=/home/ec2-user/career-tours
Environment="PATH=/home/ec2-user/career-tours/.venv/bin"
EnvironmentFile=/home/ec2-user/career-tours/.env
ExecStart=/home/ec2-user/career-tours/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 --timeout 300 --access-logfile /var/log/career-tours/access.log --error-logfile /var/log/career-tours/error.log app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create logging folders and enable the service:
```bash
sudo mkdir -p /var/log/career-tours
sudo chown ec2-user:ec2-user /var/log/career-tours

sudo systemctl daemon-reload
sudo systemctl enable career-tours --now
```

---

## Step 6: Configure Nginx Reverse Proxy

1. **Delete Default Conf**:
   Clean up the default server block from `/etc/nginx/nginx.conf` by removing or commenting out the `server { ... }` block inside the `http { ... }` context.

2. **Add Custom Server Block**:
   Create a new file at `/etc/nginx/conf.d/career-tours.conf`:
   ```nginx
   server {
       listen 80 default_server;
       listen [::]:80 default_server;
       server_name 13.126.175.239; # Replace with your Domain or Public IP

       # Allow large payloads (resume file uploads up to 10MB)
       client_max_body_size 10M;

       access_log /var/log/nginx/career_tours_access.log;
       error_log  /var/log/nginx/career_tours_error.log info;

       location / {
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

3. **Start Nginx**:
   ```bash
   sudo nginx -t # Validate syntax
   sudo systemctl enable nginx --now
   ```

---

## Verification Commands

- **Check Service Status**:
  ```bash
  sudo systemctl status career-tours
  sudo systemctl status nginx
  ```

- **Inspect Logs**:
  ```bash
  # Gunicorn error log
  tail -f /var/log/career-tours/error.log
  # Nginx access log
  tail -f /var/log/nginx/career_tours_access.log
  ```

- **Query Endpoints**:
  ```bash
  # Check Flask app health
  curl -i http://localhost/
  
  # Check PostgreSQL connection status
  curl -i http://localhost/db-test
  ```
