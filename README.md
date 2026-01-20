# Grant-Forge Admin App (FastAPI)

## What it is
Private admin console to create requests, run Grant-Forge, generate a PDF, email it, and track status.

## Required env vars
### Admin gate
- ADMIN_USER
- ADMIN_PASS

### Database (Railway Postgres)
- DATABASE_URL

### Email (SMTP)
- SMTP_HOST
- SMTP_PORT (usually 465)
- SMTP_USER
- SMTP_PASS
- MAIL_FROM

### Optional
- REPORT_DIR (defaults to /tmp/grant_forge_reports)

## Routes
- GET  /admin (Basic Auth)
- POST /admin/new
- POST /admin/run/{id}
- GET  /admin/download/{id}
- POST /admin/delivered/{id}
- POST /admin/archive/{id}
- POST /admin/delete/{id}

## Run locally
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
