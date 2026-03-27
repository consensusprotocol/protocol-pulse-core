# MASTER DATA SOURCE REPORT: Bitcoin Narrative Velocity
## Synthesized from Gemini + GPT-4o + Grok Audits

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across all three audits with consistent metadata. Highest confidence tier.

---

### SOURCE U-1: Reddit API / Pushshift

| Field | Value |
|---|---|
| **Primary URL** | `https://www.reddit.com/r/bitcoin/new.json` |
| **Pushshift URL** | `https://api.pushshift.io/reddit/search/submission/?subreddit=bitcoin` |
| **Auth** | OAuth2 for PRAW; None for raw JSON endpoint |
| **Rate Limit** | 60 req/min (authenticated PRAW); ~30 req/min (raw) |
| **Key Fields** | `title`, `selftext`, `score`, `num_comments`, `created_utc`, `upvote_ratio` |
| **Update Freq** | Real-time |
| **Subreddits** | r/Bitcoin, r/BitcoinMarkets, r/btc, r/CryptoCurrency |
| **Quality** | 8/10 |
| **Velocity Signal** | Comment velocity delta, score acceleration, crosspost spread rate |

**Critical Notes:**
- Pushshift availability is volatile as of 2024 — fallback to native Reddit API
- `created_utc` field is essential for time-series second derivative calculation
- `num_comments` growth rate over 1h/4h windows is stronger signal than raw count

---

### SOURCE U-2: Google Trends (pytrends)

| Field | Value |
|---|---|
| **URL** | `https://trends.google.com/trends/explore` (unofficial API via pytrends) |
| **Library** | `https://github.com/GeneralMills/pytrends` |
| **Auth** | None |
| **Rate Limit** | ~100-200 req/day before soft blocking; rotate IPs to extend |
| **Key Fields** | `interest_over_time`, `related_queries`, `related_topics`, `interest_by_region` |
| **Update Freq** | Daily (hourly for `now 1-d` timeframe parameter) |
| **Quality** | 9/10 |
| **Velocity Signal** | `related_queries` rising section captures emerging sub-narratives before mainstream adoption |

**Critical Notes:**
- `related_queries` "rising" field is the highest-value output — these are breakout terms with >5000% growth
- Hourly granularity available via `timeframe='now 1-d'` but degrades to daily beyond 7-day window
- Compare week-over-week interest delta for true velocity, not raw score

---

### SOURCE U-3: GitHub API (Bitcoin Core)

| Field | Value |
|---|---|
| **URL** | `https://api.github.com/repos/bitcoin/bitcoin/commits` |
| **Events URL** | `https://api.github.com/repos/bitcoin/bitcoin/events` |
| **Auth** | None for public (recommended: token for higher limits) |
| **Rate Limit** | 60 req/hr unauthenticated; 5,000 req/hr authenticated |
| **Key Fields** | `commit.message`, `commit.author.date`, `sha`, `html_url` |
| **Update Freq** | Real-time |
| **Quality** | 6/10 |
| **Velocity Signal** | BIP discussion velocity, issue open/close rate, PR comment surge |

**Critical Notes:**
- Also monitor `https://api.github.com/repos/bitcoin/bips` for protocol narrative shifts
- Low direct price signal but leading indicator for technical narrative cycles (Taproot, SegWit, etc.)
- Watch `IssuesEvent` and `PullRequestReviewCommentEvent` types in Events endpoint

---

### SOURCE U-4: Wikipedia Pageviews API

| Field | Value |
|---|---|
| **URL** | `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Bitcoin/daily/20240101/20241231` |
| **Auth** | None |
| **Rate Limit** | ~100 req/sec (formally documented) |
| **Key Fields** | `views`, `timestamp`, `article`, `granularity` |
| **Update Freq** | Daily |
| **Quality** | 7/10 |
| **Velocity Signal** | Pageview spike precedes mainstream media cycle by 12-24 hours |

**Critical Notes:**
- Also track adjacent articles: `Lightning_Network`, `Satoshi_Nakamoto`, `Bitcoin_ETF`
- Granularity options: `daily` or `monthly`; use `hourly` endpoint for intraday: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Bitcoin/hourly/`
- Cross-language spike (e.g., Japanese or Korean Wikipedia) signals regional narrative emergence

---

### SOURCE U-5: Nostr Public Relays

| Field | Value |
|---|---|
| **Relay URLs** | `wss://relay.damus.io`, `wss://relay.nostr.band`, `wss://nostr.wine`, `wss://nos.lol`, `wss://relay.snort.social` |
| **Auth** | None |
| **Rate Limit** | Relay-dependent; generally open; ~100 req/min per relay |
| **Key Fields** | `content`, `pubkey`, `created_at`, `tags` (filter on `#t` for hashtags) |
| **Update Freq** | Real-time (WebSocket stream) |
| **Quality** | 8/10 |
| **Velocity Signal** | Uncensored signal; Bitcoin-native audience; hashtag emergence speed |

