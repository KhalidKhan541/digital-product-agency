#!/usr/bin/env python3
"""Sends email sequences to creators from markdown templates."""

import argparse
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATES_PATH = PROJECT_DIR / "templates" / "email-templates.md"
LOG_PATH = PROJECT_DIR / "data" / "email-log.md"


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
        name = header_match.group(2).strip()

        subject_match = re.search(r"\*\*Subject:\*\*\s*(.+)", block)
        body_match = re.search(r"\*\*Body:\*\*\s*\n([\s\S]+?)(?=\n---|\Z)", block)

        if not subject_match or not body_match:
            continue

        subject = subject_match.group(1).strip()
        body = body_match.group(1).strip()

        emails[number] = {"name": name, "subject": subject, "body": body}

    return emails


def replace_variables(text: str, variables: dict[str, str]) -> str:
    """Replace template variables in text."""
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def send_email(sender_email: str, app_password: str, to_email: str, subject: str, body: str) -> None:
    """Send an email via Gmail SMTP."""
    msg = MIMEText(body)
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())


def log_email(log_path: Path, to_email: str, name: str, email_number: int, subject: str) -> None:
    """Append a log entry to email-log.md."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"| {timestamp} | {to_email} | {name} | Email {email_number} | {subject} | Sent |\n"

    if not log_path.exists():
        log_path.write_text("# Email Log\n\n| Timestamp | To | Creator | Email | Subject | Status |\n|-----------|----|---------|-------|---------|--------|\n")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def main():
    parser = argparse.ArgumentParser(description="Send email sequences to creators")
    parser.add_argument("--email", required=True, help="Recipient email address")
    parser.add_argument("--name", required=True, help="Creator name")
    parser.add_argument("--product", default="", help="Product name for {{product_name}}")
    parser.add_argument("--number", required=True, type=int, choices=range(1, 9), help="Email number (1-8)")
    parser.add_argument("--dry-run", action="store_true", help="Preview email without sending")
    args = parser.parse_args()

    if not TEMPLATES_PATH.exists():
        print(f"Error: Templates file not found at {TEMPLATES_PATH}")
        sys.exit(1)

    content = TEMPLATES_PATH.read_text(encoding="utf-8")
    emails = parse_templates(content)

    if args.number not in emails:
        print(f"Error: Email {args.number} not found in templates")
        sys.exit(1)

    email = emails[args.number]

    variables = {
        "creator_name": args.name,
        "product_name": args.product,
        "your_name": os.environ.get("YOUR_NAME", ""),
        "your_email": os.environ.get("SENDER_EMAIL", ""),
    }

    subject = replace_variables(email["subject"], variables)
    body = replace_variables(email["body"], variables)

    if args.dry_run:
        print(f"To: {args.email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        return

    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("Error: Set SENDER_EMAIL and GMAIL_APP_PASSWORD environment variables")
        sys.exit(1)

    send_email(sender_email, app_password, args.email, subject, body)
    log_email(LOG_PATH, args.email, args.name, args.number, subject)
    print(f"Sent email {args.number} to {args.email}")


if __name__ == "__main__":
    main()
