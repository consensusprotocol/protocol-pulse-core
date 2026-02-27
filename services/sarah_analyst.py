"""
Sarah persona for Protocol Pulse: signal analysis, daily brief generation, tweet drafts.
Voice: clinical, sovereignty-focused. Audience: Bitcoin operators who value signal over noise.
"""

import logging
from datetime import datetime

from services.ai_service import AIService

logger = logging.getLogger(__name__)

# Verified Sovereigns (editorial rule) — used for weighting
VERIFIED_SOVEREIGNS = {
    "saylor", "michael saylor", "lyn alden", "natalie brunell", "preston pysh",
    "parker lewis", "jeff booth", "saifedean", "jack dorsey", "fiatjaf",
    "marty bent", "american hodl", "pomp", "caitlin long", "lawrence lepard", "btc sessions",
}


class SarahAnalyst:
    def __init__(self):
        self.ai = AIService()

    def analyze_signals(self, feed_items, limit=3):
        """
        Rank feed_items by sovereignty impact and return top N with scores.
        feed_items: list of objects with .title, .source, .url (optional), .summary or .content.
        Returns: list of dicts with keys: item, score, sovereignty_impact, reasons.
        """
        if not feed_items:
            return []
        items = list(feed_items)[: limit * 3]
        scored = []
        for item in items:
            title = getattr(item, "title", None) or getattr(item, "content", "")[:200]
            source = (getattr(item, "source", None) or getattr(item, "author", "") or "Unknown").lower()
            # Simple scoring: verified sovereign + tier
            sovereign_bonus = 30 if any(s in source for s in VERIFIED_SOVEREIGNS) else 0
            tier = getattr(item, "tier", "general")
            tier_mult = {"macro": 2.5, "dev": 2.0, "quant": 2.0, "mining": 1.5, "media": 1.2}.get(tier, 1.0)
            score = 5.0 * tier_mult + sovereign_bonus / 10
            impact = min(10.0, score)
            scored.append({
                "item": item,
                "score": round(score, 2),
                "sovereignty_impact": round(impact, 1),
                "reasons": ["Verified sovereign" if sovereign_bonus else "High-signal source"],
            })
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    def generate_daily_brief(self, top_signals, sentiment_data=None):
        """
        Generate headline + body for a daily brief from top_signals.
        top_signals: list from analyze_signals (dicts with item, score, sovereignty_impact, reasons).
        sentiment_data: optional {state, score}.
        Returns: {'headline': str, 'body': str}
        """
        signals_text = "\n".join(
            f"- {s['item'].title if hasattr(s['item'], 'title') else getattr(s['item'], 'content', '')[:150]} "
            f"(source: {getattr(s['item'], 'source', 'Unknown')}, impact: {s.get('sovereignty_impact', 5)})"
            for s in top_signals
        )
        sentiment_line = ""
        if sentiment_data:
            sentiment_line = f"Current sentiment state: {sentiment_data.get('state', 'N/A')}, score: {sentiment_data.get('score', 'N/A')}.\n"
        prompt = f"""You are Sarah, Protocol Pulse's macro strategist. Generate a Daily Brief for today.

VOICE: Clinical, sovereignty-focused. Lyn Alden meets cypherpunk intelligence officer.
AUDIENCE: Bitcoin operators who value signal over noise.

TOP SIGNALS:
{signals_text}
{sentiment_line}

Output JSON only with two keys:
"headline": one compelling headline for the brief (under 15 words).
"body": HTML body (use <p>, <h3>). Opening 2-3 sentences, then three signal summaries, then closing CTA to /drill or /operator-costs. Under 400 words. No emojis, no hashtags."""

        try:
            raw = self.ai.generate_content_openai(prompt)
        except Exception as e:
            logger.warning("OpenAI failed for daily brief: %s", e)
            raw = None
        if not raw:
            try:
                from services.gemini_service import gemini_service
                raw = gemini_service.generate_content(prompt, system_prompt="")
            except Exception as e2:
                logger.warning("Gemini failed: %s", e2)
                return {"headline": "Daily Intelligence Brief", "body": "<p>Signals unavailable.</p>"}

        import json
        try:
            # Strip markdown code block if present
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return {
                "headline": data.get("headline", "Daily Intelligence Brief"),
                "body": data.get("body", "<p>No content.</p>"),
            }
        except json.JSONDecodeError:
            return {"headline": "Daily Intelligence Brief", "body": f"<p>{raw[:2000]}</p>"}

    def generate_tweet_draft(self, payload):
        """
        Generate a tweet draft from a brief payload.
        payload: {'signals': list} where each element has .title, .source, .sovereignty_impact (or dict with keys).
        Returns: tweet body string (may contain {link} for caller to replace).
        """
        signals = payload.get("signals") or []
        lines = []
        for s in signals:
            if hasattr(s, "title"):
                title = s.title
                source = getattr(s, "source", "Unknown")
                impact = getattr(s, "sovereignty_impact", 5)
            else:
                title = s.get("title", "Signal")
                source = s.get("source", "Unknown")
                impact = s.get("sovereignty_impact", 5)
            lines.append(f"• {title[:80]} — {source} (impact: {impact})")
        signals_blob = "\n".join(lines) if lines else "Top signals from the network."
        prompt = f"""You are Sarah from Protocol Pulse. Write a single tweet (max 280 chars) promoting today's daily brief.

SIGNALS SUMMARY:
{signals_blob}

Requirements: Clinical, no emojis, no hashtags. End with "Full brief: {{link}}" (keep {{link}} literal).
Authoritative and sovereignty-focused tone."""

        try:
            body = self.ai.generate_content_openai(prompt)
        except Exception as e:
            logger.warning("Tweet draft failed: %s", e)
            body = f"Today's intelligence brief: top signals for Bitcoin operators. Full brief: {{link}}"
        if body:
            body = body.strip()[:280]
        if "{link}" not in body:
            body = body + " Full brief: {link}"
        return body or "Full brief: {link}"


# Singleton for routes
sarah_analyst = SarahAnalyst()
