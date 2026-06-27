"""
Twitter/X Creator Finder + Email Extractor

Fully automated: finds creators, extracts emails, adds to pipeline.csv.
Runs daily via GitHub Actions.
"""

import os
import re
import json
import csv
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PIPELINE_PATH = DATA_DIR / "pipeline.csv"

SEARCH_KEYWORDS = [
    "digital products creator twitter",
    "online course creator twitter",
    "ebook creator twitter profile",
    "template shop owner twitter",
    "passive income creator twitter",
    "creator economy twitter influencer",
    "digital product seller twitter",
    "notion template creator twitter",
    "canva template designer twitter",
    "gumroad creator twitter",
    "fitness coach digital products twitter",
    "finance creator online course twitter",
    "tech creator ebook twitter",
    "marketing expert digital products twitter",
]

NICHE_KEYWORDS = {
    "fitness": ["fitness", "workout", "gym", "personal trainer", "health", "wellness", "nutrition"],
    "finance": ["finance", "investing", "accountant", "cpa", "money", "stocks", "crypto"],
    "tech": ["tech", "ai", "software", "developer", "coding", "startup", "saas"],
    "marketing": ["marketing", "copywriting", "seo", "social media", "growth", "branding"],
    "lifestyle": ["lifestyle", "wellness", "mindset", "productivity", "self-improvement"],
    "education": ["education", "teaching", "course", "learning", "coach"],
    "creator economy": ["creator", "influencer", "content creator", "personal brand"],
}


def search_web(query, num_results=10):
    """Search Google/Bing for creators."""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num_results}"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for g in soup.select("div.g"):
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("div[data-sncf], div.VwiC3b, span.aCOpRe")

            if title_el and link_el:
                href = link_el.get("href", "")
                if href.startswith("/url?"):
                    href = href.split("/url?q=")[1].split("&")[0]
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
    except Exception as e:
        logger.warning(f"Google search failed: {e}. Trying Bing...")
        try:
            url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count={num_results}"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for li in soup.select("li.b_algo"):
                title_el = li.select_one("h2 a")
                snippet_el = li.select_one("div.b_caption p")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": title_el.get("href", ""),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })
        except Exception as e2:
            logger.error(f"Bing search also failed: {e2}")

    return results


