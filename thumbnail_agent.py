"""
Thumbnail & Title Recursive Intelligence Agent
================================================
Runs weekly. Searches for latest CTR optimization research via Grok.
Builds a compounding skills file that makes every thumbnail better.

Protocol Pulse: ESPN SportsCenter for Bitcoin.
Every thumbnail must stop the scroll.
"""

import os
import json
import datetime
import requests

SKILLS_FILE = os.path.join(os.path.dirname(__file__), "THUMBNAIL_SKILLS.md")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")

SEARCH_PROMPT = """Search your knowledge for the latest YouTube thumbnail and title optimization
strategies from 2025-2026. Include:
1. Heat map research (where do eyes land first?)
2. Color psychology for CTR
3. Text overlay best practices (font size, word count, contrast)
4. Face/emotion impact on CTR
5. Title formula patterns that drive clicks
6. A/B testing insights from major creators
7. Mr. Beast team techniques
8. Algorithm-friendly practices
9. Bitcoin/finance niche specific insights
10. Mobile-first thumbnail optimization (most views are mobile)

Format as actionable rules with specific numbers where possible.
Return as markdown with ## headers for each category.
Focus on what's working RIGHT NOW in 2025-2026."""


def update_skills():
    """Search for latest thumbnail/title optimization research via Grok."""
    if not XAI_API_KEY:
        print("[thumbnail_agent] No XAI key, skipping")
        return

    print("[thumbnail_agent] Querying Grok for latest thumbnail research...")

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "grok-3-latest",
            "messages": [{"role": "user", "content": SEARCH_PROMPT}]
        },
        timeout=60
    )

    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

        entry = f"\n\n---\n## Updated: {timestamp}\n\n{content}\n"

        with open(SKILLS_FILE, "a") as f:
            f.write(entry)

        print(f"[thumbnail_agent] Skills updated: {len(content)} chars appended to {SKILLS_FILE}")
    else:
        print(f"[thumbnail_agent] Grok error: {r.status_code} — {r.text[:200]}")


def get_thumbnail_brief(article_title: str, article_summary: str) -> str:
    """Generate a thumbnail brief for a specific article using current skills."""
    if not XAI_API_KEY:
        return "[thumbnail_agent] No XAI key."

    # Load current skills
    skills = ""
    if os.path.exists(SKILLS_FILE):
        with open(SKILLS_FILE, "r") as f:
            content = f.read()
            # Use last 3000 chars (most recent skills)
            skills = content[-3000:] if len(content) > 3000 else content

    prompt = f"""You are a world-class YouTube thumbnail and title strategist.

CURRENT BEST PRACTICES (from skills file):
{skills if skills else "No skills file yet — use general best practices."}

ARTICLE:
Title: {article_title}
Summary: {article_summary}

Create a thumbnail brief:
1. MAIN TEXT (3-4 words max, high impact)
2. VISUAL CONCEPT (what image/graphic works best)
3. COLOR SCHEME (specific hex codes)
4. EMOTION/FACE (what expression if including a person)
5. TITLE (YouTube title, 55-60 chars, front-loaded hook)
6. A/B VARIANT TITLE (alternative angle)
7. CTR PREDICTION (why this works based on current data)

Bitcoin-specific: Use orange (#F7931A) as accent when relevant.
This is for Protocol Pulse — the ESPN of Bitcoin. Premium, authoritative, urgent."""

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "grok-3-latest",
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=45
    )

    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    else:
        return f"[thumbnail_agent] Error: {r.status_code}"


def get_skills_summary() -> str:
    """Return the current thumbnail skills summary."""
    if not os.path.exists(SKILLS_FILE):
        return "No skills file found. Run update_skills() first."
    with open(SKILLS_FILE, "r") as f:
        content = f.read()
    lines = content.split("\n")
    return "\n".join(lines[:50]) + f"\n\n... ({len(lines)} total lines)"


if __name__ == "__main__":
    print("[thumbnail_agent] Running skills update...")
    update_skills()
    print("[thumbnail_agent] Done.")
