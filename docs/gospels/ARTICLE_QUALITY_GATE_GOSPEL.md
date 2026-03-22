# GOSPEL: ARTICLE QUALITY GATE
# Version 1.0 | March 2026 | Status: SPEC WRITTEN, NOT YET WIRED ❌

## WHAT IT DOES
Reviews every article via local Qwen3-Coder before art.published = True is set.
Catches: AI generation tells, factual impossibilities, altcoin promotion,
broken content, out-of-range Bitcoin statistics.

## MODEL
LOCAL: Qwen3-Coder:30b via Ollama port 11435 (GPU 2, free)
FALLBACK: Auto-approve silently — gate failure NEVER blocks publishing

## FILES
Gate service: ~/protocol_pulse/services/article_quality_gate.py (TO BUILD)
Integration:  ~/protocol_pulse/services/automation.py line ~268

## RULES (checked in order)
RULE 1 — FACTUAL RANGE CHECKS (hard facts):
  BTC price: valid range $50,000 - $200,000 (2026 context)
  Hashrate: valid range 500 - 2000 EH/s
  Percentages: flag if >1000% or <-99% (likely hallucinated)
  Named quotes: flag if attributed to known figures saying implausible things

RULE 2 — AI GENERATION TELLS:
  "As an AI language model" → immediate reject
  "[PLACEHOLDER]" or "[INSERT]" in body → reject
  >3 consecutive sentences starting with "Bitcoin" → flag
  Repetition of same sentence with minor variation → flag

RULE 3 — BITCOIN ALIGNMENT:
  Altcoin described as "better than Bitcoin" → reject
  "crypto" used >5x without "Bitcoin" → flag
  Price prediction with specific future date + exact price → flag

## GATE OUTPUT SCHEMA
{
  "approved": bool,
  "score": 0-100,
  "flags": ["list of issues"],
  "source": "local_llm" | "fallback_approve"
}
Score 70-100: clean article. Score below 60: review flags. Below 40: reject.

## SAFETY RULES (non-negotiable)
- Gate failure = fallback_approve = article publishes normally
- Never block publishing due to Ollama being down
- Never modify article content — only approve/block
- Log every gate decision to ~/protocol_pulse/logs/article_quality_gate.log
- Max gate latency: 30 seconds. If exceeded: approve and log timeout.

## INTEGRATION POINT
automation.py ~line 268:
  BEFORE: art.published = True
  AFTER:  gate passes → art.published = True
          gate fails → art.published = False, tagged [QUALITY_GATE_BLOCKED]

## METRICS TO TRACK
- Daily approval rate (target: >95%)
- Most common flag types
- False positive rate (articles blocked that were actually fine)
- Gate latency average

## CC SPEC LOCATION
~/protocol_pulse/docs/cc_article_quality_gate.md
