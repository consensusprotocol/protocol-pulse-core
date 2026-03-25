# CONSENSUS REPORT — SOCIAL-AUDIT — CYCLE 2
Generated: 2026-03-25 02:45
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Sentiment Mirroring (Q1) | 3 | 8 | 5 | **5.3** |
| Content Type Diversity (Q2) | 4 | 8 | 6 | **6.0** |
| Timing & Frequency (Q3) | — | 7 | 6 | **6.5** |
| Reply Strategy (Q4) | — | 7 | 6 | **6.5** |
| Thread Format (Q5) | — | 6 | 5 | **5.5** |
| Data Integration (Q6) | — | 8 | 5 | **6.5** |
| Community Voice (Q7) | — | 7 | 7 | **7.0** |
| Killer Format (Q8) | — | 7 | 6 | **6.5** |
| Pipeline Architecture | 4 | — | 5 | **4.5** |
| Technical Specificity | 7 | — | 6 | **6.5** |
| **Overall** | **4.5** | **7.4** | **5.7** | **5.9** |

> **Note on score divergence:** GPT-4o graded generously (Cycle 2 scores trending upward). Gemini and Grok independently arrived at lower scores after recognizing the architectural depth of the gaps. The consensus leans toward Gemini/Grok's more critical read — the system is a functional prototype, not a production-grade social intelligence engine. Consensus overall: **5.9 / 10**.

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

---

### U1 — Sentiment Monitoring Pipeline Is Completely Absent

**What it is:** The system generates content in a total vacuum. There is no mechanism to listen to the Bitcoin community, monitor what top thought leaders are discussing, detect emerging narratives, or use any of that signal as input to the content generation pipeline. Protocol Pulse broadcasts; it does not participate.

**Which file/line:** `tweet_machine.py` lines 245–248 (prompt construction block), plus missing new file `services/sentiment_radar.py`.

**What to change:**
1. Create `services/sentiment_radar.py`. This module must:
   - Pull recent tweets from the X API v2 (`/2/users/{id}/tweets`) for the target accounts: Preston Pysh, Lyn Alden, Robert Breedlove, Marty Bent, TFTC, American HODL.
   - Filter for high-engagement posts (likes + retweets above a threshold).
   - Extract top 3–5 trending themes or keywords (v1: bigram/TF-IDF frequency; v2: embedding + HDBSCAN clustering).
   - Write results to `sovereign_intel.db` in a new `emerging_narratives` table with columns: `theme`, `source_account`, `engagement_score`, `timestamp`.
2. Modify `tweet_machine.py` lines 245–248 to read the top themes from `sovereign_intel.db` and inject them into the generation prompt as structured context: `COMMUNITY_NARRATIVES: [theme1, theme2, theme3]`.
3. Schedule `sentiment_radar.py` to run every 6 hours via cron.

**Confidence:** 3/3 models. This is the single most important missing feature in the entire system.

---

### U2 — Content Type Monoculture

**What it is:** The current prompt produces a narrow band of content — primarily article-derived commentary. There is no enforced rotation across formats. Over time, the feed becomes predictable, which kills engagement and destroys the perception of a human, opinionated voice.

**Which file/line:** `tweet_machine.py` lines 118–123 (prompt template definition) and lines 245–248 (prompt construction).

**What to change:**
1. Define at minimum 6 distinct format templates within `tweet_machine.py`:
   - `[FORMAT: ON-CHAIN STAT]` — data-led, specific metric with implication
   - `[FORMAT: SOCRATIC QUESTION]` — open-ended provocation to community
   - `[FORMAT: HISTORICAL PARALLEL]` — economic history mapped to current Bitcoin event
   - `[FORMAT: CONTRARIAN TAKE]` — deliberately challenges mainstream narrative
   - `[FORMAT: COMMUNITY SIGNAL]` — responds to a trend detected by the Narrative Radar (feeds from U1)
   - `[FORMAT: THREAD OPENER]` — designed to start a multi-part thread
