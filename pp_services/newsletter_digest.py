#!/usr/bin/env python3
"""
PROTOCOL PULSE — THE SOVEREIGN SIGNAL
======================================
This isn't another crypto newsletter. This is INTELLIGENCE.

The kind that moves quietly through Signal groups.
The kind hedge fund managers forward with "Don't share this widely."
The kind that makes subscribers feel like insiders.

ARCHITECTURE (4-Pass Pipeline):
1. NORMALIZE: De-duplicate, validate sources, enforce link integrity
2. EXTRACT: Structured JSON intel with zero hallucination tolerance
3. RENDER: Premium editorial prose with Bloomberg-meets-cypherpunk voice
4. TIGHTEN: Ruthless editorial pass - every word earns its place

SIGNATURE SECTIONS:
- "The Quiet Signal" - Contrarian/underpriced insight (your ace)
- Sentiment Matrix - Visual stance table
- Forward Blurb - Built-in viral mechanics

PRINCIPLES:
- Receipts over claims (every insight cites source + link)
- Compression over length (top-of-email value in 20 seconds)
- Signal over noise (ruthlessly exclude generic takes)
- Consistency over vibes (structured pipeline = reliable output)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignSignal")

# Configuration
MODEL = os.getenv("NEWSLETTER_MODEL", "gpt-4o")
MAX_BREAKDOWN_CHARS = 2000
MAX_SOURCES = 25


class NewsletterDigestService:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.grok_key = os.getenv("GROK_API_KEY")
        
    # ═══════════════════════════════════════════════════════════════
    # PASS 1: NORMALIZE & VALIDATE
    # ═══════════════════════════════════════════════════════════════
    def _normalize(self, breakdowns: List[Dict]) -> Tuple[List[Dict], set]:
        """Clean, dedupe, and validate source data"""
        normalized = []
        channels = set()
        seen_titles = set()
        
        for item in breakdowns or []:
            video = item.get("video", {}) or {}
            
            channel = (video.get("channel_name") or video.get("channel") or 
                      item.get("channel_name") or "Unknown").strip()
            title = (video.get("title") or item.get("title") or "Untitled").strip()
            url = (video.get("url") or item.get("url") or "").strip()
            twitter = (video.get("channel_twitter") or item.get("twitter") or "").strip()
            breakdown = (item.get("breakdown") or "").strip()
            
            # Skip empty or duplicate content
            if not breakdown and not title:
                continue
            if title in seen_titles:
                continue
                
            seen_titles.add(title)
            channels.add(channel)
            
            # Truncate but preserve meaning
            if len(breakdown) > MAX_BREAKDOWN_CHARS:
                breakdown = breakdown[:MAX_BREAKDOWN_CHARS].rsplit('.', 1)[0] + "..."
            
            normalized.append({
                "channel": channel,
                "title": title,
                "url": url,
                "twitter": twitter,
                "breakdown": breakdown,
                "has_link": bool(url)
            })
        
        # Keep most relevant sources
        if len(normalized) > MAX_SOURCES:
            normalized = normalized[:MAX_SOURCES]
            
        return normalized, channels

    # ═══════════════════════════════════════════════════════════════
    # PASS 2: EXTRACT STRUCTURED INTEL
    # ═══════════════════════════════════════════════════════════════
    def _extract_intel(self, items: List[Dict], channels: set) -> Dict[str, Any]:
        """Extract actionable intelligence as structured JSON"""
        
        raw_block = json.dumps(items, indent=2, ensure_ascii=False)
        date_str = datetime.utcnow().strftime('%B %d, %Y')
        
        system = """You are the Chief Intelligence Analyst at Protocol Pulse.

YOUR MANDATE:
- Extract ACTIONABLE, NON-OBVIOUS insights only
- Every claim must cite a specific source with URL
- De-duplicate repeating narratives across sources
- Down-rank generic takes ("Bitcoin is bullish", "ETFs matter")
- Be ruthlessly selective - quality over quantity
- NEVER invent facts, metrics, quotes, or links
- If URL is missing, mark needs_link: true

CRITICAL FOR QUOTES:
- The "from_the_source" quotes MUST be pulled directly from the breakdown text
- Look for statements in quotes, bold predictions, or strong opinions
- Only use quotes/paraphrases that actually appear in the source material
- This section saves readers from watching 14+ videos - make it count
- Include 4-6 of the most impactful/surprising/useful quotes

