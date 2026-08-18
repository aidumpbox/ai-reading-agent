#!/usr/bin/env python3
"""
Daily Reading Agent (Google-only, free-tier stack)
----------------------------------------------------
1. Pulls today's articles for each topic via Google Custom Search JSON API
   (free: 100 queries/day).
2. Hands them to Gemini (free tier: Flash models) along with the
   instructions in AGENTS.md, and lets the model decide what's worth
   keeping and what facts to extract.
3. Saves results to data/data.json, which index.html renders.

Env vars required (set as GitHub Actions secrets):
  GOOGLE_API_KEY  - Google Cloud API key with Custom Search JSON API enabled
  GOOGLE_CX       - Programmable Search Engine ID
  GEMINI_API_KEY  - API key from Google AI Studio (aistudio.google.com)
"""

import os
import json
import datetime
import requests
from google import genai

TOPICS = [
    "AI business news",
]
RESULTS_PER_TOPIC = 5
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "data.json")
AGENTS_FILE = os.path.join(os.path.dirname(__file__), "AGENTS.md")
GEMINI_MODEL = "gemini-2.5-flash"


def google_search(query, api_key, cx, num=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": num, "sort": "date"}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {"title": i.get("title", ""), "link": i.get("link", ""), "snippet": i.get("snippet", "")}
        for i in items
    ]


def load_agent_instructions():
    with open(AGENTS_FILE, "r") as f:
        return f.read()


def extract_with_gemini(client, instructions, articles):
    articles_block = "\n\n".join(
        f"Title: {a['title']}\nURL: {a['link']}\nSnippet: {a['snippet']}"
        for a in articles
    )
    prompt = f"{instructions}\n\n---\nToday's articles:\n\n{articles_block}\n\n---\nReturn the JSON array now."

    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = resp.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [{"skip": True, "skip_reason": "failed_to_parse", "raw": text}]


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
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    instructions = load_agent_instructions()

    today = datetime.date.today().isoformat()
    day_entry = {"date": today, "topics": []}

    for topic in TOPICS:
        print(f"Searching: {topic}")
        articles = google_search(topic, google_api_key, google_cx, num=RESULTS_PER_TOPIC)
        if not articles:
            day_entry["topics"].append({"topic": topic, "articles": []})
            continue

        print(f"Extracting facts for {len(articles)} articles via Gemini...")
        extracted = extract_with_gemini(gemini_client, instructions, articles)

        kept = [e for e in extracted if isinstance(e, dict) and not e.get("skip")]
        day_entry["topics"].append({"topic": topic, "articles": kept})

    data = load_existing_data()
    data["days"] = [d for d in data["days"] if d["date"] != today]
    data["days"].insert(0, day_entry)
    save_data(data)
    print(f"Saved results for {today} to {DATA_FILE}")


if __name__ == "__main__":
    main()