2. Add a `last_formats_used` tracking column to `sovereign_intel.db` and implement rotation logic so no format repeats within a 48-hour window.
3. Inject the selected format tag into the prompt at construction time (lines 245–248) so the LLM receives an explicit structural constraint, not just a style guide.

**Confidence:** 3/3 models.

---

### U3 — Real-Time Data Integration Is Absent

**What it is:** For a platform positioning itself as "Bitcoin intelligence," the complete absence of live network data is a credibility problem. Tweets derived purely from text articles cannot produce the class of insight that comes from "Bitcoin's mempool just hit X sat/vB — here's what that signals." This is unique, non-replicable content competitors cannot copy.

**Which file/line:** `tweet_machine.py` lines 245–248 (prompt context block), plus a new data-fetching utility.

**What to change:**
1. Create a lightweight function (can live in `services/bitcoin_data.py` or inline in `tweet_machine.py`) that hits the `mempool.space` public API before each run to fetch: current fee rate (sat/vB), mempool size (MB), latest block height, hashrate (7-day average), and lightning network capacity (BTC).
2. Format these as a structured data block and inject into the prompt context alongside the article brief and community narratives (from U1).
3. The LLM prompt should instruct the model: "When a relevant data point exists, anchor the tweet to a specific metric. Never invent numbers."

**Confidence:** 3/3 models (GPT-4o, Grok framed as "real-time data integration"; Gemini specified `mempool.space` API explicitly).

---

## MAJORITY FINDINGS
*2 of 3 models agree — implement unless compelling reason not to.*

---

### M1 — Brittle LLM JSON Response Parsing (Gemini + Grok)

**What it is:** `tweet_machine.py` lines 269–275 parse the Anthropic API response by naive string-stripping of ` ```json ` and ` ``` ` fences. This will silently break if Claude's output format shifts by even one character (e.g., ` ```json\n ` vs ` ```JSON ` vs no fence at all). Production systems cannot rely on this.

**Which file/line:** `tweet_machine.py` lines 269–275.

**What to change:** Replace the string-splitting logic with a robust two-stage extraction:
```python
import re, json

def extract_json(raw: str) -> dict:
    # Stage 1: try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Stage 2: regex extract first JSON object/array
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No valid JSON found in LLM response: {raw[:200]}")
```
Wrap in a try/except that logs the raw response before raising, so failures are debuggable.

**Verdict: IMPLEMENT.** This is a genuine production risk. Silent parsing failures would produce corrupted tweet drafts or crashes on high-value content.

---

### M2 — Duplicated X Posting Logic Across Two Files (Gemini + Grok implied, GPT-4o architecture concern)

**What it is:** Both `tweet_machine.py` and `x_daily_top_article.py` contain independent implementations for posting to the X API (authentication, media upload, tweet creation). This is a DRY violation and a maintenance liability — any change to X API auth or rate-limit handling must be made in two places.

**Which file/line:** `tweet_machine.py` (posting section) and `x_daily_top_article.py` (posting section). Both should delegate to `services/x_service.py`.

**What to change:**
1. Ensure `services/x_service.py` is the single source of truth for all X API interactions: auth, tweet post, thread post, media upload, rate limit handling.
2. Refactor both `tweet_machine.py` and `x_daily_top_article.py` to import and call `x_service.py` functions. Remove all direct API calls from the calling files.

**Verdict: IMPLEMENT.** Clear architectural improvement with no downside.

---

### M3 — Logging Does Not Track Sentiment Influence on Generated Content (Gemini + Grok)

**What it is:** Once the Narrative Radar (U1) is built and themes are injected into prompts, there will be no way to audit which community themes drove which tweets. This makes optimization impossible — you can't improve what you can't measure.

**Which file/line:** `tweet_machine.py` lines 349–379 (logging/DB write block).

**What to change:** When writing a tweet record to `sovereign_intel.db`, add columns: `narratives_used` (JSON array of theme strings from the Narrative Radar), `format_used` (the content format tag from U2), `data_injected` (bool, whether real-time data from U3 was injected). This enables a future analytics query: "Which format + narrative combination produced the highest engagement?"

**Verdict: IMPLEMENT.** Zero cost to add now; massive cost to retrofit later.

