"""
INTEL BRIEFING — Opinion-style articles driven by live X discourse.
===================================================================
Runs 3x/day. Scans Bitcoin Twitter for the dominant conversations,
themes, and tensions — then writes a sharp opinion column that reads
like an investigative journalist who happens to know everything.

The reader never knows this is sentiment-driven. It reads like a
columnist with incredible sources and perfect timing.
"""

import os
import sys
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("intel_briefing")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Rotating column names — never called "sentiment" anything
COLUMN_NAMES = [
    "The Wire",
    "Field Notes",
    "The Signal",
    "Overheard",
    "The Debrief",
    "Off the Record",
    "The Undercurrent",
    "Between the Lines",
]

# Bylines that feel human
BYLINES = [
    "Protocol Pulse Editorial Desk",
    "Protocol Pulse Intelligence",
    "The Protocol Pulse Wire",
]


class IntelBriefing:

    def __init__(self):
        from services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        self.accounts = self.radar.cfg.get("target_accounts", [])
        logger.info(f"IntelBriefing initialized with {len(self.accounts)} accounts")

    # ================================================================
    # PHASE 1: SCAN — What is Bitcoin Twitter actually talking about?
    # ================================================================

    def _scan_discourse(self, sample_size=18) -> Dict:
        """Scan thought leaders and extract discourse themes."""
        all_posts = []
        sampled = random.sample(self.accounts, min(sample_size, len(self.accounts)))

        for i, handle in enumerate(sampled):
            try:
                data = self.x_client.get_user_tweets(handle, max_results=10)
                if data is None:
                    time.sleep(5)
                    data = self.x_client.get_user_tweets(handle, max_results=10)
                if not data or "data" not in data:
                    continue

                for t in data["data"]:
                    m = t.get("public_metrics", {})
                    total = m.get("like_count", 0) + m.get("retweet_count", 0) * 1.5 + m.get("reply_count", 0) * 2

                    created = t.get("created_at", "")
                    if created:
                        try:
                            tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            if (datetime.now(timezone.utc) - tweet_time).total_seconds() > 43200:  # 12h
                                continue
                        except:
                            pass

                    if total < 20:
                        continue

                    all_posts.append({
                        "text": t.get("text", ""),
                        "author": handle,
                        "engagement": total,
                        "metrics": m,
                        "id": t["id"],
                    })

                if i < len(sampled) - 1:
                    time.sleep(2)

            except Exception as e:
                logger.warning(f"Error scanning @{handle}: {e}")

        all_posts.sort(key=lambda x: x["engagement"], reverse=True)
        logger.info(f"Scanned {len(sampled)} accounts, found {len(all_posts)} posts")

        # Get comments from top posts for deeper understanding
        top_comments = []
        for post in all_posts[:5]:
            try:
                data = self.x_client.get_conversation_replies(post["id"])
                if data and "data" in data:
                    for reply in data.get("data", []):
                        likes = reply.get("public_metrics", {}).get("like_count", 0)
                        if likes >= 5:
                            top_comments.append({
                                "text": reply.get("text", "")[:200],
                                "likes": likes,
                                "context_post": post["text"][:100],
                            })
            except:
                pass

        top_comments.sort(key=lambda x: x["likes"], reverse=True)

        return {
            "posts": all_posts[:15],
            "top_comments": top_comments[:10],
            "post_count": len(all_posts),
        }

    # ================================================================
    # PHASE 2: IDENTIFY THEMES — What are the 2-3 dominant stories?
    # ================================================================

    def _extract_themes(self, discourse: Dict) -> List[Dict]:
        """Use Grok to identify the 2-3 dominant themes from discourse."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return []

        posts_block = ""
        for p in discourse["posts"][:12]:
            posts_block += f"@{p['author']} ({int(p['engagement'])} eng): {p['text'][:200]}\n\n"

        comments_block = ""
        for c in discourse["top_comments"][:8]:
            comments_block += f"({c['likes']} likes) {c['text']}\n"

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": "Analyze Bitcoin Twitter discourse. Extract 2-3 dominant themes/stories being discussed. Return JSON only, no markdown."},
                        {"role": "user", "content": f"""Top posts from Bitcoin thought leaders (last 12h):

