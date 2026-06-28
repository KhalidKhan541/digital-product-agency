import os
import csv
import re
import json
import urllib.request
from groq import Groq

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pipeline.csv')
GROQ_MODEL = "llama-3.3-70b-versatile"

SKIP_DOMAINS = {'example.com', 'email.com', 'sentry.io', 'wixpress.com', 'github.com',
                'googleusercontent.com', 'google.com', 'facebook.com', 'twitter.com',
                'instagram.com', 'tiktok.com', 'youtube.com', 'substack.com', 'x.com',
                'duckduckgo.com', 'bing.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'protonmail.com', 'aol.com', 'mail.com', 'icloud.com', 'brave.com'}

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'


def is_valid_email(email):
    if not email or '@' not in email or len(email) < 6 or len(email) > 100:
        return False
    domain = email.split('@')[1].lower()
    if domain in SKIP_DOMAINS:
        return False
    if email.startswith(('error-', 'noreply', 'no-reply', 'test', 'admin@')):
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def exa_search(query, api_key, num_results=5):
    data = json.dumps({
        "query": query,
        "numResults": num_results,
        "type": "neural",
        "contents": {"highlights": True, "text": True}
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.exa.ai/search",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"    Exa error: {e}")
    return None


def extract_emails_from_exa(results):
    emails = []
    if not results:
        return emails

    for r in results.get('results', []):
        text = r.get('text', '') or ''
        highlights = r.get('highlights', []) or []
        all_text = text + ' ' + ' '.join(highlights)
        found = re.findall(EMAIL_REGEX, all_text)
        for e in found:
            if is_valid_email(e):
                emails.append(e.lower())

    return list(set(emails))


def find_email_via_groq(client, name, handle, niche):
    prompt = f"""Find the email address for this content creator:

Name: {name}
Handle: @{handle}
Niche: {niche}

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
            if email and '@' in email and email != 'null' and is_valid_email(email):
                return email
    except Exception as e:
        print(f"    Groq error: {e}")
    return None


def search_creator(client, exa_key, name, handle, niche):
    queries = [
        f'{name} {handle} email contact',
        f'{name} {niche} creator email',
        f'{handle} newsletter email',
    ]

    for q in queries:
        print(f"    Exa: {q}")
        result = exa_search(q, exa_key, num_results=3)
        if result:
            emails = extract_emails_from_exa(result)
            if emails:
                return emails[0]
        import time
        time.sleep(1)

    print("    Trying Groq AI...")
    return find_email_via_groq(client, name, handle, niche)


def needs_search(email):
    return not email or email.strip() in ("", "none", "null", "nan", "not_found")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    exa_key = os.environ.get("EXA_API_KEY")

    if not api_key:
        print("Error: GROQ_API_KEY not set")
        return
    if not exa_key:
        print("Error: EXA_API_KEY not set")
        print("Get free key at https://dashboard.exa.ai (20,000 free requests/month)")
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

    print(f"Searching {len(creators)} creators with Exa AI")
    print("=" * 50)

    found = 0
    for i, row in enumerate(creators, 1):
        name = row.get('name', '?')
        handle = row.get('handle', '')
        niche = row.get('niche', '')

        print(f"\n[{i}/{len(creators)}] {name} (@{handle})")
        email = search_creator(client, exa_key, name, handle, niche)

        if email and is_valid_email(email):
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