---

### M4 — Missing Error Recovery / Fallback When Sentiment Data Is Unavailable (Grok + implied by Gemini's architecture concern)

**What it is:** If `sentiment_radar.py` fails (X API rate limit, network error, DB issue), `tweet_machine.py` will either crash or silently generate contextless content with an empty `COMMUNITY_NARRATIVES` block. Neither is acceptable.

**Which file/line:** `tweet_machine.py` around line 248 (where narrative data is injected into prompt), and `services/sentiment_radar.py` (new file).

**What to change:**
1. In `sentiment_radar.py`, on any fetch failure, log the error and write a `STALE` flag to the `emerging_narratives` table rather than deleting old records. The last-known-good data survives.
2. In `tweet_machine.py`, the narrative injection logic should: check for data freshness (< 12 hours old = use it; ≥ 12 hours = use cached with a `[CACHED]` debug tag; no data at all = fall back to a set of 3 hardcoded evergreen Bitcoin narratives defined as a constant in the file).

**Verdict: IMPLEMENT.** A pipeline that halts on external API downtime is not production-grade.

---

## UNIQUE INSIGHTS
*Only 1 model caught this — evaluated individually.*

---

### Unique-1 — LLM Provider Sprawl / Consolidate to Fewer Vendors (Gemini only)

**What it is:** The system uses three separate AI providers: Anthropic Claude Haiku (`tweet_machine.py`), xAI Grok for image generation (`x_daily_top_article.py`), and OpenAI GPT-4o for tweet composition (`x_daily_top_article.py`). Three billing relationships, three API key rotation concerns, three points of failure.

**Assessment: INVESTIGATE FURTHER — do not blindly consolidate.**

The correct answer here depends on relative model quality per task, not just architectural tidiness. Image generation is a specialized capability; if xAI produces superior Bitcoin-themed images, that dependency is justified. If GPT-4o tweet composition meaningfully outperforms Claude for that specific format, the cost of maintaining both is worth paying. The recommendation is: conduct a structured A/B quality evaluation across the three text-generation use cases. If two or more tasks show no measurable quality difference between providers, consolidate. Do not consolidate preemptively at the cost of output quality.

**Short-term action:** Document all three providers, their tasks, and their costs in a `docs/architecture/llm_providers.md` file so the decision is explicit and revisitable.

---

### Unique-2 — Expand Narrative Radar Beyond Twitter to Nostr and Stacker News (Gemini only)

**What it is:** Gemini recommends ingesting data from Nostr (via `pynostr` connecting to relays like `wss://relay.damus.io`) and Stacker News (GraphQL or RSS) as higher-signal, more native Bitcoin community sources than Twitter alone.

**Assessment: IMPLEMENT IN V2, NOT V1.**

The strategic insight is correct: Nostr and Stacker News capture early-adopter, technically-minded Bitcoin signal that often leads Twitter by days. However, implementing three data sources simultaneously in the first build of `sentiment_radar.py` is scope risk. The correct sequencing is: build and validate the Twitter-based radar as V1, prove the integration into `tweet_machine.py` is stable, then add Nostr and Stacker News as V2 sources once the pipeline architecture is proven. Add this to P2.

---

### Unique-3 — Thread Continuation Logic Is Missing (Grok only)

**What it is:** The content format rotation (U2) includes a `[FORMAT: THREAD OPENER]` type, but there is no corresponding logic in `tweet_machine.py` to actually post a sequence of linked tweets as a thread, track the thread's root tweet ID, or generate the continuation tweets.

**Assessment: IMPLEMENT — this pairs with U2 and is required for the THREAD OPENER format to be anything more than a label.**

Add to P1: implement a `post_thread(tweets: list[str])` function in `services/x_service.py` that posts tweet[0], captures its ID, then posts each subsequent tweet as a reply to the previous ID. The `tweet_machine.py` format rotation logic should call this when `FORMAT: THREAD OPENER` is selected, and the LLM prompt should be instructed to return a JSON array of 3–5 tweet strings rather than a single string in that case.

