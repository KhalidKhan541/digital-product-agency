import os
import csv
import re
import time
import json
import urllib.parse
import urllib.request
from groq import Groq

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pipeline.csv')
GROQ_MODEL = "llama-3.3-70b-versatile"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
SKIP_DOMAINS = {'example.com', 'email.com', 'sentry.io', 'wixpress.com', 'github.com',
                'googleusercontent.com', 'google.com', 'facebook.com', 'twitter.com',
                'instagram.com', 'tiktok.com', 'youtube.com', 'substack.com'}


def bing_search(query):
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  Bing search failed: {e}")
    return ""


def extract_emails_from_text(text):
    raw = re.findall(EMAIL_REGEX, text)
    valid = []
    for e in raw:
        domain = e.split('@')[1].lower()
        if domain not in SKIP_DOMAINS and not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            valid.append(e.lower())
    return list(set(valid))


def find_email_via_groq(client, name, handle, niche):
    prompt = f"""You are a research assistant. Given this content creator info, guess their most likely business email address.

Creator: {name}
Handle: @{handle}
Niche: {niche}

Common email patterns for creators:
- {{name}}@gmail.com
- {{first}}@{{domain}}.com (if they have a website)
- hello@{{domain}}.com
- contact@{{domain}}.com

Use the Groq API websearch or your knowledge to find any public email for this person.
Return ONLY a JSON object:
{{"email": "found@email.com"}} or {{"email": null}} if you cannot find one."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        text = response.choices[0].message.content.strip()
        match = re.search(r'\{[^{}]*"email"[^{}]*\}', text)
        if match:
            result = json.loads(match.group())
            email = result.get("email")
            if email and '@' in email:
                return email
    except Exception as e:
        print(f"  Groq guess error: {e}")
    return None


def search_creator_email(client, name, handle, niche):
    queries = [
        f'"{name}" email contact',
        f'"{name}" "{handle}" email',
        f'{name} {niche} newsletter email',
        f'site:linkedin.com "{name}" {handle}',
    ]

    for query in queries:
        print(f"  Searching: {query}")
        html = bing_search(query)
        if html:
            emails = extract_emails_from_text(html)
            if emails:
                return emails[0]
        time.sleep(1)

    print("  Trying Groq AI guess...")
    email = find_email_via_groq(client, name, handle, niche)
    if email:
        return email

    return None


def is_email_searchable(email):
    return not email or email.strip() in ("", "none", "null", "nan", "not_found")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set")
        return

    client = Groq(api_key=api_key)

    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found at {CSV_PATH}")
        return

    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    creators = [row for row in rows if is_email_searchable(row.get('email', ''))]

    if not creators:
        print("All creators already have emails.")
        return

    print(f"Searching emails for {len(creators)} creators")
    print("=" * 60)

    found = 0
    not_found = 0

    for i, row in enumerate(creators, 1):
        name = row.get('name', 'Unknown')
        handle = row.get('handle', '')
        niche = row.get('niche', '')

        print(f"\n[{i}/{len(creators)}] {name} (@{handle})")

        email = search_creator_email(client, name, handle, niche)

        if email:
            row['email'] = email
            row['email_stage'] = 'none'
            found += 1
            print(f"  FOUND: {email}")
        else:
            row['email'] = ''
            row['email_stage'] = 'none'
            not_found += 1
            print(f"  NOT FOUND - will retry next run")

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 60)
    print(f"DONE - Found: {found}, Not found: {not_found}")


if __name__ == "__main__":
    main()