OUTPUT: Valid JSON only. No markdown. No explanation."""

        prompt = f"""Analyze {len(items)} intelligence sources from {len(channels)} thought leaders.

DATE: {date_str}
CHANNELS MONITORED: {len(channels)}

RAW INTELLIGENCE:
{raw_block}

Extract structured intel with this EXACT schema:
{{
  "meta": {{
    "date": "{date_str}",
    "channels_count": {len(channels)},
    "sources_count": {len(items)}
  }},
  
  "subject_lines": [
    "5 subject line options - punchy, specific, honest (<80 chars each)"
  ],
  
  "teaser": "2 sentences max. The hook that makes someone open the email.",
  
  "forward_blurb": "1 sentence for forwarding: 'You need to read this because...'",
  
  "executive_summary": {{
    "narrative": "3 sentences: What changed this week? What's the signal? Why does it matter?",
    "bullets": ["3 key points, each under 15 words"]
  }},
  
  "actionable_alpha": [
    {{
      "headline": "Sharp, specific headline (<10 words)",
      "insight": "The non-obvious takeaway (1-2 sentences)",
      "so_what": "Actionable implication for the reader",
      "source": {{"channel": "", "title": "", "url": "", "twitter": ""}},
      "needs_link": false
    }}
  ],
  
  "quiet_signal": {{
    "insight": "The contrarian/underpriced take most are missing (2-3 sentences)",
    "why_underpriced": "Why this matters more than people realize",
    "quotable": "One line people will screenshot",
    "source": {{"channel": "", "title": "", "url": "", "twitter": ""}}
  }},
  
  "sentiment_matrix": [
    {{
      "channel": "",
      "twitter": "",
      "stance": "🟢 Bullish|🟡 Neutral|🔴 Bearish",
      "key_signal": "Under 12 words - their core thesis this week",
      "url": ""
    }}
  ],
  
  "aggregate_sentiment": {{
    "reading": "Bullish|Neutral|Bearish|Mixed",
    "confidence": "High|Medium|Low",
    "synthesis": "1-2 sentences: What does the smart money collectively see?"
  }},
  
  "deep_signal": [
    {{
      "channel": "",
      "title": "",
      "url": "",
      "twitter": "",
      "why_watch": "1 sentence: What makes this worth 20 minutes?",
      "key_insight": "2-3 sentences of genuine ANALYSIS, not summary",
      "needs_link": false
    }}
  ],
  
  "radar": [
    {{
      "item": "Specific thing to watch",
      "trigger": "Date, metric, event, or level to monitor",
      "why": "Why this matters"
    }}
  ],
  
  "pulse_take": {{
    "perspective": "2-3 sentences: Protocol Pulse editorial stance",
    "next_question": "The question serious operators should be asking",
    "quotable": "One memorable line that captures the week"
  }}
}}

CRITICAL: Return ONLY valid JSON. No markdown formatting. No code blocks."""

        try:
            response = self.openai.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            text = response.choices[0].message.content.strip()
            
            # Clean any accidental markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:].strip()
            
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Intel JSON parse failed: {e}")
            return {"error": "parse_failed", "raw": text[:2000] if 'text' in dir() else ""}
        except Exception as e:
            logger.error(f"Intel extraction failed: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════
    # PASS 3: RENDER PREMIUM BRIEF
    # ═══════════════════════════════════════════════════════════════
    def _render_brief(self, intel: Dict[str, Any]) -> str:
        """Transform structured intel into premium editorial prose"""
        
        if intel.get("error"):
            return f"""SUBJECT: Protocol Pulse Weekly — Generation Error
TEASER: The digest failed to compile. Check logs.

# 🔴 Protocol Pulse | Weekly Intelligence Brief

**ERROR:** Intel extraction failed.

{intel.get('raw', 'No additional data.')[:1000]}"""

        meta = intel.get("meta", {})
        
        system = """You are the lead writer for Protocol Pulse, crafting the weekly intelligence brief.

VOICE: Bloomberg meets cypherpunk
- Calm authority, zero hype
- Specific over vague
- Decisive over hedge-y
- Professional with soul

READERS: Serious Bitcoiners, fund managers, freedom-tech builders
- They have 3 minutes
- They already know the basics
- They want SIGNAL and WHY IT MATTERS

OUTPUT: Clean Markdown only. No code blocks. No extra commentary."""

        prompt = f"""Transform this structured intel into the final newsletter:

{json.dumps(intel, indent=2, ensure_ascii=False)}

