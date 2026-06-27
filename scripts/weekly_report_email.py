#!/usr/bin/env python3
"""Weekly analytics report generator and email sender."""

import csv
import os
import smtplib
from collections import Counter
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PIPELINE_CSV = os.path.join(DATA_DIR, "pipeline.csv")
REVENUE_PER_LAUNCH = 497.0


def load_pipeline():
    """Load and return all rows from pipeline.csv."""
    rows = []
    with open(PIPELINE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_followers(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def calculate_metrics(rows):
    """Calculate all report metrics from pipeline rows."""
    total = len(rows)
    statuses = Counter(r.get("status", "new") for r in rows)
    niches = Counter(r.get("niche", "unknown") for r in rows)

    contacted = sum(
        1 for r in rows
        if r.get("status") in ("contacted", "replied", "converted")
    )
    replied = sum(
        1 for r in rows
        if r.get("status") in ("replied", "converted")
    )
    converted = statuses.get("converted", 0)
    products_created = converted
    revenue_estimate = products_created * REVENUE_PER_LAUNCH

    response_rate = (replied / contacted * 100) if contacted > 0 else 0.0
    conversion_rate = (converted / contacted * 100) if contacted > 0 else 0.0

    avg_followers = (
        sum(parse_followers(r.get("followers", 0)) for r in rows) / total
        if total
        else 0
    )

    return {
        "total_creators": total,
        "contacted": contacted,
        "replied": replied,
        "converted": converted,
        "response_rate": response_rate,
        "conversion_rate": conversion_rate,
        "products_created": products_created,
        "revenue_estimate": revenue_estimate,
        "statuses": dict(statuses),
        "niches": dict(niches),
        "avg_followers": int(avg_followers),
    }


def build_bar(label, value, max_val, width=30):
    """Render a single text bar for chart data."""
    filled = int((value / max_val) * width) if max_val > 0 else 0
    bar = "#" * filled + "-" * (width - filled)
    return f"  {label:<14s} {bar} {value}"


def build_niche_chart(niches):
    """Build a text-based bar chart of creators by niche."""
    if not niches:
        return "  No data available."
    max_val = max(niches.values())
    lines = []
    for niche, count in sorted(niches.items(), key=lambda x: -x[1]):
        lines.append(build_bar(niche, count, max_val))
    return "\n".join(lines)


def build_status_chart(statuses):
    """Build a text-based bar chart of creators by status."""
    if not statuses:
        return "  No data available."
    max_val = max(statuses.values())
    lines = []
    for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
        lines.append(build_bar(status, count, max_val))
    return "\n".join(lines)


def build_funnel(metrics):
    """Build a text-based conversion funnel visualization."""
    total = metrics["total_creators"]
    contacted = metrics["contacted"]
    replied = metrics["replied"]
    converted = metrics["converted"]

    stages = [
        ("Total Pool", total),
        ("Contacted", contacted),
        ("Replied", replied),
        ("Converted", converted),
    ]

    max_val = max(v for _, v in stages) if stages else 1
    lines = []
    for label, count in stages:
        width = max(1, int((count / max_val) * 40)) if max_val > 0 else 1
        block = "#" * width
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"  {label:<14s} {block}  {count} ({pct:.1f}%)")
    return "\n".join(lines)


def format_delta(current, previous):
    """Format a delta string with arrow indicator."""
    if previous == 0:
        return " (no prior data)"
    diff = current - previous
    pct = (diff / previous * 100) if previous else 0
    arrow = "+" if diff >= 0 else ""
    return f" ({arrow}{diff}, {arrow}{pct:.0f}%)"


def build_report_body(metrics, prev_metrics=None):
    """Build the full plain-text email body."""
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%b %d")
    week_end = now.strftime("%b %d, %Y")
    date_range = f"{week_start} - {week_end}"

    d_total = format_delta(
        metrics["total_creators"], prev_metrics["total_creators"]
    ) if prev_metrics else ""
    d_contacted = format_delta(
        metrics["contacted"], prev_metrics["contacted"]
    ) if prev_metrics else ""
    d_response = format_delta(
        metrics["response_rate"], prev_metrics["response_rate"]
    ) if prev_metrics else ""
    d_revenue = format_delta(
        metrics["revenue_estimate"], prev_metrics["revenue_estimate"]
    ) if prev_metrics else ""
    d_converted = format_delta(
        metrics["converted"], prev_metrics["converted"]
    ) if prev_metrics else ""

    niche_chart = build_niche_chart(metrics["niches"])
    status_chart = build_status_chart(metrics["statuses"])
    funnel = build_funnel(metrics)

    report = f"""
============================================================
        WEEKLY ANALYTICS REPORT — {date_range}
============================================================

--- KEY METRICS ---

  Total Creators in Pipeline:  {metrics['total_creators']}{d_total}
  Contacted This Week:         {metrics['contacted']}{d_contacted}
  Response Rate:               {metrics['response_rate']:.1f}%{d_response}
  Products Created:            {metrics['products_created']}{d_converted}
  Revenue Estimate:            ${metrics['revenue_estimate']:,.0f}{d_revenue}
  Avg Followers per Creator:   {metrics['avg_followers']:,}


--- CONVERSION FUNNEL ---

{funnel}


--- CREATORS BY NICHE ---

{niche_chart}


--- PIPELINE STATUS ---

{status_chart}


--- RECOMMENDATIONS ---

{generate_recommendations(metrics)}

============================================================
Generated: {now.strftime('%Y-%m-%d %H:%M')}
"""

    return report.strip()


def generate_recommendations(metrics):
    """Generate actionable recommendations based on metrics."""
    recs = []
    if metrics["contacted"] == 0:
        recs.append("  [!] No creators contacted yet. Start outreach this week.")
    elif metrics["response_rate"] < 20:
        recs.append("  [!] Response rate below 20%. Review DM templates.")
    elif metrics["response_rate"] > 40:
        recs.append("  [+] Strong response rate. Scale outreach volume.")

    if metrics["converted"] == 0 and metrics["contacted"] > 5:
        recs.append(
            f"  [!] {metrics['contacted']} contacted but 0 conversions."
            " Consider follow-ups or offer adjustments."
        )

    if metrics["products_created"] > 0:
        avg_rev = metrics["revenue_estimate"] / metrics["products_created"]
        recs.append(
            f"  [+] {metrics['products_created']} products live."
            f" At ${REVENUE_PER_LAUNCH}/launch, track actual sales."
        )

    niches = metrics["niches"]
    if niches:
        top_niche = max(niches, key=niches.get)
        recs.append(
            f"  [i] Largest niche: {top_niche}"
            f" ({niches[top_niche]} creators)."
            " Consider niche-specific product templates."
        )

    if not recs:
        recs.append("  [i] Pipeline is healthy. Continue current cadence.")

    return "\n".join(recs)


def build_email(metrics, prev_metrics=None):
    """Build the email subject and HTML body."""
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%b %d")
    week_end = now.strftime("%b %d, %Y")
    date_range = f"{week_start} - {week_end}"

    subject = f"Weekly Report - {date_range}"
    body = build_report_body(metrics, prev_metrics)

    html_body = body.replace("\n", "<br>").replace(" ", "&nbsp;")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Digital Product Agency <{os.environ.get('SENDER_EMAIL', '')}>"
    msg["To"] = os.environ.get("RECIPIENT_EMAIL", "")

    msg.attach(MIMEText(body, "plain"))
    msg.attach(
        MIMEText(
            f"<html><body><pre style='font-family:monospace;"
            f"font-size:13px'>{html_body}</pre></body></html>",
            "html",
        )
    )

    return msg


def send_report(metrics, prev_metrics=None):
    """Send the weekly report email via Gmail SMTP."""
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

    msg = build_email(metrics, prev_metrics)
    msg["From"] = f"Digital Product Agency <{sender}>"
    msg["To"] = recipient

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
    rows = load_pipeline()
    if not rows:
        print("No data in pipeline.csv")
        return

    metrics = calculate_metrics(rows)
    print(build_report_body(metrics))
    print()
    send_report(metrics)


if __name__ == "__main__":
    main()
