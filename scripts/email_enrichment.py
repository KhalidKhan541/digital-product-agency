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
}

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
SKIP_DOMAINS = {'example.com', 'email.com', 'sentry.io', 'wixpress.com', 'github.com',
                'googleusercontent.com', 'google.com', 'facebook.com', 'twitter.com',
                'instagram.com', 'tiktok.com', 'youtube.com', 'substack.com', 'x.com',
                'duckduckgo.com', 'bing.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'protonmail.com', 'aol.com', 'mail.com', 'icloud.com'}


def is_valid_email(email):
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1].lower()
    if domain in SKIP_DOMAINS:
        return False
    if email.startswith('error-') or email.startswith('noreply') or email.startswith('no-reply'):
        return False
    if len(email) < 6 or len(email) > 100:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    return True


def ddg_search(query):
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"    DDG failed: {e}")
    return ""


def extract_emails(text):
    raw = re.findall(EMAIL_REGEX, text)
    return [e.lower() for e in raw if is_valid_email(e)]


def extract_website_url(html):
    match = re.search(r'href="(https?://[^"]*)"', html)
    if match:
        url = match.group(1)
        if not any(x in url for x in ['twitter.com', 'x.com', 'instagram.com', 'facebook.com', 'tiktok.com']):
            return url
    return None


def scrape_website_for_email(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            emails = extract_emails(html)
            return emails[0] if emails else None
    except:
        return None


def find_email_via_groq(client, name, handle, niche):
    prompt = f"""Find the email address for this Twitter/X content creator:

Name: {name}
Handle: @{handle}
Niche: {niche}

Search your knowledge for any public email this creator has shared.
Return ONLY: {{"email": "email@example.com"}} or {{"email": null}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        text = response.choices[0].message.content.strip()
        match = re.search(r'\{[^{}]*"email"[^{}]*\}', text)
        if match:
            result = json.loads(match.group())
            email = result.get("email")
            if email and '@' in email and email != 'null':
                return email
    except Exception as e:
        print(f"    Groq error: {e}")
    return None


def search_creator(client, name, handle, niche):
    queries = [
        f'"{name}" "{handle}" email',
        f'"{name}" contact email {niche}',
        f'@{handle} email newsletter',
    ]

    for q in queries:
        print(f"    Search: {q}")
        html = ddg_search(q)
        if html:
            emails = extract_emails(html)
            if emails:
                valid = [e for e in emails if is_valid_email(e)]
                if valid:
                    return valid[0]
            website = extract_website_url(html)
            if website:
                print(f"    Found website: {website}")
                email = scrape_website_for_email(website)
                if email and is_valid_email(email):
                    return email
        time.sleep(2)

    print("    Trying Groq AI...")
        email = find_email_via_groq(client, name, handle, niche)
        if email and is_valid_email(email):
            return email

    return None


def needs_search(email):
    return not email or email.strip() in ("", "none", "null", "nan", "not_found")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set")
        return

    client = Groq(api_key=api_key)

    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found")
        return

    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    creators = [r for r in rows if needs_search(r.get('email', ''))]

    if not creators:
        print("All creators have emails.")
        return

    print(f"Searching {len(creators)} creators")
    print("=" * 50)

    found = 0
    for i, row in enumerate(creators, 1):
        name = row.get('name', '?')
        handle = row.get('handle', '')
        niche = row.get('niche', '')

        print(f"\n[{i}/{len(creators)}] {name} (@{handle})")
        email = search_creator(client, name, handle, niche)

        if email:
            row['email'] = email
            row['email_stage'] = 'none'
            found += 1
            print(f"  => {email}")
        else:
            row['email'] = ''
            row['email_stage'] = 'none'
            print(f"  => not found")

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone: {found}/{len(creators)} found")


if __name__ == "__main__":
    main()
