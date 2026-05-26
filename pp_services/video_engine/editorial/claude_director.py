"""
Claude Editorial Director — Stage 2
======================================
The brain of Pulse Check Content OS.
Takes clusters + full context → complete ShowPlanV2.

Uses Anthropic Claude API for editorial judgment:
- Story selection and ordering
- Narrator script writing
- Clip selection with exact transcript matching
- Shorts planning
- Signal vs Noise segment

Fallback: "Quick Hits Edition" if Claude fails twice.
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from pp_services.video_engine.editorial.schemas import (
    ShowPlanV2, ClusterOutput, Story, ClipDefinition, TweetOverlay,
    SignalVsNoise, ShortPlan, CommunityPulse, ClaimWithEvidence
)

logger = logging.getLogger("ClaudeDirector")

CLAUDE_SYSTEM_PROMPT = """You are the Editorial Director for Pulse Check, a daily Bitcoin intelligence video
brief produced by Protocol Pulse. You have the editorial voice and judgment of a
veteran news producer who deeply understands Bitcoin.

EDITORIAL STANCE:
- Bitcoin-first. Not "crypto."
- Self-custody > custodial convenience.
- Skeptical of unsourced claims (bullish or bearish).
- Respectful to builders. Ruthless to grifters.
- Frame feuds as idea disagreements, not personal attacks.

Your audience: Bitcoin-curious to intermediate. They want to feel informed, not
lectured. They want to understand WHY things matter, not just WHAT happened.

## YOUR TASK

From today's source material, produce a complete SHOW PLAN for today's Pulse Check
episode (target: 5-8 minutes of content).

## SHOW STRUCTURE (every episode)

1. COLD OPEN (15 sec) — tease today's stories with energy and authority
2. LEAD STORY (2-3 min) — most important/interesting story
3. FOLLOW STORY (1.5-2 min) — second story, ideally connects thematically
4. SIGNAL vs NOISE (30 sec) — daily ritual: 1 signal, 1 noise, 1 wildcard
5. QUICK HITS (1-2 min) — rapid fire smaller stories
6. COMMUNITY PULSE (30 sec) — tweets, reactions, engagement hook
7. OUTRO (10 sec) — callback to lead, "Stay sovereign"

## STORY MODES (use at least one non-default per episode when material allows)

- single_thread: straightforward narrative (default)
- debate: present two opposing views, let audience decide
- timeline: "here's how we got here" chronological
- mythbust: "everyone's saying X, but actually..."

## SLOW NEWS DAY LOGIC

If fewer than 3 high-relevance stories (score >= 7), choose one:
- DEEP DIVE: single topic, 3-5 segments, thorough exploration
- WEEK IN REVIEW: past 5 days themes synthesized
- EDUCATION: teach a core Bitcoin concept using this week's stories
Never pad with filler. A tight 3-minute episode beats a weak 7-minute one.

## CLIP SELECTION RULES (ABSOLUTELY NON-NEGOTIABLE)

1. COMPLETE THOUGHTS ONLY: Every clip MUST start at the beginning of a sentence
   and end at the end of a sentence. NEVER cut mid-word or mid-thought.

2. SELF-CONTAINED: The clip must make sense to someone who ONLY heard the narrator
   intro + the clip. No orphan references ("as I was saying...", "that thing...").

3. SPEAKER IDENTIFIED: Narrator ALWAYS introduces who is speaking before clip plays.
   "Here's how Nik Bhatia from The Bitcoin Layer put it:"

4. NATURAL BOUNDARIES: Prefer clips that start after a breath/pause and end at pause.

5. LENGTH: 15-30 seconds per clip. Under 15 = no impact. Over 30 = narrator should
   be talking instead.

6. ONE POINT PER CLIP: Each clip = one clear insight. Two points = two clips with
   narrator bridge between them.

7. DEDUP: If multiple sources cover same story, pick ONE best clip.

8. EXACT TRANSCRIPT: clip_transcript must contain the EXACT words from the source
   transcript. Do not paraphrase. This text is used for timestamp matching.

9. NEVER CLIP REJECTED SEGMENTS: Cross-reference rejected[] from triage. Do not
   select any timestamp range that overlaps with a rejected segment.

## NARRATOR VOICE GUIDELINES

- Conversational but authoritative. Think: smart friend who works in Bitcoin.
- NOT generic AI. NOT corporate anchor. NOT hype/clickbait.
- Uses "we" and "you" — speaks to the community, not at them.
- Short sentences. Punchy. Varied rhythm. Some one word. Others flow.
- Provides CONTEXT clips don't: who, what, why it matters.
- Has editorial perspective — not just "what happened" but "why you should care."
- Bridges between stories feel natural: "Speaking of institutions..." or
  "Now, while that's playing out on the macro side..."
