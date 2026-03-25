# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: social-audit
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### Q1 — SENTIMENT MIRRORING

**DETAILED ANSWER:**
To monitor and mirror community sentiment effectively, we need to scrape and analyze content from top Bitcoin thought leaders. This involves identifying trending themes and sentiments from their most-liked posts and comments. The goal is to create our own version of this content that resonates with our audience while maintaining our unique voice.

**CONCRETE EXAMPLES:**
- If Preston Pysh tweets about the implications of a new Federal Reserve policy on Bitcoin, we could craft a tweet discussing the same topic but with a contrarian angle, emphasizing Bitcoin's resilience against fiat policies.
- Monitor Lyn Alden's posts on macroeconomic trends and create tweets that juxtapose these trends with Bitcoin's performance.

**TECHNICAL APPROACH:**
- **APIs & Tools:** Use Twitter API to fetch tweets from specific accounts like Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, Marty Bent, and American HODL. Use sentiment analysis tools like VADER or TextBlob to analyze the sentiment of these tweets.
- **Pipeline:** Set up a cron job to run daily sentiment analysis on fetched tweets. Use natural language processing (NLP) to identify trending themes and keywords. Feed these insights into our tweet generation model to craft similar content with our voice.

**WHY THIS WINS:**
This approach ensures our content is aligned with current community interests and sentiments, increasing engagement and relevance. By mirroring popular themes with our unique voice, we maintain authenticity and avoid sounding like a generic bot.

### Q2 — CONTENT TYPES

**DETAILED ANSWER:**
1. **Data-Driven Insights:** Share unique insights derived from Bitcoin's on-chain data, such as hashrate trends or mempool activity.
2. **Contrarian Takes:** Provide a fresh perspective on mainstream news, challenging common narratives.
3. **Historical Comparisons:** Draw parallels between historical economic events and current Bitcoin developments.
4. **Community Spotlights:** Highlight notable contributions or opinions from community members.
5. **Provocative Questions:** Pose thought-provoking questions that encourage community discussion.

**CONCRETE EXAMPLES:**
- "Bitcoin's hashrate just hit an all-time high. What does this mean for network security in an era of increasing state surveillance?"
- "Remember the 2008 financial crisis? Here's why Bitcoin is the antidote to the next one."

**TECHNICAL APPROACH:**
- Use SQL queries to extract relevant data from our database.
- Implement a content calendar to schedule diverse content types.
- Use AI models to generate content based on historical and current data.

**WHY THIS WINS:**
These formats cater to the intellectual curiosity of our audience, encouraging engagement and discussion while reinforcing our brand as a thought leader.

### Q3 — TIMING & FREQUENCY

**DETAILED ANSWER:**
The optimal posting schedule for a Bitcoin intelligence account in 2026 would involve posting during peak engagement times. Based on historical data, the best times are typically early morning and late afternoon in the US time zones.

**CONCRETE EXAMPLES:**
- Post at 9 AM and 5 PM EST to capture both the morning and evening audience.
- Schedule additional posts during key Bitcoin events or announcements.

**TECHNICAL APPROACH:**
- Use social media management tools like Buffer or Hootsuite to schedule posts.
- Analyze engagement metrics to refine posting times continuously.

**WHY THIS WINS:**
Posting during peak times maximizes visibility and engagement, ensuring our content reaches the largest possible audience.

### Q4 — REPLY STRATEGY

**DETAILED ANSWER:**
Automated replies can be effective if they are crafted to add value and engage genuinely with the conversation. The key is to avoid generic responses and instead offer insights or ask questions that provoke further discussion.

**CONCRETE EXAMPLES:**
- If a thread discusses Bitcoin's energy consumption, reply with data-backed insights on the environmental benefits of Bitcoin mining.

**TECHNICAL APPROACH:**
- Use sentiment analysis to identify positive threads.
- Develop a library of high-quality, pre-approved replies that can be customized based on the context.

**WHY THIS WINS:**
This strategy positions us as an active participant in the community, enhancing our reputation and fostering deeper engagement.

### Q5 — THREAD FORMAT

**DETAILED ANSWER:**
Threads should be used for in-depth analysis or storytelling that requires more than 280 characters. They are ideal for breaking down complex topics or providing a comprehensive overview of a significant event.

**CONCRETE EXAMPLES:**
- A thread explaining the implications of a new Bitcoin regulation, with each tweet covering a different aspect.

**TECHNICAL APPROACH:**
- Use AI to identify topics that warrant a thread.
- Craft each tweet in the thread to be standalone yet cohesive.

**WHY THIS WINS:**
Threads allow us to provide detailed insights and maintain reader engagement over

## GROK — CYCLE 1 OUTPUT
Below is a detailed product audit of Protocol Pulse's social media pipeline, addressing the eight questions with actionable insights, technical approaches, and specific examples. The goal is to ensure every tweet resonates with the Bitcoin community as if crafted by a brilliant, opinionated Bitcoiner with deep network intelligence, embodying the PBX voice (contrarian, dry wit, Austrian economics lens).

---

### Q1 — SENTIMENT MIRRORING
**Detailed Answer:**  
To monitor and mirror community sentiment from top Bitcoin thought leaders, we can build a sentiment analysis pipeline that scrapes, analyzes, and adapts trending content. This involves tracking posts and comments from key accounts, identifying high-engagement themes, and generating original content that aligns with Protocol Pulse’s cypherpunk voice while avoiding direct copying.  
- **Sources & Accounts:** Focus on thought leaders like Preston Pysh (@PrestonPysh), Lyn Alden (@LynAldenContact), Robert Breedlove (@Breedlove22), Marty Bent (@MartyBent), TFTC (@TFTC21), and American HODL (@American_HODL). These accounts represent a mix of macro-economic analysis, Bitcoin philosophy, and community sentiment.  
- **Pipeline:**  
  1. **Scraping:** Use the X API v2 (via Tweepy in Python) to fetch recent tweets and replies from these accounts, filtering for high engagement (likes, retweets, comments) over the past 24-48 hours.  
  2. **Sentiment & Theme Analysis:** Employ NLP models like Hugging Face’s Transformers (e.g., `distilbert-base-uncased-finetuned-sst-2-english` for sentiment) or custom keyword extraction to identify dominant themes (e.g., “fiat debasement,” “self-custody,” “mining centralization”). Use clustering (e.g., K-means on TF-IDF vectors) to group similar topics.  
  3. **Content Generation:** Feed trending themes into a fine-tuned LLM (e.g., Claude or GPT-4o) with a prompt enforcing Protocol Pulse’s voice and ensuring originality (e.g., “Reframe this sentiment on fiat debasement in a contrarian, dry-wit tone without copying the original”).  
  4. **Validation:** Cross-check generated content against recent posts using a similarity metric (like in `tweet_machine.py`’s `_keyword_overlap`) to avoid redundancy.  
