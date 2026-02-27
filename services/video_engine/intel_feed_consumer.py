"""
INTEL FEED CONSUMER
====================
Bridges the intelligence pipeline output into downstream systems:
  1. daily_intel.json  -> Article generator (video-sourced articles)
  2. tweet_queue.json  -> X/Twitter automation (pre-composed tweets)
  3. newsletter_digest.json -> Newsletter engine (digest data)

This closes the intelligence loop:
  Monitor -> Transcribe -> Analyze -> [Produce Video] -> Feed Articles/Tweets/Newsletter
"""

import os
import json
import time
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("IntelFeedConsumer")

INTEL_DIR = Path("data/video_engine/intel")

# Limits
MAX_ARTICLES_PER_RUN = 3
MAX_TWEETS_PER_RUN = 8
TWEET_DELAY_SECONDS = 120  # 2 min between tweets to avoid rate limits


class IntelFeedConsumer:
    """Consume intel feeds and push to downstream systems."""

    def __init__(self, date: str = None):
        self.today = date or datetime.now().strftime("%Y-%m-%d")
        self.date_display = datetime.now().strftime("%B %d, %Y")

    def consume_all(self) -> Dict:
        """Run all feed consumers. Returns summary of actions taken."""
        logger.info(f"\n{'='*60}")
        logger.info(f"INTEL FEED CONSUMER — {self.today}")
        logger.info(f"{'='*60}\n")

        results = {}

        # 1. Articles from daily intel
        if os.environ.get("ENABLE_INTEL_ARTICLES", "true").lower() in ("true", "1"):
            results["articles"] = self.generate_articles_from_intel()
        else:
            logger.info("  Intel articles: disabled (ENABLE_INTEL_ARTICLES != true)")
            results["articles"] = {"skipped": True}

        # 2. Tweets from tweet queue
        if os.environ.get("ENABLE_TWEETS", "").lower() in ("true", "1"):
            results["tweets"] = self.post_tweet_queue()
        else:
            logger.info("  Tweet queue: disabled (ENABLE_TWEETS != true)")
            results["tweets"] = {"skipped": True}

        # 3. Newsletter digest
        results["newsletter"] = self.prepare_newsletter_digest()

        logger.info(f"\n  Feed consumer complete:")
        for system, result in results.items():
            if result.get("skipped"):
                logger.info(f"    {system}: skipped")
            else:
                logger.info(f"    {system}: {result.get('count', 0)} items processed")

        return results

    # ─────────────────────────────────────────────────────────
    # ARTICLES FROM INTEL
    # ─────────────────────────────────────────────────────────

    def generate_articles_from_intel(self) -> Dict:
        """Generate articles from daily intel highlights.

        Takes the top-scored highlights that weren't covered by RSS
        and generates original articles about what thought leaders said.
        """
        intel = self._load_intel("daily_intel")
        if not intel:
            return {"error": "No daily intel found", "count": 0}

        highlights = intel.get("highlights", [])
        if not highlights:
            return {"error": "No highlights in intel", "count": 0}

        # Sort by hook_score descending
        highlights.sort(key=lambda h: h.get("hook_score", 0), reverse=True)

        generated = []
        errors = []

        for highlight in highlights[:MAX_ARTICLES_PER_RUN * 2]:  # Try up to 2x to fill quota
            if len(generated) >= MAX_ARTICLES_PER_RUN:
                break

            channel = highlight.get("channel", "Unknown")
            quote = highlight.get("key_quote", "")
            score = highlight.get("hook_score", 0)

            if score < 65:
                logger.info(f"  Skipping {channel} (score {score} < 65)")
                continue

            logger.info(f"  Generating article from {channel} (score: {score})...")

            result = self._generate_single_article(highlight)
            if result and result.get("success"):
                generated.append({
                    "channel": channel,
                    "article_id": result.get("article_id"),
                    "title": result.get("title"),
                    "hook_score": score
                })
                logger.info(f"    + Article: {result.get('title', '')[:60]}")
            else:
                error_msg = result.get("error", "Unknown") if result else "Generation failed"
                if result and result.get("skipped"):
                    logger.info(f"    - Skipped: {result.get('reason', 'duplicate')}")
                else:
                    errors.append({"channel": channel, "error": error_msg})
                    logger.warning(f"    - Failed: {error_msg}")

        return {
            "count": len(generated),
            "articles": generated,
            "errors": errors
        }

    def _generate_single_article(self, highlight: Dict) -> Optional[Dict]:
        """Generate one article from a highlight. Runs inside Flask app context."""
        try:
            from app import app, db
            from models import Article
            from services.image_service import ImageGenerationService
            from services.article_automation import (
                _is_topic_oversaturated, _check_headline_diversity,
                _rewrite_headline_without_bitcoin, strip_html_fences
            )
            from openai import OpenAI

            channel = highlight.get("channel", "Unknown")
            handle = highlight.get("channel_handle", "")
            video_title = highlight.get("video_title", "")
            video_id = highlight.get("video_id", "")
            key_quote = highlight.get("key_quote", "")
            summary = highlight.get("summary", "")
            themes = highlight.get("themes", [])

            # Build a source-like dict for dedup checking
            source_title = f"{channel}: {key_quote[:80]}"

            # Dedup check
            if _is_topic_oversaturated(source_title, max_same=1, hours=24):
                return {"success": False, "skipped": True, "reason": "topic_oversaturated"}

            # Check headline diversity
            diversity = _check_headline_diversity(hours=72)
            headline_constraint = ""
            if not diversity["allowed"]:
                headline_constraint = (
                    f'\nHEADLINE CONSTRAINT: {diversity["bitcoin_starts"]}/{diversity["total"]} '
                    f'recent headlines ({diversity["ratio"]:.0%}) start with "Bitcoin". '
                    f'Your headline MUST NOT start with "Bitcoin".'
                )

            source_url = f"https://youtube.com/watch?v={video_id}" if video_id else ""

            prompt = f"""You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet.

Write an article based on what {channel} ({handle}) said in their latest video.
{headline_constraint}

SOURCE MATERIAL (verified — this is from a real video transcript):
Channel: {channel} ({handle})
Video Title: {video_title}
Key Quote: "{key_quote}"
Summary: {summary}
Themes: {', '.join(themes)}
Video URL: {source_url}

INSTRUCTIONS:
- Write about what {channel} SAID and what it MEANS, not about the channel itself
- The key quote is the anchor — build the article around the insight
- Add your own analysis: who wins, who loses, what changes
- Reference the specific channel and video so readers can watch
- This is VIDEO-SOURCED intelligence, not a news rewrite

FORMAT:
<h1 class="article-header">[Sharp headline — under 10 words]</h1>
<div class="tldr-section"><em><strong>TL;DR: [2-3 sentences. Pure facts.]</strong></em></div>
<p class="article-paragraph">[HOOK — open with the most interesting thing they said]</p>
<p class="article-paragraph">[CONTEXT — who said it, where, and why it matters]</p>
<p class="article-paragraph">[ANALYSIS — what this means for Bitcoin, with <strong>one shareable line</strong>]</p>
<p class="article-paragraph">[CLOSE — forward-looking insight or bold prediction]</p>
<h2 class="article-header">Sources</h2>
<ul class="sources-list"><li><a href="{source_url}">{channel} — {video_title[:80]}</a></li></ul>

Target: 350-500 words. Every sentence earns its place.
Clean HTML only. No markdown. No backticks."""

            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7
            )

            content = strip_html_fences(response.choices[0].message.content)

            # Extract title
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
            title = title_match.group(1) if title_match else f"{channel} on {themes[0] if themes else 'Bitcoin'}"

            # Extract summary
            tldr_match = re.search(r'TL;DR:\s*([^<]+)', content)
            article_summary = tldr_match.group(1).strip() if tldr_match else summary[:200]

            # Headline diversity rewrite
            if not diversity["allowed"] and title.strip().lower().startswith("bitcoin"):
                title = _rewrite_headline_without_bitcoin(openai_client, title)

            # Grok review (if available)
            grok_score = 75  # Default pass score for intel-sourced articles
            should_publish = True
            try:
                from services.grok_review_service import grok_review_service
                review = grok_review_service.review_article(title, content, topic=f"Video intel: {channel}")
                grok_score = review.get("score", 75)
                if review.get("revised_title"):
                    title = review["revised_title"]
                should_publish = grok_score >= 60  # Lower bar — source is verified video
            except Exception as e:
                logger.warning(f"  Grok review skipped: {e}")

            # Save to database
            with app.app_context():
                img_service = ImageGenerationService()
                header_image = img_service.generate_article_header_image(title)

                article = Article(
                    title=title,
                    content=content,
                    summary=article_summary,
                    author="Protocol Pulse AI",
                    category="Bitcoin",
                    source_url=source_url,
                    source_type="video_intel",
                    published=should_publish,
                    published_at=datetime.utcnow() if should_publish else None,
                    header_image_url=header_image
                )

                db.session.add(article)
                db.session.commit()

                return {
                    "success": True,
                    "article_id": article.id,
                    "title": title,
                    "published": should_publish,
                    "grok_score": grok_score,
                    "source_channel": channel
                }

        except Exception as e:
            logger.error(f"  Article generation failed: {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────
    # TWEETS FROM QUEUE
    # ─────────────────────────────────────────────────────────

    def post_tweet_queue(self) -> Dict:
        """Post pre-composed tweets from the intel pipeline."""
        queue = self._load_intel("tweet_queue")
        if not queue:
            return {"error": "No tweet queue found", "count": 0}

        tweets = queue.get("tweets", [])
        if not tweets:
            return {"error": "Empty tweet queue", "count": 0}

        # Sort by hook_score descending — post best tweets first
        tweets.sort(key=lambda t: t.get("hook_score", 0), reverse=True)
        tweets = tweets[:MAX_TWEETS_PER_RUN]

        posted = []
        errors = []
        posted_path = INTEL_DIR / f"tweets_posted_{self.today}.json"
        already_posted = set()
        if posted_path.exists():
            already_posted = set(json.loads(posted_path.read_text()).get("posted_texts", []))

        try:
            from services.x_automation_service import XAutomationService
            x_service = XAutomationService()

            if not x_service.configured:
                return {"error": "X API not configured", "count": 0}

            for i, tweet in enumerate(tweets):
                text = tweet.get("text", "").strip()
                if not text:
                    continue

                # Skip if already posted
                if text[:100] in already_posted:
                    logger.info(f"  Tweet {i+1}: already posted, skipping")
                    continue

                logger.info(f"  Posting tweet {i+1}/{len(tweets)}: {text[:50]}...")

                result = x_service.post_tweet(text)
                if result and result.get("success"):
                    posted.append({
                        "text": text[:100],
                        "tweet_id": result.get("tweet_id"),
                        "source_channel": tweet.get("source_channel")
                    })
                    already_posted.add(text[:100])
                    logger.info(f"    + Posted: {result.get('tweet_id')}")
                else:
                    error_msg = result.get("error", "Unknown") if result else "Post failed"
                    # Check for rate limit / disabled
                    if result and result.get("reason") == "tweets disabled":
                        logger.info(f"    - Tweets disabled by kill switch")
                        break
                    errors.append({"text": text[:50], "error": error_msg})
                    logger.warning(f"    - Failed: {error_msg}")

                # Rate limit delay between tweets
                if i < len(tweets) - 1:
                    time.sleep(TWEET_DELAY_SECONDS)

        except ImportError:
            return {"error": "XAutomationService not available", "count": 0}
        except Exception as e:
            logger.error(f"Tweet queue processing failed: {e}")
            errors.append({"error": str(e)})

        # Save posted tracking
        posted_path.write_text(json.dumps({
            "date": self.today,
            "posted_texts": list(already_posted),
            "count": len(posted)
        }, indent=2))

        return {
            "count": len(posted),
            "posted": posted,
            "errors": errors
        }

    # ─────────────────────────────────────────────────────────
    # NEWSLETTER DIGEST
    # ─────────────────────────────────────────────────────────

    def prepare_newsletter_digest(self) -> Dict:
        """Prepare newsletter data from intel digest.

        Saves a consolidated digest file that the newsletter engine
        can pick up for the next send.
        """
        digest = self._load_intel("newsletter_digest")
        if not digest:
            return {"error": "No newsletter digest found", "count": 0}

        # Enrich with daily intel for more complete data
        daily_intel = self._load_intel("daily_intel") or {}

        enriched = {
            "date": self.today,
            "date_display": digest.get("date_display", self.date_display),
            "themes": digest.get("themes", []),
            "highlights": digest.get("top_highlights", []),
            "stats": {
                "channels_scanned": daily_intel.get("channels_scanned", 0),
                "videos_analyzed": daily_intel.get("videos_analyzed", 0),
                "clips_produced": daily_intel.get("clips_produced", 0)
            },
            "top_quote": daily_intel.get("top_quote", ""),
            "video_link": digest.get("video_link", ""),
            "ready_for_send": True
        }

        # Save enriched digest for newsletter engine
        enriched_path = INTEL_DIR / f"newsletter_ready_{self.today}.json"
        enriched_path.write_text(json.dumps(enriched, indent=2))
        logger.info(f"  + Newsletter digest ready: {enriched_path}")
        logger.info(f"    {len(enriched['highlights'])} highlights, themes: {', '.join(enriched['themes'][:3])}")

        return {
            "count": len(enriched["highlights"]),
            "path": str(enriched_path),
            "themes": enriched["themes"]
        }

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────

    def _load_intel(self, prefix: str) -> Optional[Dict]:
        """Load an intel JSON file for today's date."""
        path = INTEL_DIR / f"{prefix}_{self.today}.json"
        if not path.exists():
            logger.warning(f"  Intel file not found: {path}")
            return None
        try:
            return json.loads(path.read_text())
        except Exception as e:
            logger.error(f"  Failed to load {path}: {e}")
            return None


def consume_intel_feeds(date: str = None) -> Dict:
    """Convenience function to run the full intel feed consumer."""
    consumer = IntelFeedConsumer(date)
    return consumer.consume_all()
