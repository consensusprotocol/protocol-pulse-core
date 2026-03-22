# GOSPEL: NITTER TWEET SEMANTIC SCORING
# Version 1.0 | March 2026 | Status: NOT BUILT ❌

## PROBLEM BEING SOLVED
Current nitter_scraper.py computes:
  engagement_rate = (likes + retweets*2) / max(followers, 1000)
This means a viral meme beats a deep analysis tweet every time.
Saylor HODL tweet from 3 days ago scores higher than today's
Lyn Alden thread on monetary debasement because it has more likes.
Result: social segment shows stale noise instead of fresh signal.

## WHAT IT DOES
After scraping raw tweets, runs each through local Qwen to score
SIGNAL QUALITY (0-10) independently of engagement metrics.
Final score = 0.4 * signal_quality + 0.6 * engagement_normalized
This ensures high-signal low-engagement tweets can beat low-signal viral tweets.

## MODEL
LOCAL: Qwen3-Coder:30b via Ollama port 11435 (GPU 2, free)
BATCH: Score up to 50 tweets per nitter run in a single batch prompt
MAX LATENCY: 60 seconds total for full batch (acceptable — runs every 6h)

## SIGNAL QUALITY RUBRIC (what Qwen scores)
10 — Original analysis with specific data, first-principles Bitcoin reasoning
8  — Sharp observation with one specific number or fact
6  — Commentary on real event, no original analysis
4  — Retweet sentiment, vague bullish/bearish take
2  — Meme, price celebration, generic "Bitcoin fixes this"
0  — Spam, obvious shitcoin, unrelated content

## SCORING PROMPT STRUCTURE
Batch all tweets in one call:
  "Rate each tweet 0-10 for Bitcoin signal quality.
   Signal = specific data + original analysis + sovereign perspective.
   Noise = price hype + generic takes + memes.
   Return JSON array: [{handle, score, reason}]"

## SCHEMA ADDITION TO raw_tweets.json
Each tweet gets new field: "signal_score": float (0.0-10.0)
Combined score formula:
  combined = (signal_score * 0.4) + (min(engagement_rate, 1.0) * 0.6 * 10)
social_fetcher.py sorts by combined score DESC

## FILES
Scraper:  ~/protocol_pulse/services/nitter_scraper.py (ADD scoring function)
Fetcher:  ~/protocol_pulse/video_pipeline_v3/utils/social_fetcher.py (UPDATE sort)
Data:     ~/protocol_pulse/data/tweet_study/raw_tweets.json (ADD signal_score field)

## PERFORMANCE TARGET
- Top 5 tweets in each episode: avg signal_score >= 7.0
- Zero tweets with signal_score < 3.0 in final selection
- Stale tweets (>24h): signal_score capped at 5.0 regardless of content

## WHAT NEVER CHANGES
- If Ollama unavailable: use engagement_rate only (current behavior), no hard fail
- Never remove likes/retweets from schema — needed for engagement calc
- Batch size max 50 tweets per Qwen call — larger batches lose coherence