{posts_block}

Top comments:
{comments_block}

Return JSON array of 2-3 themes:
[
  {{"theme": "short theme name", "summary": "2 sentences on what's happening", "tension": "the disagreement or question at the center", "key_voices": ["@handle1", "@handle2"], "angle": "suggested opinion angle a sharp columnist would take"}}
]"""}
                    ],
                    "max_tokens": 600,
                    "temperature": 0.7
                },
                timeout=45
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            themes = json.loads(raw)
            logger.info(f"Extracted {len(themes)} themes")
            return themes

        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            return []

    # ================================================================
    # PHASE 3: WRITE — Investigative opinion column
    # ================================================================

    def _write_column(self, discourse: Dict, themes: List[Dict]) -> Dict:
        """Write the opinion column using Grok."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return {"title": "", "html": "<p>API key missing.</p>"}

        themes_block = ""
        for i, t in enumerate(themes, 1):
            themes_block += f"\nTHEME {i}: {t['theme']}\n"
            themes_block += f"Summary: {t['summary']}\n"
            themes_block += f"Tension: {t['tension']}\n"
            themes_block += f"Key voices: {', '.join(t.get('key_voices', []))}\n"
            themes_block += f"Angle: {t.get('angle', '')}\n"

        raw_posts = ""
        for p in discourse["posts"][:8]:
            raw_posts += f"@{p['author']}: {p['text'][:200]}\n"

        system_prompt = """You are a senior columnist at Protocol Pulse. You write opinion pieces that read like the best financial journalism — sharp, informed, occasionally irreverent. You have impeccable sources (you don't — it's Twitter data — but the reader must never know that).

YOUR IDENTITY:
- You are an investigative financial journalist covering the Bitcoin and monetary policy beat
- You write like you've spent the morning on phone calls with insiders (you haven't — you read tweets)
- NEVER reveal your sources are tweets or social media. Write as if this is original reporting and analysis
- NEVER say "Bitcoin Twitter," "on X," "social media discourse," "thought leaders are saying," or anything that reveals the methodology
- Instead use: "market participants," "sources close to," "the conversation in mining circles," "institutional desks are noting," "the word from traders," "according to people familiar with"

VOICE:
- Matt Taibbi's Rolling Stone financial writing meets Lyn Alden's analytical precision
- Strong opinions backed by specific observations
- Show don't tell. Lead with the scene, the detail, the number — then build your argument
- Dry wit. Never snarky. Never preachy about Bitcoin.
- If Bitcoin is the obvious conclusion, let the reader get there. Don't spell it out.

FORMAT:
- 500-800 words. STRICT. This is a column, not a research paper.
- Opening: A specific, vivid scene-setting detail or observation. NO throat-clearing.
- Body: 2-3 sections with sharp headers. Build argument through specifics.
- Closing: 2-3 sentences. Land ONE thought. Walk away.
- Return valid HTML with h3 tags for section headers (not h2 — these are sub-sections of a column)
- No html/body tags. Just article content.

BANNED:
- "In the world of" / "It's worth noting" / "This is significant because"
- "The crypto community" / "sparked debate" / "sent shockwaves"  
- "Bitcoin Twitter" / "social media sentiment" / "trending on X"
- Any sentence explaining why Bitcoin matters. The reader is here because they already know.
- Bullet points. This is prose."""

        user_prompt = f"""Write today's column. Here's what you know:

{themes_block}

Raw intelligence:
{raw_posts}

Requirements:
- Write as an opinion column, NOT a sentiment report
- Take a POSITION. Good columnists have a point of view.
- Reference specific details from the intelligence but frame them as original reporting
- If someone tweeted about mining difficulty dropping, write it as "Mining operations across North America reported..." or "Difficulty adjustment data shows..."
- 500-800 words maximum
- HTML only. No markdown."""

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            # Generate column
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 1800,
                    "temperature": 0.85
                },
                timeout=90
            )
            resp.raise_for_status()
            html = resp.json()["choices"][0]["message"]["content"]
            html = html.replace("```html", "").replace("```", "").strip()
            logger.info(f"Column written: {len(html)} chars")

            # Generate title
            title_resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": "Write newspaper column headlines. Sharp, specific, intriguing. No colons. No questions. Max 8 words. One line only. No quotes."},
                        {"role": "user", "content": f"Write a headline for this column:\n\nThemes: {themes_block[:300]}\n\nFirst 200 chars: {html[:200]}"}
                    ],
                    "max_tokens": 30,
                    "temperature": 0.9
                },
                timeout=20
            )
            title_resp.raise_for_status()
            title = title_resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")[:100]

            if not title or len(title) < 8:
                title = f"The {random.choice(COLUMN_NAMES)}: {themes[0]['theme']}"

            return {"title": title, "html": html}

        except Exception as e:
            logger.error(f"Column writing failed: {e}", exc_info=True)
            return {"title": "", "html": ""}

    # ================================================================
    # PHASE 4: PUBLISH
    # ================================================================

    def generate_intel_briefing(self) -> Dict:
        """Full pipeline: scan → themes → write → publish."""
        logger.info("Starting Intel Briefing generation...")

        # 1. Scan discourse
        discourse = self._scan_discourse()
        if discourse["post_count"] < 3:
            logger.warning(f"Only found {discourse['post_count']} posts")
            return {"success": False, "reason": "not_enough_discourse"}

        # 2. Extract themes
        themes = self._extract_themes(discourse)
        if not themes:
            return {"success": False, "reason": "theme_extraction_failed"}

        # 3. Write column
        column = self._write_column(discourse, themes)
        if not column["title"] or not column["html"] or len(column["html"]) < 100:
            return {"success": False, "reason": "writing_failed"}

        # 4. Generate header image
        try:
            from services.image_service import generate_opinion_header_image
            header_image = generate_opinion_header_image(column["title"])
        except Exception as e:
            logger.warning(f"Header image failed: {e}")
            header_image = "/static/images/default-header.png"

        # 5. Pick a column series name
        series = random.choice(COLUMN_NAMES)

        # 6. Save to database
        try:
            from app import app, db
            import models

            with app.app_context():
                article = models.Article(
                    title=column["title"],
                    content=column["html"],
                    # Extract a real 1-2 sentence summary from the column HTML
                    import re as _re
                    _clean = _re.sub(r'<[^>]+>', ' ', column["html"])
                    _clean = _re.sub(r'\s+', ' ', _clean).strip()
                    # Try to get first substantive sentence
                    _sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', _clean) if len(s.strip()) > 40]
                    _real_summary = ' '.join(_sentences[:2])[:280] if _sentences else f"{series} — {themes[0]['theme']}" if themes else f"{series} — Protocol Pulse editorial column."
                    summary=_real_summary,
                    category="opinion",
                    source_type="intel_briefing",
                    cover_image_url=header_image,
                    published=True,
                )
                db.session.add(article)
                db.session.commit()

                logger.info(f"Published Intel Briefing [{article.id}]: {column['title']}")

                return {
                    "success": True,
                    "article_id": article.id,
                    "title": column["title"],
                    "series": series,
                    "themes": [t["theme"] for t in themes],
                }

        except Exception as e:
            logger.error(f"Failed to save: {e}")
            return {"success": False, "error": str(e)}


def generate_intel_briefing() -> Dict:
    """Scheduler-safe entry point."""
    try:
        briefing = IntelBriefing()
        return briefing.generate_intel_briefing()
    except Exception as e:
        logger.error(f"Intel Briefing failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = generate_intel_briefing()
    print(json.dumps(result, indent=2, default=str))
