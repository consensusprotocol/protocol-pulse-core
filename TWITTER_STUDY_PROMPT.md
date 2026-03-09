# TWITTER ENGAGEMENT STUDY — Claude Code Session Prompt
## Fire this in a Claude Code session on Ultron

---

You are building a Twitter/X engagement analysis tool to reverse-engineer the tweet style that wins in the Bitcoin corner of X. The goal is a data-backed voice blueprint for Protocol Pulse's automated tweet pipeline. Target voice blend: Theo Von (absurdist deadpan humor) + Michael Saylor (conviction + hard data) + Lyn Alden (quiet depth, "I did the homework").

## STEP 0: ENVIRONMENT CHECK

1. Verify the Twitter API bearer token exists:
```bash
echo $TWITTER_BEARER_TOKEN | head -c 20
```
If not set, check `~/protocol_pulse/.env` or Replit secrets. Export it before proceeding.

2. Verify Python dependencies. Install if missing:
```bash
pip install requests pandas --break-system-packages
```

3. Create output directories:
```bash
mkdir -p ~/protocol_pulse/data/tweet_study
```

## STEP 1: HANDLE VERIFICATION

Before pulling any tweets, verify every handle resolves to a real user_id. Log any that fail. Do NOT proceed with broken handles.

Account list (16 accounts across 4 tiers):

**Conviction + data tier**
@saylor @PrestonPysh @gladstein @WClementeIII @APompliano

**Depth + nuance tier**
@LynAldenContact @adam3us @nic__carter @NickSzabo4

**Irreverent / deadpan tier**
@maxkeiser @MartyBent @PeterMcCormack @americanhodl @daborosgrams

**High-engagement hybrids**
@CryptoHayes @ErikVoorhees

For each handle, call `GET /2/users/by/username/:username` and store the user_id and followers_count. If a handle fails (suspended, deleted, renamed), log it and continue with remaining accounts. Report which handles failed at the top of the final output.

## STEP 2: TWEET COLLECTION

For each verified account, pull the last 200 original tweets. Use `GET /2/users/:id/tweets` with these parameters:

```
max_results=100 (paginate twice for 200)
tweet.fields=created_at,public_metrics,entities,referenced_tweets
exclude=retweets
```

For every tweet, capture and store:
- full text
- created_at (timestamp)
- public_metrics: retweet_count, reply_count, like_count, quote_count
- impression_count IF available on this API tier. If the field is missing or returns an error, skip it silently and note "impressions unavailable" in the report. Do NOT let this crash the script.
- Whether the tweet is: original, reply, or quote tweet (check referenced_tweets field)
- Whether it starts a thread (next tweet from same user within 2 minutes, also a reply to self)
- Character count and word count
- Contains a URL (boolean)
- Contains media/image (boolean)
- Contains numbers/data points (regex: any digit sequence, $, %, B/M/K suffix)
- Contains a question mark
- Contains an em dash (U+2014) or en dash (U+2013)
- Contains profanity/casual language (basic word list: damn, hell, shit, fuck, ass, bullshit, lmao, lol)
- Contains emoji (boolean)

**RATE LIMIT HANDLING — CRITICAL:**
- Add a 1.1 second delay between every API call
- After each call, read the `x-rate-limit-remaining` and `x-rate-limit-reset` response headers
- Log remaining quota after every 5 calls
- If remaining < 5, sleep until reset time + 5 seconds
- Twitter Basic tier: 10,000 tweet reads/month, 15 requests per 15-min window for user timeline
- This study uses ~3,200 tweet reads (200 x 16). That is ~32% of monthly quota. Acceptable.
- If any call returns 429 (rate limited), log it, sleep until reset, retry once. If retry fails, stop cleanly and save all data collected so far.

## STEP 3: SCORING

For each tweet, calculate:

**Raw engagement score:**
```
raw = likes + (retweets * 2) + (replies * 3) + (quotes * 4)
```

Rationale: Likes are passive. Retweets require endorsement. Replies require effort. Quotes require the most (writing original content in response). Weight accordingly.

**Engagement rate:**
```
rate = raw_engagement / account_followers_count
```

This normalizes across accounts. A tweet from a 50K follower account getting 500 likes is more impressive than a 5M follower account getting 500 likes.

**Top percentile flag:**
Mark the top 10% of tweets across the entire dataset (all accounts combined, ranked by engagement rate).

## STEP 4: ANALYSIS

Run the following analyses on the full dataset AND separately on the top 10% subset.

### 4A: Structure Analysis
- % original tweets vs replies vs quote tweets
- % that are thread starters
- % that contain a question
- % that contain data/numbers
- % that contain a URL
- % that contain media
- Average character length (full dataset vs top 10%)
- Average word count (full dataset vs top 10%)

### 4B: Style Analysis
- % that contain em dashes (track separately: does em dash presence correlate with HIGHER or LOWER engagement rate?)
- % that contain emoji
- % that contain profanity/casual language
- Average sentence count per tweet
- Most common punctuation ending (period, question mark, no punctuation, exclamation)
- % that start with a data point/number vs a word

### 4C: Tone Word Frequency
From the top 50 tweets by engagement rate, extract the most common:
- Nouns (excluding stop words)
- Verbs
- Adjectives
- Named entities (people, companies, coins)
- Two-word and three-word phrases (bigrams/trigrams)

