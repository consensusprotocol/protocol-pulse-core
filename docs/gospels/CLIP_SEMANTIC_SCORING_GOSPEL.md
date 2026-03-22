# GOSPEL: CLIP RELEVANCE SEMANTIC SCORING
# Version 1.0 | March 2026 | Status: NOT BUILT ❌

## PROBLEM BEING SOLVED
Current clip_extractor.py scores clips using keyword matching:
  HIGH_SIGNAL keywords get +3 points each
  OPINION_MARKERS get +2 points each
  Word density bonus
This misses: sarcasm, context, nuance, PBX alignment.
A clip saying "Bitcoin is dead" scores the same as "Bitcoin is unstoppable"
because both contain the keyword "Bitcoin."

## WHAT IT DOES
After transcript extraction, sends clip transcript to local Qwen for
semantic scoring on 4 dimensions. Replaces pure keyword score as
primary ranking signal. Keyword score becomes a tiebreaker only.

## MODEL
LOCAL: Qwen3-Coder:30b via Ollama port 11435 (GPU 2, free)
WHEN: After clip extraction, before selections.json is written
LATENCY: ~5 seconds per clip, ~25 seconds for 5-clip batch (acceptable)

## 4 SCORING DIMENSIONS (0-10 each, weighted average)

SIGNAL DENSITY (weight 40%)
Does this clip contain specific, verifiable information?
10 = specific price, hashrate, on-chain metric with source
5  = general market commentary with one data point
0  = opinion with no data, pure sentiment

CYPHERPUNK ALIGNMENT (weight 30%)
Does this align with Protocol Pulse's sovereign Bitcoin perspective?
10 = monetary sovereignty, censorship resistance, self-custody
7  = Bitcoin fundamentals, mining, network health
3  = generic crypto commentary
0  = anti-Bitcoin, altcoin promotion, regulatory cheerleading

PBX INTEREST (weight 20%)
Would PBX find this genuinely interesting to react to?
10 = something that would make PBX say "nobody's talking about this"
5  = solid clip, expected content from this channel
0  = filler, ad read, sponsor mention, talking head with nothing new

FRESHNESS SIGNAL (weight 10%)
Does this reference something happening TODAY?
10 = today's specific event/number
5  = this week context
0  = generic timeless content

## COMBINED SCORE
semantic_score = (signal*0.4 + cypherpunk*0.3 + pbx*0.2 + freshness*0.1)
final_score = semantic_score * 0.7 + keyword_score_normalized * 0.3

## SCORING PROMPT
"Rate this Bitcoin media clip transcript on 4 dimensions (0-10 each).
Return ONLY JSON: {signal_density, cypherpunk_alignment, pbx_interest, freshness}

TRANSCRIPT: {transcript_text[:600]}
CHANNEL: {channel_name}
VIDEO TITLE: {video_title}"

## FILES
Extractor: ~/protocol_pulse/video_pipeline_v3/clip_extractor.py (ADD semantic scorer)
Selections: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/selections.json (ADD scores)

## QUALITY FLOOR
Minimum semantic_score to be selected: 5.0
If no clip scores above 5.0: fall back to keyword scoring (current behavior)
Never reject ALL clips — always select at least 3 for the episode

## WHAT NEVER CHANGES
- Fallback to keyword scoring if Ollama unavailable
- Never re-score already-selected clips mid-render
- selections.json schema: add semantic_score, do not remove existing fields