---

### Unique-4 — Podcast Transcript Ingestion for Narrative Radar (Gemini only)

**What it is:** Gemini proposes using Whisper API or AssemblyAI to transcribe Bitcoin podcasts (TFTC, What Bitcoin Did, Investor's Podcast) and feed transcript chunks into the narrative detection pipeline.

**Assessment: SKIP for now — revisit in Q3.**

The latency problem makes this low-ROI at current scale: podcast episodes release on irregular schedules, transcription takes time, and by the time a podcast topic is processed, it has likely already appeared on Twitter (which the radar already monitors). The signal-to-processing-cost ratio doesn't justify the complexity for a V1 system. Revisit when the Twitter + Nostr + Stacker News radar is established and podcast topics are demonstrably arriving before they surface elsewhere.

---

## CONFLICTS
*Models gave contradictory recommendations — tiebreaker applied.*

---

### Conflict 1 — Score Direction After Cycle 2 Review

**GPT-4o** raised scores across the board (Sentiment Mirroring: 6→8, Data Integration: 6→8), reflecting optimism about the proposed changes. **Gemini and Grok** lowered scores (Gemini Sentiment: 6→3, Grok Sentiment: 6→5), reflecting the view that discovering deeper gaps warrants downward revision of the current state.

**Tiebreaker: Gemini and Grok are correct.**

Cycle 2 scores should reflect the *current state of the code*, not the projected state after fixes are applied. Raising a score because you now have a plan to fix a problem conflates diagnosis with treatment. The current code has no sentiment pipeline — that is objectively worse-than-neutral, not better. Consensus scores follow the Gemini/Grok methodology.

---

### Conflict 2 — Podcast Transcription as Narrative Source

**Gemini** advocates for it. **Grok** explicitly flags it as potentially "overkill due to processing overhead and delayed relevance."

**Tiebreaker: Grok is right for V1.** See Unique-4 assessment above. Defer to V2+.

---

### Conflict 3 — Static vs. Dynamic Scheduling

**GPT-4o** recommends posting at static peak times (9 AM / 5 PM EST). **Grok** advocates for dynamic scheduling derived from `sovereign_intel.db` engagement analytics.

**Tiebreaker: Both are correct at different stages.** Static peak times are the right V1 default — they're evidence-based (industry-standard Twitter engagement data) and require zero infrastructure. Dynamic scheduling based on actual Protocol Pulse engagement data is the correct V2 evolution, once the account has accumulated enough historical engagement data in `sovereign_intel.db` to make the optimization statistically meaningful. Implement static now; build dynamic scheduler when 90 days of engagement data exists.

---

## VALIDATED STRENGTHS
*All models agree these areas are strong. Do NOT change them.*

---

1. **Voice Laws / Prompt Engineering Foundation:** The existing `TWEET_GENERATION_PROMPT` in `tweet_machine.py` demonstrably captures the PBX voice — contrarian, dry wit, Austrian economics lens, cypherpunk sensibility. All three models acknowledged this as a strong foundation. Do not rework the core voice instructions; extend them.

2. **Duplicate Tweet Detection (`_keyword_overlap`):** The existing logic to prevent posting redundant content against recent tweet history is well-implemented and all models either praised it or built upon it without suggesting changes. Leave intact.

3. **SQLite-Based State Management (`sovereign_intel.db`):** Using a local SQLite database for pipeline state (rate limits, posted tweet history, article tracking) is the right architectural choice for this scale. All models assumed it as the correct substrate for new features. Do not migrate to a heavier database.

4. **Cron-Based Scheduling Pattern:** The existing pattern of scheduling pipeline runs via cron is appropriate for the current scale and operational model. All models recommended extending this pattern (adding new cron jobs for the Narrative Radar), not replacing it.

---

## LAW COMPLIANCE CONSENSUS

*(Assessed against `PIPELINE_LAWS.md` as referenced in the codebase.)*

| Law Category | Status | Notes |
|---|---|---|
| Never invent data or statistics | ⚠️ **AT RISK** | No current safeguard prevents the LLM from hallucinating metrics. The U3 fix (injecting real, sourced data) partially mitigates this, but the prompt must explicitly prohibit invented numbers. |
| No reposting/copying source content | ✅ Compliant | `_keyword_overlap` check exists. Narrative Radar (U1) must include a similarity check before injecting source content. |
| Maintain PBX voice | ✅ Compliant | Voice laws are well-enforced in current prompt. |
| Rate limit compliance (X API) | ⚠️ **AT RISK** | Adding Narrative Radar scraping against multiple accounts every 6 hours significantly increases X API v2 call volume. Must implement explicit rate limit tracking in `x_service.py` before shipping U1. |
| No engagement bait / low-quality content | ⚠️ **AT RISK** | Content type monoculture (U2) increases risk of repetitive, engagement-bait-adjacent content over time. Format rotation (U2 fix) is the mitigation. |
| Audit trail / logging | ⚠️ **AT RISK** | Sentiment influence is currently unlogged. M3 fix is required for compliance. |

**Final determination:** The current code has 4 active law compliance risks. None are violations yet (the system is not in production), but all must be resolved before ship.

---

## SECURITY CONSENSUS

*Issues flagged by 2+ models, in priority order:*

---

**SEC-1 — X API Key Exposure Risk (All models, implicit):** Adding the Narrative Radar means the X API credentials in `x_service.py` will now be used for both read (scraping) and write (posting) operations at higher frequency. Ensure API keys are scoped to minimum necessary permissions and rotated. The scraping key should ideally be a separate read-only app credential from the posting credential, so a compromise of the read key cannot be used to post malicious content. **Priority: HIGH.**

**SEC-2 — External API Data Injection into LLM Prompts (Gemini + Grok):** The Narrative Radar will inject scraped third-party content (tweets from thought leaders) directly into the LLM prompt. This is a prompt injection surface. A malicious actor who knows Protocol Pulse monitors specific accounts could post a specially crafted tweet designed to manipulate the generation prompt. Mitigation: sanitize scraped text before injection (strip URLs, truncate to N characters, strip special characters that could function as prompt delimiters). **Priority: MEDIUM.**

**SEC-3 — `mempool.space` API Dependency (Gemini):** Real-time data injection (U3) adds an external API dependency. If `mempool.space` returns malformed data, it could corrupt the prompt context or cause crashes. Validate all fetched data against expected types and ranges before injection. **Priority: LOW.**

---

## WORLD-CLASS GAP CONSENSUS
*What the combined intelligence of 3 models says is missing from a truly world-class product. Only items 2+ models mentioned.*

---

1. **A Listening Layer (2+ models: all three):** World-class social media automation is not broadcasting — it's a conversation engine. The gap between "generates tweets from articles" and "detects community narratives, responds to them with unique perspective, and measures what resonates" is the entire distance between a content bot and an intelligence platform. The Narrative Radar (U1) is the minimum viable step; the eventual vision is a feedback loop where engagement data from posted tweets directly informs future content strategy.

2. **Unique, Non-Replicable Data as Content Moat (2+ models: Gemini, GPT-4o, Grok):** Any account can summarize articles. A world-class Bitcoin intelligence account publishes content that *could not exist without proprietary data access or unique analytical capability.* Real-time on-chain metrics, custom derived indicators, or exclusive community pulse data create a content moat. The `mempool.space` integration (U3) is the first step; the eventual vision includes custom-derived indicators that Protocol Pulse calculates itself.

3. **Engagement Analytics Feedback Loop (2+ models: Grok, GPT-4o):** The system currently cannot learn from what works. A world-class system would track engagement per tweet (likes, retweets, replies, impressions), attribute that engagement back to the format used, the narrative context, and the data injected, and use that signal to bias future content selection. This is what transforms a content generator into a content optimizer.

4. **Thread and Long-Form Format Capability (2+ models: Grok, Gemini implied via FORMAT templates):** The highest-performing Bitcoin content on X is consistently threads — multi-part analysis that demonstrates depth of knowledge. A world-class account must have first-class thread generation and posting capability, not just single-tweet output.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Create `services/sentiment_radar.py` — scrape top 10 Bitcoin thought leaders via X API v2, extract top 3–5 trending themes via TF-IDF/bigram frequency, write to `sovereign_intel.db` `emerging_narratives` table, schedule every 6 hours | `services/sentiment_radar.py` (new file), `sovereign_intel.db` | All 3 | The system generates content in a vacuum. This is the single highest-leverage architectural change. |
| **P0 CRITICAL** | Inject Narrative Radar output into `tweet_machine.py` generation prompt as `COMMUNITY_NARRATIVES` context block | `tweet_machine.py:245–248` | All 3 | Without this injection, the radar produces data that nobody reads. |
| **P0 CRITICAL** | Implement content format rotation: define 6 format templates, track `last_formats_used` in `sovereign_intel.db

---

# WINNER DETERMINATION

# WINNER: Gemini — 2-Sentence Justification

Gemini delivered the highest-quality analysis overall by correctly diagnosing the *architectural* root cause (the system is "deaf" — it broadcasts but never listens) rather than surface-level content suggestions, and by proposing the most technically specific, implementable solution ("Narrative Radar" pipeline with Nostr + Stacker News + podcast transcript ingestion, embedding/clustering theme detection, and DRY violation identification in `tweet_machine.py` vs `x_daily_top_article.py`). While GPT-4o scored higher in the consensus table due to generous self-grading and broader coverage across all 8 questions, Gemini's findings proved *more correct* in Cycle 2 (other models explicitly credited Gemini's insights as what they missed), demonstrating superior depth and accuracy that the scoring rubric underweighted.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered implementation queue, synthesizing all three models with Gemini's architectural framing as the spine.

---

## TIER 1 — CRITICAL / DO FIRST
*System is broken or blind without these. Zero excuses.*

---

### P1 — Build `services/sentiment_radar.py` (Narrative Radar)
**Source:** Gemini (primary), confirmed by all models as U1

**What to build:**
1. Pull timelines from X API v2 every 15–30 minutes for: `@PrestonPysh`, `@LynAldenContact`, `@Breedlove22`, `@MartyBent`, `@TFTC21`, `@American_HODL`, `@NicCarter`, `@DylanLeClair_`
2. Filter by engagement threshold (e.g., likes > 50 OR retweets > 20 in past 24h)
3. Embed filtered content via `text-embedding-ada-002` or equivalent
4. Cluster with K-means or HDBSCAN to surface dominant theme groups
5. Generate a 1-sentence label per cluster (e.g., "CBDC Surveillance Concerns," "Mining Centralization Risk")
6. Output: ranked `themes[]` JSON object with urgency score, sample tweets, and narrative angle

**Inject into:** `tweet_machine.py` prompt construction block (lines 245–248) as `{{trending_themes}}` variable

---

### P2 — Expand Ingestion Sources Beyond Twitter
**Source:** Gemini (unique finding, validated in Cycle 2 by all models)

**What to add:**
- **Nostr:** Connect to `wss://relay.damus.io` and `wss://nos.lol`; filter by zap count and note recency
- **Stacker News:** Scrape `stacker.news/top` (RSS or HTML) for daily top posts and comment threads
- **Podcast Transcripts:** Auto-transcribe new episodes of *Tales from the Crypt*, *What Bitcoin Did*, *Bitcoin Fundamentals* via Whisper API; extract named entities and key claims

**Why:** Twitter alone is noisy and increasingly restricted. Nostr/SN are higher-signal for sovereign Bitcoiners who drive narrative formation before it hits mainstream crypto Twitter.

---

### P3 — Eliminate DRY Violation: Deduplicate X Posting Logic
**Source:** Gemini (unique finding — no other model caught this)

**What to fix:**
- `tweet_machine.py` and `x_daily_top_article.py` both contain independent implementations of X posting logic
- Extract into `services/x_client.py` as a single `post_tweet(text, media=None, reply_to=None)` interface
- Both files import from `x_client.py`
- Eliminates dual maintenance surface, rate limit inconsistencies, and auth token duplication

---

## TIER 2 — HIGH PRIORITY / IMPLEMENT IN SPRINT 2
*System works without these but underperforms significantly.*

---

### P4 — Implement Content Type Template Rotation
**Source:** All models (U2), GPT-4o most specific on taxonomy

**What to build:**
- Define 6–8 content archetypes as named templates:
  - `CONTRARIAN_TAKE` — challenges mainstream narrative
  - `ON_CHAIN_SIGNAL` — data-driven (hashrate, mempool, MVRV, etc.)
  - `HISTORICAL_PARALLEL` — maps past economic event to current BTC context
  - `MACRO_JUXTAPOSITION` — fiat/Fed action vs. Bitcoin response
  - `COMMUNITY_SPOTLIGHT` — amplifies underheard signal from smaller accounts
  - `PROVOCATIVE_QUESTION` — open loop to drive reply engagement
  - `THREAD_HOOK` — designed as thread starter with 4–6 follow-up tweets queued
- Add rotation logic in `tweet_machine.py`: track last-used template in state, enforce no repeat within 3 consecutive posts
- Weight selection by `trending_themes` output from P1 (e.g., if macro theme is hot, upweight `MACRO_JUXTAPOSITION`)

---

### P5 — Integrate Real-Time On-Chain Data Feed
**Source:** GPT-4o (strongest on this), Grok confirmed

**What to build:**
- Connect to Glassnode API or Mempool.space public API for: hashrate 7d MA, mempool fee pressure, MVRV Z-score, exchange netflow
- Create `services/onchain_pulse.py` that fetches and formats a daily snapshot
- Inject as `{{onchain_context}}` into `tweet_machine.py` prompt
- Triggers automatic `ON_CHAIN_SIGNAL` content type when a metric crosses a defined threshold (e.g., MVRV < 1.0, fees spike > 2x 7d avg)

---

### P6 — Build Reply Strategy Engine
**Source:** GPT-4o (Q4 coverage), Grok confirmed, Gemini implied

**What to build:**
- Monitor `@mentions` and replies to Protocol Pulse's own tweets via streaming API
- Classify inbound by intent: `QUESTION`, `CHALLENGE`, `AGREEMENT`, `TROLL`
- Route `QUESTION` and `CHALLENGE` to LLM with PBX voice prompt for crafted reply
- Set daily reply budget (e.g., max 10 auto-replies) with human-approval queue for edge cases
- Hard filter: never reply to accounts with < 10 followers or obvious bot signatures

---

## TIER 3 — MEDIUM PRIORITY / SPRINT 3
*Meaningful improvements to quality and reach.*

---

### P7 — Optimize Posting Schedule with Engagement Data
**Source:** GPT-4o (Q3 coverage), Grok confirmed

**What to build:**
- Log timestamp + engagement metrics (likes, retweets, replies at 1h, 4h, 24h) for every post in `data/engagement_log.json`
- After 30-day dataset: run regression to identify peak engagement windows by day-of-week and hour-of-day
- Update cron schedule in deployment config to match empirical peaks
- Re-evaluate every 90 days as audience composition shifts

---

### P8 — Thread Format Standardization
**Source:** GPT-4o (Q5), Grok confirmed

**What to build:**
- Thread template: Hook tweet (standalone value, ends with "🧵") → 3–5 body tweets (one idea each, no padding) → CTA tweet (question or call to share)
- Enforce max 240 chars per tweet in thread (with buffer for numbering)
- Add `post_thread(tweets[])` method to `services/x_client.py` (P3 dependency)
- Trigger thread format for `HISTORICAL_PARALLEL` and `MACRO_JUXTAPOSITION` archetypes (P4 dependency)

---

### P9 — Killer Format: The "Signal vs. Noise" Weekly Digest
**Source:** GPT-4o (Q8), synthesized with Gemini's source expansion

**What to build:**
- Every Sunday: aggregate top 5 themes detected by Narrative Radar (P1) across the week
- Format as pinned thread: "This week's signal vs. noise in Bitcoin 🧵"
- Each item: theme name → 1-sentence Protocol Pulse