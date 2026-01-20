import os
import secrets
import uuid
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import Dict, Any, Optional, List

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

app = FastAPI()

# ------------------------
# Admin Gate (Basic Auth)
# ------------------------
security = HTTPBasic()

def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(credentials.username, os.getenv("ADMIN_USER", ""))
    pass_ok = secrets.compare_digest(credentials.password, os.getenv("ADMIN_PASS", ""))
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# ------------------------
# DB
# ------------------------
def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")

# ------------------------
# Report output dir
# ------------------------
REPORT_DIR = os.getenv("REPORT_DIR", "/tmp/grant_forge_reports")
os.makedirs(REPORT_DIR, exist_ok=True)

def safe_slug(s: str) -> str:
    keep = []
    for ch in (s or "").strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in (" ", "-", "_"):
            keep.append("_")
    out = "".join(keep).strip("_")
    return out[:40] if out else "UNKNOWN"

# ------------------------
# Grant-Forge core stub (replace with sealed logic)
# ------------------------
def run_grant_forge(intake: Dict[str, Any]) -> str:
    grant = intake.get("grant_name", "UNKNOWN")
    entity = intake.get("applicant_entity", "UNKNOWN")
    purpose = intake.get("purpose", "")
    use_of_funds = intake.get("use_of_funds", "")
    deadline = intake.get("deadline_jurisdiction", "")

    report = f"""GRANT-FORGE — GRANT READINESS REVIEW

Grant/Program: {grant}
Applicant: {entity}
Deadline/Jurisdiction: {deadline}

1) Eligibility Alignment
- TBD (engine output)

2) Narrative Strength
- TBD (engine output)

3) Compliance / Risk Flags
- TBD (engine output)

4) Readiness Call
- PROCEED / REVISE / DO NOT SUBMIT

Notes
- Purpose: {purpose[:800]}
- Use of Funds: {use_of_funds[:800]}
"""
    return report

# ------------------------
# PDF writer (reportlab)
# ------------------------
def write_report_file(request_id: str, client_name: str, grant_name: str, report_text: str) -> str:
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    fname = f"{date_str}_GRANTFORGE_{safe_slug(client_name)}_{safe_slug(grant_name)}_REVIEW.pdf"
    path = os.path.join(REPORT_DIR, f"{request_id}_{fname}")

    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    x = 40
    y = height - 40
    line_height = 14

    for line in report_text.split("\n"):
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(x, y, line)
        y -= line_height

    c.save()
    return path

# ------------------------
# Email sender (SMTP)
# ------------------------
def send_report_email(to_email: str, pdf_path: str):
    msg = EmailMessage()
    msg["Subject"] = "Grant-Forge Review"
    msg["From"] = os.getenv("MAIL_FROM")
    msg["To"] = to_email

    msg.set_content(
        "Your Grant-Forge review is attached.\n\n"
        "— JS Acquisitions LLC"
    )

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(pdf_path),
        )

    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "465"))) as s:
        s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        s.send_message(msg)

# ------------------------
# Admin UI (HTML)
# ------------------------
@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_queue():
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM requests ORDER BY created_at DESC")
        rows = cur.fetchall()

    def row_html(r: Dict[str, Any]) -> str:
        rid = str(r["id"])
        status_ = r["status"]

        btn_run = ""
        if status_ in ("APPROVED", "PAID"):
            btn_run = f"""
              <form method='post' action='/admin/run/{rid}' style='display:inline;'>
                <button type='submit'>RUN</button>
              </form>
            """

        btn_download = ""
        if r.get("report_path") and status_ in ("REPORT_READY", "DELIVERED", "ARCHIVED"):
            btn_download = f" <a href='/admin/download/{rid}'>DOWNLOAD</a> "

        btn_delivered = ""
        if status_ == "REPORT_READY":
            btn_delivered = f"""
              <form method='post' action='/admin/delivered/{rid}' style='display:inline;'>
                <button type='submit'>MARK DELIVERED</button>
              </form>
            """

        btn_archive = ""
        if status_ in ("DELIVERED", "REPORT_READY"):
            btn_archive = f"""
              <form method='post' action='/admin/archive/{rid}' style='display:inline;'>
                <button type='submit'>ARCHIVE</button>
              </form>
            """

        btn_delete = f"""
          <form method='post' action='/admin/delete/{rid}' style='display:inline;'>
            <button type='submit'>DELETE</button>
          </form>
        """

        intake = r.get("intake") or {}
        grant_name = intake.get("grant_name", "")

        created = r["created_at"].isoformat(timespec="seconds") if hasattr(r["created_at"], "isoformat") else str(r["created_at"])

        return f"""
        <tr>
          <td>{created}</td>
          <td>{r['client_name']}</td>
          <td>{r['client_email']}</td>
          <td>{grant_name}</td>
          <td><b>{status_}</b></td>
          <td>{btn_run} {btn_download} {btn_delivered} {btn_archive} {btn_delete}</td>
        </tr>
        """

    table = "\n".join(row_html(r) for r in rows)

    html = f"""
    <html>
      <head>
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        <title>Grant-Forge Admin</title>
        <style>
          body {{ font-family: Arial, sans-serif; padding: 12px; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
          th {{ background: #f5f5f5; }}
          .card {{ max-width: 980px; margin: 0 auto; }}
          input, textarea {{ width: 100%; padding: 8px; }}
          button {{ padding: 8px 10px; margin: 2px 0; }}
          .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
          @media (max-width: 720px) {{ .row {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <div class='card'>
          <h2>Grant-Forge Admin — Queue</h2>

          <h3>New Request (Manual Intake)</h3>
          <form method='post' action='/admin/new'>
            <div class='row'>
              <div>
                <label>Client Name</label>
                <input name='client_name' required />
              </div>
              <div>
                <label>Client Email</label>
                <input name='client_email' type='email' required />
              </div>
            </div>

            <label>Grant/Program Name</label>
            <input name='grant_name' required />

            <label>Applicant Entity</label>
            <input name='applicant_entity' required />

            <label>Purpose of Funding (1–2 paragraphs)</label>
            <textarea name='purpose' rows='4' required></textarea>

            <label>Target Use of Funds</label>
            <textarea name='use_of_funds' rows='3' required></textarea>

            <label>Deadline & Jurisdiction</label>
            <input name='deadline_jurisdiction' required />

            <div class='row'>
              <div>
                <label>Status</label>
                <input name='status_' value='PAID' />
                <small>Use APPROVED or PAID. Default is PAID.</small>
              </div>
              <div>
                <label>Notes (internal)</label>
                <input name='notes' />
              </div>
            </div>

            <button type='submit'>CREATE REQUEST</button>
          </form>

          <hr />

          <h3>Requests</h3>
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Client</th>
                <th>Email</th>
                <th>Grant</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {table}
            </tbody>
          </table>
        </div>
      </body>
    </html>
    """
    return html