**Critical Notes:**
- This is the highest signal-to-noise source for native Bitcoin community narrative — no algorithmic curation
- Filter `kinds: [1]` for text notes; `kinds: [6]` for reposts (velocity amplification signal)
- Use `nostr.band` search API: `https://api.nostr.band/v0/search/notes?q=bitcoin&limit=100` for REST fallback

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Agreed)

---

### SOURCE M-1: CoinDesk RSS

| Field | Value |
|---|---|
| **URL** | `https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml` |
| **Auth** | None |
| **Rate Limit** | None documented; respectful polling recommended (1 req/5min) |
| **Key Fields** | `title`, `description`, `pubDate`, `category`, `link` |
| **Update Freq** | Hourly |
| **Quality** | 8/10 |

---

### SOURCE M-2: CoinTelegraph RSS

| Field | Value |
|---|---|
| **URL** | `https://cointelegraph.com/rss` |
| **Auth** | None |
| **Rate Limit** | None documented |
| **Key Fields** | `title`, `description`, `pubDate`, `category` |
| **Update Freq** | Hourly |
| **Quality** | 7/10 |

---

### SOURCE M-3: Bitcoin Magazine RSS

| Field | Value |
|---|---|
| **URL** | `https://bitcoinmagazine.com/feed` |
| **Auth** | None |
| **Rate Limit** | None documented |
| **Key Fields** | `title`, `description`, `pubDate` |
| **Update Freq** | Hourly |
| **Quality** | 7/10 |

---

### SOURCE M-4: The Block RSS

| Field | Value |
|---|---|
| **URL** | `https://www.theblock.co/feed` |
| **Auth** | None |
| **Rate Limit** | None documented |
| **Key Fields** | `title`, `description`, `pubDate` |
| **Update Freq** | Hourly |
| **Quality** | 8/10 |

---

### SOURCE M-5: YouTube Data API v3

| Field | Value |
|---|---|
| **URL** | `https://www.googleapis.com/youtube/v3/search?part=snippet&q=bitcoin&type=video&order=date&key={API_KEY}` |
| **Auth** | API Key (free tier available via Google Cloud Console) |
| **Rate Limit** | 10,000 units/day free |
| **Key Fields** | `snippet.title`, `snippet.description`, `snippet.publishedAt`, `statistics.viewCount`, `statistics.commentCount` |
| **Update Freq** | Real-time |
| **Quality** | 7/10 |
| **Velocity Signal** | View count acceleration in first 2 hours post-publish; comment rate per hour |

---

### SOURCE M-6: Hacker News API

| Field | Value |
|---|---|
| **URL** | `https://hacker-news.firebaseio.com/v0/newstories.json` |
| **Item URL** | `https://hacker-news.firebaseio.com/v0/item/{id}.json` |
| **Auth** | None |
| **Rate Limit** | None documented (Firebase backend; very generous) |
| **Key Fields** | `title`, `score`, `time`, `descendants` (comment count), `url` |
| **Update Freq** | Real-time |
| **Quality** | 7/10 |
| **Velocity Signal** | Score velocity in first 30 minutes; technical Bitcoin narratives reach HN before mainstream media |

---

## SECTION 3: UNIQUE FINDINGS BY MODEL

What each model surfaced that the others completely missed:

---

### GEMINI UNIQUE CONTRIBUTIONS

**1. Second Derivative Framework (Conceptual)**
- Explicitly defined the mathematical basis: measuring `d²x/dt²` not `dx/dt`
- No other model framed narrative velocity as acceleration vs. velocity — critical distinction
- Operationalizable: calculate rolling 1h and 4h rate-of-change, then delta between them

**2. Nostr `kinds: [6]` Repost Tracking**
- Specifically identified repost event type as amplification signal
- Others mentioned Nostr but missed the event-type filter for spread measurement

**3. Pytrends `related_queries` Rising Section**
- Explicitly called out the "rising" subcategory as the highest-value field
- This captures sub-narratives (e.g., "bitcoin etf approval date") before they become primary search terms

**4. Multi-Relay Nostr Architecture**
- Listed 5 specific relay URLs vs. other models listing 1-2
- Correctly noted relay aggregation is necessary since no single relay has full network coverage

---

