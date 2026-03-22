Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Migrate x_daily_top_article.py compose_tweet() from gpt-4o to local Qwen3-Coder:30b.
This generates a single promotional tweet for the top daily article.
The voice laws are already strict — local Qwen with the same prompt produces same quality.

FILE: ~/protocol_pulse/services/x_daily_top_article.py
LOCAL LLM: http://localhost:11435, model qwen3-coder:30b
FALLBACK: gpt-4o (keep existing as fallback)

CRITICAL CONSTRAINT: NO HASHTAGS in any output. Add explicit check.
CRITICAL CONSTRAINT: x_service.py stays on gpt-4o. Do NOT touch it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTIGATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read compose_tweet() function in full (line ~141).
Note the exact prompt — it must be preserved exactly.
Note the URL injection logic after generation — keep it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In compose_tweet():
1. Before the existing OpenAI call, try local Ollama:
   import requests as _req
   try:
       resp = _req.post("http://localhost:11435/api/chat", json={
           "model": "qwen3-coder:30b",
           "messages": [{"role": "system", "content": "You write Bitcoin tweets. Return only the tweet text."},
                        {"role": "user", "content": prompt}],
           "stream": False, "options": {"temperature": 0.7}
       }, timeout=20)
       tweet = resp.json().get("message", {}).get("content", "").strip()
       if tweet and len(tweet) > 20 and "#" not in tweet:
           # Inject URL if missing
           if url not in tweet: tweet = tweet.rstrip() + f"\n{url}"
           logger.info("compose_tweet: LOCAL LLM path")
           return tweet[:280]
   except Exception as e:
       logger.info(f"compose_tweet: local failed ({e}), using GPT-4o")

2. Existing GPT-4o call remains as fallback — no changes to it

3. Add hashtag strip as final gate before any tweet is returned:
   import re
   tweet = re.sub(r" #\w+", "", tweet).strip()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -c "
import sys; sys.path.insert(0, '/home/ultron/protocol_pulse')
from services.x_daily_top_article import compose_tweet
test_article = {'title': 'Bitcoin Hashrate Hits Record 1000 EH/s', 'summary': 'Network fundamentals at all time high', 'url': 'https://protocolpulse.io/articles/test'}
tweet = compose_tweet(test_article)
print('TWEET:', tweet)
print('HAS_HASHTAG:', '#' in tweet)
print('HAS_URL:', 'protocolpulse.io' in tweet)
"
Should show: no hashtags, URL present, under 280 chars, cypherpunk voice.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/x_daily_top_article.py
git commit -m "feat(x_daily): local Qwen3 tweet composition, gpt-4o fallback, hashtag strip gate"
git push

DO NOT touch: x_service.py, tweet_machine.py, routes.py, assembler.py