FORMAT EXACTLY AS FOLLOWS:

SUBJECT: [Pick best from subject_lines]
TEASER: [Use teaser field]

---

# 🔴 PROTOCOL PULSE | WEEKLY INTELLIGENCE BRIEF
*{meta.get('date', 'Date Unknown')} • {meta.get('channels_count', 'N')} thought leaders monitored*

---

## EXECUTIVE SUMMARY

[Use executive_summary.narrative - 3 sharp sentences]

---

## 🎯 ACTIONABLE ALPHA

[For each item in actionable_alpha:]
- **[headline]** — [insight]. *So what:* [so_what] *(Source: [channel] — [title])*

[If needs_link is true, append "(link pending)" to source]
[3-5 bullets max. Quality over quantity.]

---

## 🔮 THE QUIET SIGNAL
*The contrarian take most are missing*

[quiet_signal.insight]

[quiet_signal.why_underpriced]

> "[quiet_signal.quotable]"

— *[source.channel]*

---

## 📊 SENTIMENT MATRIX

| Source | Stance | Key Signal |
|--------|--------|------------|
[For each in sentiment_matrix: | [channel] | [stance] | [key_signal] |]

**Aggregate Read:** [aggregate_sentiment.reading] ([aggregate_sentiment.confidence] confidence) — [aggregate_sentiment.synthesis]

---

## 🔬 DEEP SIGNAL

[For each in deep_signal:]
- **[title]** ([channel]) — [why_watch] [Link if url exists, else "(link pending)"]

  [key_insight - 2-3 sentences of ANALYSIS]

---

## 🎙️ FROM THE SOURCE
*What the thought leaders actually said this week*

[For each in from_the_source:]

> "[quote]"
> — **[channel]** ([@twitter]) on *[context]*

*Why it matters:* [implication]

---

## 📡 ON THE RADAR

[For each in radar:]
- **[item]** — [why] *Watch:* [trigger]

---

## THE PROTOCOL PULSE TAKE

[pulse_take.perspective]

**The question:** [pulse_take.next_question]

> "[pulse_take.quotable]"

---

*{intel.get('forward_blurb', 'Forward this to someone who needs the edge.')}*

---

**Protocol Pulse** monitors {meta.get('channels_count', 'elite')} thought leaders so you don't have to.
This is your edge. Guard it.

