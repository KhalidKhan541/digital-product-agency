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
MAX_RETRIES = 3
RETRY_DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def google_search(query, num_results=5):
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}&num={num_results}"
    
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                return html
        except Exception as e:
            print(f"  Search attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return ""


def extract_emails_with_groq(client, text, creator_name):
    prompt = f"""Extract email addresses from the following text about {creator_name}.

Text:
{text[:3000]}

Return ONLY a JSON object in this exact format:
{{
  "emails": ["email1@example.com", "email2@example.com"],
  "confidence": "high" or "medium" or "low",
  "source": "brief description of where the email was found"
}}

If no email addresses are found, return:
{{
  "emails": [],
  "confidence": "none",
  "source": "no email found"
}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=250
        )
        
        result_text = response.choices[0].message.content.strip()
        
        json_match = re.search(r'\{[^{}]*"emails"[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
    except Exception as e:
        print(f"  Groq extraction error: {e}")
    
    return {"emails": [], "confidence": "none", "source": "extraction failed"}


def search_creator_email(client, name, handle, niche):
    search_queries = [
        f"{name} email contact",
        f"{name} @{handle} email",
    ]
    
    all_html = ""
    found_emails = []
    
    for query in search_queries:
        print(f"  Searching: {query}")
        html = google_search(query)
        if html:
            all_html += html + "\n"
        
        if all_html:
            result = extract_emails_with_groq(client, all_html, name)
            if result.get("emails"):
                found_emails.extend(result["emails"])
                if len(found_emails) > 0:
                    return list(set(found_emails))
        time.sleep(1)
    
    fallback_queries = [
        f"@{handle} email",
        f"{name} {niche} contact email",
    ]
    
    for query in fallback_queries:
        print(f"  Fallback search: {query}")
        html = google_search(query)
        if html:
            all_html += html + "\n"
        
        if all_html:
            result = extract_emails_with_groq(client, all_html, name)
            if result.get("emails"):
                found_emails.extend(result["emails"])
                if len(found_emails) > 0:
                    return list(set(found_emails))
        time.sleep(1)
    
    return list(set(found_emails)) if found_emails else []


def is_email_empty(email):
    return not email or email.strip() == "" or email.strip().lower() in ["", "none", "null", "nan"]


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set")
        return
    
    client = Groq(api_key=api_key)
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return
    
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    creators_to_enrich = [row for row in rows if is_email_empty(row.get('email', ''))]
    
    if not creators_to_enrich:
        print("No creators found with empty emails.")
        return
    
    print(f"Found {len(creators_to_enrich)} creators to enrich")
    print("=" * 60)
    
    emails_found = 0
    emails_not_found = 0
    
    for i, row in enumerate(creators_to_enrich, 1):
        name = row.get('name', 'Unknown')
        handle = row.get('handle', '')
        niche = row.get('niche', '')
        
        print(f"\n[{i}/{len(creators_to_enrich)}] Processing: {name} (@{handle})")
        
        emails = search_creator_email(client, name, handle, niche)
        
        if emails:
            row['email'] = emails[0]
            row['email_stage'] = 'none'
            emails_found += 1
            print(f"  FOUND: {emails[0]}")
        else:
            row['email'] = 'not_found'
            row['email_stage'] = 'exhausted'
            emails_not_found += 1
            print(f"  NOT FOUND")
    
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print("\n" + "=" * 60)
    print("ENRICHMENT COMPLETE")
    print(f"Emails found: {emails_found}")
    print(f"Emails not found: {emails_not_found}")
    print(f"CSV updated: {CSV_PATH}")


if __name__ == "__main__":
    main()
