# GOSPEL: LOCAL LLM INTEGRATION MASTER
# Version 1.0 | March 2026

## THE PRINCIPLE
Every task that does NOT require frontier-model reasoning should run locally.
Qwen3-Coder-30B on GPU 2 handles: structured data synthesis, code repair,
signal scoring, quality gating, short-form writing.
Claude/GPT reserved for: episode script generation, complex reasoning, article writing.

## INFRASTRUCTURE
Model:   Qwen3-Coder:30b (18GB, GPU 2 only)
Server:  Ollama at http://localhost:11435
Boot:    systemd service ollama-watchdog (auto-starts on reboot)
Health:  curl http://localhost:11435/api/tags → must return 200

## THE 7 LOCAL LLM FEATURES

| # | Feature                    | Status      | Gospel File                              |
|---|----------------------------|-------------|------------------------------------------|
| 1 | Stage Broadcast Scripts    | ✅ LIVE      | STAGE_BROADCAST_LOCAL_LLM_GOSPEL.md      |
| 2 | Article Quality Gate       | ❌ NOT WIRED | ARTICLE_QUALITY_GATE_GOSPEL.md           |
| 3 | Nitter Tweet Scoring       | ❌ NOT BUILT | NITTER_SEMANTIC_SCORING_GOSPEL.md        |
| 4 | Clip Relevance Scoring     | ❌ NOT BUILT | CLIP_SEMANTIC_SCORING_GOSPEL.md          |
| 5 | Morning Brief Generation   | ❌ NOT MIGRATED | MORNING_BRIEF_LOCAL_LLM_GOSPEL.md     |
| 6 | Substack Digest            | ⚠️ NEEDS AUDIT | SUBSTACK_DIGEST_LOCAL_LLM_GOSPEL.md   |
| 7 | Regression Auto-Repair     | ❌ NOT BUILT | REGRESSION_AUTO_REPAIR_GOSPEL.md         |

## HIDDEN API COST (additional — from audit)
GPT-4o being called in 12+ services beyond the 7 above:
  article_automation.py (3 calls), launch_sequence.py (4 calls),
  pulse_intelligence.py (2 calls), blockware_intel_scraper.py,
  x_daily_top_article.py, story_dedup.py, x_service.py
These are Phase 2 migration targets after the 7 primary features are live.

## ESTIMATED TOTAL SAVINGS WHEN ALL 7 LIVE
  Stage Broadcast:       $95/year
  Morning Brief:         $3/year
  Substack Digest:       $2/year
  Article Quality Gate:  Risk reduction (priceless)
  Nitter Scoring:        Quality improvement (priceless)
  Clip Scoring:          Quality improvement (priceless)
  Regression Repair:     ~2h/week saved (priceless for autonomy)
  GPT-4o services:       ~$200-500/year (Phase 2)

## FALLBACK RULE (universal, applies to ALL 7)
EVERY local LLM call MUST have a fallback.
If Ollama is down: silently use API or approve/skip.
NEVER hard-fail a production feature because local model is unavailable.
The local model is an enhancement. The product ships with or without it.

## BUILD ORDER (recommended)
1. ✅ Stage Broadcast (done)
2. Article Quality Gate (CC spec ready — fire first)
3. Morning Brief Migration (simple swap)
4. Nitter Tweet Scoring (run after next nitter scrape)
5. Clip Scoring (run in next render cycle)
6. Substack Digest (after audit)
7. Regression Auto-Repair (most complex — do last)