### 4D: Per-Account Rankings
- Average engagement rate per account (ranked highest to lowest)
- Best single tweet per account (text + score)
- Median engagement rate per account
- Which tier (conviction/depth/irreverent/hybrid) has the highest average engagement rate?

### 4E: Reply Analysis
From quote tweets and replies in the top 10%, analyze:
- What kind of original tweet are they replying to? (news, opinion, data, meme)
- How long is the reply vs the original?
- Does the reply add data, humor, contrarian take, or agreement?

## STEP 5: DELIVERABLES

Save ALL of the following:

### File 1: `~/protocol_pulse/data/tweet_study/raw_tweets.json`
Full raw dataset. Every tweet from every account with all fields. This is the reusable asset for future runs.

### File 2: `~/protocol_pulse/data/tweet_study/TWEET_VOICE_STUDY.md`
The final report. Structure it EXACTLY like this:

```markdown
# Protocol Pulse Tweet Voice Study
## Data collected: [date]
## Accounts analyzed: [count] ([list any failed handles])
## Total tweets analyzed: [count]
## Twitter API tier: [Basic/Pro]

---

## 1. TOP 15 HIGHEST-ENGAGEMENT TWEETS

| Rank | Account | Eng Rate | Likes | RTs | Replies | Text (first 120 chars) | Date |
|------|---------|----------|-------|-----|---------|----------------------|------|
| 1    | ...     | ...      | ...   | ... | ...     | ...                  | ...  |

## 2. PER-ACCOUNT ENGAGEMENT RANKING

| Rank | Account | Followers | Avg Eng Rate | Median Eng Rate | Best Tweet Eng Rate |
|------|---------|-----------|-------------|----------------|-------------------|
| 1    | ...     | ...       | ...         | ...            | ...               |

## 3. STRUCTURE PATTERNS

### Full Dataset vs Top 10%
| Metric | Full Dataset | Top 10% | Delta |
|--------|-------------|---------|-------|
| Avg chars | ... | ... | ... |
| Avg words | ... | ... | ... |
| % questions | ... | ... | ... |
| % with data/numbers | ... | ... | ... |
| % original (not reply/QT) | ... | ... | ... |
| % with media | ... | ... | ... |
| % thread starters | ... | ... | ... |

## 4. STYLE PATTERNS

### Em Dash Correlation
- Tweets WITH em dash: avg engagement rate = ...
- Tweets WITHOUT em dash: avg engagement rate = ...
- Verdict: [em dashes help / hurt / neutral]

### Other Style Metrics
| Metric | Full Dataset | Top 10% |
|--------|-------------|---------|
| % with emoji | ... | ... |
| % with profanity | ... | ... |
| % ending in period | ... | ... |
| % ending in question mark | ... | ... |
| % ending in no punctuation | ... | ... |
| % starting with a number | ... | ... |
| Avg sentences per tweet | ... | ... |

## 5. TONE WORDS (from top 50 tweets)

### Most common nouns: ...
### Most common verbs: ...
### Most common bigrams: ...
### Most common named entities: ...

## 6. TIER COMPARISON

| Tier | Avg Eng Rate | Best Account | Worst Account |
|------|-------------|-------------|--------------|
| Conviction + Data | ... | ... | ... |
| Depth + Nuance | ... | ... | ... |
| Irreverent / Deadpan | ... | ... | ... |
| High-Eng Hybrids | ... | ... | ... |

## 7. PBX VOICE LAWS v1 (Data Edition)

[Generate 8-10 concise, actionable rules based ONLY on the data above. Each rule includes the supporting stat. Format:]

**Rule 1:** [Rule text]. Top 10% average: [stat]. Example tweet: "[real tweet from dataset]"

**Rule 2:** ...

[Continue for all rules]

## 8. EXAMPLE TWEETS THAT NAIL THE BLEND

[Pick 5 real tweets from the dataset that best represent the Theo Von x Saylor x Lyn Alden voice blend. For each, explain in one sentence WHY it works.]
```

### File 3: Git commit
```bash
cd ~/protocol_pulse
git add data/tweet_study/
git commit -m "feat: twitter engagement study - voice blueprint data for tweet pipeline"
git push origin main
```

## RULES FOR THIS SESSION

- Save raw data FIRST, analysis SECOND. If the script crashes during analysis, the raw data is preserved.
- Do NOT hardcode the bearer token in any file. Read from environment variable only.
- All API calls go through a single `call_twitter_api()` function that handles auth, rate limiting, retries, and logging.
- If a single account fails mid-pull, log the error and continue with the next account. Do not abort the entire study.
- Print a progress line after each account completes: "[3/16] @saylor: 200 tweets pulled, avg eng rate: 0.0043"
- Total runtime estimate: ~15-20 minutes (rate limit delays dominate).
- When writing PBX Voice Laws in section 7, NEVER use em dashes. Practice what we preach.

## AFTER COMPLETION

Run this to confirm:
```bash
cat ~/protocol_pulse/data/tweet_study/TWEET_VOICE_STUDY.md | head -50
wc -l ~/protocol_pulse/data/tweet_study/raw_tweets.json
echo "Study complete"
```

Report the scp path so PBX can download the report:
```
scp ultron@192.168.1.152:~/protocol_pulse/data/tweet_study/TWEET_VOICE_STUDY.md ~/Downloads/
```