- **Technical Approach:** Extend `services/x_service.py` to include a `sentiment_mirror` module. Use X API endpoints (`/2/users/{id}/tweets`, `/2/tweets/{id}/liking_users`) for data collection. Schedule via cron to run every 6 hours. Store sentiment trends in SQLite (`sovereign_intel.db`) for historical analysis.  
- **Why This Wins:** Mirroring sentiment builds relevance by tapping into live community conversations, ensuring Protocol Pulse feels like an active participant rather than a detached bot. Focusing on specific thought leaders ensures high-signal input, unlike broader hashtag scraping which often captures noise.

**Concrete Example:**  
- Original (Preston Pysh): “Central banks printing trillions while Bitcoin’s supply stays fixed at 21M. The math isn’t hard.” (500 likes)  
- Protocol Pulse Reframe: “Central banks are inflation factories with unlimited ink. Bitcoin’s 21M cap is the only math that matters. Why trust fiat clowns?”  

---

### Q2 — CONTENT TYPES
**Detailed Answer:** Beyond article summaries, these five tweet formats can drive engagement for a Bitcoin intelligence brand by offering variety, value, and community resonance:  
1. **Data-Driven Network Insights:** Share real-time Bitcoin network stats with a sharp take. Example: “Hashrate just hit 650 EH/s, up 12% this month. Miners are betting on Bitcoin’s future while fiat burns. Are you?”  
2. **Historical Parallels:** Draw contrarian comparisons between Bitcoin’s evolution and past monetary systems. Example: “Gold was sound money until governments hoarded it. Bitcoin’s self-custody flips the script. History won’t repeat.”  
3. **Provocative Questions on Sovereignty:** Pose uncomfortable questions about privacy or control. Example: “If your bank can freeze your funds, do you really own them? Bitcoin asks the questions fiat can’t answer.”  
4. **Meme-Style Satire with Dry Wit:** Use subtle humor to critique fiat or institutional overreach. Example: “Fed raises rates again to ‘fight inflation.’ Meanwhile, Bitcoin’s code doesn’t care about Powell’s feelings.”  
5. **Community Call-to-Action:** Engage directly by asking for opinions on Bitcoin-related dilemmas. Example: “Running a node is the ultimate middle finger to surveillance. What’s stopping you from spinning one up?”  
- **Technical Approach:** Add these formats as templates in `tweet_machine.py` under `TWEET_GENERATION_PROMPT`, with a rotation logic to ensure variety (e.g., one of each per week). Use live data APIs (e.g., mempool.space for hashrate) for network insights.  
- **Why This Wins:** These formats cater to different audience needs—education, humor, debate, and action—while reinforcing Protocol Pulse’s cypherpunk identity. They stand out against generic price commentary or news regurgitation.

---

##

## GEMINI — CYCLE 1 OUTPUT
An excellent and highly detailed feature package. The existing code in `tweet_machine.py` demonstrates a strong foundation in prompt engineering and operational discipline. The goal now is to evolve from a content *generator* to a social intelligence *engine*.

Here is a full product audit and strategic playbook to achieve that goal.

---

### **Q1 — SENTIMENT MIRRORING**

The goal is to tap into the Bitcoin community's "hive mind," identify emerging narratives, and create content that resonates with the current zeitgeist. This moves Protocol Pulse from broadcasting to engaging in a conversation.

**DETAILED ANSWER**
Implement a "Narrative Radar" pipeline that runs continuously. This pipeline will ingest high-signal content from key sources, use natural language processing (NLP) to identify dominant themes, and surface these themes as content opportunities. Instead of just mirroring sentiment, we will use it as a stimulus to generate a unique, Protocol Pulse take on the topic.

**Key Sources:**
1.  **X/Twitter Accounts:** The specified list (Pysh, Alden, Breedlove, Bent, etc.) is the core. Add others like Nic Carter (for critical perspectives), Dylan LeClair (for on-chain), and accounts known for high-signal threads.
2.  **Nostr:** This is the native protocol for many sovereign-minded Bitcoiners. Monitoring popular notes and zaps on relays like `wss://relay.damus.io` is crucial for detecting early signals.
3.  **Stacker News:** The "Hacker News for Bitcoiners." The top posts and comments are a goldmine of what the technically-minded community finds important.
4.  **Podcast Transcripts:** Key podcasts like *Tales from the Crypt*, *What Bitcoin Did*, and *The Investor's Podcast Network* (Bitcoin Fundamentals). Transcribe new episodes to extract core topics.

**TECHNICAL APPROACH**
1.  **Data Ingestion (The Scrapers):**
    *   **Twitter:** Use the X API v2 `users/:id/tweets` endpoint to pull timelines of the target accounts every 15 minutes. Use the `conversation_id` field to also pull in high-engagement replies to their tweets.
    *   **Nostr:** Use a Python library like `pynostr` to connect to multiple public relays and subscribe to events (Kind 1 notes) from the public keys of target individuals.
    *   **Stacker News:** Scrape their RSS feed or use their GraphQL API if available.
    *   **Podcasts:** Use a service like AssemblyAI or OpenAI's Whisper API to automatically transcribe new episodes from their RSS feeds.

