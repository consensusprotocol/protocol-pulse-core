Read ~/protocol_pulse/services/tweet_machine.py IN FULL.
Read ~/protocol_pulse/services/x_daily_top_article.py first 100 lines.
Read ~/protocol_pulse/data/social_queue/pending_tweets.json 2>/dev/null.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOCIAL PIPELINE — CROSS-LLM PRODUCT AUDIT + BUILD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a PRODUCT audit of Protocol Pulse's social media pipeline.
Goal: make every tweet feel like it was written by a brilliant,
opinionated Bitcoiner who lives on a Bitcoin standard and has deep
network intelligence — not an AI bot.

CONTEXT:
- Protocol Pulse = cypherpunk Bitcoin intelligence platform
- Audience = Bitcoiners, node runners, sovereign individuals
- Voice = PBX: contrarian, dry wit, Austrian economics lens
- Current: 1-2 tweets/day from article summaries
- Target: viral-worthy, community-resonant content

AUDIT QUESTIONS for each LLM (Gemini, GPT-4o, Grok):

Q1. SENTIMENT MIRRORING: The user wants to monitor top thought 
    leaders' most-liked posts/comments for community sentiment,
    then create our own version of that content. How do you
    implement this technically? What sources? What's the pipeline?

Q2. CONTENT TYPES: Beyond article summaries, what 5 tweet formats
    would drive the most engagement for a Bitcoin intelligence brand?
    Be specific with examples.

Q3. TIMING & FREQUENCY: What is the optimal posting schedule
    for a Bitcoin intelligence account in 2026? Day/time patterns?

Q4. REPLY STRATEGY: Should we build automated replies to trending
    Bitcoin threads? How do you do it without looking like a bot?

Q5. THREAD FORMAT: When and how should we use Twitter threads
    vs single tweets for maximum reach?

Q6. DATA INTEGRATION: We have live BTC price, mempool, FNG, hashrate,
    block height. How do you turn this into compelling social content
    automatically?

Q7. COMMUNITY VOICE: How do you make AI-generated content feel
    genuinely human and community-native? Specific techniques.

Q8. KILLER FORMAT: What is ONE tweet format that would make
    Protocol Pulse go viral in the Bitcoin community?

THEN BUILD:
After audit, implement the consensus improvements in tweet_machine.py:
1. Add sentiment mirroring: scrape top Bitcoin thought leader tweets
   (Preston Pysh, Lyn Alden, Robert Breedlove, TFTC) for trending themes
2. Add 3 new tweet formats beyond article summaries
3. Improve the PBX voice prompt to sound more human/contrarian
4. Add data-driven tweets (BTC price milestone, mempool congestion alerts)

COMMIT when done:
  git add services/tweet_machine.py
  git commit -m "feat(social): sentiment mirroring, new tweet formats, PBX voice improvement"
  git push
