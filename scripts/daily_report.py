import os
import csv
import smtplib
import requests
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import Counter

PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "pipeline.csv")

GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]


def load_pipeline():
    with open(PIPELINE_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def generate_stats(rows):
    today = date.today()
    total = len(rows)

    contacted_today = sum(
        1 for r in rows if parse_date(r.get("contacted_date", "")) == today
    )

    emails_today = sum(
        1 for r in rows
        if parse_date(r.get("last_email_date", "")) == today
        or parse_date(r.get("contacted_date", "")) == today
    )

    status_counts = Counter(r.get("status", "unknown").strip().lower() for r in rows)

    follow_up_needed = []
    for r in rows:
        status = r.get("status", "").strip().lower()
        last_contact = parse_date(r.get("last_followup_date", "") or r.get("contacted_date", ""))
        if status in ("contacted", "follow-up", "waiting") and last_contact:
            days_since = (today - last_contact).days
            if days_since >= 3:
                follow_up_needed.append(r)

    contacted_total = sum(
        1 for r in rows if r.get("status", "").strip().lower() in
        ("contacted", "replied", "follow-up", "waiting", "converted", "booked", "closed")
    )
    converted_total = sum(
        1 for r in rows if r.get("status", "").strip().lower() in
        ("converted", "booked", "closed", "paid")
    )
    conversion_rate = (converted_total / contacted_total * 100) if contacted_total > 0 else 0

    return {
        "total": total,
        "contacted_today": contacted_today,
        "emails_today": emails_today,
        "status_counts": dict(status_counts),
        "follow_up_needed": follow_up_needed,
        "conversion_rate": conversion_rate,
        "converted_total": converted_total,
        "contacted_total": contacted_total,
        "today": today,
    }


def ai_analysis(stats):
    prompt = (
        f"Analyze this creator pipeline summary for {stats['today']}:\n"
        f"- Total creators: {stats['total']}\n"
        f"- Contacted today: {stats['contacted_today']}\n"
        f"- Emails sent today: {stats['emails_today']}\n"
        f"- Status breakdown: {stats['status_counts']}\n"
        f"- Creators needing follow-up: {len(stats['follow_up_needed'])}\n"
        f"- Conversion rate: {stats['conversion_rate']:.1f}%\n\n"
        "Provide a brief 3-4 sentence analysis with actionable insights. "
        "Keep it concise and focused on what needs attention."
    )

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI analysis unavailable: {e}"


def build_html_report(stats, analysis):
    follow_up_rows = ""
    for r in stats["follow_up_needed"][:10]:
        name = r.get("name", r.get("creator_name", "Unknown"))
        platform = r.get("platform", "")
        last_contact = r.get("last_followup_date", "") or r.get("contacted_date", "")
        follow_up_rows += f"<tr><td>{name}</td><td>{platform}</td><td>{last_contact}</td></tr>\n"

    status_rows = ""
    for stage, count in sorted(stats["status_counts"].items()):
        status_rows += f"<tr><td>{stage.title()}</td><td>{count}</td></tr>\n"

    today_str = stats["today"].strftime("%B %d, %Y")

    html = f"""\
<html>
<head>
<style>
  body {{ font-family: Arial, sans-serif; color: #333; max-width: 650px; margin: 0 auto; }}
  h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 8px; }}
  h2 {{ color: #555; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f0f4ff; }}
  .metric {{ display: inline-block; background: #f0f4ff; border-radius: 8px;
             padding: 12px 20px; margin: 6px 8px 6px 0; text-align: center; }}
  .metric .value {{ font-size: 28px; font-weight: bold; color: #1a73e8; }}
  .metric .label {{ font-size: 12px; color: #666; }}
  .ai-box {{ background: #f9f9f9; border-left: 4px solid #1a73e8;
             padding: 12px 16px; margin: 16px 0; }}
</style>
</head>
<body>
  <h1>Daily Pipeline Report &mdash; {today_str}</h1>

  <div>
    <div class="metric"><div class="value">{stats['total']}</div><div class="label">Total Creators</div></div>
    <div class="metric"><div class="value">{stats['contacted_today']}</div><div class="label">Contacted Today</div></div>
    <div class="metric"><div class="value">{stats['emails_today']}</div><div class="label">Emails Sent Today</div></div>
    <div class="metric"><div class="value">{stats['conversion_rate']:.1f}%</div><div class="label">Conversion Rate</div></div>
    <div class="metric"><div class="value">{len(stats['follow_up_needed'])}</div><div class="label">Need Follow-Up</div></div>
  </div>

  <h2>Status Breakdown</h2>
  <table>
    <tr><th>Stage</th><th>Count</th></tr>
    {status_rows}
  </table>

  <h2>Creators Needing Follow-Up</h2>
  {"<p>No creators need follow-up right now.</p>" if not follow_up_rows else
   f'<table><tr><th>Name</th><th>Platform</th><th>Last Contact</th></tr>{follow_up_rows}</table>'}

  <h2>AI Analysis</h2>
  <div class="ai-box">{analysis}</div>
</body>
</html>
"""
    return html


def send_email(html_content, stats):
    today_str = stats["today"].strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Pipeline Report - {today_str}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    plain_text = (
        f"Daily Pipeline Report - {today_str}\n\n"
        f"Total Creators: {stats['total']}\n"
        f"Contacted Today: {stats['contacted_today']}\n"
        f"Emails Sent Today: {stats['emails_today']}\n"
        f"Conversion Rate: {stats['conversion_rate']:.1f}%\n"
        f"Need Follow-Up: {len(stats['follow_up_needed'])}\n\n"
        "View this email in an HTML-capable client for the full report."
    )

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    print(f"Report sent to {RECIPIENT_EMAIL}")


def main():
    if not os.path.exists(PIPELINE_PATH):
        print(f"Pipeline file not found: {PIPELINE_PATH}")
        return

    rows = load_pipeline()
    print(f"Loaded {len(rows)} rows from pipeline.csv")

    stats = generate_stats(rows)
    analysis = ai_analysis(stats)
    html = build_html_report(stats, analysis)
    send_email(html, stats)


if __name__ == "__main__":
    main()
