import os
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from groq import Groq


def load_pipeline(csv_path):
    """Load pipeline CSV and return rows with metadata."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    return fieldnames, rows


def save_pipeline(csv_path, fieldnames, rows):
    """Save updated pipeline back to CSV."""
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_dm(client, creator_name, creator_handle, niche):
    """Generate a personalized DM using Groq API."""
    prompt = f"""Write a Twitter DM to {creator_name} ({creator_handle}), a creator in the {niche} space.

Rules:
- Under 200 characters
- Honest and direct, no hype or salesy language
- Mention a 70/30 revenue split (they keep 70%, we take 30%)
- Sound like a real person, not a marketer
- Ask if they'd be interested in monetizing their content through digital products
- Do NOT use emojis
- Do NOT use exclamation marks excessively

Write ONLY the DM text, nothing else."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def build_email_body(dms):
    """Build the email body with all DMs."""
    date_str = datetime.now().strftime("%B %d, %Y")
    lines = [
        f"Daily DMs Ready - {date_str}",
        "=" * 50,
        "",
        "INSTRUCTIONS:",
        "1. Open Twitter/X in your browser",
        "2. Click on each creator's handle to go to their profile",
        "3. Click 'Message' or the DM icon",
        "4. Copy and paste the DM text below",
        "5. Send it",
        "",
        "Keep it natural - send a few at a time, not all at once.",
        "",
        "=" * 50,
        "",
    ]

    for i, dm in enumerate(dms, 1):
        lines.append(f"--- DM {i} ---")
        lines.append(f"Creator: {dm['name']}")
        lines.append(f"Handle: {dm['handle']}")
        lines.append(f"Niche: {dm['niche']}")
        lines.append("")
        lines.append(dm["text"])
        lines.append("")

    lines.append("=" * 50)
    lines.append(f"Total DMs: {len(dms)}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return "\n".join(lines)


def send_email(subject, body, sender_email, password, recipient_email):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(msg)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "pipeline.csv")

    groq_key = os.environ.get("GROQ_API_KEY")
    sender_email = os.environ.get("SENDER_EMAIL")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    missing = []
    if not groq_key:
        missing.append("GROQ_API_KEY")
    if not sender_email:
        missing.append("SENDER_EMAIL")
    if not gmail_password:
        missing.append("GMAIL_APP_PASSWORD")
    if not recipient_email:
        missing.append("RECIPIENT_EMAIL")
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        return

    if not os.path.exists(csv_path):
        print(f"Pipeline file not found: {csv_path}")
        return

    fieldnames, rows = load_pipeline(csv_path)

    new_creators = [r for r in rows if r.get("status", "").strip().lower() == "new"]

    if not new_creators:
        print("No creators with status 'new' found.")
        return

    print(f"Found {len(new_creators)} new creators. Generating DMs...")

    client = Groq(api_key=groq_key)

    dms = []
    for row in new_creators:
        name = row.get("name", "Unknown")
        handle = row.get("handle", "unknown")
        niche = row.get("niche", "content creation")

        print(f"  Generating DM for {name} ({handle})...")
        dm_text = generate_dm(client, name, handle, niche)

        dms.append({"name": name, "handle": handle, "niche": niche, "text": dm_text})

        for r in rows:
            if r.get("handle") == handle and r.get("status", "").strip().lower() == "new":
                r["status"] = "contacted"

    email_body = build_email_body(dms)
    date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"Daily DMs Ready - {date_str}"

    send_email(subject, email_body, sender_email, gmail_password, recipient_email)
    print(f"Email sent to {recipient_email}")

    save_pipeline(csv_path, fieldnames, rows)
    print(f"Pipeline updated: {csv_path}")


if __name__ == "__main__":
    main()
