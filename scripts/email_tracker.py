#!/usr/bin/env python3
"""
Email Tracker - Automated email sequence manager for creators.

Reads pipeline.csv, tracks email stages, and sends follow-up emails
on schedule using Gmail SMTP with Groq API personalization.
"""

import csv
import logging
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PIPELINE_PATH = DATA_DIR / "pipeline.csv"
TEMPLATES_PATH = PROJECT_DIR / "templates" / "email-templates.md"
LOG_PATH = DATA_DIR / "email-tracker.log"

EMAIL_INTERVALS = {
    "email_1": timedelta(days=0),
    "email_2": timedelta(days=2),
    "email_3": timedelta(days=3),
    "email_4": timedelta(days=3),
    "email_5": timedelta(days=3),
    "email_6": timedelta(days=3),
    "email_7": timedelta(days=3),
    "email_8": timedelta(days=3),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_pipeline(path: Path) -> list[dict]:
    """Load pipeline CSV and return list of creator dicts."""
    if not path.exists():
        logger.error("Pipeline file not found: %s", path)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_pipeline(path: Path, rows: list[dict]) -> None:
    """Write updated rows back to pipeline CSV."""
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_templates(content: str) -> dict[int, dict]:
    """Parse email templates from markdown content."""
    emails = {}
    blocks = re.split(r"\n---\n", content)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        header_match = re.search(r"## Email (\d+):\s*(.+)", block)
        if not header_match:
            continue

        number = int(header_match.group(1))
        subject_match = re.search(r"\*\*Subject:\*\*\s*(.+)", block)
        body_match = re.search(r"\*\*Body:\*\*\s*\n([\s\S]+?)(?=\n---|\Z)", block)

        if not subject_match or not body_match:
            continue

        emails[number] = {
            "subject": subject_match.group(1).strip(),
            "body": body_match.group(1).strip(),
        }

    return emails


def groq_personalize(text: str, creator: dict) -> str:
    """Use Groq API to personalize email content based on creator data."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set, using template as-is")
        return text

    prompt = f"""Personalize this email for a content creator. Keep the same tone and structure.
Replace any generic placeholders with specific, relevant details based on the creator info below.
Do NOT add greetings or sign-offs - keep those as-is in the template.

Creator info:
- Name: {creator.get('name', 'Unknown')}
- Handle: {creator.get('handle', 'Unknown')}
- Niche: {creator.get('niche', 'Unknown')}
- Followers: {creator.get('followers', 'Unknown')}

Original email:
{text}

Personalized email:"""

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error("Groq API error: %s", e)
        return text


def send_email(to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Send email via Gmail SMTP. Returns True on success."""
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not password:
        logger.error("SENDER_EMAIL and GMAIL_APP_PASSWORD must be set")
        return False

    msg = MIMEText(body)
    msg["From"] = f"Digital Product Agency <{sender}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Reply-To"] = sender

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        logger.info("Email sent to %s (%s)", to_email, to_name)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def get_next_email_stage(current_stage: str) -> str | None:
    """Return the next email stage after current_stage."""
    if current_stage == "none":
        stage_num = 0
    elif current_stage.startswith("email_"):
        try:
            stage_num = int(current_stage.split("_")[1])
        except (IndexError, ValueError):
            stage_num = 0
    else:
        stage_num = 0
    next_num = stage_num + 1
    next_stage = f"email_{next_num}"
    return next_stage if next_num <= 8 else None


