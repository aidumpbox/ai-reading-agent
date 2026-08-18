#!/usr/bin/env python3
"""
Daily Reading Agent
--------------------
1. Searches Google Custom Search (news) for a list of topics.
2. Sends each article's title/snippet/url to Claude to extract
   structured facts.
3. Appends the day's results to data/data.json, which a static
   webpage (index.html) reads and renders.

Env vars required (set as GitHub Actions secrets):
  GOOGLE_API_KEY   - Google Cloud API key with Custom Search JSON API enabled
  GOOGLE_CX        - Programmable Search Engine ID (the "cx" value)
  ANTHROPIC_API_KEY - Anthropic API key
"""

import os
import json
import datetime
import requests
import anthropic

# ---- Config ----------------------------------------------------------
TOPICS = [
    "AI business news",
]
RESULTS_PER_TOPIC = 5          # how many articles to pull per topic per day
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "data.json")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ---- Google Custom Search ---------------------------------------------

def google_search(query, api_key, cx, num=5):
    """Return a list of {title, link, snippet} dicts from Google CSE."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": num,
        "sort": "date",  # bias toward recent results
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]


# ---- Claude extraction --------------------------------------------------

EXTRACTION_PROMPT = """You will be given a news article's title, URL, and snippet.
Extract the key facts and data points a reader would want from a daily digest.

Return ONLY valid JSON (no markdown fences, no preamble) matching this shape:
{{
  "headline": "short restated headline",
  "key_facts": ["fact 1", "fact 2", "..."],
  "companies_or_entities": ["..."],
  "numbers_mentioned": ["e.g. $2.1B funding round", "e.g. 40% growth"],
  "why_it_matters": "one sentence"
}}

Article title: {title}
Article URL: {link}
Article snippet: {snippet}
"""


def extract_facts(client, article):
    prompt = EXTRACTION_PROMPT.format(
        title=article["title"], link=article["link"], snippet=article["snippet"]
    )
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # Strip accidental code fences just in case
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "failed_to_parse", "raw": text}


# ---- Main ----------------------------------------------------------------

def load_existing_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"days": []}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    google_api_key = os.environ["GOOGLE_API_KEY"]
    google_cx = os.environ["GOOGLE_CX"]
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today = datetime.date.today().isoformat()
    day_entry = {"date": today, "topics": []}

    for topic in TOPICS:
        print(f"Searching: {topic}")
        articles = google_search(topic, google_api_key, google_cx, num=RESULTS_PER_TOPIC)

        extracted_articles = []
        for article in articles:
            facts = extract_facts(anthropic_client, article)
            extracted_articles.append(
                {
                    "title": article["title"],
                    "link": article["link"],
                    "extracted": facts,
                }
            )

        day_entry["topics"].append({"topic": topic, "articles": extracted_articles})

    data = load_existing_data()
    # Replace today's entry if the workflow runs twice in a day, else append
    data["days"] = [d for d in data["days"] if d["date"] != today]
    data["days"].insert(0, day_entry)  # newest first
    save_data(data)
    print(f"Saved results for {today} to {DATA_FILE}")


if __name__ == "__main__":
    main()
