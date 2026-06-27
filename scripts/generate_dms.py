import csv
import json
import os
import requests
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

PIPELINE_PATH = "data/pipeline.csv"
OUTPUT_PATH = "data/generated-dms.md"

DM_PROMPT = """You are writing a short, honest Twitter/X DM to a creator.

Your goal: pitch a 70/30 revenue split partnership where you build and sell a digital product for them using their existing content and audience.

Context about the creator:
- Name: {name}
- Handle: {handle}
- Niche: {niche}
- Followers: {followers}
- Notes: {notes}

DM requirements:
- Under 200 characters
- Be honest and direct — no hype, no fake flattery
- Mention the 70/30 split (they keep 70%)
- Reference something specific about them
- Don't be pushy

Return ONLY the DM text, no quotes, no explanation."""


def load_creators():
    creators = []
    with open(PIPELINE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").strip().lower() == "new":
                creators.append(row)
    return creators


def generate_dm(creator):
    prompt = DM_PROMPT.format(**creator)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 150,
    }

    resp = requests.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return data["choices"][0]["message"]["content"].strip().strip('"').strip("'")


def save_markdown(creators, dms):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Generated DMs — {now}",
        "",
        f"**Total DMs generated:** {len(dms)}",
        "",
        "---",
        "",
    ]

    for creator, dm in zip(creators, dms):
        lines.append(f"## {creator['name']} ({creator['handle']})")
        lines.append(f"- **Niche:** {creator['niche']}")
        lines.append(f"- **Followers:** {creator['followers']}")
        lines.append(f"- **Notes:** {creator['notes']}")
        lines.append("")
        lines.append("```")
        lines.append(dm)
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **DMs ready:** {len(dms)}")
    lines.append("")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not set")
        exit(1)

    creators = load_creators()
    print(f"Found {len(creators)} creators with status 'new'")

    if not creators:
        print("No new creators to process")
        exit(0)

    dms = []
    for creator in creators:
        print(f"Generating DM for {creator['name']} ({creator['handle']})...")
        try:
            dm = generate_dm(creator)
            dms.append(dm)
            print(f"  -> {dm[:80]}...")
        except Exception as e:
            print(f"  Error: {e}")
            dms.append("[Generation failed]")

    save_markdown(creators, dms)
    print(f"\nSaved {len(dms)} DMs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
