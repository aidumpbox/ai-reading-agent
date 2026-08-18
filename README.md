# Daily Reading Agent

Reads news on chosen topics daily, extracts structured facts with Claude,
and displays them on a static webpage. Runs unattended via GitHub Actions.

Currently tracking: **AI business news**

## How it works

1. `agent.py` searches Google Custom Search for each topic in `TOPICS`.
2. Each article gets sent to Claude, which extracts key facts, entities,
   numbers, and a "why it matters" line as structured JSON.
3. Results are appended to `data/data.json` (newest day first).
4. `index.html` fetches that JSON and renders it — no backend needed.
5. A GitHub Actions workflow (`.github/workflows/daily-run.yml`) runs the
   script every day and commits the updated data file.

## Setup

### 1. Google Custom Search
- Go to https://programmablesearchengine.google.com/ and create a search engine.
  - Set it to search the entire web.
  - Copy the **Search engine ID** (this is your `GOOGLE_CX`).
- Go to https://console.cloud.google.com/, enable the **Custom Search JSON API**,
  and create an API key (this is your `GOOGLE_API_KEY`).
- Free tier: 100 queries/day.

### 2. Anthropic API key
- Get one from https://console.anthropic.com/ (this is your `ANTHROPIC_API_KEY`).

### 3. GitHub repo secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
Add all three:
- `GOOGLE_API_KEY`
- `GOOGLE_CX`
- `ANTHROPIC_API_KEY`

### 4. Enable GitHub Pages
**Settings → Pages → Source: Deploy from branch → main → / (root)**

### 5. Test it manually
Go to the **Actions** tab → **Daily Reading Agent** → **Run workflow**,
to trigger a run without waiting for the schedule.

## Local testing

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
export GOOGLE_CX=your_cx
export ANTHROPIC_API_KEY=your_key
python agent.py
```

Then open `index.html` locally (or serve the folder) to check the output.

## Adding topics

Edit the `TOPICS` list at the top of `agent.py`:

```python
TOPICS = [
    "AI business news",
    "another topic here",
]
```

Keep an eye on the Google CSE free tier (100 queries/day) — each topic
uses 1 query per run.
