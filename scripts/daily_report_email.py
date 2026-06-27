#!/usr/bin/env python3
"""Daily report generator and email sender.

Reads pipeline.csv and email-log.md, generates a daily summary report,
and sends it via Gmail SMTP.

Usage:
    python scripts/daily_report_email.py

Env vars:
    SENDER_EMAIL      - Gmail address to send from
    GMAIL_APP_PASSWORD - Gmail app password
    RECIPIENT_EMAIL   - Where to send the report
"""

import csv
import os
import smtplib
from collections import Counter
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PIPELINE_CSV = DATA_DIR / "pipeline.csv"
EMAIL_LOG = DATA_DIR / "email-log.md"

TARGET_STATUSES = ["new", "contacted", "interested", "building", "launched"]


def load_pipeline():
    """Load all rows from pipeline.csv."""
    rows = []
    with open(PIPELINE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def count_by_status(rows):
    """Count creators grouped by status."""
    counts = Counter()
    for row in rows:
        status = row.get("status", "unknown").strip().lower()
        counts[status] += 1
    return counts


def parse_email_log():
    """Parse email-log.md and return list of log entries."""
    entries = []
    if not EMAIL_LOG.exists():
        return entries

    with open(EMAIL_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]
            if len(cells) < 6:
                continue
            if cells[0] in ("Timestamp", "---", ""):
                continue
            entries.append({
                "timestamp": cells[0],
                "to": cells[1],
                "creator": cells[2],
                "email": cells[3],
                "subject": cells[4],
                "status": cells[5],
            })
    return entries


def filter_today(entries):
    """Filter log entries to only those from today."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_entries = []
    for entry in entries:
        if entry["timestamp"].startswith(today_str):
            today_entries.append(entry)
    return today_entries


def determine_tasks(rows):
    """Determine today's tasks based on pipeline status."""
    tasks = []
    status_counts = count_by_status(rows)

    new_count = status_counts.get("new", 0)
    if new_count > 0:
        tasks.append(f"Send DMs to {new_count} new creator(s)")

    contacted_count = status_counts.get("contacted", 0)
    if contacted_count > 0:
        tasks.append(f"Follow up with {contacted_count} contacted creator(s)")

    interested_count = status_counts.get("interested", 0)
    if interested_count > 0:
        tasks.append(f"Start building for {interested_count} interested creator(s)")

    building_count = status_counts.get("building", 0)
    if building_count > 0:
        tasks.append(f"Check progress on {building_count} building creator(s)")

    launched_count = status_counts.get("launched", 0)
    if launched_count > 0:
        tasks.append(f"Review {launched_count} launched product(s)")

    if not tasks:
        tasks.append("No tasks today. Find new creators to add to pipeline.")

    return tasks


def calculate_response_rate(rows):
    """Calculate response rate from contacted creators."""
    contacted = 0
    replied = 0
    for row in rows:
        status = row.get("status", "").strip().lower()
        if status in ("contacted", "interested", "building", "launched"):
            contacted += 1
        if status in ("interested", "building", "launched"):
            replied += 1
    if contacted == 0:
        return 0.0
    return (replied / contacted) * 100


def suggest_next_actions(status_counts):
    """Suggest next actions based on pipeline state."""
    actions = []

    new = status_counts.get("new", 0)
    contacted = status_counts.get("contacted", 0)
    interested = status_counts.get("interested", 0)
    building = status_counts.get("building", 0)
    launched = status_counts.get("launched", 0)

    if new > 0:
        actions.append(f"1. Draft and send DMs to {new} new creator(s)")
    if contacted > 0:
        actions.append(f"2. Follow up with {contacted} creator(s) who haven't replied")
    if interested > 0:
        actions.append(f"3. Send product details to {interested} interested creator(s)")
    if building > 0:
        actions.append(f"4. Build digital product(s) for {building} creator(s)")
    if launched > 0:
        actions.append(f"5. Share launch results and collect feedback from {launched} creator(s)")

    if not actions:
        actions.append("1. Research and add new creators to the pipeline")

    return actions


def build_report(rows):
    """Build the daily report body."""
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")

    status_counts = count_by_status(rows)
    total = len(rows)
    response_rate = calculate_response_rate(rows)
    tasks = determine_tasks(rows)
    actions = suggest_next_actions(status_counts)

    email_entries = parse_email_log()
    today_emails = filter_today(email_entries)
    dms_sent = sum(1 for e in today_emails if "DM" in e.get("email", "") or "dm" in e.get("email", "").lower())
    emails_sent = len(today_emails)

    # Build pipeline summary table
    pipeline_lines = []
    for status in TARGET_STATUSES:
        count = status_counts.get(status, 0)
        bar = "#" * count if count > 0 else "-"
        pipeline_lines.append(f"| {status:<14} | {count:>4} | {bar}")

    pipeline_table = "\n".join(pipeline_lines)

    # Build today's tasks list
    tasks_lines = [f"- {t}" for t in tasks]
    tasks_text = "\n".join(tasks_lines)

    # Build next actions list
    actions_lines = [f"- {a}" for a in actions]
    actions_text = "\n".join(actions_lines)

    report = f"""
================================================================
          DAILY REPORT - {date_str}
================================================================

--- PIPELINE SUMMARY ---

| Status         | Count | Visual                    |
|----------------|-------|---------------------------|
{pipeline_table}

  Total Creators: {total}


--- TODAY'S TASKS ---
{tasks_text}


--- TODAY'S ACTIVITY ---

  DMs Sent Today:     {dms_sent}
  Emails Sent Today:  {emails_sent}
  Response Rate:      {response_rate:.1f}%


--- NEXT ACTIONS ---
{actions_text}


================================================================
Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}
================================================================"""

    return report.strip()


def build_email(report_text):
    """Build the email message."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    subject = f"Daily Report - {date_str}"

    sender = os.environ.get("SENDER_EMAIL", "")
    recipient = os.environ.get("RECIPIENT_EMAIL", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Digital Product Agency <{sender}>"
    msg["To"] = recipient

    msg.attach(MIMEText(report_text, "plain"))

    html_body = report_text.replace("\n", "<br>").replace(" ", "&nbsp;")
    msg.attach(
        MIMEText(
            f"<html><body><pre style='font-family:monospace;"
            f"font-size:13px'>{html_body}</pre></body></html>",
            "html",
        )
    )

    return msg


def send_report(report_text):
    """Send the daily report email via Gmail SMTP."""
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    missing = []
    if not sender:
        missing.append("SENDER_EMAIL")
    if not password:
        missing.append("GMAIL_APP_PASSWORD")
    if not recipient:
        missing.append("RECIPIENT_EMAIL")
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        return False

    msg = build_email(report_text)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"Report sent to {recipient}")
        return True
    except Exception as e:
        print(f"Failed to send report: {e}")
        return False


def main():
    if not PIPELINE_CSV.exists():
        print(f"Pipeline file not found: {PIPELINE_CSV}")
        return

    rows = load_pipeline()
    if not rows:
        print("No data in pipeline.csv")
        return

    report = build_report(rows)
    print(report)
    print()
    send_report(report)


if __name__ == "__main__":
    main()