2.  **NLP Pipeline (The Brain):**
    *   **Embedding:** For each piece of content (tweet, note, comment, transcript chunk), generate a vector embedding using a sentence-transformer model (e.g., `all-MiniLM-L6-v2`). This converts text into a numerical representation of its meaning.
    *   **Clustering:** Every hour, run a clustering algorithm (like HDBSCAN, which is great because it doesn't require specifying the number of clusters) on the embeddings generated in the last 24 hours. This will group semantically similar content together.
    *   **Theme Extraction & Summarization:** For each cluster, send the top 5-10 text samples to a powerful LLM (GPT-4o or Claude 3 Opus) with a prompt: `These are highly-engaged posts from the Bitcoin community. Identify the single, underlying theme or debate. Summarize it in a 5-word concept name (e.g., "CBDC Surveillance Concerns", "Hashrate Geopolitical Shift", "Self-Custody vs. ETFs").`
    *   **Storage:** Store these extracted themes, their summary, and representative posts in a new SQLite/Postgres table: `emerging_narratives`.

3.  **Content Trigger (The Cannon):**
    *   Modify `tweet_machine.py`. Before generating tweets, query the `emerging_narratives` table for the top 3 themes from the last 12 hours.
    *   Inject these themes into the generation prompt:
        ```
        ...
        COMMUNITY NARRATIVE RADAR:
        The community is currently debating these hot topics. Your angle should be aware of, but not a direct copy of, these narratives. Find a contrarian or deeper-level insight.
        - Topic 1: [CBDC Surveillance Concerns]
        - Topic 2: [Hashrate Geopolitical Shift]
        ...
        ```

**WHY THIS WINS**
This approach avoids simplistic "sentiment analysis" (positive/negative scores) and instead performs sophisticated **theme detection**. It finds *what* people are talking about, not just *how* they feel. It keeps the content fresh, relevant, and plugged into the community's brain, while preserving the unique Protocol Pulse voice by tasking the AI to find a non-obvious angle.

---

### **Q2 — CONTENT TYPES**

To maximize engagement, the content mix must be diverse. Relying only on brief summaries or article links is insufficient.

**DETAILED ANSWER & CONCRETE EXAMPLES**
1.  **The Unseen Metric:** Juxtapose a niche on-chain/macro metric with a real-world implication. This establishes authority and provides unique value.
    *   **Example:** "The 90-day Coin Days Destroyed metric is at a 5-year low. Old hands are not sellin

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — SOCIAL-AUDIT — CYCLE 1
Generated: 2026-03-25 02:42
Models: gpt4o, grok, gemini

---

## SCORES

> **Note:** The three model outputs are strategic/product audit responses to open-ended questions, not code reviews with explicit numeric scores. Scores below are synthesized from depth of technical analysis, specificity of implementation guidance, actionability, and coverage of all 8 questions. Scale: 1–10.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Sentiment Mirroring (Q1) | 9 | 6 | 8 | 8 |
| Content Type Diversity (Q2) | 9 | 7 | 8 | 8 |
| Timing & Frequency (Q3) | 9 | 5 | 8 | 7 |
| Reply Strategy (Q4) | 7 | 6 | 9 | 7 |
| Thread Format (Q5) | 6 | 6 | N/A | 6 |
| Data Integration (Q6) | 8 | 7 | 7 | 7 |
| Community Voice (Q7) | 8 | 6 | 8 | 7 |
| Killer Format (Q8) | 7 | 6 | 7 | 7 |
| Technical Specificity | 9 | 5 | 8 | 7 |
| Pipeline Architecture | 9 | 4 | 8 | 7 |
| **Overall** | **8.4** | **5.8** | **7.9** | **7.4** |

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — Sentiment Monitoring Pipeline Is Missing and Must Be Built
**What it is:** All three models independently identified that Protocol Pulse currently lacks any mechanism to ingest, analyze, or respond to community sentiment. The system generates content in a vacuum. There is no feedback loop from the Bitcoin community's actual conversations.

**Which file:** `services/x_service.py` (extend), `tweet_machine.py` (consume), new module `services/sentiment_radar.py` (create)

**What to change:**
- Create `services/sentiment_radar.py` that polls the X API v2 (`/2/users/{id}/tweets`) for a curated list of high-signal accounts (Preston Pysh, Lyn Alden, Robert Breedlove, Marty Bent, TFTC, American HODL at minimum)
- Store fetched content and derived themes in `sovereign_intel.db` in a new `emerging_narratives` table
- Inject top 3 active themes into the `tweet_machine.py` generation prompt before content is produced
- Schedule scraping via cron at regular intervals (consensus: every 6 hours minimum)

---

### U2 — Content Type Monoculture: The System Needs Diversified Format Templates
**What it is:** All three models flagged that the current pipeline produces a narrow, repetitive content format (article summaries + occasional takes). There is no templated variety forcing different cognitive formats across the posting week.

**Which file:** `tweet_machine.py` — `TWEET_GENERATION_PROMPT` and angle-selection logic

**What to change:**
- Add explicit named format types to the generation prompt, including: data-driven network insights, socratic questions, historical monetary analogies, contrarian hot takes, "what they say vs. what they do" juxtapositions
- Implement rotation logic so the same format cannot repeat in consecutive posts
- Each format should have a dedicated sub-prompt template within the generation pipeline

---

### U3 — Real-Time Data Integration Is Absent from Content Generation
**What it is:

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: services/tweet_machine.py (483 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | tweet_machine.py — Protocol Pulse Social Intelligence Layer
   4 | Phase 3: Daily tweet generation from morning intelligence brief
   5 | 
   6 | Runs at 6:30am ET daily. Uses morning_intelligence_brief.json to generate 
   7 | 3-5 Protocol Pulse tweets. Posts via X API v2 write if credentials exist,
   8 | otherwise queues to pending_tweets.json for manual review.
   9 | 
  10 | Voice: authoritative, cypherpunk, signal-dense, no fluff.
  11 | Think Marty Bent meets Bloomberg Terminal.
  12 | """
  13 | 
  14 | import json
  15 | import re
  16 | import logging
  17 | import os
  18 | import sqlite3
  19 | import sys
  20 | import urllib.request
  21 | from datetime import datetime, timezone
  22 | from pathlib import Path
  23 | 
  24 | # ── Paths ────────────────────────────────────────────────────────────────────
  25 | BASE = Path("/home/ultron/protocol_pulse")
  26 | BRIEF_PATH = BASE / "data" / "intelligence" / "morning_intelligence_brief.json"
  27 | QUEUE_PATH = BASE / "data" / "social_queue" / "pending_tweets.json"
  28 | LOG_PATH = BASE / "logs" / "tweet_machine.log"
  29 | SOVEREIGN_DB = BASE / "data" / "sovereign_intel.db"
  30 | 
  31 | QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
  32 | LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  33 | 
  34 | # Load .env
  35 | def load_env():
  36 |     env_path = BASE / ".env"
  37 |     if env_path.exists():
  38 |         for line in env_path.read_text().splitlines():
  39 |             if "=" in line and not line.startswith("#"):
  40 |                 k, _, v = line.partition("=")
  41 |                 os.environ.setdefault(k.strip(), v.strip())
  42 | 
  43 | load_env()
  44 | ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
  45 | X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
  46 | X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")
  47 | X_API_KEY = os.environ.get("X_API_KEY", os.environ.get("X_CONSUMER_KEY", ""))
  48 | X_API_SECRET = os.environ.get("X_API_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))
  49 | 
  50 | logging.basicConfig(
  51 |     level=logging.INFO,
  52 |     format="[tweet_machine] %(asctime)s %(levelname)s %(message)s",
  53 |     handlers=[
  54 |         logging.FileHandler(LOG_PATH),
  55 |         logging.StreamHandler(),
  56 |     ],
  57 | )
  58 | logger = logging.getLogger("tweet_machine")
  59 | 
  60 | CAN_POST = bool(X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET and X_API_KEY and X_API_SECRET)
  61 | 
  62 | TWEET_VOICE_LAWS = """
  63 | PROTOCOL PULSE VOICE LAWS (data-derived, March 2026 study):
  64 | 
  65 | LAW 1 - LEAD WITH DATA: Numbers in 72% of top tweets vs 57% overall.
  66 |   Open with a specific figure or stat. Not a vibe. A number.
  67 | 
  68 | LAW 2 - SHORTER WINS: Top 10% average 113 chars. Target under 150. Hard cap 280.
  69 |   Every word earns its place.
  70 | 
  71 | LAW 3 - NO DASHES OF ANY KIND: No em dashes, no double dashes (--), no hyphens used as pauses.
  72 |   Let sentence structure carry the rhythm. Punctuation is a crutch.
  73 | 
  74 | LAW 4 - ASK QUESTIONS SURGICALLY: 8% of top tweets. Genuinely uncomfortable to ignore.
  75 | 
  76 | LAW 5 - NO EMOJI. No exclamation marks. No trailing period. No dashes of any kind.
  77 | 
  78 | LAW 6 - ORIGINAL TAKES ONLY: 84% of top tweets are original positions, not reactions.
  79 | 
  80 | LAW 7 - ONE CLEAN IDEA: Max 3 sentences. One observation, one implication, one landing.
  81 | 
  82 | IDENTITY LAWS (override everything -- apply first):
  83 | 
  84 | BITCOIN ONLY: Protocol Pulse is a Bitcoin platform. Not crypto. Not web3. Not DeFi.
  85 |   Bitcoin is a monetary protocol. Everything else is noise.
  86 |   Never cover: altcoins, stablecoins, Ethereum, Solana, NFTs, DeFi, or broad crypto markets.
  87 | 
  88 | CYPHERPUNK ETHOS: Our lens is sovereignty, privacy, sound money, and freedom from
  89 |   institutional and state control. We are not a mainstream finance outlet.
  90 |   We do not celebrate stablecoin bills, ETF approvals, or institutional on-ramps as victories.
  91 |   We observe them as signals about where power is moving -- and where it isnt.
  92 | 
  93 | NEVER USE THESE ANGLES:
  94 |   - Stablecoin legislation or stablecoin yield
  95 |   - Altcoin or broad crypto price action
  96 |   - Regulatory clarity framed as a Bitcoin win
  97 |   - Government approval as validation
  98 |   - Institutional adoption cheerleading
  99 |   - Mainstream crypto sentiment
 100 | 
 101 | PREFERRED ANGLES:
 102 |   - Bitcoin as hard money vs fiat debasement
 103 |   - Sovereignty, self-custody, censorship resistance
 104 |   - Macro signals that reveal WHY Bitcoin exists
 105 |   - Mining, hashrate, network fundamentals
 106 |   - Geopolitical and monetary system stress
 107 |   - What central banks and governments are doing wrong
 108 |   - Financial privacy and freedom of transaction
 109 |   - The gap between what institutions say and what they do
 110 | """
 111 | 
 112 | TWEET_GENERATION_PROMPT = """You are the tweet writer for Protocol Pulse -- an autonomous Bitcoin intelligence platform.
 113 | 
 114 | Generate exactly 1 tweet for @ProtocolPulseHQ based on today's intelligence brief.
 115 | Pick the single highest-signal angle. Make it land.
 116 | 
 117 | CRITICAL — ANGLE DIVERSITY LAW:
 118 | The recently posted tweets below represent USED angles. You MUST pick a completely
 119 | different angle, different data point, and different framing. Never rephrase a posted tweet.
 120 | If today's brief only has one story, find a different dimension of it (different stat, different
 121 | implication, different audience insight). Repetition destroys credibility.
 122 | A good feed has variety: one macro signal, one protocol stat, one sovereignty/freedom angle.
 123 | Never post the same narrative twice within 48 hours.
 124 | 
 125 | INTELLIGENCE BRIEF:
 126 | {brief_text}
 127 | 
 128 | VOICE LAWS (mandatory):
 129 | {voice_laws}
 130 | 
 131 | HARD RULES:
 132 | - Never start with: Just, Hot take, Thread:, GM, Attention, Breaking, We
 133 | - Never use exclamation marks
 134 | - Never end with a period
 135 | - No hashtags
 136 | - No emoji
 137 | - No em dashes (the long dash: --)
 138 | - No double dashes (--)
 139 | - No dashes used as pauses or separators of any kind
 140 | 
 141 | EXAMPLES OF THE RIGHT VOICE:
 142 | - "Capitalism started in 1602 with the world's first stock exchange. It died in 2026 with the first unrealized gains tax. Neofeudalism arrived quietly"
 143 | - "Strategy acquired BTC again. No press conference. No explanation needed"
 144 | - "Remember all the talk of auditing the gold reserves in Fort Knox last year?"
 145 | 
 146 | Respond with a JSON object only. No markdown. No preamble:
 147 | {{"text": "<tweet -- max 280 chars, no trailing period, no emoji, no hashtags>", "angle": "<narrative addressed>", "type": "<stat|observation|question|signal>", "char_count": 0}}"""
 148 | 
 149 | 
 150 | def load_brief() -> dict:
 151 |     """Load morning intelligence brief."""
 152 |     if not BRIEF_PATH.exists():
 153 |         logger.error(f"Brief not found: {BRIEF_PATH}")
 154 |         logger.error("Run morning_brief.py first.")
 155 |         return {}
 156 |     age_hours = (
 157 |         datetime.now().timestamp() - BRIEF_PATH.stat().st_mtime
 158 |     ) / 3600
 159 |     if age_hours > 12:
 160 |         logger.warning(f"Brief is {age_hours:.1f}h old — may be stale")
 161 |     with open(BRIEF_PATH) as f:
 162 |         return json.load(f)
 163 | 
 164 | 
 165 | 
 166 | def get_todays_posted_tweets() -> list[str]:
 167 |     """Fetch tweet texts already posted today to avoid repeats."""
 168 |     try:
 169 |         conn = sqlite3.connect(str(BASE / "instance" / "protocol_pulse.db"))
 170 |         from datetime import timedelta
 171 |         cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
 172 |         rows = conn.execute(
 173 |             "SELECT tweet_content FROM auto_tweet WHERE posted_at >= ? ORDER BY posted_at DESC LIMIT 20",
 174 |             (cutoff_48h,)
 175 |         ).fetchall()
 176 |         conn.close()
 177 |         return [r[0] for r in rows if r[0]]
 178 |     except Exception as e:
 179 |         logger.warning(f"Could not fetch posted tweets: {e}")
 180 |         return []
 181 | 
 182 | 
 183 | def _keyword_overlap(text_a: str, text_b: str) -> float:
 184 |     """Return fraction of significant words shared between two tweets."""
 185 |     stop = {"the","a","an","is","are","was","were","and","or","but","in","on","at","to","of","for","with","this","that","it","as","by"}
 186 |     def words(t): return set(w.lower() for w in re.findall(r"\w+", t) if w.lower() not in stop and len(w) > 3)
 187 |     wa, wb = words(text_a), words(text_b)
 188 |     if not wa or not wb: return 0.0
 189 |     return len(wa & wb) / min(len(wa), len(wb))
 190 | 
 191 | 
 192 | def is_too_similar(new_tweet: str, posted: list[str], threshold: float = 0.40) -> bool:
 193 |     """Return True if new_tweet overlaps too much with any recently posted tweet."""
 194 |     for old in posted:
 195 |         if _keyword_overlap(new_tweet, old) >= threshold:
 196 |             logger.warning(f"DEDUP blocked — {_keyword_overlap(new_tweet, old):.0%} overlap with: {old[:60]}")
 197 |             return True
 198 |     return False
 199 | 
 200 | def generate_tweets(brief: dict, count: int = 1) -> list:
 201 |     """Call Claude Haiku to generate tweets from the brief."""
 202 |     if not ANTHROPIC_API_KEY:
 203 |         logger.error("ANTHROPIC_API_KEY not set")
 204 |         return []
 205 | 
 206 |     brief_text = json.dumps(brief, indent=2)[:3000]
 207 |     posted_today = get_todays_posted_tweets()
 208 |     used_context = ""
 209 |     if posted_today:
 210 |         used_context = "\nALREADY POSTED TODAY - pick a DIFFERENT angle:\n"
 211 |         used_context += "\n".join("- " + t[:100] for t in posted_today)
 212 | 
 213 |     # Concept dedup: tell the LLM which concepts are banned
 214 |     banned_concepts_context = ""
 215 |     try:
 216 |         sys.path.insert(0, str(BASE))
 217 |         from services.x_service import get_banned_concepts
 218 |         banned = get_banned_concepts(hours=72)
 219 |         if banned:
 220 |             banned_concepts_context = (
 221 |                 "\n\nBANNED CONCEPTS (do NOT use these — already posted in last 72h):\n"
 222 |                 + "\n".join(f"  - {c.replace('_', ' ')}" for c in banned)
 223 |                 + "\nPick a concept NOT on this list. Genuinely different angle."
 224 |             )
 225 |     except Exception as e:
 226 |         logger.warning(f"Could not load banned concepts: {e}")
 227 | 
 228 |     # Angle diversity: tell the LLM which categories are available
 229 |     available_angles_context = ""
 230 |     try:
 231 |         from services.x_service import get_available_angles, ANGLE_CATEGORIES
 232 |         available = get_available_angles()
 233 |         if available:
 234 |             available_angles_context = (
 235 |                 "\n\nANGLE CATEGORY ENFORCEMENT: You MUST pick one of these unused categories for today's tweet. "
 236 |                 "Return it in the 'angle' field of your JSON response.\n"
 237 |                 f"Available categories: {', '.join(available)}\n"
 238 |                 f"All categories: {', '.join(ANGLE_CATEGORIES)}"
 239 |             )
 240 |         else:
 241 |             logger.warning("All angle categories used today — no available angles")
 242 |     except Exception as e:
 243 |         logger.warning(f"Could not load angle categories: {e}")
 244 | 
 245 |     prompt = TWEET_GENERATION_PROMPT.format(
 246 |         brief_text=brief_text + used_context + banned_concepts_context + available_angles_context,
 247 |         voice_laws=TWEET_VOICE_LAWS
 248 |     )
 249 | 
 250 |     payload = {
 251 |         "model": "claude-haiku-4-5-20251001",
 252 |         "max_tokens": 500,
 253 |         "messages": [{"role": "user", "content": prompt}],
 254 |     }
 255 |     req = urllib.request.Request(
 256 |         "https://api.anthropic.com/v1/messages",
 257 |         data=json.dumps(payload).encode(),
 258 |         headers={
 259 |             "Content-Type": "application/json",
 260 |             "x-api-key": ANTHROPIC_API_KEY,
 261 |             "anthropic-version": "2023-06-01",
 262 |             "User-Agent": "ProtocolPulse/1.0",
 263 |         },
 264 |     )
 265 |     try:
 266 |         resp = urllib.request.urlopen(req, timeout=30)
 267 |         data = json.loads(resp.read())
 268 |         content = data.get("content", [{}])[0].get("text", "").strip()
 269 |         # Strip markdown fences
 270 |         if content.startswith("```"):
 271 |             content = content.split("```", 2)[1]
 272 |             if content.startswith("json"):
 273 |                 content = content[4:]
 274 |             content = content.rsplit("```", 1)[0].strip()
 275 |         parsed = json.loads(content)
 276 |         if isinstance(parsed, dict):
 277 |             parsed = [parsed]
 278 |         logger.info(f"Generated {len(parsed)} tweet(s)")
 279 |         return parsed
 280 |     except Exception as e:
 281 |         logger.error(f"Tweet generation failed: {e}")
 282 |         return []
 283 | 
 284 | 
 285 | def _strip_hashtags(text: str) -> str:
 286 |     """Remove any hashtags from outgoing text. X algorithms penalize them."""
 287 |     import re
 288 |     return re.sub(r" #\w+", "", text).strip()
 289 | 
 290 | 
 291 | def post_to_x(tweet_text: str) -> dict:
 292 |     """Post a tweet via X API v2 using OAuth 1.0a."""
 293 |     # Requires: tweepy or manual OAuth 1.0a signing
 294 |     try:
 295 |         import tweepy
 296 |         client = tweepy.Client(
 297 |             consumer_key=X_API_KEY,
 298 |             consumer_secret=X_API_SECRET,
 299 |             access_token=X_ACCESS_TOKEN,
 300 |             access_token_secret=X_ACCESS_TOKEN_SECRET,
 301 |         )
 302 |         response = client.create_tweet(text=tweet_text)
 303 |         tweet_id = response.data["id"]
 304 |         logger.info(f"Posted tweet {tweet_id}: {tweet_text[:50]}...")
 305 |         return {"success": True, "tweet_id": tweet_id}
 306 |     except ImportError:
 307 |         logger.error("tweepy not installed — cannot post. Use: pip3 install tweepy")
 308 |         return {"success": False, "error": "tweepy not installed"}
 309 |     except Exception as e:
 310 |         logger.error(f"X API post failed: {e}")
 311 |         return {"success": False, "error": str(e)}
 312 | 
 313 | 
 314 | def queue_tweet(tweet: dict, brief: dict) -> None:
 315 |     """Add tweet to pending_tweets.json queue for manual review."""
 316 |     # Load existing queue
 317 |     existing = []
 318 |     if QUEUE_PATH.exists():
 319 |         with open(QUEUE_PATH) as f:
 320 |             existing = json.load(f)
 321 | 
 322 |     entry = {
 323 |         "id": f"tweet_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{tweet.get('priority', 0)}",
 324 |         "text": tweet.get("text", ""),
 325 |         "angle": tweet.get("angle", ""),
 326 |         "type": tweet.get("type", ""),
 327 |         "priority": tweet.get("priority", 3),
 328 |         "status": "pending",
 329 |         "generated_at": datetime.now(timezone.utc).isoformat(),
 330 |         "brief_date": brief.get("date", ""),
 331 |         "sentiment": brief.get("sentiment", ""),
 332 |     }
 333 | 
 334 |     # Dedup by text
 335 |     existing_texts = {e.get("text", "") for e in existing}
 336 |     if entry["text"] not in existing_texts:
 337 |         existing.append(entry)
 338 |         with open(QUEUE_PATH, "w") as f:
 339 |             json.dump(existing, f, indent=2, ensure_ascii=False)
 340 |         logger.info(f"Queued: {entry['text'][:60]}...")
 341 | 
 342 | 
 343 | def log_to_db(tweet: dict, posted: bool, tweet_id: str = None) -> None:
 344 |     """Log tweet to sovereign_intel.db auto_tweet table."""
 345 |     try:
 346 |         conn = sqlite3.connect(str(SOVEREIGN_DB))
 347 |         c = conn.cursor()
 348 |         c.execute("""
 349 |             CREATE TABLE IF NOT EXISTS auto_tweet (
 350 |                 id INTEGER PRIMARY KEY AUTOINCREMENT,
 351 |                 tweet_text TEXT NOT NULL,
 352 |                 tweet_type TEXT DEFAULT 'generated',
 353 |                 angle TEXT,
 354 |                 status TEXT DEFAULT 'pending',
 355 |                 x_tweet_id TEXT,
 356 |                 generated_at TEXT,
 357 |                 posted_at TEXT,
 358 |                 sentiment TEXT,
 359 |                 brief_date TEXT
 360 |             )
 361 |         """)
 362 |         c.execute(
 363 |             """INSERT INTO auto_tweet 
 364 |                (tweet_text, tweet_type, angle, status, x_tweet_id, generated_at, posted_at, sentiment, brief_date)
 365 |                VALUES (?,?,?,?,?,?,?,?,?)""",
 366 |             (
 367 |                 tweet.get("text", ""),
 368 |                 tweet.get("type", "generated"),
 369 |                 tweet.get("angle", ""),
 370 |                 "posted" if posted else "queued",
 371 |                 tweet_id,
 372 |                 datetime.now(timezone.utc).isoformat(),
 373 |                 datetime.now(timezone.utc).isoformat() if posted else None,
 374 |                 tweet.get("sentiment", ""),
 375 |                 tweet.get("brief_date", ""),
 376 |             ),
 377 |         )
 378 |         conn.commit()
 379 |         conn.close()
 380 |     except Exception as e:
 381 |         logger.warning(f"DB log failed: {e}")
 382 | 
 383 | 
 384 | def main():
 385 |     logger.info("=" * 60)
 386 |     logger.info("Tweet Machine starting")
 387 |     logger.info("=" * 60)
 388 | 
 389 |     if not CAN_POST:
 390 |         logger.warning(
 391 |             "X write credentials not found in .env — operating in QUEUE mode.\n"
 392 |             "Missing: X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_API_KEY, X_API_SECRET\n"
 393 |             "Tweets will be written to: " + str(QUEUE_PATH)
 394 |         )
 395 |     else:
 396 |         logger.info("X write credentials found — will auto-post")
 397 | 
 398 |     # Load brief
 399 |     brief = load_brief()
 400 |     if not brief:
 401 |         logger.error("Cannot generate tweets without a brief. Exiting.")
 402 |         sys.exit(1)
 403 | 
 404 |     logger.info(
 405 |         f"Brief loaded: {brief.get('date','?')} | "
 406 |         f"Sentiment: {brief.get('sentiment','?')} | "
 407 |         f"BTC: {brief.get('btc_price','?')}"
 408 |     )
 409 | 
 410 |     # Generate tweets
 411 |     tweets = generate_tweets(brief, count=1)
 412 |     if not tweets:
 413 |         logger.error("No tweets generated. Exiting.")
 414 |         sys.exit(1)
 415 | 
 416 |     # Sort by priority
 417 |     tweets.sort(key=lambda t: t.get("priority", 5))
 418 | 
 419 |     # Post or queue
 420 |     posted_count = 0
 421 |     queued_count = 0
 422 | 
 423 |     for tweet in tweets:
 424 |         text = tweet.get("text", "").strip()
 425 |         if not text:
 426 |             continue
 427 |         if len(text) > 280:
 428 |             logger.warning(f"Tweet too long ({len(text)} chars), truncating: {text[:50]}...")
 429 |             text = text[:277] + "..."
 430 |             tweet["text"] = text
 431 | 
 432 |         if CAN_POST:
 433 |             text = _strip_hashtags(text)  # Hard gate
 434 | 
 435 |             # Global rate gate check
 436 |             try:
 437 |                 sys.path.insert(0, str(BASE))
 438 |                 from services.x_service import can_post_tweet, ANGLE_CATEGORIES
 439 |                 angle = tweet.get("angle", "macro_monetary")
 440 |                 # Normalize angle to valid category
 441 |                 if angle not in ANGLE_CATEGORIES:
 442 |                     angle = "macro_monetary"
 443 |                 allowed, reason = can_post_tweet(text, source="tweet_machine", angle_category=angle)
 444 |                 if not allowed:
 445 |                     logger.warning(f"GATE BLOCKED: {reason}")
 446 |                     queue_tweet(tweet, brief)
 447 |                     log_to_db(tweet, posted=False)
 448 |                     queued_count += 1
 449 |                     continue
 450 |             except Exception as e:
 451 |                 logger.warning(f"Gate check failed (allowing): {e}")
 452 | 
 453 |             # Dedup check (legacy, redundant with gate but kept as safety net)
 454 |             posted_today = get_todays_posted_tweets()
 455 |             if is_too_similar(text, posted_today):
 456 |                 logger.warning("DEDUP blocked tweet")
 457 |                 queue_tweet(tweet, brief)
 458 |                 log_to_db(tweet, posted=False)
 459 |                 queued_count += 1
 460 |                 continue
 461 | 
 462 |             result = post_to_x(text)
 463 |             if result.get("success"):
 464 |                 log_to_db(tweet, posted=True, tweet_id=result.get("tweet_id"))
 465 |                 posted_count += 1
 466 |             else:
 467 |                 queue_tweet(tweet, brief)
 468 |                 log_to_db(tweet, posted=False)
 469 |                 queued_count += 1
 470 |         else:
 471 |             queue_tweet(tweet, brief)
 472 |             log_to_db(tweet, posted=False)
 473 |             queued_count += 1
 474 | 
 475 |     logger.info(f"Done: {posted_count} posted, {queued_count} queued")
 476 |     if queued_count > 0:
 477 |         logger.info(f"Review queue at: {QUEUE_PATH}")
 478 | 
 479 | 
 480 | if __name__ == "__main__":
 481 |     main()
 482 | 
 483 | 
```

### File: services/x_daily_top_article.py (274 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | x_daily_top_article.py
   4 | Posts the top Protocol Pulse article of the day to X (Twitter).
   5 | - Picks highest read_count article published in last 24h
   6 | - Falls back to latest article if no reads yet
   7 | - Generates a 1200x675 custom X card image via Grok/DALL-E
   8 | - Posts with cypherpunk voice and article link
   9 | - Runs once daily at 14:00 ET
  10 | """
  11 | 
  12 | import os, sys, re, json, logging, time, base64
  13 | from datetime import datetime, timedelta
  14 | from pathlib import Path
  15 | 
  16 | BASE = Path("/home/ultron/protocol_pulse")
  17 | sys.path.insert(0, str(BASE))
  18 | 
  19 | logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
  20 | logger = logging.getLogger("x_top_article")
  21 | 
  22 | # X/Twitter image dimensions
  23 | X_IMAGE_WIDTH  = 1200
  24 | X_IMAGE_HEIGHT = 675
  25 | 
  26 | SITE_URL = "https://protocolpulse.io"
  27 | 
  28 | 
  29 | def get_top_article():
  30 |     """Get top article of the day by read_count, fallback to latest."""
  31 |     try:
  32 |         from dotenv import load_dotenv
  33 |         load_dotenv(BASE / ".env")
  34 |         from app import app
  35 |         import models
  36 |         
  37 |         with app.app_context():
  38 |             cutoff = datetime.utcnow() - timedelta(hours=24)
  39 |             
  40 |             # Try top by read_count
  41 |             article = (
  42 |                 models.Article.query
  43 |                 .filter(models.Article.published == True)
  44 |                 .filter(models.Article.created_at >= cutoff)
  45 |                 .order_by(models.Article.read_count.desc(), models.Article.created_at.desc())
  46 |                 .first()
  47 |             )
  48 |             
  49 |             # Fallback to overall latest
  50 |             if not article:
  51 |                 article = (
  52 |                     models.Article.query
  53 |                     .filter(models.Article.published == True)
  54 |                     .order_by(models.Article.created_at.desc())
  55 |                     .first()
  56 |                 )
  57 |             
  58 |             if article:
  59 |                 return {
  60 |                     "id": article.id,
  61 |                     "title": article.title,
  62 |                     "summary": article.summary or "",
  63 |                     "category": article.category or "Bitcoin",
  64 |                     "slug": article.slug or str(article.id),
  65 |                     "cover_image_url": article.cover_image_url or "",
  66 |                     "read_count": article.read_count or 0,
  67 |                 }
  68 |         return None
  69 |     except Exception as e:
  70 |         logger.error(f"get_top_article failed: {e}")
  71 |         return None
  72 | 
  73 | 
  74 | def generate_x_card_image(article: dict) -> str | None:
  75 |     """
  76 |     Generate a 1200x675 X card image for the article.
  77 |     Uses Grok (xAI) image generation.
  78 |     Returns local file path or None.
  79 |     """
  80 |     try:
  81 |         import urllib.request as _req
  82 |         from dotenv import load_dotenv
  83 |         load_dotenv(BASE / ".env")
  84 |         
  85 |         xai_key = os.getenv("XAI_API_KEY")
  86 |         if not xai_key:
  87 |             logger.warning("XAI_API_KEY not set — skipping X card image")
  88 |             return None
  89 |         
  90 |         title = article["title"][:80]
  91 |         category = article["category"]
  92 |         
  93 |         prompt = (
  94 |             f"Professional Bitcoin intelligence media card, 1200x675 pixels. "
  95 |             f"Category: {category}. Topic: {title}. "
  96 |             f"Dark cinematic background (#0a0a0a), dramatic red accent lighting (#CC2222), "
  97 |             f"high contrast, editorial photography style, no text overlaid. "
  98 |             f"Moody, authoritative, financial news aesthetic. "
  99 |             f"Bitcoin motif subtle in background. Ultra-sharp, 4K quality."
 100 |         )
 101 |         
 102 |         payload = json.dumps({
 103 |             "model": "grok-2-image-1212",
 104 |             "prompt": prompt,
 105 |             "n": 1,
 106 |             "size": "1792x1024",  # closest to 1200x675 ratio
 107 |         }).encode()
 108 |         
 109 |         req = _req.Request(
 110 |             "https://api.x.ai/v1/images/generations",
 111 |             data=payload,
 112 |             headers={
 113 |                 "Content-Type": "application/json",
 114 |                 "Authorization": f"Bearer {xai_key}"
 115 |             }
 116 |         )
 117 |         with _req.urlopen(req, timeout=30) as r:
 118 |             result = json.loads(r.read())
 119 |         
 120 |         img_url = result["data"][0].get("url")
 121 |         if not img_url:
 122 |             return None
 123 |         
 124 |         # Download the image
 125 |         out_path = BASE / "static" / "images" / "x_cards" / f"x_card_{article['id']}.jpg"
 126 |         out_path.parent.mkdir(parents=True, exist_ok=True)
 127 |         
 128 |         req2 = _req.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
 129 |         with _req.urlopen(req2, timeout=20) as r:
 130 |             img_data = r.read()
 131 |         
 132 |         out_path.write_bytes(img_data)
 133 |         logger.info(f"X card image saved: {out_path} ({len(img_data)//1024}KB)")
 134 |         return str(out_path)
 135 |         
 136 |     except Exception as e:
 137 |         logger.warning(f"X card image generation failed: {e}")
 138 |         return None
 139 | 
 140 | 
 141 | def compose_tweet(article: dict) -> str:
 142 |     """Generate cypherpunk tweet copy for the article."""
 143 |     try:
 144 |         from dotenv import load_dotenv
 145 |         load_dotenv(BASE / ".env")
 146 |         from openai import OpenAI
 147 |         client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 148 |         
 149 |         slug = article.get("slug", str(article["id"]))
 150 |         url = f"{SITE_URL}/articles/{slug}"
 151 |         
 152 |         prompt = f"""Write a single X (Twitter) post for this Protocol Pulse article.
 153 |         
 154 | Article: {article["title"]}
 155 | Category: {article["category"]}
 156 | Summary: {article["summary"][:200]}
 157 | Link: {url}
 158 | 
 159 | Rules:
 160 | - Max 240 chars including the URL (URL = 23 chars)
 161 | - So max 217 chars of text
 162 | - Voice: authoritative, cypherpunk, signal-dense
 163 | - One sharp insight or provocative question
 164 | - ABSOLUTELY NO hashtags. Zero. Not #Bitcoin, not #BTC, not any. X algorithms penalize hashtags. Never use them.
 165 | - End with the URL on its own line
 166 | - No em dashes in the tweet (Twitter strips them oddly)
 167 | 
 168 | Return ONLY the tweet text, nothing else."""
 169 | 
 170 |         resp = client.chat.completions.create(
 171 |             model="gpt-4o",
 172 |             messages=[{"role": "user", "content": prompt}],
 173 |             max_tokens=100,
 174 |             temperature=0.8
 175 |         )
 176 |         tweet = resp.choices[0].message.content.strip()
 177 |         
 178 |         # Ensure URL is in the tweet
 179 |         if url not in tweet:
 180 |             tweet = tweet.rstrip() + f"\n{url}"
 181 |         
 182 |         return tweet[:280]
 183 |         
 184 |     except Exception as e:
 185 |         logger.error(f"Tweet composition failed: {e}")
 186 |         slug = article.get("slug", str(article["id"]))
 187 |         return f"{article['title'][:180]}\n{SITE_URL}/articles/{slug}"
 188 | 
 189 | 
 190 | def post_to_x(tweet_text: str, image_path: str = None) -> bool:
 191 |     """Post tweet via X API v2 with optional image."""
 192 |     try:
 193 |         from dotenv import load_dotenv
 194 |         load_dotenv(BASE / ".env")
 195 |         
 196 |         api_key    = os.getenv("X_API_KEY", "")
 197 |         api_secret = os.getenv("X_API_SECRET", "")
 198 |         acc_token  = os.getenv("X_ACCESS_TOKEN", "")
 199 |         acc_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "")
 200 |         
 201 |         if not all([api_key, api_secret, acc_token, acc_secret]):
 202 |             logger.error("Missing X API credentials")
 203 |             return False
 204 |         
 205 |         import tweepy
 206 |         client = tweepy.Client(
 207 |             consumer_key=api_key,
 208 |             consumer_secret=api_secret,
 209 |             access_token=acc_token,
 210 |             access_token_secret=acc_secret
 211 |         )
 212 |         
 213 |         media_id = None
 214 |         if image_path and os.path.exists(image_path):
 215 |             try:
 216 |                 auth = tweepy.OAuth1UserHandler(api_key, api_secret, acc_token, acc_secret)
 217 |                 api_v1 = tweepy.API(auth)
 218 |                 media = api_v1.media_upload(filename=image_path)
 219 |                 media_id = media.media_id_string
 220 |                 logger.info(f"Image uploaded: media_id={media_id}")
 221 |             except Exception as img_err:
 222 |                 logger.warning(f"Image upload failed: {img_err}")
 223 |         
 224 |         kwargs = {"text": tweet_text}
 225 |         if media_id:
 226 |             kwargs["media_ids"] = [media_id]
 227 |         
 228 |         resp = client.create_tweet(**kwargs)
 229 |         tweet_id = resp.data["id"]
 230 |         logger.info(f"Tweet posted: https://x.com/ProtocolPulse/status/{tweet_id}")
 231 |         print(f"SUCCESS: https://x.com/ProtocolPulse/status/{tweet_id}")
 232 |         return True
 233 |         
 234 |     except Exception as e:
 235 |         logger.error(f"X post failed: {e}")
 236 |         return False
 237 | 
 238 | 
 239 | def run_daily_top_article():
 240 |     """Main entry: find top article, generate image, tweet it."""
 241 |     logger.info("Starting X daily top article publisher...")
 242 |     
 243 |     article = get_top_article()
 244 |     if not article:
 245 |         logger.error("No article found")
 246 |         return
 247 |     
 248 |     logger.info(f"Top article: [{article['id']}] {article['title'][:60]} (reads: {article['read_count']})")
 249 |     
 250 |     # Generate X-optimized card image
 251 |     image_path = generate_x_card_image(article)
 252 |     
 253 |     # Compose tweet
 254 |     tweet = compose_tweet(article)
 255 |     logger.info(f"Tweet ({len(tweet)} chars):\n{tweet}")
 256 |     
 257 |     # Post
 258 |     success = post_to_x(tweet, image_path)
 259 |     
 260 |     # Log result
 261 |     log_path = BASE / "logs" / "x_publisher.log"
 262 |     with open(log_path, "a") as f:
 263 |         f.write(json.dumps({
 264 |             "ts": datetime.utcnow().isoformat(),
 265 |             "article_id": article["id"],
 266 |             "title": article["title"],
 267 |             "success": success,
 268 |             "tweet_len": len(tweet),
 269 |         }) + "\n")
 270 | 
 271 | 
 272 | if __name__ == "__main__":
 273 |     run_daily_top_article()
 274 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