[Website](https://protocolpulse.io) • [Twitter](https://twitter.com/ProtocolPulse) • [Telegram](https://t.me/protocolpulseHQ)

*You're receiving this because you want the signal. Unsubscribe if you prefer the noise.*

---

RULES:
- Under 1000 words total
- No emojis except section headers (already provided)
- Every claim traces to a source
- No invented facts or metrics"""

        try:
            response = self.openai.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Brief render failed: {e}")
            return f"# Error\n\nFailed to render brief: {e}"

    # ═══════════════════════════════════════════════════════════════
    # PASS 4: RUTHLESS EDITORIAL TIGHTENING
    # ═══════════════════════════════════════════════════════════════
    def _tighten(self, draft: str) -> str:
        """Remove fluff, sharpen prose, ensure every word earns its place"""
        
        prompt = f"""You are a ruthless editor for a premium intelligence brief.

DRAFT:
{draft}

TIGHTEN BY:
- Remove filler words, hedging language, redundancy
- Collapse repetitive bullets
- Sharpen vague phrases into concrete statements
- Cut any "crypto bro" language or hype
- Ensure every sentence delivers value
- Remove unnecessary adjectives

PRESERVE:
- All section headers and structure
- SUBJECT and TEASER lines at top
- All source citations
- The signature "Quiet Signal" section
- Footer and links

Return ONLY the improved Markdown. No commentary."""

        try:
            response = self.openai.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=2500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Tighten pass failed: {e}")
            return draft  # Return original if tightening fails

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════
    def generate_weekly_digest(self, breakdowns: List[Dict]) -> Dict:
        """Full pipeline: normalize → extract → render → tighten"""
        
        if not breakdowns:
            return {"error": "No breakdowns provided"}
        
        # Pass 1: Normalize
        items, channels = self._normalize(breakdowns)
        if not items:
            return {"error": "No valid sources after normalization"}
        
        logger.info(f"[PASS 1] Normalized {len(items)} sources from {len(channels)} channels")
        
        # Pass 2: Extract
        intel = self._extract_intel(items, channels)
        if intel.get("error"):
            return {"error": intel["error"], "raw": intel.get("raw")}
        
        logger.info("[PASS 2] Structured intel extracted")
        
        # Pass 3: Render
        draft = self._render_brief(intel)
        logger.info(f"[PASS 3] Brief rendered ({len(draft)} chars)")
        
        # Pass 4: Tighten
        final = self._tighten(draft)
        logger.info(f"[PASS 4] Brief tightened ({len(final)} chars)")
        
        # Extract subject/teaser from final output
        lines = final.split('\n')
        subject = None
        teaser = None
        
        for line in lines[:5]:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("TEASER:"):
                teaser = line.replace("TEASER:", "").strip()
        
        return {
            "status": "success",
            "digest": final,
            "subject": subject,
            "teaser": teaser,
            "structured_intel": intel,
            "sources_count": len(items),
            "channels_covered": len(channels),
            "generated_at": datetime.utcnow().isoformat()
        }

    def generate_and_publish(self) -> Dict:
        """Generate and publish to all channels"""
        
        try:
            from pp_services.pulse_intelligence import pulse_intelligence
            
            logger.info("═" * 50)
            logger.info("PROTOCOL PULSE — SOVEREIGN SIGNAL GENERATION")
            logger.info("═" * 50)
            
            # Gather intelligence
            pulse_result = pulse_intelligence.run_daily_pulse()
            breakdowns = pulse_result.get("breakdowns", [])
            
            if not breakdowns:
                return {"error": "No intelligence to compile"}
            
            # Generate digest
            result = self.generate_weekly_digest(breakdowns)
            
            if result.get("error"):
                return result
            
            digest = result["digest"]
            intel = result.get("structured_intel", {})
            subject = result.get("subject") or f"Protocol Pulse Weekly | {datetime.utcnow().strftime('%b %d')}"
            teaser = result.get("teaser") or ""
            channels = result.get("channels_covered", 0)
            
            published = []
            errors = []
            
            # Substack
            try:
                from pp_services.substack_service import SubstackService
                substack = SubstackService()
                substack.publish_to_substack(title=subject.replace("🔴", "").strip(), body_markdown=digest)
                published.append("substack")
                logger.info("✅ Published to Substack")
            except Exception as e:
                errors.append(f"substack: {e}")
            
            # X/Twitter
            try:
                from pp_services.x_service import XService
                x = XService()
                x_post = f"""🔴 Weekly Intelligence Brief dropped.

{channels} thought leaders. One brief.

The signal through the noise ↓

https://protocolpulse.substack.com"""
                x.post_tweet(x_post)
                published.append("x")
                logger.info("✅ Posted to X")
            except Exception as e:
                errors.append(f"x: {e}")
            
            # Nostr
            try:
                from pp_services.nostr_service import post_to_nostr
                nostr_post = f"""🔴 PROTOCOL PULSE | WEEKLY INTELLIGENCE BRIEF

{intel.get('executive_summary', {}).get('narrative', teaser)}

Full brief: https://protocolpulse.substack.com"""
                post_to_nostr(nostr_post)
                published.append("nostr")
                logger.info("✅ Posted to Nostr")
            except Exception as e:
                errors.append(f"nostr: {e}")
            
            # Telegram
            try:
                from pp_services.telegram_service import send_telegram_message
                
                quiet = intel.get("quiet_signal", {})
                tg_msg = f"""🔴 <b>WEEKLY INTELLIGENCE BRIEF</b>

{intel.get('executive_summary', {}).get('narrative', '')[:350]}

<b>The Quiet Signal:</b>
{quiet.get('insight', '')[:200]}

📰 <a href="https://protocolpulse.substack.com">Read the full brief</a>

<i>Protocol Pulse — Your edge. Guard it.</i>"""
                
                send_telegram_message(tg_msg, parse_mode='HTML')
                published.append("telegram")
                logger.info("✅ Sent to Telegram")
            except Exception as e:
                errors.append(f"telegram: {e}")
            
            logger.info("═" * 50)
            logger.info(f"GENERATION COMPLETE | Published: {', '.join(published)}")
            logger.info("═" * 50)
            
            return {
                "status": "success",
                "digest_length": len(digest),
                "sources": result["sources_count"],
                "channels": channels,
                "subject": subject,
                "published_to": published,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"error": str(e)}


# Singleton
newsletter_digest = NewsletterDigestService()

if __name__ == "__main__":
    result = newsletter_digest.generate_and_publish()
    print(json.dumps(result, indent=2, default=str))
