"""
PULSE ALERT — Breaking News Mini-Pipeline
===========================================
Detects high-signal breaking events and produces rapid-response content.
Runs every 30 minutes (or on-demand) as a lightweight companion to the
full daily Pulse Check pipeline.

Detection sources:
  1. Twitter API — spike in mentions/engagement on tracked accounts
  2. CoinGecko — BTC price moves > 5% in 1 hour
  3. Manual trigger — operator sends event via /dashboard/pulse/alert

Output (per alert):
  - Breaking tweet thread (ready to post)
  - Breaking article (500-word rapid analysis)
  - Push notification payload (Discord/Telegram)
  - Optional: 60-second vertical short (if clip available)

Design principles:
  - Fast: < 2 minutes from detection to content
  - Conservative: High threshold to avoid false alarms
  - Deduplicating: Won't fire twice for the same event in 6 hours
  - Gated: ENABLE_PULSE_ALERT=true to activate
"""
import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("PulseAlert")

ALERT_STATE_PATH = Path("state/pulse_alerts.json")
ALERT_COOLDOWN_HOURS = 6
BTC_PRICE_THRESHOLD_PCT = 5.0
TWEET_ENGAGEMENT_SPIKE = 3.0  # 3x normal engagement


class PulseAlert:
    """Breaking news detection and rapid-response content generator."""

    def __init__(self):
        self.enabled = os.environ.get("ENABLE_PULSE_ALERT", "").lower() == "true"
        self.state = self._load_state()

    def scan(self) -> List[dict]:
        """Scan all sources for breaking events. Returns list of detected events."""
        if not self.enabled:
            return []

        logger.info("Scanning for breaking events...")
        events = []

        # 1. Price alert
        price_event = self._check_price_alert()
        if price_event:
            events.append(price_event)

        # 2. Tweet spike
        tweet_events = self._check_tweet_spike()
        events.extend(tweet_events)

        # Deduplicate against recent alerts
        events = self._deduplicate(events)

        if events:
            logger.info(f"  Detected {len(events)} breaking event(s)")
        else:
            logger.debug("  No breaking events detected")

        return events

    def process_event(self, event: dict) -> dict:
        """Process a detected event into distributable content."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PULSE ALERT — {event.get('type', 'unknown').upper()}")
        logger.info(f"{'='*60}\n")

        result = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "content": {}
        }

        # Generate tweet thread
        result["content"]["tweet"] = self._generate_alert_tweet(event)

        # Generate article
        result["content"]["article"] = self._generate_alert_article(event)

        # Generate push notification
        result["content"]["notification"] = self._generate_notification(event)

        # Record in state
        self._record_alert(event, result)

        return result

    def scan_and_process(self) -> List[dict]:
        """Full scan + process loop. Returns list of processed alerts."""
        events = self.scan()
        results = []
        for event in events:
            try:
                result = self.process_event(event)
                results.append(result)
            except Exception as e:
                logger.error(f"  Failed to process event: {e}")
        return results

    # ─── Detection ───

    def _check_price_alert(self) -> Optional[dict]:
        """Check BTC price for significant move."""
        try:
            from services.video_engine.sources.market_data import MarketDataProvider
            market = MarketDataProvider()
            data = market.fetch()

            if not data:
                return None

            btc = data.get("bitcoin", {})
            change_1h = abs(btc.get("price_change_percentage_1h_in_currency", 0) or 0)

            if change_1h >= BTC_PRICE_THRESHOLD_PCT:
                direction = "surges" if btc.get("price_change_percentage_1h_in_currency", 0) > 0 else "drops"
                price = btc.get("current_price", 0)
                return {
                    "type": "price_move",
                    "headline": f"BTC {direction} {change_1h:.1f}% in one hour to ${price:,.0f}",
                    "details": {
                        "price": price,
                        "change_1h_pct": change_1h,
                        "direction": direction,
                        "market_cap": btc.get("market_cap", 0),
                        "volume_24h": btc.get("total_volume", 0),
                    },
                    "severity": "high" if change_1h >= 8 else "medium",
                    "detected_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.debug(f"  Price check failed: {e}")

        return None

    def _check_tweet_spike(self) -> List[dict]:
        """Check for unusual engagement spikes on tracked accounts."""
        events = []
        try:
            config_path = Path("config/editorial_config.json")
            if not config_path.exists():
                return events

            config = json.loads(config_path.read_text())
            alert_accounts = config.get("alert_accounts", config.get("tweet_accounts", []))

            if not alert_accounts:
                return events

            from services.video_engine.sources.tweet_monitor import TweetMonitor

            # Use a high engagement threshold for breaking detection
            monitor = TweetMonitor(alert_accounts, min_likes=5000)
            tweets = monitor.fetch_notable_tweets()

            # Look for tweets from the last hour with exceptionally high engagement
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            for tweet in tweets:
                created = tweet.get("created_at", "")
                try:
                    tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    continue

                if tweet_time < one_hour_ago:
                    continue

                likes = tweet.get("public_metrics", {}).get("like_count", 0)
                retweets = tweet.get("public_metrics", {}).get("retweet_count", 0)

                # High engagement = potential breaking news
                if likes >= 10000 or retweets >= 3000:
                    events.append({
                        "type": "tweet_spike",
                        "headline": tweet.get("text", "")[:200],
                        "details": {
                            "author": tweet.get("author_username", ""),
                            "likes": likes,
                            "retweets": retweets,
                            "tweet_id": tweet.get("id", ""),
                        },
                        "severity": "high" if likes >= 25000 else "medium",
                        "detected_at": datetime.utcnow().isoformat()
                    })

        except Exception as e:
            logger.debug(f"  Tweet spike check failed: {e}")

        return events

    # ─── Content Generation ───

    def _generate_alert_tweet(self, event: dict) -> dict:
        """Generate a breaking news tweet thread."""
        headline = event.get("headline", "Breaking Bitcoin News")
        event_type = event.get("type", "unknown")
        details = event.get("details", {})

        if event_type == "price_move":
            main_tweet = (
                f"PULSE ALERT\n\n"
                f"{headline}\n\n"
                f"24h volume: ${details.get('volume_24h', 0) / 1e9:.1f}B\n\n"
                f"Full analysis incoming. Stay sharp."
            )
            reply = (
                f"Context: This is the largest 1-hour move in "
                f"{'recent weeks' if details.get('change_1h_pct', 0) < 10 else 'months'}.\n\n"
                f"Watch for: liquidation cascades, exchange outflows, "
                f"and follow-through in the next 4 hours."
            )
        elif event_type == "tweet_spike":
            author = details.get("author", "")
            main_tweet = (
                f"PULSE ALERT\n\n"
                f"@{author}: {headline[:200]}\n\n"
                f"{details.get('likes', 0):,} likes | "
                f"{details.get('retweets', 0):,} retweets in < 1 hour"
            )
            reply = "Full Pulse Check analysis coming in today's episode."
        else:
            main_tweet = f"PULSE ALERT\n\n{headline}"
            reply = "Stay tuned for full coverage."

        return {
            "main_tweet": main_tweet[:280],
            "reply": reply[:280],
            "hashtags": ["#Bitcoin", "#BTC", "#PulseAlert"]
        }

    def _generate_alert_article(self, event: dict) -> dict:
        """Generate a rapid-response article (500 words)."""
        headline = event.get("headline", "Breaking Bitcoin News")
        event_type = event.get("type", "unknown")
        details = event.get("details", {})
        severity = event.get("severity", "medium")

        # Try Claude for smart article generation
        article_body = self._ai_generate_article(event)

        if not article_body:
            # Fallback: template-based article
            if event_type == "price_move":
                article_body = (
                    f"Bitcoin has made a significant move, "
                    f"{'surging' if details.get('direction') == 'surges' else 'dropping'} "
                    f"{details.get('change_1h_pct', 0):.1f}% in just one hour "
                    f"to ${details.get('price', 0):,.0f}.\n\n"
                    f"The move represents one of the largest hourly swings in recent weeks, "
                    f"with 24-hour trading volume at ${details.get('volume_24h', 0) / 1e9:.1f} billion.\n\n"
                    f"This is a developing story. Full analysis will be available in today's Pulse Check."
                )
            elif event_type == "tweet_spike":
                article_body = (
                    f"A tweet from @{details.get('author', 'unknown')} is gaining rapid traction "
                    f"in the Bitcoin community, accumulating {details.get('likes', 0):,} likes "
                    f"and {details.get('retweets', 0):,} retweets in under an hour.\n\n"
                    f"The tweet reads: \"{headline[:200]}\"\n\n"
                    f"This is a developing story. Full coverage in today's Pulse Check."
                )
            else:
                article_body = f"Breaking: {headline}\n\nThis is a developing story."

        return {
            "title": f"PULSE ALERT: {headline[:100]}",
            "body": article_body,
            "severity": severity,
            "category": "breaking",
            "auto_publish": severity == "high"
        }

    def _ai_generate_article(self, event: dict) -> Optional[str]:
        """Use Claude to generate a rapid-response article."""
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return None

            client = anthropic.Anthropic(api_key=api_key)

            prompt = (
                f"Write a 300-word breaking news article for Protocol Pulse (Bitcoin intelligence platform).\n\n"
                f"Event type: {event.get('type', 'unknown')}\n"
                f"Headline: {event.get('headline', '')}\n"
                f"Details: {json.dumps(event.get('details', {}), default=str)}\n"
                f"Severity: {event.get('severity', 'medium')}\n\n"
                f"Style: Factual, measured, no hype. State what happened, provide context, "
                f"note what to watch for next. Do NOT give financial advice.\n"
                f"Format: Plain text paragraphs, no markdown headers."
            )

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.debug(f"  AI article generation failed: {e}")
            return None

    def _generate_notification(self, event: dict) -> dict:
        """Generate push notification payload."""
        headline = event.get("headline", "Breaking Bitcoin News")
        severity = event.get("severity", "medium")

        color = 0xFF0000 if severity == "high" else 0xFF8C00  # red or orange

        return {
            "discord": {
                "embeds": [{
                    "title": f"PULSE ALERT: {headline[:200]}",
                    "color": color,
                    "description": json.dumps(event.get("details", {}), indent=2, default=str)[:1000],
                    "footer": {"text": f"Severity: {severity} | {datetime.utcnow().strftime('%H:%M UTC')}"}
                }]
            },
            "telegram": {
                "text": (
                    f"<b>PULSE ALERT</b>\n\n"
                    f"{headline[:200]}\n\n"
                    f"Severity: {severity}"
                ),
                "parse_mode": "HTML"
            }
        }

    # ─── State Management ───

    def _deduplicate(self, events: List[dict]) -> List[dict]:
        """Remove events that match recent alerts within cooldown window."""
        cutoff = datetime.utcnow() - timedelta(hours=ALERT_COOLDOWN_HOURS)
        recent_keys = set()

        for alert in self.state.get("recent_alerts", []):
            alert_time = alert.get("timestamp", "")
            try:
                if datetime.fromisoformat(alert_time) > cutoff:
                    recent_keys.add(alert.get("key", ""))
            except Exception:
                pass

        deduped = []
        for event in events:
            key = self._event_key(event)
            if key not in recent_keys:
                deduped.append(event)
            else:
                logger.debug(f"  Dedup: skipping {key}")

        return deduped

    def _event_key(self, event: dict) -> str:
        """Generate a dedup key for an event."""
        event_type = event.get("type", "")
        if event_type == "price_move":
            direction = event.get("details", {}).get("direction", "")
            return f"price_{direction}"
        elif event_type == "tweet_spike":
            return f"tweet_{event.get('details', {}).get('tweet_id', '')}"
        return f"{event_type}_{hash(event.get('headline', ''))}"

    def _record_alert(self, event: dict, result: dict):
        """Record alert in persistent state."""
        self.state.setdefault("recent_alerts", []).insert(0, {
            "key": self._event_key(event),
            "timestamp": datetime.utcnow().isoformat(),
            "type": event.get("type"),
            "headline": event.get("headline", "")[:200],
            "severity": event.get("severity"),
        })

        # Keep only last 50 alerts
        self.state["recent_alerts"] = self.state["recent_alerts"][:50]
        self.state["last_scan"] = datetime.utcnow().isoformat()

        self._save_state()

    def _load_state(self) -> dict:
        """Load alert state."""
        if ALERT_STATE_PATH.exists():
            try:
                return json.loads(ALERT_STATE_PATH.read_text())
            except Exception:
                pass
        return {"recent_alerts": [], "last_scan": None}

    def _save_state(self):
        """Save alert state."""
        ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ALERT_STATE_PATH.write_text(json.dumps(self.state, indent=2, default=str))

    # ─── Distribution ───

    def distribute(self, result: dict):
        """Send alert content to all channels."""
        content = result.get("content", {})

        # Post tweet
        if os.environ.get("ENABLE_TWEETS", "").lower() == "true":
            self._post_alert_tweet(content.get("tweet", {}))

        # Send notifications
        self._send_alert_notifications(content.get("notification", {}))

        # Auto-publish article (if high severity)
        article = content.get("article", {})
        if article.get("auto_publish"):
            self._publish_alert_article(article)

    def _post_alert_tweet(self, tweet_content: dict):
        """Post alert tweet."""
        try:
            from services.video_engine.pulse_distributor import post_tweet
            main = tweet_content.get("main_tweet", "")
            if main:
                post_tweet(main)
                logger.info("  Alert tweet posted")
        except Exception as e:
            logger.warning(f"  Alert tweet failed: {e}")

    def _send_alert_notifications(self, notification: dict):
        """Send Discord/Telegram notifications."""
        try:
            from services.video_engine.pipeline_alerts import (
                send_discord_message, send_telegram_message
            )

            discord_payload = notification.get("discord")
            if discord_payload:
                send_discord_message(discord_payload)

            telegram_payload = notification.get("telegram")
            if telegram_payload:
                send_telegram_message(
                    telegram_payload.get("text", ""),
                    parse_mode=telegram_payload.get("parse_mode", "HTML")
                )
        except Exception as e:
            logger.warning(f"  Alert notification failed: {e}")

    def _publish_alert_article(self, article: dict):
        """Auto-publish breaking article."""
        try:
            # Use the existing article system
            from services.content_generator import generate_and_save_article

            generate_and_save_article(
                topic=article.get("title", ""),
                body_override=article.get("body"),
                category="breaking",
                auto_publish=True
            )
            logger.info("  Alert article published")
        except Exception as e:
            logger.warning(f"  Alert article publish failed: {e}")


class PulseAlertScheduler:
    """Schedule periodic alert scans."""

    def __init__(self):
        self.alert = PulseAlert()

    def run_scan(self):
        """Run one scan cycle."""
        if not self.alert.enabled:
            return

        results = self.alert.scan_and_process()
        for result in results:
            try:
                self.alert.distribute(result)
            except Exception as e:
                logger.error(f"  Alert distribution failed: {e}")

    def register_with_scheduler(self, scheduler):
        """Register with APScheduler for periodic scans."""
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler.add_job(
            self.run_scan,
            trigger=IntervalTrigger(minutes=30),
            id="pulse_alert_scan",
            name="Pulse Alert Scanner",
            replace_existing=True,
            max_instances=1
        )
        logger.info("  Pulse Alert scanner registered (every 30 min)")