def should_send_email(creator: dict) -> tuple[bool, str]:
    """Check if an email should be sent to this creator. Returns (should_send, next_stage)."""
    email = creator.get("email", "").strip()
    if not email or email in ("not_found", "none", "null", "n/a"):
        return False, ""

    stage = creator.get("email_stage", "none").strip()
    last_sent = creator.get("last_email_date", "").strip()

    if stage == "none":
        return True, "email_1"

    next_stage = get_next_email_stage(stage)
    if not next_stage:
        return False, ""

    if not last_sent:
        return True, next_stage

    try:
        last_date = datetime.strptime(last_sent, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            last_date = datetime.strptime(last_sent, "%Y-%m-%d")
        except ValueError:
            logger.warning("Invalid last_email_date for %s: %s", creator["handle"], last_sent)
            return True, next_stage

    days_needed = sum(
        EMAIL_INTERVALS[f"email_{i}"].days for i in range(1, int(next_stage.split("_")[1]) + 1)
    )
    days_since_start = (datetime.now() - last_date).days
    interval_needed = EMAIL_INTERVALS[next_stage].days

    if days_since_start >= interval_needed:
        return True, next_stage

    return False, ""


def build_personalized_email(
    templates: dict[int, dict], creator: dict, stage: str
) -> tuple[str, str]:
    """Build personalized subject and body for the given stage."""
    email_num = int(stage.split("_")[1])
    template = templates.get(email_num)
    if not template:
        raise ValueError(f"No template found for {stage}")

    text = f"Subject: {template['subject']}\n\n{template['body']}"
    personalized = groq_personalize(text, creator)

    lines = personalized.split("\n\n", 1)
    if len(lines) == 2 and lines[0].startswith("Subject:"):
        subject = lines[0].replace("Subject:", "").strip()
        body = lines[1].strip()
    else:
        subject = template["subject"]
        body = personalized.strip()

    return subject, body


def build_summary_report(sent_count: int, creators: list[dict], results: list[dict]) -> str:
    """Build a summary report email body."""
    lines = [
        "Email Tracker Summary Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Total emails sent this run: {sent_count}",
        "",
        "Details:",
    ]

    for r in results:
        status_icon = "OK" if r["success"] else "FAIL"
        lines.append(
            f"  [{status_icon}] {r['creator']} - {r['stage']} - {r['subject']}"
        )

    lines.extend(["", "---", "Current Pipeline Status:"])

    for c in creators:
        email = c.get("email", "")
        stage = c.get("email_stage", "none")
        status = c.get("status", "")
        lines.append(f"  {c['name']} ({c['handle']}): stage={stage}, status={status}")

    return "\n".join(lines)


def main():
    """Main entry point for email tracker."""
    logger.info("=== Email Tracker Started ===")

    if not PIPELINE_PATH.exists():
        logger.error("Pipeline CSV not found: %s", PIPELINE_PATH)
        sys.exit(1)

    if not TEMPLATES_PATH.exists():
        logger.error("Templates file not found: %s", TEMPLATES_PATH)
        sys.exit(1)

    templates = parse_templates(TEMPLATES_PATH.read_text(encoding="utf-8"))
    logger.info("Loaded %d email templates", len(templates))

    rows = load_pipeline(PIPELINE_PATH)
    logger.info("Loaded %d creators from pipeline", len(rows))

    sent_count = 0
    results = []

    for i, creator in enumerate(rows):
        handle = creator.get("handle", "unknown")
        should_send, next_stage = should_send_email(creator)

        if not should_send:
            logger.debug("No email needed for %s (stage: %s)", handle, creator.get("email_stage"))
            continue

        email = creator.get("email", "").strip()
        name = creator.get("name", "").strip()
        if not email or not name:
            logger.warning("Skipping %s - missing email or name", handle)
            continue

        try:
            subject, body = build_personalized_email(templates, creator, next_stage)
        except Exception as e:
            logger.error("Failed to build email for %s: %s", handle, e)
            results.append({
                "creator": handle,
                "stage": next_stage,
                "subject": "ERROR",
                "success": False,
            })
            continue

        success = send_email(email, name, subject, body)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if success:
            rows[i]["email_stage"] = next_stage
            rows[i]["last_email_date"] = now
            rows[i]["status"] = "contacted"
            rows[i]["status_changed_at"] = now
            sent_count += 1

        results.append({
            "creator": handle,
            "stage": next_stage,
            "subject": subject,
            "success": success,
        })

    save_pipeline(PIPELINE_PATH, rows)
    logger.info("Pipeline updated. %d emails sent this run.", sent_count)

    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    if recipient_email:
        report_body = build_summary_report(sent_count, rows, results)
        send_email(
            to_email=recipient_email,
            to_name="Report",
            subject=f"Email Tracker Report - {datetime.now().strftime('%Y-%m-%d')}",
            body=report_body,
        )
        logger.info("Summary report sent to %s", recipient_email)
    else:
        logger.warning("RECIPIENT_EMAIL not set, skipping summary report")

    logger.info("=== Email Tracker Finished ===")


if __name__ == "__main__":
    main()