@app.post("/admin/new", dependencies=[Depends(require_admin)])
def admin_new_request(
    client_name: str = Form(...),
    client_email: str = Form(...),
    grant_name: str = Form(...),
    applicant_entity: str = Form(...),
    purpose: str = Form(...),
    use_of_funds: str = Form(...),
    deadline_jurisdiction: str = Form(...),
    status_: str = Form("PAID"),
    notes: Optional[str] = Form(None),
):
    rid = uuid.uuid4()
    intake = {
        "grant_name": grant_name.strip(),
        "applicant_entity": applicant_entity.strip(),
        "purpose": purpose.strip(),
        "use_of_funds": use_of_funds.strip(),
        "deadline_jurisdiction": deadline_jurisdiction.strip(),
    }
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO requests (
              id, created_at, client_name, client_email, status, intake
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                rid,
                datetime.utcnow(),
                client_name.strip(),
                client_email.strip(),
                (status_ or "PAID").strip().upper(),
                psycopg2.extras.Json(intake),
            ),
        )
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/run/{request_id}", dependencies=[Depends(require_admin)])
def admin_run(request_id: str):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM requests WHERE id=%s", (request_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Request not found")
        if r["status"] not in ("APPROVED", "PAID"):
            return RedirectResponse(url="/admin", status_code=303)

        cur.execute("UPDATE requests SET status=%s WHERE id=%s", ("RUN_STARTED", request_id))

        intake = r["intake"] or {}
        report_text = run_grant_forge(intake)

        report_path = write_report_file(
            request_id=str(r["id"]),
            client_name=r["client_name"],
            grant_name=intake.get("grant_name", "UNKNOWN"),
            report_text=report_text
        )

        cur.execute(
            "UPDATE requests SET status=%s, report_path=%s, report_created_at=%s WHERE id=%s",
            ("REPORT_READY", report_path, datetime.utcnow(), request_id),
        )

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT client_email FROM requests WHERE id=%s", (request_id,))
        row = cur.fetchone()
        client_email = row["client_email"] if row else None

    if client_email:
        send_report_email(client_email, report_path)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE requests SET status=%s, delivered_at=%s WHERE id=%s",
                ("DELIVERED", datetime.utcnow(), request_id),
            )

    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin/download/{request_id}", dependencies=[Depends(require_admin)])
def admin_download(request_id: str):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT report_path FROM requests WHERE id=%s", (request_id,))
        row = cur.fetchone()
        if not row or not row.get("report_path"):
            raise HTTPException(status_code=404, detail="Report not found")
        path = row["report_path"]

    filename = os.path.basename(path)
    return FileResponse(path, filename=filename, media_type="application/pdf")

@app.post("/admin/delivered/{request_id}", dependencies=[Depends(require_admin)])
def admin_mark_delivered(request_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE requests SET status=%s, delivered_at=%s WHERE id=%s AND status=%s",
            ("DELIVERED", datetime.utcnow(), request_id, "REPORT_READY"),
        )
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/archive/{request_id}", dependencies=[Depends(require_admin)])
def admin_archive(request_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE requests SET status=%s, archived_at=%s WHERE id=%s AND status IN (%s, %s)",
            ("ARCHIVED", datetime.utcnow(), request_id, "REPORT_READY", "DELIVERED"),
        )
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/delete/{request_id}", dependencies=[Depends(require_admin)])
def admin_delete(request_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM requests WHERE id=%s", (request_id,))
    return RedirectResponse(url="/admin", status_code=303)
