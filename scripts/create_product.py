#!/usr/bin/env python3
"""Create digital product using Groq API"""

import os
import json
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_KEY_HERE")

def create_product(creator_name, niche, product_type="ebook"):
    """Generate a complete digital product"""
    
    prompt = f"""Create a comprehensive {product_type} about {niche} for {creator_name}'s audience.
    
    Include:
    1. Title and subtitle
    2. Table of contents with 5-7 chapters
    3. Full content for chapter 1 (1000+ words)
    4. Key takeaways for each chapter
    5. Action items
    6. Landing page copy
    7. 5-email launch sequence
    
    Make it valuable, actionable, and professional."""
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are an expert digital product creator. Output in markdown."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
    )
    
    return response.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    creator = input("Creator name: ")
    niche = input("Niche: ")
    ptype = input("Product type (ebook/template/guide): ") or "ebook"
    
    product = create_product(creator, niche, ptype)
    
    filename = f"product_{creator.lower().replace(' ', '_')}.md"
    with open(filename, "w") as f:
        f.write(product)
    
    print(f"Product saved to {filename}")
