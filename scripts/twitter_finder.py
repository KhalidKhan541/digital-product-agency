"""
Twitter/X Creator Finder Script

Finds Twitter/X creators in specific niches using web search and Groq API.
Outputs results in pipeline.csv format.
"""

import os
import re
import json
import csv
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SEARCH_KEYWORDS = [
    "digital products creator twitter",
    "online course creator twitter/X",
    "ebook creator twitter profile",
    "template shop owner twitter",
    "passive income creator twitter",
    "creator economy twitter influencer",
    "digital product seller twitter",
    "notion template creator twitter",
    "canva template designer twitter",
    "gumroad creator twitter",
]

NICHE_KEYWORDS = {
    "digital products": ["digital product", "digital download", "pdf", "template"],
    "online courses": ["course", "teach", "learn", "education", "udemy", "skillshare"],
    "ebooks": ["ebook", "e-book", "book", "author", "write"],
    "templates": ["template", "notion", "canva", "design", "figma"],
    "passive income": ["passive income", "financial freedom", "money online", "side hustle"],
    "creator economy": ["creator", "influencer", "content creator", "personal brand"],
}


@dataclass
class TwitterCreator:
    username: str
    display_name: str
    bio: str
    follower_count: str
    niche: str
    source: str
    discovered_date: str


def get_groq_api_key() -> Optional[str]:
    return os.environ.get("GROQ_API_KEY")


def search_web(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    """Search the web using Google scraping as fallback."""
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


def extract_twitter_username(text: str) -> Optional[str]:
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


def identify_niche(bio: str) -> str:
    """Identify the niche based on bio keywords."""
    bio_lower = bio.lower()

    for niche, keywords in NICHE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in bio_lower:
                return niche

    return "general creator"


def use_groq_to_analyze_creator(search_results: List[Dict], keyword: str) -> List[Dict]:
    """Use Groq API to analyze search results and identify good creators."""
    api_key = get_groq_api_key()

    if not api_key:
        logger.warning("GROQ_API_KEY not set, using basic parsing instead")
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
- niche: Their specific niche

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
            creators = json.loads(json_match.group())
            logger.info(f"Groq identified {len(creators)} creators for '{keyword}'")
            return creators

    except Exception as e:
        logger.error(f"Groq API error: {e}")

    return []


def search_and_collect_creators() -> List[TwitterCreator]:
    """Main search loop to collect Twitter creators."""
    all_creators: List[TwitterCreator] = []
    seen_usernames = set()

    for keyword in SEARCH_KEYWORDS:
        logger.info(f"Searching for: {keyword}")

        search_results = search_web(keyword, num_results=10)

        if not search_results:
            logger.warning(f"No results for '{keyword}'")
            continue

        groq_creators = use_groq_to_analyze_creator(search_results, keyword)

        for creator_data in groq_creators:
            username = creator_data.get("username", "").strip()

            if not username or username in seen_usernames:
                continue

            seen_usernames.add(username)

            niche = creator_data.get("niche", "")
            if not niche or niche == "general creator":
                bio = creator_data.get("bio", "")
                niche = identify_niche(bio)

            creator = TwitterCreator(
                username=username,
                display_name=creator_data.get("display_name", username),
                bio=creator_data.get("bio", ""),
                follower_count=creator_data.get("follower_count", "Unknown"),
                niche=niche,
                source=f"twitter_search:{keyword}",
                discovered_date=datetime.now().strftime("%Y-%m-%d"),
            )
            all_creators.append(creator)

        for result in search_results:
            username = extract_twitter_username(result.get("url", "") + " " + result.get("snippet", ""))

            if not username or username in seen_usernames:
                continue

            seen_usernames.add(username)

            bio = result.get("snippet", "")
            niche = identify_niche(bio)

            creator = TwitterCreator(
                username=username,
                display_name=username,
                bio=bio[:200] if bio else "",
                follower_count="Unknown",
                niche=niche,
                source=f"web_search:{keyword}",
                discovered_date=datetime.now().strftime("%Y-%m-%d"),
            )
            all_creators.append(creator)

        time.sleep(2)

    logger.info(f"Total creators found: {len(all_creators)}")
    return all_creators


def save_to_csv(creators: List[TwitterCreator], output_path: str) -> str:
    """Save creators to CSV in pipeline.csv format."""
    fieldnames = [
        "username",
        "display_name",
        "bio",
        "follower_count",
        "niche",
        "source",
        "discovered_date",
    ]

    file_exists = os.path.exists(output_path)

    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for creator in creators:
            writer.writerow(asdict(creator))

    logger.info(f"Saved {len(creators)} creators to {output_path}")
    return output_path


def main():
    """Main entry point for GitHub Actions."""
    logger.info("Starting Twitter Creator Finder")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"twitter_creators_{timestamp}.csv")

    creators = search_and_collect_creators()

    if creators:
        save_to_csv(creators, output_path)

        print(f"\n{'='*60}")
        print(f"DIScovered {len(creators)} Twitter/X creators")
        print(f"{'='*60}\n")

        for i, creator in enumerate(creators, 1):
            print(f"{i}. @{creator.username} ({creator.niche})")
            print(f"   Bio: {creator.bio[:80]}...")
            print()

        return {"creators_found": len(creators), "output_file": output_path}
    else:
        logger.warning("No creators found")
        return {"creators_found": 0, "output_file": None}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