- NEVER uses: "In this video" / "Don't forget to like" / "As always" / filler.

## PROVENANCE

For each narrator script making a factual claim, include claims[] array:
- claim: the specific factual statement
- evidence: list of source_ids or URLs
- risk: "low" / "medium" / "high"

If a claim is high-risk with no evidence, SOFTEN IT:
"Reports suggest..." or "According to [source]..."

## SHORTS PLAN

Plan 3-5 vertical shorts. Each short:
- hook_text: 3-5 word bold text (first 3 seconds on screen)
- short_intro_script: narrator setup (10-12 seconds)
- clip_ref: which clip index in that story
- takeaway_script: narrator wrap (10-15 seconds)
- cta: "Full Pulse Check in bio."

## OUTPUT FORMAT

Return a single JSON object matching this exact structure. No prose outside JSON.
Include ALL fields including signal_vs_noise, shorts_plan, tomorrows_watchlist.

{
  "episode_date": "YYYY-MM-DD",
  "episode_headline": "...",
  "cold_open_script": "...",
  "stories": [
    {
      "story_number": 1,
      "story_type": "lead",
      "story_mode": "single_thread|debate|timeline|mythbust",
      "headline": "...",
      "narrator_intro_script": "...",
      "clips": [
        {
          "source_type": "youtube",
          "source_name": "channel name",
          "source_id": "video_id",
          "speaker": "speaker name",
          "clip_transcript": "EXACT words from transcript",
          "approx_start": "MM:SS",
          "approx_end": "MM:SS",
          "why_this_clip": "...",
          "intro_line": "narrator intro before clip",
          "starts_complete_sentence": true,
          "ends_complete_sentence": true,
          "thought_is_self_contained": true
        }
      ],
      "tweet_overlays": [],
      "narrator_bridge_script": null,
      "narrator_wrap_script": "...",
      "claims": [{"claim": "...", "evidence": ["source_id"], "risk": "low"}],
      "broll_category": "mining|macro|adoption|dev|regulation|community|generic",
      "emotion": "calm|urgent|encouraging|serious"
    }
  ],
  "quick_hits": [],
  "signal_vs_noise": {
    "narrator_intro": "Signal versus noise, in 30 seconds.",
    "signal": "...", "noise": "...", "wildcard": "..."
  },
  "community_pulse": {
    "narrator_intro": "...",
    "tweets": [],
    "engagement_hook": "..."
  },
  "shorts_plan": [],
  "outro_script": "...",
  "tomorrows_watchlist": [],
  "estimated_duration_seconds": 360,
  "dominant_theme": "...",
  "tone": "informative"
}"""


class ClaudeDirector:
    """Stage 2: Editorial brain that produces the complete ShowPlanV2."""

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = os.environ.get("CLAUDE_DIRECTOR_MODEL", "claude-haiku-4-5-20251001")
        self.tokens_in = 0
        self.tokens_out = 0
        self.retries = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def create_show_plan(self, cluster_output: ClusterOutput,
                          source_bundle: Dict,
                          editorial_memory: Dict = None,
                          bundle_path: Path = None,
                          date_str: str = None) -> Optional[ShowPlanV2]:
        """
        Generate complete show plan from clusters + source material.
        Retries once on failure, then falls back to Quick Hits Edition.
        """
        if not self.configured:
            logger.error("ANTHROPIC_API_KEY not set — cannot run Claude Director")
            return self._fallback_show_plan(source_bundle, date_str)

        date_str = date_str or datetime.utcnow().strftime("%Y-%m-%d")

        logger.info(f"\n{'='*60}")
        logger.info(f"CLAUDE DIRECTOR — Stage 2")
        logger.info(f"{'='*60}\n")

        # Build context for Claude
        context = self._build_context(cluster_output, source_bundle,
                                       editorial_memory, date_str)

        # Attempt 1
        plan = self._call_claude(context, date_str)
        if plan:
            if bundle_path:
                self._save_plan(plan, bundle_path)
            return plan

        # Attempt 2 (retry with error info)
        logger.warning("  First attempt failed, retrying...")
        self.retries += 1
        time.sleep(2)
        plan = self._call_claude(context, date_str, retry=True)
        if plan:
            if bundle_path:
                self._save_plan(plan, bundle_path)
            return plan

        # Fallback: Quick Hits Edition
        logger.warning("  Claude Director failed twice, falling back to Quick Hits Edition")
        plan = self._fallback_show_plan(source_bundle, date_str)
        if plan and bundle_path:
            self._save_plan(plan, bundle_path)
        return plan

    def _build_context(self, cluster_output: ClusterOutput,
                        source_bundle: Dict,
                        editorial_memory: Dict,
                        date_str: str) -> str:
        """Build the full context prompt for Claude."""
        sections = []

        # Date
        sections.append(f"TODAY'S DATE: {date_str}")

        # Clusters
        sections.append("\n## STORY CLUSTERS (from triage + clustering)")
        for c in cluster_output.clusters:
            sections.append(f"\n### Cluster: {c.topic}")
            sections.append(f"  Novelty: {c.novelty_score:.2f}")
            sections.append(f"  Sources: {', '.join(c.sources_represented)}")
            sections.append(f"  Hero candidates: {c.hero_candidates}")
            sections.append(f"  All candidates: {c.all_candidates}")

        # Transcripts (windows around hero candidates)
        youtube = source_bundle.get("sources", {}).get("youtube", {})
        transcripts = youtube.get("transcripts", [])

        sections.append("\n## SOURCE TRANSCRIPTS (timestamped)")
        for tx in transcripts:
            text = tx.get("timestamped_text", "") or tx.get("text", "")
            # Limit per transcript to keep within context
            if len(text) > 6000:
                text = text[:6000] + "\n[TRUNCATED]"
            sections.append(f"\n### {tx.get('source_name', '?')} — {tx.get('title', '?')}")
            sections.append(f"Video ID: {tx.get('source_id', '?')}")
            sections.append(text)

        # Tweets
        tweets = source_bundle.get("sources", {}).get("tweets", {}).get("tweets", [])
        if tweets:
            sections.append("\n## NOTABLE TWEETS (last 24h)")
            for t in tweets[:20]:
                sections.append(
                    f"@{t.get('author_handle', '?')} ({t.get('likes', 0)} likes): "
                    f"{t.get('text', '')}"
                )

        # Market data
        market = source_bundle.get("sources", {}).get("market", {})
        if market.get("price_usd"):
            sections.append(f"\n## MARKET SNAPSHOT")
            sections.append(market.get("narrator_text", ""))

        # Editorial memory
        if editorial_memory:
            sections.append("\n## EDITORIAL MEMORY (last 14 days)")
            recent = editorial_memory.get("recent_episodes", [])
            if recent:
                sections.append("Recent episode themes:")
                for ep in recent[:7]:
                    sections.append(f"  {ep.get('date', '?')}: {ep.get('theme', '?')}")

            running = editorial_memory.get("running_stories", [])
            if running:
                sections.append("Running stories:")
                for s in running[:5]:
                    sections.append(
                        f"  {s.get('topic', '?')} — covered {s.get('times_covered', 0)} times")

            worked = editorial_memory.get("what_worked_yesterday")
            if worked:
                sections.append(f"What worked yesterday: {worked}")

        return "\n".join(sections)

    def _call_claude(self, context: str, date_str: str,
                      retry: bool = False) -> Optional[ShowPlanV2]:
        """Call Claude API and parse ShowPlanV2 response."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            user_msg = f"Create today's Pulse Check show plan.\n\n{context}"
            if retry:
                user_msg += (
                    "\n\nPREVIOUS ATTEMPT FAILED. Common issues: "
                    "missing required fields, clip_transcript not exact match, "
                    "missing signal_vs_noise. Please output VALID JSON only."
                )

            response = client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=CLAUDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}]
            )

            # Track tokens
            self.tokens_in += response.usage.input_tokens
            self.tokens_out += response.usage.output_tokens

            content = response.content[0].text.strip()

            # Strip markdown fences
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()

            # Parse JSON
            data = json.loads(content)

            # Ensure date
            data["episode_date"] = date_str

            # Normalize Claude's natural output to match strict schemas
            data = self._normalize_plan_data(data)

            # Validate against schema
            plan = ShowPlanV2(**data)
            logger.info(f"  Show plan created: {plan.episode_headline}")
            logger.info(f"    Stories: {len(plan.stories)}, "
                        f"Quick hits: {len(plan.quick_hits)}, "
                        f"Shorts: {len(plan.shorts_plan)}")
            logger.info(f"    Duration: ~{plan.estimated_duration_seconds}s")
            logger.info(f"    Tokens: {response.usage.input_tokens} in, "
                        f"{response.usage.output_tokens} out")

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"  Claude response not valid JSON: {e}")
            return None
        except ImportError:
            logger.error("  anthropic package not installed")
            return None
        except Exception as e:
            logger.error(f"  Claude Director failed: {e}")
            return None

    # ── Normalization: map Claude's natural JSON to strict schema fields ──

    def _normalize_plan_data(self, data: dict) -> dict:
        """
        Bridge between Claude's free-form JSON and Pydantic schemas.
        Claude often uses intuitive but non-schema field names.
        """
        story_offset = len(data.get("stories", []))

        # Normalize stories
        for idx, story in enumerate(data.get("stories", [])):
            self._normalize_story(story, idx + 1, default_type="lead" if idx == 0 else "follow")

        # Normalize quick_hits — Claude sends simplified dicts, schema wants full Story
        for idx, qh in enumerate(data.get("quick_hits", [])):
            self._normalize_story(qh, story_offset + idx + 1, default_type="quick_hit")

        # Normalize community_pulse tweets
        cp = data.get("community_pulse")
        if isinstance(cp, dict) and "tweets" in cp:
            cp["tweets"] = [self._normalize_tweet(t) for t in cp["tweets"]]

        # Normalize shorts_plan
        for short in data.get("shorts_plan", []):
            if short.get("story_ref") is None:
                short["story_ref"] = 1
            if short.get("clip_ref") is None:
                short["clip_ref"] = 0

        return data

    def _normalize_story(self, story: dict, number: int, default_type: str = "quick_hit"):
        """Ensure a story dict has all required fields for the Story schema."""
        if "story_number" not in story:
            story["story_number"] = number
        if "story_type" not in story:
            story["story_type"] = default_type
        if "narrator_intro_script" not in story:
            story["narrator_intro_script"] = story.get("headline", story.get("text", ""))
        if "clips" not in story:
            story["clips"] = []

        # Normalize tweet_overlays inside each story
        if "tweet_overlays" in story:
            story["tweet_overlays"] = [
                self._normalize_tweet(t) for t in story["tweet_overlays"]
            ]

        # Drop fields the schema doesn't expect (e.g. duration_seconds)
        allowed = {
            "story_number", "story_type", "story_mode", "headline",
            "narrator_intro_script", "clips", "tweet_overlays",
            "narrator_bridge_script", "narrator_wrap_script", "claims",
            "broll_category", "emotion",
        }
        for key in list(story.keys()):
            if key not in allowed:
                story.pop(key)

    @staticmethod
    def _normalize_tweet(t: dict) -> dict:
        """Map Claude's tweet fields to TweetOverlay schema."""
        out = dict(t)

        # author / handle → author_handle
        if "author_handle" not in out:
            out["author_handle"] = (
                out.pop("author", None)
                or out.pop("handle", None)
                or out.pop("tweet_id", None)
                or "unknown"
            )

        # author_name fallback
        if "author_name" not in out:
            out["author_name"] = out.get("author_handle", "")

        # tweet_text fallback
        if "tweet_text" not in out:
            out["tweet_text"] = out.pop("text", None) or out.pop("content", None) or ""

        # narrator_read fallback — Claude sometimes sends on_screen_duration (a number)
        if "narrator_read" not in out:
            val = out.pop("on_screen_duration", None) or out.pop("narration", None)
            if isinstance(val, (int, float)):
                val = out.get("tweet_text", "")
            out["narrator_read"] = val or out.get("tweet_text", "")

        # Drop non-schema keys (tweet_id, likes, on_screen_duration, etc.)
        allowed = {"author_handle", "author_name", "tweet_text", "tweet_url", "narrator_read"}
        for key in list(out.keys()):
            if key not in allowed:
                out.pop(key)

        return out

    def _fallback_show_plan(self, source_bundle: Dict,
                             date_str: str = None) -> Optional[ShowPlanV2]:
        """
        Generate a minimal Quick Hits Edition when Claude Director fails.
        Narrator-only with market context. No clips (safe fallback).
        """
        date_str = date_str or datetime.utcnow().strftime("%Y-%m-%d")
        market = source_bundle.get("sources", {}).get("market", {})
        market_text = market.get("narrator_text", "Markets are moving.")

        logger.info("  Building Quick Hits Edition fallback...")

        plan = ShowPlanV2(
            episode_date=date_str,
            episode_headline="Quick Hits Edition",
            cold_open_script=(
                f"Pulse Check, {date_str}. Quick Hits Edition today. "
                f"{market_text} Let's get into it."
            ),
            stories=[],
            signal_vs_noise=SignalVsNoise(
                signal="The Bitcoin network continues to process blocks.",
                noise="Panic-driven price predictions with no thesis.",
                wildcard="Today's edition is lighter than usual."
            ),
            outro_script="That's your Pulse Check. Stay sovereign. Stack sats.",
            estimated_duration_seconds=120,
            dominant_theme="quick_hits",
            tone="informative",
            slow_news_mode="deep_dive"
        )

        return plan

    def _save_plan(self, plan: ShowPlanV2, bundle_path: Path):
        """Save show plan to episode bundle."""
        out_path = bundle_path / "show_plan" / "show_plan_v2.json"
        out_path.write_text(json.dumps(plan.dict(), indent=2, default=str))
        logger.info(f"  Saved: {out_path}")