### GPT-4o UNIQUE CONTRIBUTIONS

**1. YouTube Data API with Statistical Detail**
- Most detailed YouTube implementation including `statistics.viewCount` and comment velocity
- Unique framing: view acceleration in first 2 hours as leading narrative indicator
- Others mentioned YouTube abstractly; GPT-4o provided the exact API endpoint structure

**2. Hacker News as Technical Leading Indicator**
- Correctly identified HN as a signal that precedes mainstream coverage for technical Bitcoin narratives
- Specific Firebase endpoint structure provided

**3. OAuth2 Specificity for Reddit**
- Most precise on authentication requirements and the OAuth2 flow specifically
- Noted the `User-Agent` header requirement for raw endpoint access without auth

---

### GROK UNIQUE CONTRIBUTIONS

**1. Pushshift Exact Parameterized URL**
- Most specific Pushshift implementation: `?subreddit=bitcoin&size=100&sort=desc&sort_type=created_utc`
- The `sort_type=created_utc` parameter is critical for time-series ordering — others omitted this

**2. IP Rotation for Google Trends**
- Only model to note that pytrends gets soft-blocked and requires IP rotation to extend daily limits
- Practical operational detail other models missed

**3. Multi-Subreddit Targeting**
- Explicitly listed r/Bitcoin, r/BitcoinMarkets, r/btc, r/CryptoCurrency as the combined monitoring set
- Others focused on single subreddit

**4. nostr.band REST Fallback**
- `https://api.nostr.band/v0/search/notes?q=bitcoin&limit=100`
- Critical operational detail: REST fallback when WebSocket implementation is not available

**5. Cross-Language Wikipedia Monitoring**
- Japanese and Korean Wikipedia spike as regional narrative emergence signal
- No other model identified this cross-lingual velocity indicator

---

## SECTION 4: PRIORITY RANKING

---

### P0 — CRITICAL (Deploy Immediately, Highest Velocity Signal)

| # | Source | Rationale |
|---|---|---|
| 1 | **Nostr Relays** | Native Bitcoin community, zero curation, real-time, repost velocity measurable |
| 2 | **Reddit (r/Bitcoin + r/BitcoinMarkets)** | Highest volume Bitcoin discussion, comment velocity is leading indicator |
| 3 | **Google Trends (pytrends — related_queries rising)** | Sub-narrative detection 24-72h before mainstream; only source measuring search acceleration |
| 4 | **RSS Feed Aggregation (CoinDesk + CoinTelegraph + TheBlock + BitcoinMagazine)** | Combined publish rate is narrative institutionalization signal; free, no auth |

---

### P1 — HIGH VALUE (Deploy in Phase 2)

| # | Source | Rationale |
|---|---|---|
| 5 | **Wikipedia Pageviews (hourly)** | Reliable mainstream attention proxy; cross-language variant adds regional signal |
| 6 | **Hacker News API** | Technical narrative leading indicator; free, no auth, real-time |
| 7 | **YouTube Data API** | View acceleration on Bitcoin content predicts 48h narrative spread; requires free API key |
| 8 | **Google Trends (interest_over_time hourly)** | Complements related_queries; provides macro narrative intensity baseline |

---

### P2 — SUPPLEMENTARY (Deploy if P0/P1 Insufficient)

| # | Source | Rationale |
|---|---|---|
| 9 | **GitHub API (Bitcoin Core + BIPs)** | Low frequency signal; valuable only for technical upgrade narratives |
| 10 | **Bitcointalk Forum Scrape** | `https://bitcointalk.org/index.php?action=recent` — No API, requires scraping; OG community but declining volume |
| 11 | **Telegram Public Channels** | Via `https://t.me/s/{channel}` public preview scrape — high signal but fragile |
| 12 | **LinkedIn (Manual)** | No free API; institutional Bitcoin narrative adoption visible here before price action |

---

## SECTION 5: PRIMARY FREE DATA FETCH — No API Key Required

```python
"""
Bitcoin Narrative Velocity Collector
All sources require zero API keys
Measures d²x/dt² (acceleration of narrative prevalence)
"""

import asyncio
import json
import time
import requests
import feedparser
import websockets
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from pytrends.request import TrendReq


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BITCOIN_KEYWORDS = ["bitcoin", "btc", "sats", "satoshi", "lightning network", "bitcoin etf"]
RSS_FEEDS = {
    "coindesk":         "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "cointelegraph":    "https://cointelegraph.com/rss",
    "bitcoin_magazine": "https://bitcoinmagazine.com/feed",
    "theblock":         "https://www.theblock.co/feed",
}
NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "w