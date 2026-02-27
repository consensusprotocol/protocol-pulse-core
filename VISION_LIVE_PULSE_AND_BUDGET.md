# Protocol Pulse — Live Pulse Vision & $500/mo Budget

**Purpose:** Clever AI-drafted Space tweets (no templates), $500/mo budget allocation, and the 24/7 live-stream avatar as the “heartbeat of Bitcoin.”

**See IMPLEMENTATION_PLAN_AVATAR_NEWS_SPACES.md** for: Avatar + partner YouTube; Spaces = wait for transcript then tweet (tag + quote); breaking-news dual-image; get-started phases.

---

## 1. Spaces Tweets: Clever, Trust-Building, Conversion-Focused

You want tweets that **reflect what’s actually being discussed**, are **accurate on topics**, and are **written to convert** (drive people into the Space). No generic templates.

### 1.1 What We Can Use Today (No Extra Cost)

The **X Spaces API does not provide live audio or transcript**. It gives **metadata** only:

- Space **title**
- **Hosts** and **speakers** (usernames/display names)
- **Participant count** (listeners)
- **State** (live/scheduled)
- **Started_at** (and optional topics if the host set them)

**AI drafting from this:** We send the model a structured prompt with title, host names, speaker names, listener count, and (if we add it) a short “topic” hint. The model produces **one conversion-focused tweet** that:

- Hooks from the title and who’s speaking (so it’s accurate to what we know).
- Feels specific, not generic (“[Host] just opened the floor on [topic from title] — [N] in the room. This is the one.”).
- Stays under 280 chars and includes the Space link.

**Trust:** The tweet only claims what we know (title, hosts, listener count). We avoid inventing “what’s being discussed” unless we add transcript later.

**Cost:** Same as before: **~$200/mo X API** + **~$15–40/mo** for AI draft (e.g. GPT-4o or Claude) per Space tweet, depending on volume. Well within budget.

### 1.2 Upgrading to “Read the Room” (Optional Later)

To make tweets reflect **actual discussion** (topics, hot takes, sentiment):

- **Option A — Third-party transcript:** e.g. [XSPACESTREAM](https://xspacestream.com/) (~$7–65/mo) for real-time transcription; we’d need to wire their output (or similar) into our pipeline and pass “last 2 min summary” or “top topics” into the AI prompt. Adds cost but gives true “what’s being discussed.”
- **Option B — Self-hosted:** When your **2× RTX 490s** are in place, a separate service could capture Space audio (e.g. via a browser automation or approved capture method), run **Whisper** (or similar) locally for transcription, then feed “recent transcript summary” into the same AI tweet-draft prompt. No ongoing transcript API cost; one-time dev + GPU power.

**Recommendation:** Ship **Phase 1** with metadata-only AI drafting (clever, accurate to title/hosts/count). Add transcript (A or B) in a later phase when you want “they’re literally discussing X right now” in the tweet.

---

## 2. $500/mo Budget Allocation

| Line item | Monthly cost | Notes |
|-----------|---------------|--------|
| **X API Basic** | **$200** | Spaces search + tweet/RT; fixed. |
| **AI for Space tweet drafting** | **$20–50** | GPT-4o or Claude per Space; volume-dependent. |
| **AI for 24/7 avatar script** (see below) | **$80–150** | Script generation every 5–15 min; use cheaper models where possible. |
| **Avatar / streaming (Phase 1)** | **$0–100** | Heygen/D-ID trial or minimal usage; or $0 if you go straight to local GPU. |
| **Buffer / misc APIs** | **$20–70** | AssemblyAI, extra OpenAI, etc. |
| **Total** | **~$320–500** | Keeps you at or under $500; GPU power (2× 490) is one-time + electricity, not this pool. |

**Priorities:**  
- Lock in **X $200** and **AI drafting** for Spaces first.  
- Use the rest for **avatar pipeline** (script + optional cloud avatar until 490s take over rendering).

---

## 3. 24/7 Live Stream Avatar — “Pulse of Bitcoin”

You want a **24/7 live-stream avatar** that:

- Breaks down **what’s happening in real time** (markets, narratives, Spaces).
- Comments on **sentiment** (e.g. from your existing sentiment pipeline).
- Surfaces **top thought-leader X tweets and Nostr statements**.
- Feels like a **literal pulse / heartbeat of Bitcoin** — rare, always-on, trustworthy.

**→ Dedicated “Stage” (Cinema Mode) page:** When you build the viewer experience, use a custom landing page (not just a YouTube embed) with live transcript, sentiment “heartbeat” line, and “Watch Source” for partners. See **FUTURE_TASKS.md** for the full spec.

### 3.1 Data You Already Have (or Can Wire)

| Source | What it gives | Where in stack |
|--------|----------------|----------------|
| **Sentiment** | State (e.g. FOMO, FEAR), score, velocity | `SentimentSnapshot`, `PulseEvent`, sentiment dashboard |
| **Top X / Nostr** | Thought-leader posts, engagement, content | `CollectedSignal`, verified signals API, Grok/social feedback |
| **Spaces** | Live rooms: title, hosts, listener count | X Spaces API (once implemented) |
| **Whale / mempool** | Large moves, fee spikes | Whale watcher, Mempool.space APIs |
| **Prices / macro** | BTC and context | `price_service`, external feeds |

So the “heartbeat” is: **sentiment + top voices (X + Nostr) + live Spaces + on-chain/market cues**.

### 3.2 High-Level Pipeline

```
[Sentiment + Signals + Spaces metadata + Whale/Mempool] 
        → aggregated “Pulse” context (e.g. every 5–15 min)
        → AI script: “What’s happening now + top takes + sentiment”
        → Avatar speaks script (voice + face)
        → 24/7 stream (e.g. YouTube Live / Twitch / custom)
```

- **Script:** One model call per cycle (e.g. every 10 min). Input: structured summary of sentiment, 3–5 top X/Nostr quotes or headlines, live Spaces (title + hosts + count), and optional whale/mempool one-liner. Output: 60–90 sec script, punchy and accurate. **Cost:** ~$80–150/mo if you use GPT-4o/Claude; less if you use a smaller model for first draft.
- **Avatar:** Either (1) **cloud** (Heygen, D-ID, etc.) for speed to ship, or (2) **local on 2× 490s** (Wav2Lip + face model, or similar) so avatar cost goes to $0 and you get full control. Your GPUs are ideal for the latter.
- **Stream:** OBS or a small service that plays the latest avatar clip on a loop and overlays “LIVE” + ticker; or true “new segment every N minutes” so it feels live.

### 3.3 Where the 2× RTX 490s Fit

- **Video/avatar rendering:** Run the avatar (lip-sync, expression) **on your machine** so you don’t pay per minute to Heygen/D-ID. Both cards can run inference in parallel (e.g. one rendering the next clip while the other finishes the current).
- **Transcription (optional):** If you add self-hosted Space transcription, one GPU can run Whisper while the other does avatar or other video tasks.
- **AI inference:** You could run a local LLM for script drafting to cut API cost; 490s can run reasonably large models. Optional; cloud LLM is simpler to start.

### 3.4 Phased Rollout

| Phase | What | Budget impact |
|-------|------|----------------|
| **1** | Spaces: X API + AI-drafted tweets (metadata-only), no templates | ~$200 + ~$20–50 |
| **2** | “Pulse” script: aggregate sentiment + CollectedSignal + Spaces metadata → AI script every 10 min (no avatar yet; e.g. post script as text or TTS clip) | +~$80–150 AI |
| **3** | Avatar: Heygen/D-ID or local (2× 490) → 24/7 stream | +$0–100 or $0 if local |
| **4** | (Optional) Space transcript → even better Space tweets + “they’re discussing X right now” in avatar | +$0 (self-host) or +$7–65 (third-party) |

This keeps you **under $500/mo** while moving toward the full “live pulse” experience and using the 490s to avoid ongoing avatar/transcript fees.

---

## 4. Implementation Checklist (Spaces Tweets, Phase 1)

- [ ] Add X API credentials to `core/.env` (all five Twitter vars).
- [ ] Implement Spaces client in `x_service.py`: search live Spaces, lookup by ID, parse title/hosts/speakers/count.
- [ ] Add `LiveSpace` model and scheduler job: poll every 10–15 min, store/update Spaces, detect threshold crosses.
- [ ] **AI tweet draft:** For each Space that crosses a threshold, call OpenAI/Anthropic with prompt: “Given this live Space: title=[], hosts=[], speakers=[], listeners=N. Write one conversion-focused tweet (max 280 chars) that’s accurate and hooks people. Include space link: [url]. No hashtags.”
- [ ] Post tweet + optional RT from `XService`; mark `tweeted_at` / `tweet_id` so we don’t double-tweet.
- [ ] (Later) Optional: add transcript input (third-party or self-hosted) to the same prompt for “read the room” tweets.

---

## 5. Summary

- **Spaces tweets:** Will be **AI-drafted and conversion-focused**, using **all metadata we have** (title, hosts, speakers, count). Accurate and trust-building within what the API gives; “read the room” can be added later via transcript.
- **Budget:** **$500/mo** is enough for X ($200), AI for Space tweets ($20–50), and AI + light cloud avatar for the 24/7 Pulse ($80–150 + $0–100). Buffer stays in range.
- **24/7 avatar:** Feasible with your existing sentiment + CollectedSignal + Spaces (and optional whale/mempool). Script from aggregated context → avatar (cloud then local) → stream. **2× 490s** are the right move to bring avatar (and optionally transcription) in-house and keep recurring cost low.

If you want, next step can be concrete prompt shape for the Space tweet (and a minimal “Pulse script” prompt) so you can drop them into your AI service and scheduler.