def extract_twitter_username(text):
    """Extract Twitter username from text."""
    patterns = [
        r"twitter\.com/([A-Za-z0-9_]+)",
        r"x\.com/([A-Za-z0-9_]+)",
        r"@([A-Za-z0-9_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            username = match.group(1)
            if len(username) <= 15 and not username.startswith(("http", "www")):
                return username
    return None


def identify_niche(bio):
    """Identify niche from bio keywords."""
    bio_lower = bio.lower()
    for niche, keywords in NICHE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in bio_lower:
                return niche
    return "creator economy"


def extract_email_from_text(text):
    """Extract email address from text."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    for email in emails:
        if not email.endswith(('.png', '.jpg', '.gif', '.svg', '.webp')):
            return email
    return None


def try_get_email_from_url(url):
    """Try to fetch a URL and extract email from it."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        email = extract_email_from_text(resp.text)
        if email:
            return email
    except Exception:
        pass
    return None


def scrape_twitter_bio(username):
    """Scrape Twitter profile page for bio and email."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        url = f"https://x.com/{username}"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        bio = ""
        website = None

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            bio = meta_desc.get("content", "")

        bio_match = re.search(r'"description"\s*:\s*"([^"]+)"', resp.text)
        if bio_match:
            bio = bio_match.group(1)

        website_match = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', resp.text)
        if website_match:
            website = website_match.group(1)

        email = extract_email_from_text(resp.text)
        if not email and website:
            email = try_get_email_from_url(website)

        return bio, website, email
    except Exception as e:
        logger.warning(f"Failed to scrape Twitter for @{username}: {e}")
        return "", None, None


def use_groq_to_analyze(search_results, keyword):
    """Use Groq API to extract creator info from search results."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set")
        return []

    results_text = "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for r in search_results[:8]
    ])

    prompt = f"""Analyze these search results about Twitter/X creators in the "{keyword}" niche.
For each creator found, extract their information.

Search Results:
{results_text}

Return a JSON array of creators found. Each creator should have:
- username: Twitter username (without @)
- display_name: Their display name
- bio: Their bio or description
- follower_count: Follower count if mentioned (or "Unknown")
- niche: Their specific niche (fitness, finance, tech, marketing, lifestyle, etc.)
- website: Their website URL if found (or null)
- email: Their email if found in any text (or null)

Only include actual Twitter/X profiles. Return ONLY the JSON array, no other text.
If no creators found, return an empty array []."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.error(f"Groq API error: {e}")

    return []


def load_existing_pipeline():
    """Load existing usernames from pipeline.csv."""
    existing = set()
    if PIPELINE_PATH.exists():
        with open(PIPELINE_PATH, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                handle = row.get("handle", "").lower().strip()
                if handle:
                    existing.add(handle)
    return existing


def save_to_pipeline(creators):
    """Save new creators directly to pipeline.csv."""
    fieldnames = [
        "name", "handle", "followers", "niche", "email",
        "status", "notes", "status_changed_at", "email_stage", "last_email_date"
    ]

    file_exists = PIPELINE_PATH.exists()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(PIPELINE_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for c in creators:
            handle = f"@{c['username']}" if not c['username'].startswith('@') else c['username']
            writer.writerow({
                "name": c.get("display_name", c["username"]),
                "handle": handle,
                "followers": c.get("follower_count", "Unknown"),
                "niche": c.get("niche", "creator economy"),
                "email": c.get("email", ""),
                "status": "new",
                "notes": c.get("bio", "")[:200],
                "status_changed_at": now,
                "email_stage": "none",
                "last_email_date": "",
            })

    logger.info(f"Saved {len(creators)} creators to pipeline.csv")


def main():
    """Main function: find creators, extract emails, add to pipeline."""
    logger.info("=== Auto Find Creators Started ===")

    existing = load_existing_pipeline()
    logger.info(f"Existing creators in pipeline: {len(existing)}")

    all_creators = []
    seen = set()

    for keyword in SEARCH_KEYWORDS:
        logger.info(f"Searching: {keyword}")
        results = search_web(keyword, num_results=10)

        if not results:
            continue

        groq_creators = use_groq_to_analyze(results, keyword)

        for c in groq_creators:
            username = c.get("username", "").strip()
            if not username or f"@{username.lower()}" in existing or username in seen:
                continue
            seen.add(username)

            email = c.get("email")
            if not email:
                bio, website, scraped_email = scrape_twitter_bio(username)
                email = scraped_email
                if not email and website:
                    email = try_get_email_from_url(website)
                if not email:
                    bio_text = c.get("bio", "") + " " + bio
                    email = extract_email_from_text(bio_text)

            all_creators.append({
                "username": username,
                "display_name": c.get("display_name", username),
                "bio": c.get("bio", "")[:200],
                "follower_count": c.get("follower_count", "Unknown"),
                "niche": c.get("niche", identify_niche(c.get("bio", ""))),
                "email": email or "",
            })

        time.sleep(2)

    if all_creators:
        save_to_pipeline(all_creators)
        print(f"\n{'='*60}")
        print(f"FOUND {len(all_creators)} NEW CREATORS")
        print(f"{'='*60}")
        for i, c in enumerate(all_creators, 1):
            email_status = f"EMAIL: {c['email']}" if c['email'] else "NO EMAIL"
            print(f"{i}. @{c['username']} ({c['niche']}) - {email_status}")
        print(f"{'='*60}")
    else:
        logger.info("No new creators found")

    logger.info("=== Auto Find Creators Finished ===")


if __name__ == "__main__":
    main()
