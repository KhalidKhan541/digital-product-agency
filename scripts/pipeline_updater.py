"""Auto-update pipeline status based on time conditions.

Reads data/pipeline.csv, updates statuses that have been pending too long,
logs changes to data/pipeline-log.md, and sends an email notification.

Usage:
    python scripts/pipeline_updater.py

Env vars:
    SENDER_EMAIL      - Gmail address to send from
    GMAIL_APP_PASSWORD - Gmail app password
    RECIPIENT_EMAIL   - Where to send notifications
"""

import csv
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_CSV = ROOT / "data" / "pipeline.csv"
PIPELINE_LOG = ROOT / "data" / "pipeline-log.md"

STATUS_RULES = {
    "contacted": {"days": 3, "next": "follow-up"},
    "interested": {"days": 7, "next": "building"},
}

FIELDNAMES = ["name", "handle", "followers", "niche", "status", "notes", "status_changed_at"]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_rows() -> list[dict]:
    rows = []
    with open(PIPELINE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Ensure the tracking column exists
            if "status_changed_at" not in row or not row["status_changed_at"]:
                row["status_changed_at"] = now_str()
            rows.append(row)
    return rows


def save_rows(rows: list[dict]) -> None:
    with open(PIPELINE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def compute_changes(rows: list[dict]) -> list[tuple[dict, str, str]]:
    """Return list of (row, old_status, new_status) for rows that need updating."""
    changes = []
    today = datetime.now()

    for row in rows:
        current = row["status"].strip().lower()
        rule = STATUS_RULES.get(current)
        if rule is None:
            continue

        last_changed = datetime.strptime(row["status_changed_at"], "%Y-%m-%d %H:%M:%S")
        if (today - last_changed).days >= rule["days"]:
            changes.append((row, row["status"], rule["next"]))

    return changes


def apply_changes(rows: list[dict], changes: list[tuple[dict, str, str]]) -> None:
    """Update rows in-place and rewrite CSV."""
    now = now_str()
    for row, old_status, new_status in changes:
        row["status"] = new_status
        row["status_changed_at"] = now
    save_rows(rows)


def append_log(changes: list[tuple[dict, str, str]]) -> None:
    if not changes:
        return

    timestamp = now_str()
    lines = [f"\n## Update — {timestamp}\n"]
    for row, old_status, new_status in changes:
        lines.append(f"- **{row['name']}** ({row['handle']}): `{old_status}` → `{new_status}`")

    with open(PIPELINE_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def send_email(changes: list[tuple[dict, str, str]]) -> None:
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not all([sender, password, recipient]):
        print("[pipeline_updater] Skipping email — missing env vars (SENDER_EMAIL, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL).")
        return

    body_lines = ["Pipeline auto-update report", ""]
    for row, old_status, new_status in changes:
        body_lines.append(f"{row['name']} ({row['handle']}): {old_status} → {new_status}")
    body_lines.append("")
    body_lines.append(f"Run at: {now_str()}")

    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = f"Pipeline Update — {len(changes)} creator(s) moved"
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        print(f"[pipeline_updater] Email sent to {recipient}")
    except Exception as e:
        print(f"[pipeline_updater] Email failed: {e}")


def main() -> None:
    rows = load_rows()
    changes = compute_changes(rows)

    if not changes:
        print("[pipeline_updater] No status changes needed.")
        return

    print(f"[pipeline_updater] {len(changes)} status change(s) to apply:")
    for row, old, new in changes:
        print(f"  {row['name']}: {old} → {new}")

    apply_changes(rows, changes)
    append_log(changes)
    send_email(changes)

    print("[pipeline_updater] Done.")


if __name__ == "__main__":
    main()
