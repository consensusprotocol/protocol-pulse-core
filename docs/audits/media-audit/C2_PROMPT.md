# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: media-audit
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### Review Task: Bitcoin Media Command Center Architecture (8 Design Questions)

I have thoroughly reviewed the provided code and documentation for the Bitcoin Media Command Center project. Below are my detailed recommendations for each of the 8 design questions, along with cost/performance impacts, implementation complexity, key risks, and mitigations. I conclude with a final verdict on prioritization and key design decisions.

---

### Q1 — ARCHITECTURE
**Detailed Recommendation:**
- **Backend Architecture:** Implement a hybrid architecture using asynchronous background jobs with `Celery` and `Redis` as the message broker and cache. Flask workers should not handle feed aggregation directly. Instead, offload RSS, YouTube, and KOL feed fetching to Celery tasks running on separate workers. Use `aiohttp` for async HTTP requests to fetch feeds concurrently.
  - **Redis Caching:** Cache feed data in Redis with a TTL (Time To Live) to reduce database load and API calls. Store raw feed data (JSON) and processed content separately.
  - **SQLite Caching:** Persist processed feed data (episodes, videos, posts) in SQLite via SQLAlchemy for long-term storage and querying. Use indexes on `published_date`, `source_type`, and `signal_score` for fast retrieval.
  - **Async Fetching:** Use Python’s `asyncio` with `aiohttp` for non-blocking feed fetching within Celery tasks. This prevents blocking Flask’s event loop during feed updates.
- **Refresh Intervals:**
  - RSS Feeds (Podcasts): Every 15 minutes. Podcasts update infrequently, and this balances freshness with server load.
  - YouTube Channels: Every 1 hour. Video uploads are less frequent, and YouTube API quotas are a concern.
  - X/Nostr KOL Feeds: Every 5 minutes. These are high-signal, real-time sources requiring frequent updates.
- **Workflow:** A scheduled Celery Beat task triggers feed updates at the defined intervals. On completion, update Redis cache and SQLite database. Flask routes serve data from Redis (fast path) or SQLite (fallback) without triggering fetches.
- **Infrastructure:** Deploy Celery workers on the Ultron server (2x RTX 4090, 93GB RAM) to leverage its compute capacity. Ensure Redis is hosted on the same server for low-latency cache access.

**Estimated Cost/Performance Impact:**
- Cost: Minimal. Redis and Celery are open-source. YouTube API quotas may incur costs if exceeded (free tier: 10,000 units/day, ~$0.50 per 1,000 extra units). Assuming 7 channels x 24 fetches/day = 168 calls, well within free tier.
- Performance: High. Async fetching and caching reduce Flask worker load. Redis delivers sub-millisecond response times for cached data, supporting ~1000 concurrent users at peak.

**Implementation Complexity:** MEDIUM
- Requires setting up Celery, Redis, and Celery Beat. Configuration and debugging of async tasks add moderate complexity.

**Key Risks and Mitigations:**
- Risk: Feed fetching failures due to rate limits or downtime.
  - Mitigation: Implement exponential backoff retries in Celery tasks and fallback to cached data if fetch fails.
- Risk: Redis cache inconsistency with SQLite.
  - Mitigation: Use Redis as a read-through cache with a short TTL (e.g., 5 minutes for KOL feeds), forcing periodic SQLite sync.

---

### Q2 — D3 NETWORK GRAPH
**Detailed Recommendation:**
- **Visualization Design:** Use D3.js to create a force-directed graph where nodes represent Bitcoin voices/channels (e.g., Odell, Livera) and edges represent cross-references/mentions. Nodes are sized by influence (e.g., follower count or signal score) and colored by source type (e.g., red for X, purple for Nostr).
- **Detection of References:** Parse feed content (tweets, Nostr notes, video descriptions) for mentions using regex (e.g., `@handle`) and quote tweet patterns (e.g., URLs or “RT @”). Use a background Celery task to analyze content on ingest, updating a relationship table in SQLite (`VoiceReference` model: `source_id`, `target_id`, `mention_type`).
- **Data Structure:** Store graph data as an adjacency list in SQLite for persistence and as a JSON object in Redis for fast client-side retrieval. Format: `{nodes: [{id, name, size, color}], links: [{source, target, weight}]}`.
- **Animation of Node Pulses:** On new posts, emit a WebSocket event (via Flask-SocketIO) to clients with the updated node ID. Use D3 transitions to animate a pulse effect (e.g., temporary radius increase + glow) with `d3.transition().duration(1000).attr("r", size * 1.5).transition().attr("r", size)`.
- **D3 Force Simulation Config for ~50 Nodes:**
  ```javascript
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-800))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(80))
    .alpha(0.3)
    .alphaDecay(0.02);
  ```
  This config ensures readable spacing for 50 nodes with moderate repulsion and collision avoidance.
- 

## GEMINI — CYCLE 1 OUTPUT
## PROTOCOL PULSE — CODE AUDIT & ARCHITECTURE REVIEW

**AUDITOR:** Gemini 2.5 Pro
**SUBJECT:** `media-audit` Feature, Bitcoin Media Command Center
**ANALYSIS:** Comprehensive architectural review and implementation plan based on the 8 key design questions.

---

### EXECUTIVE SUMMARY

The vision for a world-class Bitcoin media hub is achievable but requires a significant architectural evolution from the current implementation. The existing `rss_service.py` and front-end data handling are insufficient for the scale proposed (15+ feeds, live data, complex processing).

My core recommendation is to decouple data **ingestion and processing** from data **presentation** using a standard background worker and caching architecture (Celery + Redis). This is the only viable path to prevent blocking Flask workers and ensure a responsive user experience. The current code shows a hardcoded blocklist and only two feeds, indicating the system is not yet built for scale. The provided `media_hub.html` is a solid foundation for the UI, but its data sources must be made more robust.

The following is a detailed, question-by-question breakdown of the recommended architecture.

---

### Q1 — ARCHITECTURE

**What is the optimal backend architecture for aggregating 15 RSS feeds + 7 YouTube channels + live X/Nostr KOL feeds simultaneously WITHOUT blocking Flask workers or degrading site perf?**

#### DETAILED RECOMMENDATION

The architecture must be asynchronous and distributed. A monolithic, synchronous Flask process will fail under this load.

1.  **Background Workers (Celery):** Implement Celery as the task queue manager. All data fetching (RSS, YouTube API) and processing (summarization, signal scoring) must happen in Celery workers, completely separate from the Flask web processes.
    *   **Producer:** The Flask app (or a cron-like scheduler like Celery Beat) will add tasks to the queue (e.g., `fetch_rss_feed.delay(feed_url)`).
    *   **Consumer:** One or more Celery worker processes will execute these tasks, fetching data and storing the results.

2.  **Caching Layer (Redis):** Use Redis for multiple purposes:
    *   **Celery Broker:** Manages the queue of tasks between Flask and the workers.
    *   **Results Backend:** Stores the results of completed tasks.
    *   **Application Cache:** This is critical. The Flask route (`/media_hub`) should **not** query the database directly on every page load. It should read pre-computed JSON or even rendered HTML fragments from a Redis cache. The Celery workers are responsible for populating this cache. Example key: `cache:media_hub:podcast_feed`.

3.  **Database (SQLite/PostgreSQL):**
    *   SQLite is acceptable for now but will become a bottleneck under high write concurrency from workers. Plan to migrate to PostgreSQL for production.
    *   **New Models Required:** The current `Podcast` model is for internal content. You need new models for aggregated content:
        *   `FeedSource(source_url, name, type, last_fetched)`
        *   `FeedItem(source_id, guid, title, link, content, published_at, signal_score, summary)`

4.  **Async Fetching in Workers:** Within the Celery tasks, use asynchronous libraries like `httpx` or `aiohttp` to fetch all 15 RSS feeds and 7 YouTube channels concurrently, not sequentially. This will dramatically reduce the runtime of the aggregation task.

5.  **Optimal Refresh Intervals (managed by Celery Beat):**
    *   **Nostr/X:** Continue using the live client-side WebSocket approach for real-time updates. The backend should not poll for these.
    *   **Podcast RSS Feeds:** 15-20 minutes. Podcasts are not published frequently enough to warrant faster polling.
    *   **YouTube Channels:** 30-60 minutes. Use the YouTube Data API v3, respecting quotas.
    *   **KOL X Feeds (for non-live components):** 5-10 minutes. Poll for engagement metrics on recent posts.

#### ESTIMATED COST / PERFORMANCE
*   **Cost:** Adds a Redis instance to the infrastructure (~$15-50/mo for a managed instance).
*   **Performance:** Drastically improves front-end performance. Page load for `/media_hub` becomes a few milliseconds (reading from Redis) instead of seconds (blocking on 20+ network requests).

#### IMPLEMENTATION COMPLEXITY: **HIGH**
*   This is a fundamental architectural change, requiring setup of Celery, Redis, new DB models, and refactoring all data-fetching logic into background tasks.

#### KEY RISKS & MITIGATIONS
*   **Risk:** Complexity of managing a distributed system (Celery workers can fail, queues can back up).
    *   **Mitigation:** Implement robust monitoring and alerting for Celery (e.g., using Flower). Start with a simple setup and add complexity as needed.
*   **Risk:** YouTube API rate limits and costs.
    *   **Mitigation:** Cache API results aggressively in Redis. Use ETag headers to only fetch data when it has changed.

---

### Q2 — D3 NETWORK GRAPH

**Design the Bitcoin voice network topology visualization.**

#### DETAILED RECOMMENDATION



## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — MEDIA-AUDIT — CYCLE 1
Generated: 2026-03-25 19:27
Models: grok, gemini (+1 failed)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Architecture (Q1) | 4/10 | N/A (failed) | 4/10 | 4/10 |
| D3 Network Graph (Q2) | 3/10 | N/A | 3/10 | 3/10 |
| Live Ticker (Q3) | 5/10 | N/A | 5/10 | 5/10 |
| Feed Aggregation / Scalability | 3/10 | N/A | 3/10 | 3/10 |
| Data Models | 4/10 | N/A | 4/10 | 4/10 |
| Real-Time / WebSocket Layer | 5/10 | N/A | 5/10 | 5/10 |
| CSS / Front-End Foundations | 6/10 | N/A | 6/10 | 6/10 |
| Overall Codebase Readiness | 4/10 | N/A | 4/10 | **4/10** |

> **Scoring note:** GPT-4o failed due to token rate limit (39,649 tokens requested vs. 30,000 TPM limit). All consensus determinations are drawn from Gemini 2.5 Pro and Grok-3 only. Where both models agree, confidence is treated as high. Where only one model speaks, findings are flagged as unique insights requiring manual evaluation.

---

## UNANIMOUS FINDINGS
*(Both Grok and Gemini agree — implement unconditionally)*

---

### U1 — Flask Workers Must NOT Handle Feed Aggregation
**What it is:** The current `rss_service.py` and Flask routes perform synchronous feed fetching inline, blocking the web process. Both models independently identified this as a critical architectural failure that will cause request timeouts, degraded UX, and inability to scale to 15+ feeds + 7 YouTube channels + live KOL feeds simultaneously.

**File:** `rss_service.py`, Flask route handlers (all feed-related endpoints)

**What to change:** Fully decouple data ingestion from data presentation. Move all feed fetching (RSS, YouTube, X, Nostr) into Celery background tasks. Flask routes must read from a Redis cache or pre-computed database records only — never triggering a live fetch on a request cycle.

---

### U2 — Redis Is Required as Application Cache + Celery Broker
**What it is:** Both models converged on Redis serving a dual role: (a) Celery task broker/results backend, and (b) application-level read cache for the `/media_hub` route and related endpoints. Without this, every page load hits the database or worse, the network.

**File:** New infrastructure requirement; impacts `app/__init__.py`, all feed service modules

**What to change:** Add Redis to the stack. Configure Celery with Redis as broker. Pre-compute and cache JSON payloads (e.g., `cache:media_hub:podcast_feed`, `cache:media_hub:kol_graph`) in Celery workers. Flask reads exclusively from cache. Stale-while-revalidate pattern recommended.

---

### U3 — New Database Models Are Required for Aggregated Content
**What it is:** The existing `Podcast` model is for internal Protocol Pulse content only. Both models identified that aggregated external feed data (episodes, videos, KOL posts) has no proper schema. This means ingested content is either dropped, misfit into the wrong model, or not persisted at all.

**File:** `models.py` (or equivalent ORM file)

**What to change:**


---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/media_hub.html (242 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}The Network — Protocol Pulse Media Hub{% endblock %}
   3 | {% block meta_description %}Bitcoin intelligence network. Live signals from Nostr and X.{% endblock %}
   4 | {% block head %}
   5 | <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
   6 | <style>
   7 | :root{--void:#000;--deep:#040408;--card:#08080e;--elevated:#0e0e16;--hover:#14141e;--border:rgba(255,255,255,0.05);--border-h:rgba(255,255,255,0.1);--bright:#f5f5f5;--pri:#e0e0e0;--sec:rgba(255,255,255,0.5);--mut:rgba(255,255,255,0.25);--red:#dc2626;--red-g:rgba(220,38,38,0.12);--btc:#f7931a;--purple:#a855f7;--blue:#3b82f6;--green:#22c55e;--cyan:#06b6d4}
   8 | *{box-sizing:border-box;margin:0;padding:0}
   9 | .mh{font-family:'DM Sans',-apple-system,sans-serif;background:var(--void);color:var(--pri);min-height:100vh;padding-top:80px}
  10 | .mono{font-family:'Geist Mono',monospace}
  11 | .wrap{max-width:1440px;margin:0 auto;padding:0 clamp(16px,4vw,48px)}
  12 | .hero{position:relative;padding:80px 0 60px;overflow:hidden}
  13 | .hero-bg{position:absolute;inset:0;overflow:hidden}
  14 | .hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(220,38,38,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(220,38,38,0.03) 1px,transparent 1px);background-size:60px 60px;animation:gridDrift 20s linear infinite}
  15 | @keyframes gridDrift{from{transform:translate(0,0)}to{transform:translate(60px,60px)}}
  16 | .hero-orb{position:absolute;border-radius:50%;filter:blur(80px);animation:orbFloat 8s ease-in-out infinite}
  17 | .hero-orb-1{width:400px;height:400px;background:rgba(220,38,38,0.08);top:-100px;left:20%}
  18 | .hero-orb-2{width:300px;height:300px;background:rgba(247,147,26,0.05);bottom:-80px;right:15%;animation-delay:-3s}
  19 | .hero-orb-3{width:200px;height:200px;background:rgba(168,85,247,0.04);top:40%;left:60%;animation-delay:-5s}
  20 | @keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(30px,-20px) scale(1.1)}}
  21 | .hero-scanline{position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(220,38,38,0.3),transparent);animation:scanDown 4s linear infinite;opacity:0.4}
  22 | @keyframes scanDown{from{top:0}to{top:100%}}
  23 | .hero-vignette{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%,transparent 40%,var(--void) 100%)}
  24 | .hero-inner{position:relative;z-index:2}
  25 | .hero-tag{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.15);border-radius:24px;margin-bottom:28px;opacity:0;animation:fadeUp .6s ease forwards}
  26 | .hero-tag-dot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:tagPulse 2s infinite}
  27 | @keyframes tagPulse{0%,100%{opacity:1}50%{opacity:0.3}}
  28 | .hero-tag-text{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--red)}
  29 | .hero-h{font-family:'Instrument Serif',Georgia,serif;font-size:clamp(56px,10vw,120px);font-weight:400;line-height:0.95;color:var(--bright);letter-spacing:-3px;margin-bottom:20px;opacity:0;animation:fadeUp .6s ease .1s forwards}
  30 | .hero-h em{font-style:italic;background:linear-gradient(135deg,var(--red),var(--btc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  31 | .hero-sub{font-size:17px;font-weight:300;color:var(--sec);max-width:480px;line-height:1.6;opacity:0;animation:fadeUp .6s ease .2s forwards}
  32 | .hero-metrics{display:flex;gap:40px;margin-top:40px;opacity:0;animation:fadeUp .6s ease .3s forwards}
  33 | .hero-metric{position:relative;padding:16px 0}
  34 | .hero-metric::after{content:'';position:absolute;right:-20px;top:50%;transform:translateY(-50%);width:1px;height:24px;background:var(--border)}
  35 | .hero-metric:last-child::after{display:none}
  36 | .hero-metric-val{font-family:'Geist Mono',monospace;font-size:28px;font-weight:600;color:var(--bright)}
  37 | .hero-metric-lab{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1.5px;margin-top:4px}
  38 | .hero-status{display:flex;gap:24px;margin-top:32px;opacity:0;animation:fadeUp .6s ease .4s forwards}
  39 | .hero-status-item{display:flex;align-items:center;gap:6px;font-family:'Geist Mono',monospace;font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1px}
  40 | .hero-status-dot{width:5px;height:5px;border-radius:50%}
  41 | .hero-status-dot.live{background:var(--green);box-shadow:0 0 6px var(--green)}
  42 | .hero-status-dot.sync{background:var(--btc);animation:tagPulse 1.5s infinite}
  43 | @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
  44 | .sec{padding:64px 0;border-top:1px solid var(--border)}
  45 | .sec-lab{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--red);margin-bottom:14px}
  46 | .sec-h{font-family:'Instrument Serif',Georgia,serif;font-size:clamp(26px,4vw,38px);font-weight:400;color:var(--bright);letter-spacing:-0.5px;margin-bottom:10px}
  47 | .sec-desc{font-size:14px;color:var(--sec);max-width:480px;line-height:1.6;margin-bottom:40px}
  48 | .intel-dash{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;min-height:500px}
  49 | .intel-col{display:flex;flex-direction:column;min-width:0}
  50 | .intel-col-head{display:flex;align-items:center;gap:8px;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:10px 10px 0 0;border-bottom:none}
  51 | .intel-col-icon{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px}
  52 | .intel-col-icon.nostr{color:var(--purple)}.intel-col-icon.x{color:var(--blue)}.intel-col-icon.yt{color:var(--red)}
  53 | .intel-col-name{font-family:'Geist Mono',monospace;font-size:11px;font-weight:600;color:var(--bright);text-transform:uppercase;letter-spacing:1px}
  54 | .intel-col-status{margin-left:auto;display:flex;align-items:center;gap:4px}
  55 | .intel-col-dot{width:5px;height:5px;border-radius:50%;background:var(--green)}
  56 | .intel-col-count{font-family:'Geist Mono',monospace;font-size:10px;color:var(--mut)}
  57 | .intel-feed{flex:1;background:var(--card);border:1px solid var(--border);border-radius:0 0 10px 10px;overflow-y:auto;max-height:700px;padding:8px}
  58 | .intel-feed::-webkit-scrollbar{width:3px}.intel-feed::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:2px}
  59 | .fi{padding:12px 14px;margin-bottom:6px;border-radius:10px;background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.04);transition:all .2s}
  60 | .fi:hover{border-color:rgba(255,255,255,0.08);background:rgba(255,255,255,0.025)}
  61 | .fi.new{animation:fiIn .4s cubic-bezier(.16,1,.3,1)}
  62 | @keyframes fiIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}
  63 | .fi-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
  64 | .fi-av{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;border:1px solid rgba(255,255,255,0.06)}
  65 | .fi-av.macro{background:rgba(220,38,38,0.1);color:var(--red)}.fi-av.protocol{background:rgba(168,85,247,0.1);color:var(--purple)}.fi-av.media{background:rgba(59,130,246,0.1);color:var(--blue)}
  66 | .fi-name{font-size:12px;font-weight:600;color:var(--bright);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  67 | .fi-time{font-family:'Geist Mono',monospace;font-size:9px;color:var(--mut)}
  68 | .fi-body{font-size:12px;color:var(--pri);line-height:1.5;overflow:hidden;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;word-break:break-word}
  69 | .fi-body a{color:var(--cyan);text-decoration:none}
  70 | .fi-foot{display:flex;gap:12px;margin-top:8px}
  71 | .fi-act{font-family:'Geist Mono',monospace;font-size:9px;color:var(--mut);text-decoration:none;display:flex;align-items:center;gap:3px;transition:color .2s;text-transform:uppercase;letter-spacing:.5px}
  72 | .fi-act:hover{color:var(--bright)}
  73 | .fi-quote{position:relative;padding-left:12px}
  74 | .fi-quote::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;border-radius:1px}
  75 | .fi-quote.macro::before{background:var(--red)}.fi-quote.protocol::before{background:var(--purple)}.fi-quote.media::before{background:var(--blue)}
  76 | .fi-src{font-family:'Geist Mono',monospace;font-size:9px;color:var(--mut);margin-top:6px}
  77 | .fi-pin{border-color:rgba(247,147,26,0.15);background:rgba(247,147,26,0.03)}
  78 | .intel-empty{text-align:center;padding:40px 16px;color:var(--mut);font-size:12px}
  79 | .intel-empty i{font-size:20px;margin-bottom:8px;display:block;opacity:0.3}
  80 | .intel-loader{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top:2px solid var(--red);border-radius:50%;animation:spin .7s linear infinite;margin-top:10px}
  81 | @keyframes spin{to{transform:rotate(360deg)}}
  82 | .sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
  83 | .sc{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;cursor:pointer;transition:all .3s}
  84 | .sc:hover{border-color:var(--border-h);transform:translateY(-3px);box-shadow:0 16px 48px rgba(0,0,0,.4)}
  85 | .sc:hover .sc-img{transform:scale(1.05)}
  86 | .sc-img-w{position:relative;overflow:hidden;aspect-ratio:16/9}
  87 | .sc-img{width:100%;height:100%;object-fit:cover;transition:transform .5s}
  88 | .sc-ov{position:absolute;inset:0;background:linear-gradient(180deg,transparent 30%,rgba(0,0,0,.9) 100%)}
  89 | .sc-play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:48px;height:48px;background:rgba(220,38,38,.9);border-radius:50%;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .3s}
  90 | .sc:hover .sc-play{opacity:1}.sc-play i{color:white;font-size:16px;margin-left:2px}
  91 | .sc-badge{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.7);backdrop-filter:blur(8px);padding:3px 8px;border-radius:16px;font-family:'Geist Mono',monospace;font-size:10px;color:var(--sec);border:1px solid rgba(255,255,255,.08)}
  92 | .sc-body{padding:16px 20px 20px}
  93 | .sc-host{font-size:11px;color:var(--red);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
  94 | .sc-name{font-family:'Instrument Serif',Georgia,serif;font-size:20px;color:var(--bright);margin-bottom:8px;line-height:1.3}
  95 | .sc-desc{font-size:12px;color:var(--sec);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  96 | .sd{display:none;margin-top:24px;border-radius:14px;overflow:hidden;border:1px solid var(--border);background:var(--card)}
  97 | .sd.active{display:block;animation:fadeUp .4s ease}
  98 | .sd-top{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--border)}
  99 | .sd-title{font-family:'Instrument Serif',Georgia,serif;font-size:20px;color:var(--bright)}
 100 | .sd-x{background:rgba(255,255,255,.05);border:none;color:var(--mut);width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center}
 101 | .sd-x:hover{background:rgba(255,255,255,.1);color:white}
 102 | .sd-main{display:grid;grid-template-columns:1fr 340px}
 103 | .sd-vid iframe{width:100%;aspect-ratio:16/9;border:none;display:block;background:#000}
 104 | .sd-eps{max-height:440px;overflow-y:auto;border-left:1px solid var(--border)}
 105 | .sd-ep{display:flex;gap:10px;padding:10px 14px;cursor:pointer;transition:background .15s;border-bottom:1px solid var(--border);align-items:center}
 106 | .sd-ep:hover{background:var(--hover)}.sd-ep.active{background:rgba(220,38,38,.05);border-left:3px solid var(--red)}
 107 | .sd-ep-img{width:80px;height:45px;border-radius:5px;object-fit:cover;flex-shrink:0}
 108 | .sd-ep-info{flex:1;min-width:0}
 109 | .sd-ep-n{font-family:'Geist Mono',monospace;font-size:9px;color:var(--red);letter-spacing:1px}
 110 | .sd-ep-t{font-size:11px;color:var(--pri);margin-top:2px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 111 | .pod-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
 112 | .pod-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
 113 | .pod-card:hover{border-color:var(--border-h);background:var(--elevated);transform:translateY(-2px)}
 114 | .pod-card::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:var(--red);opacity:0;transition:opacity .2s}
 115 | .pod-card:hover::before{opacity:1}
 116 | .pod-num{font-family:'Geist Mono',monospace;font-size:28px;font-weight:600;color:rgba(220,38,38,0.1);position:absolute;top:12px;right:16px}
 117 | .pod-title{font-size:14px;font-weight:600;color:var(--bright);line-height:1.4;margin-bottom:10px;padding-right:40px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 118 | .pod-meta{display:flex;align-items:center;gap:12px}
 119 | .pod-dur{font-family:'Geist Mono',monospace;font-size:11px;color:var(--mut)}
 120 | .pod-play-btn{width:28px;height:28px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;margin-left:auto;opacity:0;transition:opacity .2s}
 121 | .pod-card:hover .pod-play-btn{opacity:1}.pod-play-btn i{color:white;font-size:10px;margin-left:1px}
 122 | .pod-more{display:inline-flex;align-items:center;gap:8px;margin-top:24px;padding:10px 20px;background:transparent;border:1px solid var(--border);border-radius:8px;color:var(--sec);font-size:13px;text-decoration:none;transition:all .2s}
 123 | .pod-more:hover{border-color:var(--red);color:var(--red)}
 124 | .bg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px}
 125 | .bc{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:all .3s;text-decoration:none;display:block}
 126 | .bc:hover{border-color:var(--border-h);transform:translateY(-3px);box-shadow:0 12px 36px rgba(0,0,0,.3)}
 127 | .bc-cov{aspect-ratio:2/3;display:flex;align-items:flex-end;position:relative;border-radius:4px 4px 0 0;overflow:hidden}
 128 | .bc-img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:2}
 129 | .bc-spine{position:absolute;left:0;top:8%;bottom:8%;width:3px;border-radius:0 2px 2px 0}
 130 | .bc-txt{padding:16px 14px;position:relative;z-index:1;width:100%}
 131 | .bc-txt-t{font-family:'Instrument Serif',Georgia,serif;font-size:14px;font-weight:400;color:rgba(255,255,255,0.9);line-height:1.3;margin-bottom:4px}
 132 | .bc-txt-a{font-family:'Geist Mono',monospace;font-size:9px;color:rgba(255,255,255,0.4);letter-spacing:0.5px;text-transform:uppercase}
 133 | .bc-info{padding:10px 12px 12px}
 134 | .bc-badge{font-family:'Geist Mono',monospace;font-size:8px;letter-spacing:1.5px;text-transform:uppercase;color:var(--btc);margin-bottom:4px}
 135 | .bc-badge.econ{color:var(--green)}
 136 | .bc-name{font-size:11px;font-weight:600;color:var(--bright);margin-bottom:2px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 137 | .bc-auth{font-size:10px;color:var(--sec)}
 138 | .bcat{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--mut);margin-top:36px;margin-bottom:14px;padding-bottom:6px;border-bottom:1px solid var(--border)}
 139 | .bcat:first-of-type{margin-top:0}
 140 | .btog{display:flex;align-items:center;gap:10px;margin-top:36px;padding:12px 18px;background:var(--card);border:1px solid var(--border);border-radius:10px;cursor:pointer;width:100%;color:var(--sec);font-size:13px;font-weight:500;transition:all .2s}
 141 | .btog:hover{border-color:var(--border-h);color:var(--bright)}
 142 | .btog i{transition:transform .3s}.btog.open i{transform:rotate(180deg)}
 143 | .bhid{display:none}.bhid.show{display:block;animation:fadeUp .4s ease}
 144 | .nl{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:48px;text-align:center;position:relative;overflow:hidden}
 145 | .nl::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at center,var(--red-g) 0%,transparent 60%);pointer-events:none}
 146 | .nl-h{font-family:'Instrument Serif',Georgia,serif;font-size:28px;color:var(--bright);margin-bottom:10px;position:relative}
 147 | .nl-p{font-size:14px;color:var(--sec);margin-bottom:28px;position:relative}
 148 | .nl-f{display:flex;gap:10px;max-width:400px;margin:0 auto;position:relative}
 149 | .nl-i{flex:1;padding:12px 16px;background:var(--void);border:1px solid var(--border);border-radius:8px;color:var(--bright);font-size:13px;outline:none}
 150 | .nl-i:focus{border-color:var(--red)}.nl-i::placeholder{color:var(--mut)}
 151 | .nl-b{padding:12px 24px;background:var(--red);border:none;border-radius:8px;color:white;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
 152 | .abar{position:fixed;bottom:0;left:0;right:0;background:rgba(8,8,14,.95);border-top:1px solid var(--border);padding:10px 24px;display:none;align-items:center;gap:14px;z-index:1000;backdrop-filter:blur(20px)}
 153 | .abar.active{display:flex}.abar-now{flex:1;font-size:12px;color:var(--pri);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 154 | @media(max-width:1024px){.intel-dash{grid-template-columns:1fr 1fr}.intel-col:nth-child(3){grid-column:span 2}}
 155 | .sm-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(12px);z-index:2000;align-items:center;justify-content:center}
 156 | .sm-overlay.active{display:flex}
 157 | .sm-panel{background:var(--card);border:1px solid var(--border);border-radius:16px;max-width:480px;width:90%;max-height:85vh;overflow-y:auto;padding:32px;position:relative;animation:fadeUp .3s ease}
 158 | .sm-close{position:absolute;top:14px;right:14px;background:rgba(255,255,255,.05);border:none;color:var(--mut);width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center;z-index:1}
 159 | .sm-close:hover{background:rgba(255,255,255,.1);color:white}
 160 | .sm-header{display:flex;gap:16px;align-items:center;margin-bottom:20px}
 161 | .sm-cover{width:80px;height:120px;border-radius:8px;flex-shrink:0}
 162 | .sm-title{font-family:'Instrument Serif',Georgia,serif;font-size:22px;color:var(--bright);margin-bottom:4px}
 163 | .sm-author{font-family:'Geist Mono',monospace;font-size:11px;color:var(--sec);text-transform:uppercase;letter-spacing:1px}
 164 | .sm-desc{font-size:13px;color:var(--sec);line-height:1.6;margin-bottom:20px}
 165 | .sm-eps{font-family:'Geist Mono',monospace;font-size:11px;color:var(--mut);margin-bottom:24px;padding:12px;background:rgba(255,255,255,.02);border:1px solid var(--border);border-radius:8px}
 166 | .sm-cta{display:inline-flex;align-items:center;gap:8px;padding:12px 24px;background:var(--red);border:none;border-radius:8px;color:white;font-size:13px;font-weight:600;text-decoration:none;transition:all .2s}
 167 | .sm-cta:hover{background:#b91c1c;box-shadow:0 0 20px rgba(220,38,38,.3)}
 168 | @media(max-width:768px){.hero{padding:60px 0 40px}.hero-metrics{gap:24px;flex-wrap:wrap}.sec{padding:40px 0}.intel-dash{grid-template-columns:1fr}.intel-col:nth-child(3){grid-column:auto}.sg{grid-template-columns:1fr}.sd-main{grid-template-columns:1fr}.sd-eps{max-height:250px;border-left:none;border-top:1px solid var(--border)}.pod-grid{grid-template-columns:1fr}.bg{grid-template-columns:repeat(2,1fr)}.nl{padding:32px 20px}.nl-f{flex-direction:column}}
 169 | </style>
 170 | {% endblock %}
 171 | {% block content %}
 172 | <div class="mh"><div class="wrap">
 173 | <div class="hero"><div class="hero-bg"><div class="hero-grid"></div><div class="hero-orb hero-orb-1"></div><div class="hero-orb hero-orb-2"></div><div class="hero-orb hero-orb-3"></div><div class="hero-scanline"></div><div class="hero-vignette"></div></div>
 174 | <div class="hero-inner"><div class="hero-tag"><div class="hero-tag-dot"></div><span class="hero-tag-text">Intelligence Network Active</span></div>
 175 | <h1 class="hero-h">The <em>Network</em></h1>
 176 | <p class="hero-sub">Sovereign signal intelligence. Live feeds from Nostr relays, X propagation, and the voices shaping the ecosystem.</p>
 177 | <div class="hero-metrics"><div class="hero-metric"><div class="hero-metric-val">{{ series_count }}</div><div class="hero-metric-lab">Series</div></div><div class="hero-metric"><div class="hero-metric-val">{{ podcast_count }}</div><div class="hero-metric-lab">Episodes</div></div><div class="hero-metric"><div class="hero-metric-val">{{ all_books|length }}</div><div class="hero-metric-lab">Books</div></div><div class="hero-metric"><div class="hero-metric-val" id="liveN">0</div><div class="hero-metric-lab">Live Notes</div></div></div>
 178 | <div class="hero-status"><div class="hero-status-item"><div class="hero-status-dot live"></div>Nostr Relays</div><div class="hero-status-item"><div class="hero-status-dot sync"></div>X Propagation</div></div></div></div>
 179 | <div class="sec" id="signal"><div class="sec-lab">01 — Live Intelligence</div><h2 class="sec-h">Signal Dashboard</h2><p class="sec-desc">Three intelligence streams. Nostr notes, X propagation, and curated thought leader insights.</p>
 180 | <div class="intel-dash">
 181 | <div class="intel-col"><div class="intel-col-head"><div class="intel-col-icon nostr"><i class="fas fa-bolt"></i></div><span class="intel-col-name">Nostr</span><div class="intel-col-status"><div class="intel-col-dot" id="nDot"></div><span class="intel-col-count" id="nCount">0</span></div></div><div class="intel-feed" id="nFeed"><div class="intel-empty"><i class="fas fa-satellite-dish"></i>Connecting to relays...<div class="intel-loader"></div></div></div></div>
 182 | <div class="intel-col"><div class="intel-col-head"><div class="intel-col-icon x"><i class="fab fa-x-twitter"></i></div><span class="intel-col-name">X Propagation</span><div class="intel-col-status"><div class="intel-col-dot" id="xDot"></div><span class="intel-col-count" id="xCount">0</span></div></div><div class="intel-feed" id="xFeed"><div class="intel-empty"><i class="fab fa-x-twitter"></i>Monitoring X channels...<div class="intel-loader"></div></div></div></div>
 183 | <div class="intel-col"><div class="intel-col-head"><div class="intel-col-icon yt"><i class="fas fa-quote-left"></i></div><span class="intel-col-name">Voice Intel</span><div class="intel-col-status"><span class="intel-col-count" id="qCount">0</span></div></div><div class="intel-feed" id="qFeed"><div class="intel-empty"><i class="fas fa-quote-left"></i>Loading insights...<div class="intel-loader"></div></div></div></div>
 184 | </div></div>
 185 | <div class="sec" id="series"><div class="sec-lab">02 — Original Series</div><h2 class="sec-h">Cinematic Deep Dives</h2><p class="sec-desc">Long-form explorations of the books and ideas reshaping monetary thinking.</p>
 186 | <div class="sg">{% for s in series_list %}<div class="sc" onclick="toggleSD('{{ s.key }}')"><div class="sc-img-w"><img class="sc-img" src="https://img.youtube.com/vi/{{ s.first_id }}/hqdefault.jpg" alt="{{ s.title }}" loading="lazy" onerror="this.onerror=null;this.src='https://img.youtube.com/vi/{{ s.first_id }}/mqdefault.jpg'"><div class="sc-ov"></div><div class="sc-play"><i class="fas fa-play"></i></div><div class="sc-badge">{{ s.ep_count }} episodes</div></div><div class="sc-body"><div class="sc-host">{{ s.host }}</div><h3 class="sc-name">{{ s.title }}</h3><p class="sc-desc">{{ s.description }}</p></div></div>{% endfor %}</div>
 187 | <div id="sdPanel" class="sd"><div class="sd-top"><h3 class="sd-title" id="sdTitle"></h3><button class="sd-x" onclick="closeSD()"><i class="fas fa-times"></i></button></div><div class="sd-main"><div class="sd-vid"><iframe id="sdIf" src="" allow="autoplay; encrypted-media" allowfullscreen></iframe></div><div class="sd-eps" id="sdEps"></div></div></div></div>
 188 | <div class="sec" id="podcasts"><div class="sec-lab">03 — Cypherpunk'd Podcast</div><h2 class="sec-h">Latest Episodes</h2><p class="sec-desc">Conversations with builders, thinkers, and disruptors at the frontier of sound money.</p>
 189 | <div class="pod-grid">{% for ep in latest_episodes %}<div class="pod-card" onclick="playEp('{{ ep.audio_url }}','{{ ep.title|replace("'","") }}')"><div class="pod-num mono">{{ '%02d'|format(loop.index) }}</div><div class="pod-title">{{ ep.title }}</div><div class="pod-meta"><span class="pod-dur mono">{{ ep.duration or '--:--' }}</span><div class="pod-play-btn"><i class="fas fa-play"></i></div></div></div>{% endfor %}</div>
 190 | <a href="/podcasts" class="pod-more">View all episodes <i class="fas fa-arrow-right"></i></a></div>
 191 | <div class="sec" id="books"><div class="sec-lab">04 — Essential Reading</div><h2 class="sec-h">The Library</h2><p class="sec-desc">The books that shaped Cypherpunk'd. Every link supports Protocol Pulse.</p>
 192 | <div class="bcat">Featured on Podcast</div><div class="bg">{% for b in all_books %}{% if b.get('category')=='series' %}<div class="bc" style="cursor:pointer" onclick="showSeriesPanel(this,event)" data-title="{{ b.title }}" data-author="{{ b.author }}" data-url="{{ b.amazon_url }}" data-color="{{ b.get('color','#333') }}" data-desc="{{ b.get('description','A deep dive into the ideas that shaped the Bitcoin movement.') }}" data-episodes="{{ b.get('episode_count',0) }}"><div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">{% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}<div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div><div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div></div><div class="bc-info"><div class="bc-badge">Series</div><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div></div>{% endif %}{% endfor %}</div>
 193 | <div class="bcat">Bitcoin Essentials</div><div class="bg">{% for b in all_books %}{% if b.get('category')=='essential' %}<a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc"><div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">{% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}<div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div><div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div></div><div class="bc-info"><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div></a>{% endif %}{% endfor %}</div>
 194 | <button class="btog" id="btog" onclick="togB()"><i class="fas fa-chevron-down"></i><span>Show More — Bestsellers & Economics</span><span class="mono" style="margin-left:auto;font-size:10px;color:var(--mut)">{{ all_books|selectattr('category','in',['bestseller','economics'])|list|length }} titles</span></button>
 195 | <div class="bhid" id="bmore"><div class="bcat" style="margin-top:20px">Bitcoin Bestsellers</div><div class="bg">{% for b in all_books %}{% if b.get('category')=='bestseller' %}<a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc"><div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">{% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}<div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div><div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div></div><div class="bc-info"><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div></a>{% endif %}{% endfor %}</div>
 196 | <div class="bcat">Austrian Economics</div><div class="bg">{% for b in all_books %}{% if b.get('category')=='economics' %}<a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc"><div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">{% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}<div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div><div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div></div><div class="bc-info"><div class="bc-badge econ">Economics</div><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div></a>{% endif %}{% endfor %}</div></div></div>
 197 | <div class="sec" id="subscribe"><div class="nl"><h2 class="nl-h">The signal. Every morning.</h2><p class="nl-p">Daily intelligence brief + weekly premium digest.</p><form class="nl-f" action="/newsletter/subscribe" method="POST"><input type="email" name="email" class="nl-i" placeholder="your@email.com" required><button type="submit" class="nl-b">Subscribe</button></form></div></div>
 198 | </div></div>
 199 | <div id="seriesModal" class="sm-overlay" onclick="if(event.target===this)closeSeriesPanel()">
 200 | <div class="sm-panel">
 201 | <button class="sm-close" onclick="closeSeriesPanel()"><i class="fas fa-times"></i></button>
 202 | <div class="sm-header">
 203 | <div class="sm-cover" id="smCover"></div>
 204 | <div class="sm-info"><h3 class="sm-title" id="smTitle"></h3><p class="sm-author" id="smAuthor"></p></div>
 205 | </div>
 206 | <p class="sm-desc" id="smDesc"></p>
 207 | <div class="sm-eps" id="smEps"></div>
 208 | <a href="#" id="smLink" target="_blank" rel="noopener" class="sm-cta"><i class="fas fa-book"></i> Get the Full Series</a>
 209 | </div>
 210 | </div>
 211 | <div id="abar" class="abar"><button onclick="togA()" style="background:none;border:none;color:var(--sec);font-size:16px;cursor:pointer;padding:4px 8px"><i id="aIcon" class="fas fa-pause"></i></button><div class="abar-now" id="aNow">Now Playing...</div><button onclick="stopA()" style="background:none;border:none;color:var(--mut);cursor:pointer;font-size:12px"><i class="fas fa-times"></i></button><audio id="aEl"></audio></div>
 212 | {% endblock %}
 213 | {% block scripts %}
 214 | <script>
 215 | var SD={{ series_data|tojson }},curS=null;
 216 | function toggleSD(k){var p=document.getElementById('sdPanel');if(curS===k&&p.classList.contains('active')){closeSD();return}var s=SD[k];if(!s||!s.episodes||!s.episodes.length)return;curS=k;document.getElementById('sdTitle').textContent=s.title||k;var e0=s.episodes[0];document.getElementById('sdIf').src='https://www.youtube.com/embed/'+e0.id+'?autoplay=1';var sb=document.getElementById('sdEps');sb.innerHTML=s.episodes.map(function(ep,i){return'<div class="sd-ep'+(i===0?' active':'')+'" onclick="playSE(\''+ep.id+'\','+i+',this)"><img class="sd-ep-img" src="https://img.youtube.com/vi/'+ep.id+'/mqdefault.jpg" loading="lazy"><div class="sd-ep-info"><div class="sd-ep-n">EP '+(i+1)+'</div><div class="sd-ep-t">'+ep.title+'</div></div></div>'}).join('');p.classList.add('active');setTimeout(function(){p.scrollIntoView({behavior:'smooth',block:'nearest'})},100)}
 217 | function playSE(id,i,el){document.getElementById('sdIf').src='https://www.youtube.com/embed/'+id+'?autoplay=1';document.querySelectorAll('.sd-ep').forEach(function(e){e.classList.remove('active')});if(el)el.classList.add('active')}
 218 | function closeSD(){document.getElementById('sdIf').src='';document.getElementById('sdPanel').classList.remove('active');curS=null}
 219 | var au=document.getElementById('aEl'),pl=false;
 220 | function playEp(u,t){if(!u)return;au.src=u;au.play();pl=true;document.getElementById('aNow').textContent=t;document.getElementById('aIcon').className='fas fa-pause';document.getElementById('abar').classList.add('active')}
 221 | function togA(){if(pl){au.pause();document.getElementById('aIcon').className='fas fa-play'}else{au.play();document.getElementById('aIcon').className='fas fa-pause'}pl=!pl}
 222 | function stopA(){au.pause();au.src='';pl=false;document.getElementById('abar').classList.remove('active')}
 223 | function togB(){document.getElementById('bmore').classList.toggle('show');document.getElementById('btog').classList.toggle('open')}
 224 | var RELAYS=['wss://relay.damus.io','wss://nos.lol','wss://relay.nostr.band','wss://relay.primal.net'];
 225 | var V={'82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2':{n:'Jack Dorsey',i:'JD',c:'protocol',x:'jack'},'fa984bd7dbb282f07e16e7ae87b26a2a7b9b90b7246a44771f0cf5ae58018f52':{n:'Adam Back',i:'AB',c:'protocol',x:'adam3us'},'e88a691e98d9987c964521dff60025f60700378a4879180dcbbb4a5027850411':{n:'NVK',i:'NV',c:'protocol',x:'nvk'},'04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc9':{n:'ODELL',i:'MO',c:'protocol',x:'ODELL'},'3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d':{n:'Fiatjaf',i:'FJ',c:'protocol',x:'fiatjaf'},'eab0e756d32b80bcd464f3d844b8040303075a13eabc3599a762c9ac7ab91f4f':{n:'Lyn Alden',i:'LA',c:'macro',x:'LynAldenContact'},'85080d3bad70ccdcd7f74c29a44f55bb85cbcd3dd0cbb957da1d215bdb931204':{n:'Preston Pysh',i:'PP',c:'macro',x:'PrestonPysh'},'472f440f29ef996e92a186b8d320ff180c855903882e59d50de1b8bd5669301e':{n:'Marty Bent',i:'MB',c:'media',x:'MartyBent'},'50d94fc2d8580571ee61726abcbcfb7d8e93d66b2ed13740ad0c39cd4de10dba':{n:'American HODL',i:'AH',c:'media',x:'americanhodl8'},'1989034e56b8f606c724f45a12ce84a11841621aaf7182a1f6564f578f2571a0':{n:'Jeff Booth',i:'JB',c:'macro',x:'JeffBooth'},'a341f45ff9758f570a21b000c17d4e53a3a497c8397f26c0e6d61e5acffc7a98':{n:'Saifedean',i:'SA',c:'macro',x:'saifedean'},'5d1d83de3ee5e3009d57e4a2af8bfa4a1b5b1a58f6ec4fd290dba6e048bae9ae':{n:'Natalie Brunell',i:'NB',c:'media',x:'natbrunell'},'4523be58d395b1b196a9b8c82b038b6895cb02b683d0c253a955068dba1facd0':{n:'Michael Saylor',i:'MS',c:'macro',x:'saylor'},'58c741aa630c2da35a56a77c1d05381908bd10504b7519571f2cdae6ce2b993d':{n:'Jameson Lopp',i:'JL',c:'protocol',x:'lopp'},'edcd20558f17d99327d841e4582f9b006331ac4010571eb77dc79c55f1a295c8':{n:'Willy Woo',i:'WW',c:'macro',x:'woonomic'}};
 226 | var pks=Object.keys(V),seen={},nCt=0,xCt=0,rUp=0;
 227 | function startNostr(){RELAYS.forEach(function(url){try{var ws=new WebSocket(url);ws.onopen=function(){rUp++;updND();ws.send(JSON.stringify(["REQ","pp",{kinds:[1],authors:pks,limit:30}]))};ws.onmessage=function(e){try{var m=JSON.parse(e.data);if(m[0]==='EVENT'&&m[2]&&!seen[m[2].id]){seen[m[2].id]=1;var ev=m[2];if(ev.content&&ev.content.length>15){var isReply=ev.tags&&ev.tags.some(function(t){return t[0]==='e'});if(!isReply){addN(ev);if((ev.id.charCodeAt(0)%10)>5)addX(ev)}}}}catch(x){}};ws.onclose=function(){rUp=Math.max(0,rUp-1);updND()};ws.onerror=function(){}}catch(x){}})}
 228 | function updND(){document.getElementById('nDot').style.background=rUp>0?'var(--green)':'var(--red)'}
 229 | function mkAv(v){return '<div class="fi-av '+v.c+'">'+v.i+'</div>'}
 230 | function addN(ev){nCt++;document.getElementById('nCount').textContent=nCt;document.getElementById('liveN').textContent=nCt+xCt;var f=document.getElementById('nFeed');if(f.querySelector('.intel-empty'))f.innerHTML='';var v=V[ev.pubkey]||{n:ev.pubkey.substring(0,8)+'...',i:'??',c:'protocol'};var txt=escH(ev.content);txt=txt.replace(/(https?:\/\/[^\s<]+)/g,'<a href="$1" target="_blank">$1</a>').replace(/\n/g,'<br>');if(txt.length>400)txt=txt.substring(0,400)+'...';var el=document.createElement('div');el.className='fi new';el.innerHTML='<div class="fi-head">'+mkAv(v)+'<span class="fi-name">'+v.n+'</span><span class="fi-time">'+tAgo(ev.created_at)+'</span></div><div class="fi-body">'+txt+'</div><div class="fi-foot"><a href="https://njump.me/'+ev.id+'" target="_blank" class="fi-act"><i class="fas fa-external-link-alt"></i> nostr</a></div>';f.insertBefore(el,f.firstChild);while(f.children.length>40)f.removeChild(f.lastChild)}
 231 | function addX(ev){xCt++;document.getElementById('xCount').textContent=xCt;document.getElementById('liveN').textContent=nCt+xCt;document.getElementById('xDot').style.background='var(--green)';var f=document.getElementById('xFeed');if(f.querySelector('.intel-empty'))f.innerHTML='';var v=V[ev.pubkey]||{n:ev.pubkey.substring(0,8)+'...',i:'??',c:'protocol',x:''};var txt=escH(ev.content);txt=txt.replace(/(https?:\/\/[^\s<]+)/g,'<a href="$1" target="_blank">$1</a>').replace(/\n/g,'<br>');if(txt.length>300)txt=txt.substring(0,300)+'...';var xUrl=v.x?'https://x.com/'+v.x:'#';var el=document.createElement('div');el.className='fi new';el.innerHTML='<div class="fi-head">'+mkAv(v)+'<span class="fi-name">'+v.n+'</span><span class="fi-time">'+tAgo(ev.created_at)+'</span></div><div class="fi-body">'+txt+'</div><div class="fi-foot"><a href="'+xUrl+'" target="_blank" class="fi-act"><i class="fab fa-x-twitter"></i> @'+v.x+'</a></div>';f.insertBefore(el,f.firstChild);while(f.children.length>30)f.removeChild(f.lastChild)}
 232 | var QUOTES=[{n:'Michael Saylor',i:'MS',c:'macro',q:'Bitcoin is the apex property of the human race.',s:'What Bitcoin Did'},{n:'Lyn Alden',i:'LA',c:'macro',q:'The fiscal deficit is the single most important variable for Bitcoin price.',s:'The Investor Podcast'},{n:'Jeff Booth',i:'JB',c:'macro',q:'Technology is deflationary. Central banks print money to offset it.',s:'Bitcoin 2025'},{n:'Preston Pysh',i:'PP',c:'macro',q:'Lightning settles faster than Visa and costs less than a penny.',s:'We Study Billionaires'},{n:'Jack Dorsey',i:'JD',c:'protocol',q:'Nostr is what Twitter should have been.',s:'Nostr Dev Conf'},{n:'Adam Back',i:'AB',c:'protocol',q:'Every generation of cryptographers dreamed of digital cash. Satoshi made it work.',s:'Cypherpunk History'},{n:'Saifedean',i:'SA',c:'macro',q:'Hard money forces low time preference. Fiat money destroys it.',s:'BTC Standard Pod'},{n:'Natalie Brunell',i:'NB',c:'media',q:'Every major bank is quietly building Bitcoin infrastructure.',s:'Coin Stories'},{n:'Marty Bent',i:'MB',c:'media',q:'Bitcoin mining solves the stranded energy problem.',s:'TFTC Podcast'},{n:'American HODL',i:'AH',c:'media',q:'Two types of people: those who understand Bitcoin, and those who will.',s:'BTC Spaces'},{n:'Jameson Lopp',i:'JL',c:'protocol',q:'Self-custody is the entire point. Without it, you have nothing.',s:'Security Workshop'},{n:'Willy Woo',i:'WW',c:'macro',q:'Whales are accumulating at levels not seen since 2020.',s:'BTC Forecast'},{n:'NVK',i:'NV',c:'protocol',q:'The best hardware wallet is the one you actually use.',s:'Coldcard Update'},{n:'Fiatjaf',i:'FJ',c:'protocol',q:'Open protocols always win against closed platforms.',s:'Nostr Talk'},{n:'ODELL',i:'MO',c:'protocol',q:'Privacy is about having something to protect.',s:'Citadel Dispatch'}];
 233 | var qCt=0;function startQuotes(){var f=document.getElementById('qFeed');f.innerHTML='';var now=Math.floor(Date.now()/1000);QUOTES.forEach(function(q,i){setTimeout(function(){var el=document.createElement('div');el.className='fi new'+(i<3?' fi-pin':'');var ts=now-(i*1800);  /* deterministic stagger: 30min per quote */el.innerHTML='<div class="fi-head">'+mkAv(q)+'<span class="fi-name">'+q.n+'</span><span class="fi-time">'+tAgo(ts)+'</span></div><div class="fi-body fi-quote '+q.c+'">\"'+q.q+'\"<div class="fi-src">'+q.s+'</div></div>';f.insertBefore(el,f.firstChild);qCt++;document.getElementById('qCount').textContent=qCt;while(f.children.length>20)f.removeChild(f.lastChild)},i*500)})}
 234 | function escH(t){var d=document.createElement('div');d.appendChild(document.createTextNode(t));return d.innerHTML}
 235 | function tAgo(ts){var d=Math.floor(Date.now()/1000)-ts;if(d<60)return'now';if(d<3600)return Math.floor(d/60)+'m';if(d<86400)return Math.floor(d/3600)+'h';return Math.floor(d/86400)+'d'}
 236 | function showSeriesPanel(el,ev){if(ev){ev.preventDefault();ev.stopPropagation()}var t=el.dataset.title,a=el.dataset.author,u=el.dataset.url,c=el.dataset.color||'#333',d=el.dataset.desc,ep=parseInt(el.dataset.episodes)||0;document.getElementById('smTitle').textContent=t;document.getElementById('smAuthor').textContent=a;document.getElementById('smCover').style.background='linear-gradient(160deg,'+c+'30,'+c+'10)';document.getElementById('smDesc').textContent=d;document.getElementById('smLink').href=u;document.getElementById('smEps').textContent=ep>0?ep+' episodes available':'Episodes coming soon';document.getElementById('seriesModal').classList.add('active')}
 237 | function closeSeriesPanel(){document.getElementById('seriesModal').classList.remove('active')}
 238 | document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeSD();closeSeriesPanel()}});
 239 | startNostr();setTimeout(startQuotes,1200);
 240 | </script>
 241 | {% endblock %}
 242 | 
```

### File: services/rss_service.py (355 lines)
```
   1 | import feedparser
   2 | import requests
   3 | import logging
   4 | from datetime import datetime, timedelta
   5 | from typing import List, Dict, Optional
   6 | from app import db
   7 | import models
   8 | 
   9 | class RSSService:
  10 |     """Service for managing RSS feed synchronization and generation"""
  11 |     
  12 |     # Global filter list for content to exclude from media feeds
  13 |     EXCLUDED_SHOWS = [
  14 |         'Orange Is The Nw Jill',
  15 |         'Orange Is The New Jill',
  16 |         'orange is the nw jill',
  17 |         'orange is the new jill'
  18 |     ]
  19 |     
  20 |     def __init__(self):
  21 |         self.logger = logging.getLogger(__name__)
  22 |         
  23 |         # Your podcast RSS feeds (curated list)
  24 |         self.podcast_feeds = [
  25 |             {
  26 |                 'name': "Cypherpunk'd",
  27 |                 'url': 'https://anchor.fm/s/fa724db8/podcast/rss',
  28 |                 'category': 'Privacy & Freedom',
  29 |                 'host': 'PBX',
  30 |                 'color': '#f7931a'
  31 |             },
  32 |             {
  33 |                 'name': 'Protocol Pulse', 
  34 |                 'url': 'https://feed.podbean.com/protocolpulse/feed.xml',
  35 |                 'category': 'Bitcoin & Markets',
  36 |                 'host': 'Protocol Pulse',
  37 |                 'color': '#dc2626'
  38 |             }
  39 |         ]
  40 |         
  41 |         # Episode cache for real-time display
  42 |         self._episode_cache = {}
  43 |         self._cache_expiry = None
  44 |     
  45 |     def sync_all_feeds(self) -> Dict[str, int]:
  46 |         """Synchronize all configured podcast RSS feeds"""
  47 |         results = {}
  48 |         
  49 |         for feed_config in self.podcast_feeds:
  50 |             try:
  51 |                 count = self.sync_feed(feed_config['url'], feed_config['category'], feed_config['name'])
  52 |                 results[feed_config['name']] = count
  53 |                 self.logger.info(f"Synced {count} episodes from {feed_config['name']}")
  54 |             except Exception as e:
  55 |                 self.logger.error(f"Failed to sync {feed_config['name']}: {e}")
  56 |                 results[feed_config['name']] = 0
  57 |         
  58 |         return results
  59 |     
  60 |     def sync_feed(self, rss_url: str, category: str = "Web3", rss_source: str = "Protocol Pulse") -> int:
  61 |         """Sync individual RSS feed to database"""
  62 |         try:
  63 |             feed = feedparser.parse(rss_url)
  64 |             synced_count = 0
  65 |             
  66 |             for entry in feed.entries:
  67 |                 # Skip excluded content - HARD BLOCK on "Jill" in any form
  68 |                 if self._is_excluded_content(entry.title, rss_source):
  69 |                     continue
  70 |                 if 'jill' in entry.title.lower():
  71 |                     continue
  72 |                 
  73 |                 # Check if episode already exists
  74 |                 existing = models.Podcast.query.filter_by(
  75 |                     title=entry.title,
  76 |                     audio_url=self.extract_audio_url(entry)
  77 |                 ).first()
  78 |                 
  79 |                 if existing:
  80 |                     continue
  81 |                 
  82 |                 # Create new podcast episode
  83 |                 podcast = models.Podcast()
  84 |                 podcast.title = entry.title
  85 |                 podcast.description = self.clean_description(entry.get('description', ''))
  86 |                 podcast.host = feed.feed.get('author', 'Protocol Pulse')
  87 |                 podcast.duration = self.extract_duration(entry)
  88 |                 podcast.audio_url = self.extract_audio_url(entry)
  89 |                 podcast.cover_image_url = self.extract_cover_image(entry, feed)
  90 |                 podcast.published_date = self.parse_date(entry.get('published_parsed'))
  91 |                 podcast.category = category
  92 |                 podcast.rss_source = rss_source
  93 |                 podcast.featured = False
  94 |                 
  95 |                 db.session.add(podcast)
  96 |                 synced_count += 1
  97 |             
  98 |             db.session.commit()
  99 |             return synced_count
 100 |             
 101 |         except Exception as e:
 102 |             db.session.rollback()
 103 |             self.logger.error(f"Error syncing RSS feed {rss_url}: {e}")
 104 |             raise
 105 |     
 106 |     def extract_audio_url(self, entry) -> Optional[str]:
 107 |         """Extract audio URL from RSS entry"""
 108 |         if hasattr(entry, 'enclosures') and entry.enclosures:
 109 |             for enclosure in entry.enclosures:
 110 |                 if enclosure.type.startswith('audio/'):
 111 |                     return enclosure.href
 112 |         
 113 |         # Fallback: look for links
 114 |         if hasattr(entry, 'links'):
 115 |             for link in entry.links:
 116 |                 if link.get('type', '').startswith('audio/'):
 117 |                     return link.href
 118 |         
 119 |         return None
 120 |     
 121 |     def extract_duration(self, entry) -> str:
 122 |         """Extract episode duration from RSS entry"""
 123 |         # Check iTunes duration
 124 |         if hasattr(entry, 'itunes_duration'):
 125 |             return entry.itunes_duration
 126 |         
 127 |         # Check other duration fields
 128 |         duration_fields = ['duration', 'podcast_duration']
 129 |         for field in duration_fields:
 130 |             if hasattr(entry, field):
 131 |                 return str(getattr(entry, field))
 132 |         
 133 |         return "Unknown"
 134 |     
 135 |     def extract_cover_image(self, entry, feed) -> Optional[str]:
 136 |         """Extract cover image from RSS entry or feed"""
 137 |         # Episode-specific image
 138 |         if hasattr(entry, 'image') and entry.image.get('href'):
 139 |             return entry.image.href
 140 |         
 141 |         # iTunes image
 142 |         if hasattr(entry, 'itunes_image'):
 143 |             return entry.itunes_image
 144 |         
 145 |         # Feed-level image
 146 |         if hasattr(feed.feed, 'image') and feed.feed.image.get('href'):
 147 |             return feed.feed.image.href
 148 |         
 149 |         return None
 150 |     
 151 |     def clean_description(self, description: str) -> str:
 152 |         """Clean and truncate description"""
 153 |         import re
 154 |         # Remove HTML tags
 155 |         clean_desc = re.sub(r'<[^>]*>', '', description)
 156 |         # Limit length
 157 |         if len(clean_desc) > 500:
 158 |             clean_desc = clean_desc[:497] + "..."
 159 |         return clean_desc.strip()
 160 |     
 161 |     def _is_excluded_content(self, title: str, show_name: str = '') -> bool:
 162 |         """Check if content should be excluded based on title or show name"""
 163 |         check_text = f"{title} {show_name}".lower()
 164 |         for excluded in self.EXCLUDED_SHOWS:
 165 |             if excluded.lower() in check_text:
 166 |                 self.logger.info(f"Filtering out excluded content: {title}")
 167 |                 return True
 168 |         return False
 169 |     
 170 |     def parse_date(self, date_tuple) -> datetime:
 171 |         """Parse RSS date tuple to datetime"""
 172 |         if date_tuple:
 173 |             try:
 174 |                 import time
 175 |                 return datetime.fromtimestamp(time.mktime(date_tuple))
 176 |             except:
 177 |                 pass
 178 |         return datetime.utcnow()
 179 |     
 180 |     def generate_rss_feed(self) -> str:
 181 |         """Generate RSS feed XML for published podcasts"""
 182 |         from xml.etree.ElementTree import Element, SubElement, tostring
 183 |         from xml.dom import minidom
 184 |         
 185 |         # Get latest published podcasts
 186 |         podcasts = models.Podcast.query.order_by(models.Podcast.published_date.desc()).limit(50).all()
 187 |         
 188 |         # Create RSS XML
 189 |         rss = Element('rss', version='2.0')
 190 |         rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
 191 |         rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
 192 |         
 193 |         channel = SubElement(rss, 'channel')
 194 |         
 195 |         # Channel info
 196 |         SubElement(channel, 'title').text = 'Protocol Pulse Podcast'
 197 |         SubElement(channel, 'description').text = 'The leading podcast for Web3, Bitcoin, and blockchain insights'
 198 |         SubElement(channel, 'link').text = 'https://your-domain.com/podcasts'
 199 |         SubElement(channel, 'language').text = 'en-us'
 200 |         SubElement(channel, 'copyright').text = f'© {datetime.now().year} Protocol Pulse'
 201 |         
 202 |         # Add episodes
 203 |         for podcast in podcasts:
 204 |             item = SubElement(channel, 'item')
 205 |             SubElement(item, 'title').text = podcast.title
 206 |             SubElement(item, 'description').text = podcast.description or ""
 207 |             SubElement(item, 'link').text = f'https://your-domain.com/podcasts/{podcast.id}'
 208 |             SubElement(item, 'guid').text = f'https://your-domain.com/podcasts/{podcast.id}'
 209 |             SubElement(item, 'pubDate').text = podcast.published_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
 210 |             
 211 |             if podcast.audio_url:
 212 |                 enclosure = SubElement(item, 'enclosure')
 213 |                 enclosure.set('url', podcast.audio_url)
 214 |                 enclosure.set('type', 'audio/mpeg')
 215 |                 enclosure.set('length', '0')  # You may want to add actual file size
 216 |             
 217 |             if podcast.duration:
 218 |                 SubElement(item, 'itunes:duration').text = podcast.duration
 219 |         
 220 |         # Pretty print XML
 221 |         rough_string = tostring(rss, 'utf-8')
 222 |         reparsed = minidom.parseString(rough_string)
 223 |         return reparsed.toprettyxml(indent="  ")
 224 |     
 225 |     def get_latest_episodes(self, limit: int = 20) -> List[Dict]:
 226 |         """Get latest episodes from all feeds with caching"""
 227 |         import time
 228 |         
 229 |         # Check cache validity (15 minute cache)
 230 |         if self._cache_expiry and time.time() < self._cache_expiry and self._episode_cache:
 231 |             return list(self._episode_cache.values())[:limit]
 232 |         
 233 |         all_episodes = []
 234 |         
 235 |         for feed_config in self.podcast_feeds:
 236 |             try:
 237 |                 feed = feedparser.parse(feed_config['url'])
 238 |                 show_name = feed_config['name']
 239 |                 
 240 |                 for entry in feed.entries[:10]:  # Get latest 10 per show
 241 |                     # Skip excluded content
 242 |                     if self._is_excluded_content(entry.title, show_name):
 243 |                         continue
 244 |                     
 245 |                     episode = {
 246 |                         'id': hash(entry.get('link', entry.title))  % 100000,
 247 |                         'title': entry.title,
 248 |                         'description': self.clean_description(entry.get('description', '')),
 249 |                         'audio_url': self.extract_audio_url(entry),
 250 |                         'duration': self.extract_duration(entry),
 251 |                         'published_date': self.parse_date(entry.get('published_parsed')),
 252 |                         'cover_image': self.extract_cover_image(entry, feed),
 253 |                         'show_name': show_name,
 254 |                         'host': feed_config.get('host', 'Protocol Pulse'),
 255 |                         'category': feed_config.get('category', 'Main'),
 256 |                         'color': feed_config.get('color', '#dc2626')
 257 |                     }
 258 |                     all_episodes.append(episode)
 259 |                     
 260 |             except Exception as e:
 261 |                 self.logger.error(f"Error fetching {feed_config['name']}: {e}")
 262 |         
 263 |         # Sort by date, newest first
 264 |         all_episodes.sort(key=lambda x: x['published_date'], reverse=True)
 265 |         
 266 |         # Update cache
 267 |         self._episode_cache = {ep['id']: ep for ep in all_episodes}
 268 |         self._cache_expiry = time.time() + (15 * 60)  # 15 minutes
 269 |         
 270 |         return all_episodes[:limit]
 271 |     
 272 |     def get_show_info(self) -> List[Dict]:
 273 |         """Get information about all podcast shows"""
 274 |         shows = []
 275 |         for feed_config in self.podcast_feeds:
 276 |             try:
 277 |                 feed = feedparser.parse(feed_config['url'])
 278 |                 show = {
 279 |                     'id': feed_config['name'].lower().replace(' ', '_').replace("'", ''),
 280 |                     'name': feed_config['name'],
 281 |                     'description': feed.feed.get('description', '')[:200] if hasattr(feed, 'feed') else '',
 282 |                     'host': feed_config.get('host', 'Protocol Pulse'),
 283 |                     'category': feed_config.get('category', 'Main'),
 284 |                     'color': feed_config.get('color', '#dc2626'),
 285 |                     'episode_count': len(feed.entries) if hasattr(feed, 'entries') else 0,
 286 |                     'cover_image': self._get_feed_cover(feed),
 287 |                     'rss_url': feed_config['url']
 288 |                 }
 289 |                 shows.append(show)
 290 |             except Exception as e:
 291 |                 self.logger.error(f"Error getting show info for {feed_config['name']}: {e}")
 292 |         return shows
 293 |     
 294 |     def _get_feed_cover(self, feed) -> Optional[str]:
 295 |         """Extract cover image from feed"""
 296 |         try:
 297 |             if hasattr(feed.feed, 'image') and feed.feed.image:
 298 |                 return feed.feed.image.get('href')
 299 |             if hasattr(feed.feed, 'itunes_image'):
 300 |                 return feed.feed.itunes_image.get('href')
 301 |         except:
 302 |             pass
 303 |         return None
 304 |     
 305 |     def get_episodes_by_show(self, show_id: str, limit: int = 20) -> List[Dict]:
 306 |         """Get episodes for a specific show"""
 307 |         for feed_config in self.podcast_feeds:
 308 |             config_id = feed_config['name'].lower().replace(' ', '_').replace("'", '')
 309 |             if config_id == show_id:
 310 |                 try:
 311 |                     feed = feedparser.parse(feed_config['url'])
 312 |                     episodes = []
 313 |                     for entry in feed.entries[:limit]:
 314 |                         # Skip excluded content
 315 |                         if self._is_excluded_content(entry.title, feed_config['name']):
 316 |                             continue
 317 |                         
 318 |                         episode = {
 319 |                             'id': hash(entry.get('link', entry.title)) % 100000,
 320 |                             'title': entry.title,
 321 |                             'description': self.clean_description(entry.get('description', '')),
 322 |                             'audio_url': self.extract_audio_url(entry),
 323 |                             'duration': self.extract_duration(entry),
 324 |                             'published_date': self.parse_date(entry.get('published_parsed')),
 325 |                             'cover_image': self.extract_cover_image(entry, feed),
 326 |                             'show_name': feed_config['name'],
 327 |                             'host': feed_config.get('host', 'Protocol Pulse'),
 328 |                             'color': feed_config.get('color', '#dc2626')
 329 |                         }
 330 |                         episodes.append(episode)
 331 |                     return episodes
 332 |                 except Exception as e:
 333 |                     self.logger.error(f"Error fetching episodes for {show_id}: {e}")
 334 |         return []
 335 |     
 336 |     def clear_cache(self):
 337 |         """Clear the episode cache to force refresh"""
 338 |         self._episode_cache = {}
 339 |         self._cache_expiry = None
 340 |         self.logger.info("RSS episode cache cleared")
 341 |     
 342 |     def search_episodes(self, query: str, limit: int = 10) -> List[Dict]:
 343 |         """Search episodes by title or description"""
 344 |         all_episodes = self.get_latest_episodes(limit=50)
 345 |         query_lower = query.lower()
 346 |         results = [
 347 |             ep for ep in all_episodes
 348 |             if (query_lower in ep['title'].lower() or query_lower in ep['description'].lower())
 349 |             and not self._is_excluded_content(ep['title'], ep.get('show_name', ''))
 350 |         ]
 351 |         return results[:limit]
 352 | 
 353 | 
 354 | # Global instance for convenience
 355 | rss_service = RSSService()
```

### File: models.py (1612 lines)
```
   1 | from datetime import datetime, timedelta
   2 | from flask_login import UserMixin
   3 | from werkzeug.security import generate_password_hash, check_password_hash
   4 | from app import db  # This stays here; we will fix the 'loop' in app.py
   5 | 
   6 | # =====================================
   7 | # USER & OPERATIVE MODELS
   8 | # =====================================
   9 | 
  10 | class User(UserMixin, db.Model):
  11 |     id = db.Column(db.Integer, primary_key=True)
  12 |     username = db.Column(db.String(80), unique=True, nullable=False)
  13 |     email = db.Column(db.String(120), unique=True, nullable=False)
  14 |     password_hash = db.Column(db.String(256))
  15 |     is_admin = db.Column(db.Boolean, default=False)
  16 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  17 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  18 |     
  19 |     operative_rank = db.Column(db.Integer, default=1)
  20 |     drill_completions = db.Column(db.Integer, default=0)
  21 |     brief_clicks = db.Column(db.Integer, default=0)
  22 |     operative_slug = db.Column(db.String(100), unique=True)
  23 |     crm_synced_at = db.Column(db.DateTime)
  24 |     last_drill_at = db.Column(db.DateTime)
  25 |     last_brief_at = db.Column(db.DateTime)
  26 |     
  27 |     # Premium subscription (free | operator | commander | sovereign)
  28 |     subscription_tier = db.Column(db.String(30), default='free', index=True)  # audit P1-M2
  29 |     stripe_customer_id = db.Column(db.String(120))
  30 |     stripe_subscription_id = db.Column(db.String(120))
  31 |     subscription_expires_at = db.Column(db.DateTime)
  32 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  33 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  34 |     
  35 |     # --- Auth Methods ---
  36 |     def set_password(self, password):
  37 |         self.password_hash = generate_password_hash(password)
  38 | 
  39 |     def check_password(self, password):
  40 |         return check_password_hash(self.password_hash, password)
  41 | 
  42 |     # --- Operative Logic ---
  43 |     def get_rank_name(self):
  44 |         if self.operative_rank >= 3:
  45 |             return 'SOVEREIGN ELITE'
  46 |         elif self.operative_rank >= 2:
  47 |             return 'OPERATIVE'
  48 |         return 'RECRUIT'
  49 |     
  50 |     def check_rank_progression(self):
  51 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  52 |             self.operative_rank = 3
  53 |         elif self.drill_completions >= 1:
  54 |             self.operative_rank = 2
  55 |         else:
  56 |             self.operative_rank = 1
  57 |     
  58 |     def generate_operative_slug(self):
  59 |         import hashlib
  60 |         import time
  61 |         if not self.operative_slug:
  62 |             base = self.username.lower().replace(' ', '-')[:20]
  63 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  64 |             self.operative_slug = f"{base}-{unique_hash}"
  65 |         return self.operative_slug
  66 |     
  67 |     def can_increment_drill(self):
  68 |         if not self.last_drill_at:
  69 |             return True
  70 |         cooldown = datetime.utcnow() - self.last_drill_at
  71 |         return cooldown.total_seconds() >= 300
  72 |     
  73 |     def can_increment_brief(self):
  74 |         if not self.last_brief_at:
  75 |             return True
  76 |         cooldown = datetime.utcnow() - self.last_brief_at
  77 |         return cooldown.total_seconds() >= 60
  78 |     
  79 |     def has_premium(self):
  80 |         """True if user has any paid tier (operator, commander, sovereign)."""
  81 |         tier = getattr(self, 'subscription_tier', None)
  82 |         return tier and tier != 'free'
  83 | 
  84 |     def has_commander_tier(self):
  85 |         """True if user has $99/mo Commander (or higher) tier."""
  86 |         tier = getattr(self, 'subscription_tier', None)
  87 |         return tier in ('commander', 'sovereign')
  88 | 
  89 | 
  90 | class UserProfile(db.Model):
  91 |     __tablename__ = "user_profile"
  92 |     id = db.Column(db.Integer, primary_key=True)
  93 |     user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False, index=True)
  94 |     profile_json = db.Column(db.Text, default="{}")
  95 |     behavior_json = db.Column(db.Text, default="{}")
  96 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
  97 | 
  98 | # =====================================
  99 | # CONTENT & INTELLIGENCE MODELS
 100 | # =====================================
 101 | 
 102 | class Article(db.Model):
 103 |     __tablename__ = "articles"
 104 |     id = db.Column(db.Integer, primary_key=True)
 105 |     title = db.Column(db.String(200), nullable=False)
 106 |     content = db.Column(db.Text, nullable=False)
 107 |     summary = db.Column(db.Text)
 108 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 109 |     category = db.Column(db.String(50), default="Web3", index=True)  # audit P1-M2
 110 |     tags = db.Column(db.String(500))
 111 |     source_url = db.Column(db.String(500))
 112 |     source_type = db.Column(db.String(50))
 113 |     featured = db.Column(db.Boolean, default=False)
 114 |     published = db.Column(db.Boolean, default=False, index=True)  # audit P1-M2
 115 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 116 |     premium_tier = db.Column(db.String(30), default=None)
 117 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # audit P1-M2
 118 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 119 |     published_at = db.Column(db.DateTime, nullable=True, index=True)  # audit P1-M2
 120 |     seo_title = db.Column(db.String(200))
 121 |     seo_description = db.Column(db.String(300))
 122 |     substack_url = db.Column(db.String(500))
 123 |     header_image_url = db.Column(db.String(500))
 124 |     cover_image_url = db.Column(db.String(500))
 125 |     image_status = db.Column(db.String(30), default="ok")       # ok | needs_regen | banned | duplicate
 126 |     image_phash = db.Column(db.String(64))                      # perceptual hash hex string
 127 |     slug = db.Column(db.String(300), unique=True, index=True)
 128 | 
 129 |     @staticmethod
 130 |     def make_slug(title, article_id):
 131 |         import re as _re
 132 |         s = (title or 'article').lower().strip()
 133 |         s = _re.sub(r'[^a-z0-9\s-]', '', s)
 134 |         s = _re.sub(r'[\s]+', '-', s)
 135 |         s = _re.sub(r'-+', '-', s).strip('-')[:70].rstrip('-')
 136 |         return f'{s}-{article_id}'
 137 | 
 138 |     read_count = db.Column(db.Integer, default=0)
 139 |     fact_check_passed = db.Column(db.Boolean)
 140 |     grok_review_score = db.Column(db.Float)
 141 |     gemini_review_score = db.Column(db.Float)
 142 |     quality_tier = db.Column(db.String(30))
 143 |     content_hash = db.Column(db.String(64))
 144 |     screenshot_url = db.Column(db.String(500))
 145 |     video_url = db.Column(db.String(500))
 146 | 
 147 |     def resolve_cover_image(self):
 148 |         """Law 1: cover_image_url is the single source of truth for images."""
 149 |         import os as _os
 150 |         _app_root = _os.path.dirname(_os.path.abspath(__file__))
 151 | 
 152 |         def _valid(url):
 153 |             if not url:
 154 |                 return False
 155 |             url = url.strip()
 156 |             if url.startswith("http"):
 157 |                 return True
 158 |             if url.startswith("/static/"):
 159 |                 # Accept any local /static/ path — don't reject non-default paths
 160 |                 if "default-header" not in url:
 161 |                     return True
 162 |             return False
 163 | 
 164 |         url = (self.cover_image_url or "").strip()
 165 |         if _valid(url):
 166 |             return url
 167 |         url = (self.header_image_url or "").strip()
 168 |         if _valid(url):
 169 |             return url
 170 |         return "/static/images/default-header.png"
 171 | 
 172 |     def to_api_dict(self, include_content=False):
 173 |         """Law 2: API response dict."""
 174 |         import json as _json, re as _re
 175 |         plain = _re.sub(r'<[^>]+>', '', self.content or "").strip()
 176 |         word_count = len(plain.split()) if plain else 0
 177 |         tags = []
 178 |         if self.tags:
 179 |             try:
 180 |                 tags = _json.loads(self.tags) if self.tags.startswith('[') else [t.strip() for t in self.tags.split(',') if t.strip()]
 181 |             except Exception:
 182 |                 tags = []
 183 |         result = {
 184 |             "id": self.id,
 185 |             "title": self.title or "",
 186 |             "slug": self.slug or f"article-{self.id}",
 187 |             "summary": (self.summary or plain[:200] + ("..." if len(plain) > 200 else "")).strip(),
 188 |             "category": self.category or "Bitcoin",
 189 |             "tags": tags,
 190 |             "author": self.author or "Protocol Pulse AI",
 191 |             "cover_image_url": self.resolve_cover_image(),
 192 |             "source_url": self.source_url or "",
 193 |             "source_type": self.source_type or "",
 194 |             "published_at": self.published_at.isoformat() + "Z" if self.published_at else None,
 195 |             "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
 196 |             "read_time_minutes": max(1, word_count // 200),
 197 |         }
 198 |         if include_content:
 199 |             result["content"] = self.content or ""
 200 |         return result
 201 | 
 202 | class Podcast(db.Model):
 203 |     id = db.Column(db.Integer, primary_key=True)
 204 |     title = db.Column(db.String(200), nullable=False)
 205 |     description = db.Column(db.Text)
 206 |     host = db.Column(db.String(100))
 207 |     episode_number = db.Column(db.Integer)
 208 |     duration = db.Column(db.String(20))
 209 |     audio_url = db.Column(db.String(500))
 210 |     cover_image_url = db.Column(db.String(500))
 211 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 212 |     featured = db.Column(db.Boolean, default=False)
 213 |     category = db.Column(db.String(50), default="Web3")
 214 |     rss_source = db.Column(db.String(100))
 215 | 
 216 | class ContentPrompt(db.Model):
 217 |     id = db.Column(db.Integer, primary_key=True)
 218 |     name = db.Column(db.String(100), nullable=False)
 219 |     prompt_text = db.Column(db.Text, nullable=False)
 220 |     category = db.Column(db.String(50))
 221 |     active = db.Column(db.Boolean, default=True)
 222 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 223 | 
 224 | class Advertisement(db.Model):
 225 |     id = db.Column(db.Integer, primary_key=True)
 226 |     name = db.Column(db.String(150), nullable=False)
 227 |     image_url = db.Column(db.String(300), nullable=False)
 228 |     target_url = db.Column(db.String(300), nullable=False)
 229 |     is_active = db.Column(db.Boolean, default=False)
 230 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 231 | 
 232 | 
 233 | class AffiliateProduct(db.Model):
 234 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 235 |     __tablename__ = 'affiliate_product'
 236 |     id = db.Column(db.Integer, primary_key=True)
 237 |     name = db.Column(db.String(200), nullable=False)
 238 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 239 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 240 |     affiliate_url = db.Column(db.String(500))
 241 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 242 |     short_description = db.Column(db.String(500))
 243 |     active = db.Column(db.Boolean, default=True)
 244 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 245 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 246 | 
 247 | 
 248 | class AffiliateProductClick(db.Model):
 249 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 250 |     __tablename__ = 'affiliate_product_click'
 251 |     id = db.Column(db.Integer, primary_key=True)
 252 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 253 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 254 |     page_path = db.Column(db.String(500))
 255 |     session_id = db.Column(db.String(64))
 256 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 257 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 258 | 
 259 | 
 260 | # =====================================
 261 | # AUTOMATION & LOGISTICS
 262 | # =====================================
 263 | 
 264 | class AutomationRun(db.Model):
 265 |     id = db.Column(db.Integer, primary_key=True)
 266 |     task_name = db.Column(db.String(100), nullable=False, index=True)  # audit P1-M2
 267 |     started_at = db.Column(db.DateTime, nullable=False, index=True)  # audit P1-M2
 268 |     finished_at = db.Column(db.DateTime)
 269 |     status = db.Column(db.String(20), index=True)  # audit P1-M2
 270 |     error = db.Column(db.String(500))
 271 | 
 272 | class LaunchSequence(db.Model):
 273 |     id = db.Column(db.Integer, primary_key=True)
 274 |     content_id = db.Column(db.Integer)
 275 |     content_type = db.Column(db.String(50))
 276 |     primary_post_copy = db.Column(db.Text)
 277 |     thread_replies = db.Column(db.Text)
 278 |     quote_variants = db.Column(db.Text)
 279 |     reply_drafts = db.Column(db.Text)
 280 |     hashtags = db.Column(db.String(500))
 281 |     posting_time = db.Column(db.Time)
 282 |     velocity_prediction = db.Column(db.Float)
 283 |     first_reply_link = db.Column(db.String(500))
 284 |     call_to_action = db.Column(db.String(300))
 285 |     status = db.Column(db.String(50), default='draft', index=True)  # audit P1-M2
 286 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # audit P1-M2
 287 |     approved_at = db.Column(db.DateTime)
 288 |     published_at = db.Column(db.DateTime, index=True)  # audit P1-M2
 289 |     tweet_id = db.Column(db.String(100))
 290 |     actual_velocity_score = db.Column(db.Float)
 291 |     replies_first_5min = db.Column(db.Integer, default=0)
 292 |     total_engagement = db.Column(db.Integer, default=0)
 293 |     reached_for_you = db.Column(db.Boolean, default=False)
 294 |     dispatch_window = db.Column(db.String(20))
 295 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 296 |     persona_debate = db.Column(db.Text)
 297 |     is_autonomous = db.Column(db.Boolean, default=False)
 298 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 299 |     ground_truth = db.Column(db.Text)
 300 |     target_segment = db.Column(db.String(100))
 301 |     generated_by = db.Column(db.String(50))
 302 |     nostr_event_id = db.Column(db.String(100))
 303 |     x_tweet_id = db.Column(db.String(100))
 304 |     is_approved = db.Column(db.Boolean, default=False)
 305 |     is_posted = db.Column(db.Boolean, default=False)
 306 | 
 307 | class TargetAlert(db.Model):
 308 |     id = db.Column(db.Integer, primary_key=True)
 309 |     trigger_type = db.Column(db.String(50))
 310 |     source_url = db.Column(db.String(500))
 311 |     source_account = db.Column(db.String(100))
 312 |     content_snippet = db.Column(db.Text)
 313 |     priority = db.Column(db.Integer, default=2)
 314 |     strategy_suggested = db.Column(db.String(100))
 315 |     draft_replies = db.Column(db.Text)
 316 |     status = db.Column(db.String(50), default='pending')
 317 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 318 |     responded_at = db.Column(db.DateTime)
 319 | 
 320 | class NostrEvent(db.Model):
 321 |     id = db.Column(db.Integer, primary_key=True)
 322 |     event_id = db.Column(db.String(100))
 323 |     content_type = db.Column(db.String(50))
 324 |     content_id = db.Column(db.Integer)
 325 |     relays_success = db.Column(db.Text)
 326 |     relays_failed = db.Column(db.Text)
 327 |     zaps_received = db.Column(db.Integer, default=0)
 328 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 329 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 330 | 
 331 | class ReplySquadMember(db.Model):
 332 |     id = db.Column(db.Integer, primary_key=True)
 333 |     handle = db.Column(db.String(100), nullable=False)
 334 |     display_name = db.Column(db.String(150))
 335 |     category = db.Column(db.String(100))
 336 |     priority = db.Column(db.Integer, default=2)
 337 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 338 |     last_engagement = db.Column(db.DateTime)
 339 |     notes = db.Column(db.Text)
 340 |     active = db.Column(db.Boolean, default=True)
 341 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 342 | 
 343 | # =====================================
 344 | # BITCOIN NETWORK & DONATIONS
 345 | # =====================================
 346 | 
 347 | class WhaleTransaction(db.Model):
 348 |     id = db.Column(db.Integer, primary_key=True)
 349 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 350 |     btc_amount = db.Column(db.Float, nullable=False)
 351 |     usd_value = db.Column(db.Float)
 352 |     fee_sats = db.Column(db.Integer)
 353 |     block_height = db.Column(db.Integer)
 354 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 355 |     is_mega = db.Column(db.Boolean, default=False)
 356 | 
 357 | 
 358 | class ContactSubmission(db.Model):
 359 |     """Contact form submissions (stored for admin; optional email notification)."""
 360 |     id = db.Column(db.Integer, primary_key=True)
 361 |     name = db.Column(db.String(200), nullable=False)
 362 |     email = db.Column(db.String(200), nullable=False)
 363 |     subject = db.Column(db.String(100), nullable=False)
 364 |     message = db.Column(db.Text, nullable=False)
 365 |     ip_address = db.Column(db.String(64))
 366 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 367 |     read = db.Column(db.Boolean, default=False)
 368 | 
 369 | 
 370 | class PremiumAsk(db.Model):
 371 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 372 |     id = db.Column(db.Integer, primary_key=True)
 373 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 374 |     question_text = db.Column(db.Text, nullable=False)
 375 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 376 |     answer_text = db.Column(db.Text)
 377 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 378 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 379 |     answered_at = db.Column(db.DateTime)
 380 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 381 | 
 382 | 
 383 | class PushSubscription(db.Model):
 384 |     """Web-push subscription details for whale and system notifications."""
 385 |     __tablename__ = 'push_subscription'
 386 |     __table_args__ = (
 387 |         db.Index('idx_push_subscription_user_active', 'user_id', 'is_active'),
 388 |         db.Index('idx_push_subscription_tier', 'tier'),
 389 |     )
 390 |     id = db.Column(db.Integer, primary_key=True)
 391 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
 392 |     endpoint = db.Column(db.String(1024), nullable=False, unique=True)
 393 |     p256dh = db.Column(db.String(255))
 394 |     auth = db.Column(db.String(255))
 395 |     tier = db.Column(db.String(30), default='free')
 396 |     is_active = db.Column(db.Boolean, default=True, index=True)
 397 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 398 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 399 |     user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic'))
 400 | 
 401 | 
 402 | class BitcoinDonation(db.Model):
 403 |     id = db.Column(db.Integer, primary_key=True)
 404 |     payment_id = db.Column(db.String(100))
 405 |     amount_sats = db.Column(db.Integer)
 406 |     amount_usd = db.Column(db.Float)
 407 |     donor_email = db.Column(db.String(200))
 408 |     donor_name = db.Column(db.String(200))
 409 |     message = db.Column(db.Text)
 410 |     status = db.Column(db.String(50), default='pending')
 411 |     payment_method = db.Column(db.String(50))
 412 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 413 |     confirmed_at = db.Column(db.DateTime)
 414 | 
 415 | # =====================================
 416 | # ANALYTICS & PERFORMANCE
 417 | # =====================================
 418 | 
 419 | class EngagementEvent(db.Model):
 420 |     id = db.Column(db.Integer, primary_key=True)
 421 |     event_type = db.Column(db.String(50), nullable=False)
 422 |     content_type = db.Column(db.String(50))
 423 |     content_id = db.Column(db.Integer)
 424 |     source_platform = db.Column(db.String(50))
 425 |     source_url = db.Column(db.String(500))
 426 |     persona = db.Column(db.String(50))
 427 |     strategy = db.Column(db.String(100))
 428 |     minutes_after_post = db.Column(db.Float)
 429 |     is_30min_window = db.Column(db.Boolean, default=False)
 430 |     grok_score_contribution = db.Column(db.Integer, default=0)
 431 |     user_agent = db.Column(db.String(300))
 432 |     referrer = db.Column(db.String(500))
 433 |     ip_hash = db.Column(db.String(64))
 434 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 435 | 
 436 | class ContentPerformance(db.Model):
 437 |     id = db.Column(db.Integer, primary_key=True)
 438 |     content_type = db.Column(db.String(50), nullable=False)
 439 |     content_id = db.Column(db.Integer, nullable=False)
 440 |     content_title = db.Column(db.String(300))
 441 |     total_views = db.Column(db.Integer, default=0)
 442 |     total_clicks = db.Column(db.Integer, default=0)
 443 |     total_replies = db.Column(db.Integer, default=0)
 444 |     total_retweets = db.Column(db.Integer, default=0)
 445 |     total_quotes = db.Column(db.Integer, default=0)
 446 |     total_likes = db.Column(db.Integer, default=0)
 447 |     profile_visits = db.Column(db.Integer, default=0)
 448 |     replies_0_5min = db.Column(db.Integer, default=0)
 449 |     replies_5_15min = db.Column(db.Integer, default=0)
 450 |     replies_15_30min = db.Column(db.Integer, default=0)
 451 |     replies_30plus_min = db.Column(db.Integer, default=0)
 452 |     velocity_score = db.Column(db.Float, default=0)
 453 |     grok_score_total = db.Column(db.Integer, default=0)
 454 |     reached_for_you = db.Column(db.Boolean, default=False)
 455 |     peak_velocity_minute = db.Column(db.Integer)
 456 |     alex_engagements = db.Column(db.Integer, default=0)
 457 |     sarah_engagements = db.Column(db.Integer, default=0)
 458 |     best_performing_strategy = db.Column(db.String(100))
 459 |     best_performing_time = db.Column(db.String(20))
 460 |     published_at = db.Column(db.DateTime)
 461 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 462 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 463 | 
 464 | class AnalyticsSummary(db.Model):
 465 |     id = db.Column(db.Integer, primary_key=True)
 466 |     period_type = db.Column(db.String(20), nullable=False)
 467 |     period_start = db.Column(db.Date, nullable=False)
 468 |     period_end = db.Column(db.Date, nullable=False)
 469 |     total_posts = db.Column(db.Integer, default=0)
 470 |     total_impressions = db.Column(db.Integer, default=0)
 471 |     total_engagements = db.Column(db.Integer, default=0)
 472 |     total_profile_visits = db.Column(db.Integer, default=0)
 473 |     total_followers_gained = db.Column(db.Integer, default=0)
 474 |     avg_velocity_score = db.Column(db.Float, default=0)
 475 |     avg_grok_score = db.Column(db.Float, default=0)
 476 |     for_you_reach_rate = db.Column(db.Float, default=0)
 477 |     top_performing_content_id = db.Column(db.Integer)
 478 |     top_performing_content_type = db.Column(db.String(50))
 479 |     top_performing_strategy = db.Column(db.String(100))
 480 |     alex_total_score = db.Column(db.Integer, default=0)
 481 |     sarah_total_score = db.Column(db.Integer, default=0)
 482 |     persona_winner = db.Column(db.String(50))
 483 |     best_posting_hour = db.Column(db.Integer)
 484 |     best_posting_day = db.Column(db.Integer)
 485 |     sponsor_value_estimate = db.Column(db.Float)
 486 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 487 | 
 488 | class Sponsor(db.Model):
 489 |     id = db.Column(db.Integer, primary_key=True)
 490 |     name = db.Column(db.String(200), nullable=False)
 491 |     company = db.Column(db.String(200))
 492 |     email = db.Column(db.String(200))
 493 |     website_url = db.Column(db.String(500))
 494 |     logo_url = db.Column(db.String(500))
 495 |     tier = db.Column(db.String(50), default='standard')
 496 |     status = db.Column(db.String(50), default='pending')
 497 |     impressions = db.Column(db.Integer, default=0)
 498 |     clicks = db.Column(db.Integer, default=0)
 499 |     ctr = db.Column(db.Float, default=0)
 500 |     budget_sats = db.Column(db.Integer, default=0)
 501 |     spent_sats = db.Column(db.Integer, default=0)
 502 |     cpm_sats = db.Column(db.Integer, default=1000)
 503 |     target_categories = db.Column(db.String(500))
 504 |     target_personas = db.Column(db.String(200))
 505 |     ad_copy = db.Column(db.Text)
 506 |     cta_text = db.Column(db.String(100))
 507 |     cta_url = db.Column(db.String(500))
 508 |     start_date = db.Column(db.DateTime)
 509 |     end_date = db.Column(db.DateTime)
 510 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 511 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 512 | 
 513 | class CreditAccount(db.Model):
 514 |     id = db.Column(db.Integer, primary_key=True)
 515 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 516 |     signal_points = db.Column(db.Integer, default=0)
 517 |     lifetime_points = db.Column(db.Integer, default=0)
 518 |     tier = db.Column(db.String(50), default='recruit')
 519 |     tier_progress = db.Column(db.Float, default=0)
 520 |     articles_read = db.Column(db.Integer, default=0)
 521 |     podcasts_listened = db.Column(db.Integer, default=0)
 522 |     quizzes_completed = db.Column(db.Integer, default=0)
 523 |     referrals_made = db.Column(db.Integer, default=0)
 524 |     streak_days = db.Column(db.Integer, default=0)
 525 |     longest_streak = db.Column(db.Integer, default=0)
 526 |     last_activity = db.Column(db.DateTime)
 527 |     badges = db.Column(db.Text)
 528 |     achievements = db.Column(db.Text)
 529 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 530 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 531 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 532 | 
 533 | class PredictionOracle(db.Model):
 534 |     id = db.Column(db.Integer, primary_key=True)
 535 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 536 |     prediction_type = db.Column(db.String(50))
 537 |     prediction_value = db.Column(db.Float)
 538 |     target_date = db.Column(db.DateTime)
 539 |     actual_value = db.Column(db.Float)
 540 |     accuracy_score = db.Column(db.Float)
 541 |     status = db.Column(db.String(50), default='pending')
 542 |     is_correct = db.Column(db.Boolean)
 543 |     signal_points_wagered = db.Column(db.Integer, default=0)
 544 |     signal_points_won = db.Column(db.Integer, default=0)
 545 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 546 |     resolved_at = db.Column(db.DateTime)
 547 | 
 548 | class UserSegment(db.Model):
 549 |     id = db.Column(db.Integer, primary_key=True)
 550 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 551 |     segment_type = db.Column(db.String(50), default='general')
 552 |     confidence = db.Column(db.Float, default=0.5)
 553 |     hashrate_interest = db.Column(db.Float, default=0)
 554 |     macro_interest = db.Column(db.Float, default=0)
 555 |     technical_interest = db.Column(db.Float, default=0)
 556 |     trading_interest = db.Column(db.Float, default=0)
 557 |     privacy_interest = db.Column(db.Float, default=0)
 558 |     articles_viewed = db.Column(db.Integer, default=0)
 559 |     avg_read_time = db.Column(db.Float, default=0)
 560 |     preferred_categories = db.Column(db.Text)
 561 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 562 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 563 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 564 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 565 | 
 566 | class AffiliatePartner(db.Model):
 567 |     __tablename__ = 'affiliate_partner'
 568 |     id = db.Column(db.Integer, primary_key=True)
 569 |     name = db.Column(db.String(100), unique=True, nullable=False)
 570 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 571 |     category = db.Column(db.String(50))
 572 |     url = db.Column(db.String(500))
 573 |     benefit = db.Column(db.String(200))
 574 |     is_active = db.Column(db.Boolean, default=True)
 575 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 576 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 577 | 
 578 | class AffiliateClick(db.Model):
 579 |     __tablename__ = 'affiliate_click'
 580 |     id = db.Column(db.Integer, primary_key=True)
 581 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 582 |     source_page = db.Column(db.String(500))
 583 |     ip_hash = db.Column(db.String(64))
 584 |     user_agent = db.Column(db.String(500))
 585 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 586 | 
 587 | 
 588 | class PartnerClick(db.Model):
 589 |     """Hub partner-ramp click tracking (thin-slice V1)."""
 590 |     __tablename__ = 'partner_click'
 591 |     __table_args__ = (
 592 |         db.Index('idx_partner_click_slug_time', 'partner_slug', 'created_at'),
 593 |         db.Index('idx_partner_click_session_token', 'session_token'),
 594 |     )
 595 |     id = db.Column(db.Integer, primary_key=True)
 596 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 597 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=True)
 598 |     partner_slug = db.Column(db.String(80), nullable=False, index=True)
 599 |     session_id = db.Column(db.String(64), nullable=False, index=True)
 600 |     # Unified alias for cross-device analytics and attribution joins.
 601 |     session_token = db.Column(db.String(64), index=True)
 602 |     referral_code = db.Column(db.String(120))
 603 |     source_page = db.Column(db.String(500))
 604 |     conversion_status = db.Column(db.String(30), default='pending', index=True)
 605 |     converted_at = db.Column(db.DateTime)
 606 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 607 | 
 608 | class ClipJob(db.Model):
 609 |     __tablename__ = 'clip_job'
 610 |     # NOTE: This model started life as the "Batch 1" clip planner with
 611 |     # timestamps_json + narrative_context. We keep those columns for backwards
 612 |     # compatibility, and add the V2 fields used by the Viral Clip Compilation tool.
 613 |     id = db.Column(db.Integer, primary_key=True)
 614 |     video_id = db.Column(db.String(100), nullable=False, index=True)
 615 | 
 616 |     # Legacy planner payload: JSON list of {start,end,context} and a narrative blurb.
 617 |     # These are NOT NULL in the existing SQLite schema, so new writers should still
 618 |     # populate them even if they primarily use the V2 fields.
 619 |     timestamps_json = db.Column(db.Text, nullable=False)
 620 |     narrative_context = db.Column(db.Text, nullable=False)
 621 | 
 622 |     # V2 fields (nullable so existing DB rows remain valid after migration).
 623 |     channel_name = db.Column(db.String(200), nullable=True, index=True)
 624 |     segments_json = db.Column(db.Text, nullable=True)  # JSON list of segments for reel compilation
 625 |     narration_path = db.Column(db.String(1000), nullable=True)
 626 |     output_path = db.Column(db.String(1000), nullable=True)
 627 |     metadata_json = db.Column(db.Text, nullable=True)  # JSON dict for engine metadata
 628 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 629 | 
 630 |     status = db.Column(db.String(20), default='Planned', index=True)  # Planned/Processing/Completed/Failed
 631 | 
 632 | 
 633 | class PartnerConversionNote(db.Model):
 634 |     """Admin notes for partner performance and conversion context."""
 635 |     __tablename__ = 'partner_conversion_note'
 636 |     id = db.Column(db.Integer, primary_key=True)
 637 |     partner_slug = db.Column(db.String(80), nullable=False, index=True)
 638 |     note = db.Column(db.Text, nullable=False)
 639 |     created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 640 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 641 | 
 642 | 
 643 | class Lead(db.Model):
 644 |     """Sovereign Intake lead profile used by onboarding funnel and CRM export."""
 645 |     __tablename__ = 'lead'
 646 |     __table_args__ = (
 647 |         db.Index('idx_lead_interest_capacity', 'interest_level', 'capacity_score'),
 648 |         db.Index('idx_lead_created', 'created_at'),
 649 |     )
 650 |     id = db.Column(db.Integer, primary_key=True)
 651 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 652 |     email = db.Column(db.String(150), index=True)
 653 |     name = db.Column(db.String(120))
 654 |     interest_level = db.Column(db.String(40), default='unknown', index=True)
 655 |     capacity_score = db.Column(db.Float, default=0.0, index=True)
 656 |     btc_profile = db.Column(db.String(60), default='off-zero', index=True)  # off-zero, sovereign-builder, autism-maxxer
 657 |     newsletter_opt_in = db.Column(db.Boolean, default=False, index=True)
 658 |     funnel_stage = db.Column(db.String(40), default='attention', index=True)
 659 |     status = db.Column(db.String(40), default='prospect', index=True)  # prospect|commander
 660 |     source = db.Column(db.String(80), default='onboarding')
 661 |     notes = db.Column(db.Text)
 662 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 663 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 664 | 
 665 | 
 666 | class SentryJob(db.Model):
 667 |     """Megaphone (Sentry V1): single social draft/queued post for DRY-RUN logging."""
 668 |     __tablename__ = 'sentry_job'
 669 |     __table_args__ = (db.Index('idx_sentry_job_status', 'status'),)
 670 |     id = db.Column(db.Integer, primary_key=True)
 671 |     content = db.Column(db.Text, nullable=False)
 672 |     platform = db.Column(db.String(50), nullable=False)  # X, Nostr, or X,Nostr
 673 |     status = db.Column(db.String(20), default='Draft', index=True)  # Draft | Queued | Written
 674 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 675 | 
 676 | 
 677 | class SentryQueue(db.Model):
 678 |     """Outbound social queue for Sentry Hub orchestration (DRY_RUN aware)."""
 679 |     __tablename__ = 'sentry_queue'
 680 |     __table_args__ = (
 681 |         db.Index('idx_sentry_queue_status_schedule', 'status', 'scheduled_at'),
 682 |         db.Index('idx_sentry_queue_created', 'created_at'),
 683 |     )
 684 |     id = db.Column(db.Integer, primary_key=True)
 685 |     content = db.Column(db.Text, nullable=False)
 686 |     platforms_json = db.Column(db.Text, nullable=False)  # e.g. ["x","nostr"]
 687 |     scheduled_at = db.Column(db.DateTime, index=True)
 688 |     status = db.Column(db.String(20), default='pending', index=True)  # pending, draft, posted, failed
 689 |     dry_run = db.Column(db.Boolean, default=True, index=True)
 690 |     source = db.Column(db.String(80), default='sentry_hub')
 691 |     created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 692 |     posted_at = db.Column(db.DateTime)
 693 |     error = db.Column(db.String(500))
 694 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 695 | 
 696 | class FeedItem(db.Model):
 697 |     __tablename__ = 'feed_item'
 698 |     id = db.Column(db.Integer, primary_key=True)
 699 |     source = db.Column(db.String(100), nullable=False)
 700 |     source_type = db.Column(db.String(50), nullable=False)
 701 |     tier = db.Column(db.String(20))
 702 |     title = db.Column(db.String(500))
 703 |     url = db.Column(db.String(1000), unique=True)
 704 |     published_at = db.Column(db.DateTime)
 705 |     author = db.Column(db.String(100))
 706 |     summary = db.Column(db.Text)
 707 |     platform_icon = db.Column(db.String(50))
 708 |     raw_json = db.Column(db.Text)
 709 |     verified = db.Column(db.Boolean, default=False)
 710 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 711 | 
 712 | class SentimentSnapshot(db.Model):
 713 |     __tablename__ = 'sentiment_snapshot'
 714 |     id = db.Column(db.Integer, primary_key=True)
 715 |     score = db.Column(db.Float, default=50.0)
 716 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 717 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 718 |     state_color = db.Column(db.String(20), default='#ffffff')
 719 |     velocity = db.Column(db.Float, default=0.0)
 720 |     top_keywords = db.Column(db.Text)
 721 |     top_topics_json = db.Column(db.Text)
 722 |     sample_size = db.Column(db.Integer, default=0)
 723 |     verified_weight = db.Column(db.Integer, default=0)
 724 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 725 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 726 | 
 727 | class PulseEvent(db.Model):
 728 |     __tablename__ = 'pulse_event'
 729 |     id = db.Column(db.Integer, primary_key=True)
 730 |     event_type = db.Column(db.String(50), nullable=False)
 731 |     from_state = db.Column(db.String(50))
 732 |     to_state = db.Column(db.String(50))
 733 |     score = db.Column(db.Float)
 734 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 735 |     payload_json = db.Column(db.Text)
 736 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 737 | 
 738 | class AutoPostDraft(db.Model):
 739 |     __tablename__ = 'autopost_draft'
 740 |     id = db.Column(db.Integer, primary_key=True)
 741 |     platform = db.Column(db.String(30), nullable=False)
 742 |     status = db.Column(db.String(20), default='draft')
 743 |     body = db.Column(db.Text)
 744 |     reason = db.Column(db.String(200))
 745 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 746 |     approved_at = db.Column(db.DateTime)
 747 |     posted_at = db.Column(db.DateTime)
 748 | 
 749 | class DailyBrief(db.Model):
 750 |     __tablename__ = 'daily_brief'
 751 |     id = db.Column(db.Integer, primary_key=True)
 752 |     headline = db.Column(db.String(500))
 753 |     body = db.Column(db.Text)
 754 |     signals_json = db.Column(db.Text)
 755 |     status = db.Column(db.String(20), default='draft')
 756 |     published_at = db.Column(db.DateTime)
 757 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 758 | 
 759 | class PageView(db.Model):
 760 |     __tablename__ = 'page_view'
 761 |     id = db.Column(db.Integer, primary_key=True)
 762 |     page_path = db.Column(db.String(500), nullable=False)
 763 |     page_title = db.Column(db.String(300))
 764 |     page_category = db.Column(db.String(50))
 765 |     session_id = db.Column(db.String(64))
 766 |     ip_hash = db.Column(db.String(64))
 767 |     user_agent = db.Column(db.String(300))
 768 |     referrer = db.Column(db.String(500))
 769 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 770 |     time_on_page = db.Column(db.Integer, default=0)
 771 |     scroll_depth = db.Column(db.Integer, default=0)
 772 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 773 | 
 774 | class HotMoment(db.Model):
 775 |     __tablename__ = 'hot_moment'
 776 |     id = db.Column(db.Integer, primary_key=True)
 777 |     page_path = db.Column(db.String(500), nullable=False)
 778 |     page_title = db.Column(db.String(300))
 779 |     page_category = db.Column(db.String(50))
 780 |     views_in_window = db.Column(db.Integer, default=0)
 781 |     unique_visitors = db.Column(db.Integer, default=0)
 782 |     heat_score = db.Column(db.Float, default=0)
 783 |     is_peak = db.Column(db.Boolean, default=False)
 784 |     peak_detected_at = db.Column(db.DateTime)
 785 |     tweet_drafted = db.Column(db.Boolean, default=False)
 786 |     tweet_content = db.Column(db.Text)
 787 |     tweet_posted_at = db.Column(db.DateTime)
 788 |     window_start = db.Column(db.DateTime, nullable=False)
 789 |     window_end = db.Column(db.DateTime, nullable=False)
 790 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 791 | 
 792 | class ContentSuggestion(db.Model):
 793 |     __tablename__ = 'content_suggestion'
 794 |     id = db.Column(db.Integer, primary_key=True)
 795 |     suggestion_type = db.Column(db.String(50))
 796 |     title = db.Column(db.String(300))
 797 |     description = db.Column(db.Text)
 798 |     reasoning = db.Column(db.Text)
 799 |     based_on_page = db.Column(db.String(500))
 800 |     based_on_trend = db.Column(db.String(200))
 801 |     confidence_score = db.Column(db.Float, default=0)
 802 |     status = db.Column(db.String(20), default='pending')
 803 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 804 |     actioned_at = db.Column(db.DateTime)
 805 | 
 806 | class AutoTweet(db.Model):
 807 |     __tablename__ = 'auto_tweet'
 808 |     id = db.Column(db.Integer, primary_key=True)
 809 |     trigger_type = db.Column(db.String(50))
 810 |     trigger_page = db.Column(db.String(500))
 811 |     heat_score_at_trigger = db.Column(db.Float)
 812 |     tweet_content = db.Column(db.Text, nullable=False)
 813 |     hashtags = db.Column(db.String(200))
 814 |     status = db.Column(db.String(20), default='draft')
 815 |     approved_at = db.Column(db.DateTime)
 816 |     posted_at = db.Column(db.DateTime)
 817 |     post_url = db.Column(db.String(500))
 818 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 819 | 
 820 | 
 821 | # =====================================
 822 | # X ENGAGEMENT SENTRY MODELS
 823 | # =====================================
 824 | 
 825 | class XInboxTweet(db.Model):
 826 |     __tablename__ = 'x_inbox_tweet'
 827 |     __table_args__ = (db.Index('idx_x_inbox_status_created', 'status', 'created_at'),)
 828 | 
 829 |     id = db.Column(db.Integer, primary_key=True)
 830 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
 831 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 832 |     author_name = db.Column(db.String(100))
 833 |     tweet_text = db.Column(db.Text, nullable=False)
 834 |     tweet_url = db.Column(db.String(500))
 835 |     tweet_created_at = db.Column(db.DateTime)
 836 |     status = db.Column(db.String(20), default='new', index=True)
 837 |     tier = db.Column(db.String(30))
 838 |     style = db.Column(db.String(30))
 839 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 840 | 
 841 | 
 842 | class XReplyDraft(db.Model):
 843 |     __tablename__ = 'x_reply_draft'
 844 |     __table_args__ = (db.Index('idx_x_reply_draft_confidence', 'confidence'),)
 845 | 
 846 |     id = db.Column(db.Integer, primary_key=True)
 847 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False, index=True)
 848 |     draft_text = db.Column(db.String(300), nullable=False)
 849 |     confidence = db.Column(db.Float)
 850 |     reasoning = db.Column(db.Text)
 851 |     style_used = db.Column(db.String(30))
 852 |     risk_flags = db.Column(db.Text)
 853 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 854 | 
 855 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 856 | 
 857 | 
 858 | class XReplyPost(db.Model):
 859 |     __tablename__ = 'x_reply_post'
 860 |     __table_args__ = (db.Index('idx_x_reply_post_posted_at', 'posted_at'),)
 861 | 
 862 |     id = db.Column(db.Integer, primary_key=True)
 863 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False, index=True)
 864 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 865 |     reply_tweet_id = db.Column(db.String(64), index=True)
 866 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 867 |     response_payload = db.Column(db.Text)
 868 | 
 869 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 870 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 871 | 
 872 | 
 873 | class MiningSnapshot(db.Model):
 874 |     __tablename__ = 'mining_snapshot'
 875 |     __table_args__ = (db.Index('idx_mining_snapshot_location_captured', 'location_id', 'captured_at'),)
 876 | 
 877 |     id = db.Column(db.Integer, primary_key=True)
 878 |     location_id = db.Column(db.String(80), nullable=False, index=True)
 879 |     location_name = db.Column(db.String(120))
 880 |     overall_score = db.Column(db.Float, nullable=False)
 881 |     political_score = db.Column(db.Float, default=0)
 882 |     economic_score = db.Column(db.Float, default=0)
 883 |     operational_score = db.Column(db.Float, default=0)
 884 |     factors_json = db.Column(db.Text)
 885 |     captured_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
 886 | 
 887 | # =====================================
 888 | # VALUE STREAM MODELS
 889 | # =====================================
 890 | 
 891 | class ValueCreator(db.Model):
 892 |     __tablename__ = 'value_creator'
 893 |     id = db.Column(db.Integer, primary_key=True)
 894 |     display_name = db.Column(db.String(100), nullable=False)
 895 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 896 |     lightning_address = db.Column(db.String(200))
 897 |     nip05 = db.Column(db.String(200))
 898 |     twitter_handle = db.Column(db.String(50))
 899 |     youtube_channel_id = db.Column(db.String(50))
 900 |     reddit_username = db.Column(db.String(50))
 901 |     stacker_news_username = db.Column(db.String(50))
 902 |     profile_image = db.Column(db.String(500))
 903 |     bio = db.Column(db.Text)
 904 |     total_sats_received = db.Column(db.BigInteger, default=0)
 905 |     total_zaps = db.Column(db.Integer, default=0)
 906 |     curator_score = db.Column(db.Float, default=0)
 907 |     verified = db.Column(db.Boolean, default=False)
 908 |     verified_at = db.Column(db.DateTime)
 909 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 910 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 911 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 912 |                                      foreign_keys='CuratedPost.creator_id')
 913 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 914 |                                        foreign_keys='CuratedPost.curator_id')
 915 | 
 916 | class CuratedPost(db.Model):
 917 |     __tablename__ = 'curated_post'
 918 |     id = db.Column(db.Integer, primary_key=True)
 919 |     platform = db.Column(db.String(30), nullable=False)
 920 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 921 |     original_id = db.Column(db.String(200))
 922 |     title = db.Column(db.String(500))
 923 |     content_preview = db.Column(db.Text)
 924 |     thumbnail_url = db.Column(db.String(500))
 925 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 926 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 927 |     total_sats = db.Column(db.BigInteger, default=0)
 928 |     zap_count = db.Column(db.Integer, default=0)
 929 |     boost_sats = db.Column(db.BigInteger, default=0)
 930 |     signal_score = db.Column(db.Float, default=0)
 931 |     decay_factor = db.Column(db.Float, default=1.0)
 932 |     is_verified = db.Column(db.Boolean, default=False)
 933 |     is_featured = db.Column(db.Boolean, default=False)
 934 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 935 |     last_zap_at = db.Column(db.DateTime)
 936 |     
 937 |     def calculate_signal_score(self):
 938 |         if self.submitted_at is None:
 939 |             self.submitted_at = datetime.utcnow()
 940 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 941 |         time_decay = max(0.1, 1 - (age_hours / 168))
 942 |         raw_score = (self.total_sats or 0) * 0.001 + (self.zap_count or 0) * 10
 943 |         self.signal_score = raw_score * time_decay * (self.decay_factor or 1.0)
 944 |         return self.signal_score
 945 | 
 946 | class ZapEvent(db.Model):
 947 |     __tablename__ = 'zap_event'
 948 |     id = db.Column(db.Integer, primary_key=True)
 949 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 950 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 951 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 952 |     creator_share = db.Column(db.BigInteger)
 953 |     curator_share = db.Column(db.BigInteger)
 954 |     platform_share = db.Column(db.BigInteger)
 955 |     payment_hash = db.Column(db.String(128))
 956 |     bolt11_invoice = db.Column(db.Text)
 957 |     preimage = db.Column(db.String(128))
 958 |     status = db.Column(db.String(20), default='pending')
 959 |     source = db.Column(db.String(30))
 960 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 961 |     settled_at = db.Column(db.DateTime)
 962 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 963 | 
 964 | 
 965 | class ClaimPayout(db.Model):
 966 |     """Sovereign Claim Portal: payout history to prevent double-spend and enforce rate limit."""
 967 |     __tablename__ = 'claim_payout'
 968 |     id = db.Column(db.Integer, primary_key=True)
 969 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 970 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 971 |     lightning_address = db.Column(db.String(200))
 972 |     claimed_by_pubkey = db.Column(db.String(128), nullable=False, index=True)  # Nostr pubkey who claimed
 973 |     status = db.Column(db.String(20), default='pending')  # pending, sent, failed
 974 |     payment_hash = db.Column(db.String(128))
 975 |     error_message = db.Column(db.String(500))
 976 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 977 |     settled_at = db.Column(db.DateTime)
 978 |     creator = db.relationship('ValueCreator', backref=db.backref('claim_payouts', lazy='dynamic'))
 979 | 
 980 | 
 981 | # =====================================
 982 | # SOVEREIGN INTELLIGENCE NEXUS
 983 | # =====================================
 984 | 
 985 | class KOLPulseItem(db.Model):
 986 |     """Live feed item from KOLs: X, Nostr, YouTube. Command Log / Pulse stream."""
 987 |     __tablename__ = 'kol_pulse_item'
 988 |     id = db.Column(db.Integer, primary_key=True)
 989 |     platform = db.Column(db.String(20), nullable=False, index=True)  # x, nostr, youtube
 990 |     author_handle = db.Column(db.String(100), nullable=False, index=True)
 991 |     author_name = db.Column(db.String(200))
 992 |     content = db.Column(db.Text)
 993 |     url = db.Column(db.String(1000))
 994 |     external_id = db.Column(db.String(128), unique=True, nullable=False, index=True)  # tweet_id, note_id, video_id
 995 |     raw_json = db.Column(db.Text)
 996 |     fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
 997 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 998 | 
 999 | 
1000 | class ZapCommentLog(db.Model):
1001 |     """Log of automated X/Nostr replies posted after a zap (Diplomat bridge)."""
1002 |     __tablename__ = 'zap_comment_log'
1003 |     id = db.Column(db.Integer, primary_key=True)
1004 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
1005 |     zap_event_id = db.Column(db.Integer, db.ForeignKey('zap_event.id'))
1006 |     platform = db.Column(db.String(20), nullable=False)  # x, nostr
1007 |     external_id = db.Column(db.String(128))  # tweet_id or note_id we replied to
1008 |     reply_id = db.Column(db.String(128))  # our reply tweet/note id
1009 |     message = db.Column(db.Text)
1010 |     claim_url = db.Column(db.String(500))
1011 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1012 |     post = db.relationship('CuratedPost', backref=db.backref('zap_comments', lazy='dynamic'))
1013 | 
1014 | 
1015 | class DailyMedley(db.Model):
1016 |     """Pinned Daily Value Medley: top-zapped clips spliced + narrated. Featured at top of stream."""
1017 |     __tablename__ = 'daily_medley'
1018 |     id = db.Column(db.Integer, primary_key=True)
1019 |     title = db.Column(db.String(300), nullable=False)
1020 |     description = db.Column(db.Text)
1021 |     media_url = db.Column(db.String(500))  # uploaded video URL
1022 |     source_post_ids = db.Column(db.Text)  # JSON array of curated_post ids
1023 |     published_at = db.Column(db.DateTime)
1024 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1025 | 
1026 | 
1027 | class PartnerHighlightReel(db.Model):
1028 |     """
1029 |     Draft-only partner highlight reels for manual review.
1030 | 
1031 |     story_json format:
1032 |     [
1033 |       {
1034 |         "channel": "Coin Bureau",
1035 |         "video_id": "...",
1036 |         "video_title": "...",
1037 |         "start": 320.0,
1038 |         "end": 380.0,
1039 |         "topic": "ETF flows",
1040 |         "role": "setup",
1041 |         "pre_commentary_audio": "path/to/pre_intro.mp3",
1042 |         "clip_video": "path/to/raw_clip.mp4",
1043 |         "post_commentary_audio": "path/to/post_outro.mp3"
1044 |       }
1045 |     ]
1046 |     """
1047 |     __tablename__ = 'partner_highlight_reel'
1048 |     id = db.Column(db.Integer, primary_key=True)
1049 |     date = db.Column(db.Date, nullable=False, index=True)
1050 |     theme = db.Column(db.String(200))
1051 |     story_json = db.Column(db.Text)
1052 |     video_path = db.Column(db.String(500))
1053 |     audio_path = db.Column(db.String(500))
1054 |     clips_json = db.Column(db.Text)
1055 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1056 |     source_summary = db.Column(db.Text)
1057 |     status = db.Column(db.String(50), default="draft")
1058 | 
1059 | 
1060 | class PartnerVideo(db.Model):
1061 |     """Harvested partner video metadata used by Pulse Drop timestamp extraction."""
1062 |     __tablename__ = 'partner_video'
1063 |     id = db.Column(db.Integer, primary_key=True)
1064 |     channel_name = db.Column(db.String(200), index=True)
1065 |     channel_id = db.Column(db.String(80), index=True)
1066 |     video_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
1067 |     title = db.Column(db.String(500))
1068 |     description = db.Column(db.Text)
1069 |     thumbnail = db.Column(db.String(1000))
1070 |     published_at = db.Column(db.DateTime, index=True)
1071 |     harvested_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
1072 | 
1073 | 
1074 | class PulseSegment(db.Model):
1075 |     """Narrative-ready timestamp segment from partner video descriptions."""
1076 |     __tablename__ = 'pulse_segment'
1077 |     id = db.Column(db.Integer, primary_key=True)
1078 |     partner_video_id = db.Column(db.Integer, db.ForeignKey('partner_video.id'), nullable=False, index=True)
1079 |     video_id = db.Column(db.String(30), nullable=False, index=True)
1080 |     start_sec = db.Column(db.Integer, nullable=False)
1081 |     label = db.Column(db.String(300))
1082 |     priority = db.Column(db.Float, default=0.0, index=True)
1083 |     intelligence_brief = db.Column(db.Text)
1084 |     commentary_audio = db.Column(db.String(500))
1085 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
1086 |     partner_video = db.relationship('PartnerVideo', backref=db.backref('pulse_segments', lazy='dynamic'))
1087 | 
1088 | 
1089 | class TrustEdge(db.Model):
1090 |     __tablename__ = 'trust_edge'
1091 |     id = db.Column(db.Integer, primary_key=True)
1092 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
1093 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
1094 |     trust_weight = db.Column(db.Float, default=1.0)
1095 |     total_sats_via = db.Column(db.BigInteger, default=0)
1096 |     successful_curations = db.Column(db.Integer, default=0)
1097 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1098 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
1099 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
1100 | 
1101 | class BoostStake(db.Model):
1102 |     __tablename__ = 'boost_stake'
1103 |     id = db.Column(db.Integer, primary_key=True)
1104 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
1105 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
1106 |     amount_sats = db.Column(db.BigInteger, nullable=False)
1107 |     boost_multiplier = db.Column(db.Float, default=1.0)
1108 |     expires_at = db.Column(db.DateTime)
1109 |     refunded = db.Column(db.Boolean, default=False)
1110 |     refund_amount = db.Column(db.BigInteger, default=0)
1111 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1112 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
1113 | 
1114 | class ExtensionSession(db.Model):
1115 |     __tablename__ = 'extension_session'
1116 |     id = db.Column(db.Integer, primary_key=True)
1117 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
1118 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
1119 |     browser_fingerprint = db.Column(db.String(128))
1120 |     user_agent = db.Column(db.String(500))
1121 |     is_active = db.Column(db.Boolean, default=True)
1122 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
1123 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1124 |     expires_at = db.Column(db.DateTime)
1125 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
1126 | 
1127 | class RollingActivity(db.Model):
1128 |     __tablename__ = 'rolling_activity'
1129 |     id = db.Column(db.Integer, primary_key=True)
1130 |     page_path = db.Column(db.String(500), nullable=False, index=True)
1131 |     page_name = db.Column(db.String(200))
1132 |     session_hash = db.Column(db.String(64), nullable=False)
1133 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
1134 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1135 |     
1136 |     @classmethod
1137 |     def record_activity(cls, page_path, page_name, session_hash):
1138 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
1139 |         if existing:
1140 |             existing.last_seen = datetime.utcnow()
1141 |         else:
1142 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
1143 |             db.session.add(activity)
1144 |         try:
1145 |             db.session.commit()
1146 |         except Exception:
1147 |             db.session.rollback()
1148 | 
1149 |     @classmethod
1150 |     def get_operative_density(cls, window_minutes=30, limit=5):
1151 |         from sqlalchemy import func
1152 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
1153 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
1154 |         return results
1155 | 
1156 | class RealTimeProduct(db.Model):
1157 |     __tablename__ = 'realtime_product'
1158 |     id = db.Column(db.Integer, primary_key=True)
1159 |     statement_text = db.Column(db.String(100), nullable=False)
1160 |     design_url = db.Column(db.String(500))
1161 |     design_style = db.Column(db.String(50), default='center_chest')
1162 |     text_color = db.Column(db.String(20), default='#FFFFFF')
1163 |     trigger_state = db.Column(db.String(50))
1164 |     trigger_keywords = db.Column(db.Text)
1165 |     sentiment_score = db.Column(db.Float)
1166 |     status = db.Column(db.String(20), default='draft')
1167 |     approved_at = db.Column(db.DateTime)
1168 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
1169 |     printful_product_id = db.Column(db.String(100))
1170 |     printful_sync_status = db.Column(db.String(50), default='pending')
1171 |     heat_multiplier = db.Column(db.Float, default=2.0)
1172 |     heat_expires_at = db.Column(db.DateTime)
1173 |     sarah_description = db.Column(db.Text)
1174 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1175 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
1176 |     
1177 |     def is_hot(self):
1178 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
1179 | 
1180 | class IntelligencePost(db.Model):
1181 |     id = db.Column(db.Integer, primary_key=True)
1182 |     persona = db.Column(db.String(20))
1183 |     partner_name = db.Column(db.String(100))
1184 |     partner_handle = db.Column(db.String(100))
1185 |     primary_tweet = db.Column(db.Text, nullable=False)
1186 |     thread_content = db.Column(db.Text)
1187 |     key_insight = db.Column(db.Text)
1188 |     source_video_id = db.Column(db.String(50))
1189 |     source_video_title = db.Column(db.String(500))
1190 |     x_tweet_id = db.Column(db.String(100))
1191 |     nostr_event_id = db.Column(db.String(100))
1192 |     engagement_likes = db.Column(db.Integer, default=0)
1193 |     engagement_retweets = db.Column(db.Integer, default=0)
1194 |     engagement_replies = db.Column(db.Integer, default=0)
1195 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
1196 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1197 | 
1198 | class SentimentReport(db.Model):
1199 |     id = db.Column(db.Integer, primary_key=True)
1200 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
1201 |     report_date = db.Column(db.Date, nullable=False, unique=True)
1202 |     overall_sentiment = db.Column(db.String(20))
1203 |     sentiment_score = db.Column(db.Float)
1204 |     x_posts_analyzed = db.Column(db.Integer, default=0)
1205 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
1206 |     top_themes = db.Column(db.Text)
1207 |     key_narratives = db.Column(db.Text)
1208 |     cited_sources = db.Column(db.Text)
1209 |     raw_analysis = db.Column(db.Text)
1210 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1211 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
1212 | 
1213 | class SarahBrief(db.Model):
1214 |     __tablename__ = 'sarah_brief'
1215 |     id = db.Column(db.Integer, primary_key=True)
1216 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
1217 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
1218 |     macro_state = db.Column(db.Text)
1219 |     network_calibration = db.Column(db.Text)
1220 |     signal_1_title = db.Column(db.String(500))
1221 |     signal_1_source = db.Column(db.String(500))
1222 |     signal_1_url = db.Column(db.String(500))
1223 |     signal_1_impact = db.Column(db.Float, default=0.0)
1224 |     signal_2_title = db.Column(db.String(500))
1225 |     signal_2_source = db.Column(db.String(500))
1226 |     signal_2_url = db.Column(db.String(500))
1227 |     signal_2_impact = db.Column(db.Float, default=0.0)
1228 |     signal_3_title = db.Column(db.String(500))
1229 |     signal_3_source = db.Column(db.String(500))
1230 |     signal_3_url = db.Column(db.String(500))
1231 |     signal_3_impact = db.Column(db.Float, default=0.0)
1232 |     mempool_state = db.Column(db.Text)
1233 |     hashrate_state = db.Column(db.Text)
1234 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1235 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
1236 | 
1237 | class SentimentBuffer(db.Model):
1238 |     id = db.Column(db.Integer, primary_key=True)
1239 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
1240 |     sentiment_score = db.Column(db.Float, nullable=False)
1241 |     post_count = db.Column(db.Integer, default=0)
1242 |     dominant_theme = db.Column(db.String(200))
1243 |     source_breakdown = db.Column(db.Text)
1244 | 
1245 | class EmergencyFlash(db.Model):
1246 |     id = db.Column(db.Integer, primary_key=True)
1247 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
1248 |     previous_score = db.Column(db.Float)
1249 |     current_score = db.Column(db.Float)
1250 |     drift_magnitude = db.Column(db.Float)
1251 |     direction = db.Column(db.String(20))
1252 |     trigger_reason = db.Column(db.Text)
1253 |     top_signal_url = db.Column(db.String(500))
1254 |     top_signal_author = db.Column(db.String(200))
1255 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
1256 |     acknowledged = db.Column(db.Boolean, default=False)
1257 |     acknowledged_at = db.Column(db.DateTime)
1258 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
1259 | 
1260 | class CollectedSignal(db.Model):
1261 |     __tablename__ = 'collected_signal'
1262 |     id = db.Column(db.Integer, primary_key=True)
1263 |     platform = db.Column(db.String(20), nullable=False)
1264 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
1265 |     author_name = db.Column(db.String(200), nullable=False)
1266 |     author_handle = db.Column(db.String(100), nullable=False)
1267 |     author_tier = db.Column(db.String(50), default='general')
1268 |     content = db.Column(db.Text, nullable=False)
1269 |     url = db.Column(db.String(500), nullable=False)
1270 |     engagement_likes = db.Column(db.Integer, default=0)
1271 |     engagement_reposts = db.Column(db.Integer, default=0)
1272 |     engagement_replies = db.Column(db.Integer, default=0)
1273 |     engagement_score = db.Column(db.Float, default=0.0)
1274 |     sentiment = db.Column(db.String(20))
1275 |     sentiment_score = db.Column(db.Float)
1276 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
1277 |     posted_at = db.Column(db.DateTime)
1278 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
1279 |     is_verified = db.Column(db.Boolean, default=True)
1280 |     is_legendary = db.Column(db.Boolean, default=False)
1281 |     __table_args__ = (
1282 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
1283 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
1284 |     )
1285 | 
1286 | # =====================================
1287 | # PULSE TERMINAL API — V30
1288 | # =====================================
1289 | 
1290 | class ApiKey(db.Model):
1291 |     """Paid API key for Pulse Terminal subscribers."""
1292 |     __tablename__ = 'api_keys'
1293 |     id = db.Column(db.Integer, primary_key=True)
1294 |     key_hash = db.Column(db.String(64), unique=True, nullable=False)   # SHA256 of actual key — composite idx covers single-col queries
1295 |     key_prefix = db.Column(db.String(12), nullable=False)                           # first 8 chars for display
1296 |     tier = db.Column(db.String(30), nullable=False, default='commander')
1297 |     subscriber_email = db.Column(db.String(200), nullable=False, index=True)
1298 |     stripe_customer_id = db.Column(db.String(120), index=True)
1299 |     stripe_subscription_id = db.Column(db.String(120))
1300 |     stripe_session_id = db.Column(db.String(200))
1301 |     requests_today = db.Column(db.Integer, default=0, nullable=False)
1302 |     requests_total = db.Column(db.Integer, default=0, nullable=False)
1303 |     last_used_at = db.Column(db.DateTime, index=True)
1304 |     last_reset_at = db.Column(db.DateTime, default=datetime.utcnow)  # when requests_today was last zeroed
1305 |     active = db.Column(db.Boolean, default=True, nullable=False, index=True)
1306 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
1307 | 
1308 |     __table_args__ = (
1309 |         db.Index('idx_api_keys_hash_active', 'key_hash', 'active'),
1310 |     )
1311 | 
1312 |     def reset_if_new_day(self):
1313 |         """Zero requests_today if last reset was a different calendar day (UTC)."""
1314 |         today = datetime.utcnow().date()
1315 |         if self.last_reset_at is None or self.last_reset_at.date() < today:
1316 |             self.requests_today = 0
1317 |             self.last_reset_at = datetime.utcnow()
1318 | 
1319 | 
1320 | class ApiUsageLog(db.Model):
1321 |     """Per-request usage log for Terminal API — analytics + billing audit trail."""
1322 |     __tablename__ = 'api_usage_log'
1323 |     id = db.Column(db.Integer, primary_key=True)
1324 |     key_prefix = db.Column(db.String(12), nullable=False, index=True)
1325 |     endpoint = db.Column(db.String(100), nullable=False)
1326 |     response_ms = db.Column(db.Integer)
1327 |     status_code = db.Column(db.Integer, default=200)
1328 |     ip_hash = db.Column(db.String(64))   # SHA256 of IP for privacy-safe analytics
1329 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
1330 | 
1331 |     __table_args__ = (
1332 |         db.Index('idx_usage_log_prefix_created', 'key_prefix', 'created_at'),
1333 |     )
1334 | 
1335 | # ── B1 Newsletter (Gospel: b1-newsletter) ──────────────────────────────────
1336 | 
1337 | class NewsletterSubscriber(db.Model):
1338 |     """LAW 4: Each subscriber has a unique unsubscribe_token (CAN-SPAM compliance).
1339 |     Double opt-in: confirmed=False until email link clicked."""
1340 |     __tablename__ = 'newsletter_subscribers'
1341 | 
1342 |     id = db.Column(db.Integer, primary_key=True)
1343 |     email = db.Column(db.String(320), unique=True, nullable=False)
1344 |     unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False)
1345 |     confirmation_token = db.Column(db.String(64), unique=True)
1346 |     confirmed = db.Column(db.Boolean, default=False, nullable=False)
1347 |     confirmed_at = db.Column(db.DateTime)
1348 |     subscribed = db.Column(db.Boolean, default=True, nullable=False)
1349 |     subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
1350 |     unsubscribed_at = db.Column(db.DateTime)
1351 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1352 |     source = db.Column(db.String(50))  # 'homepage', 'api', 'import'
1353 | 
1354 |     __table_args__ = (
1355 |         db.Index('idx_newsletter_sub_email', 'email'),
1356 |         db.Index('idx_newsletter_sub_token', 'unsubscribe_token'),
1357 |         db.Index('idx_newsletter_sub_active', 'subscribed'),
1358 |         db.Index('idx_newsletter_sub_confirm', 'confirmation_token'),
1359 |     )
1360 | 
1361 | 
1362 | class NewsletterSend(db.Model):
1363 |     """LAW 2: One newsletter per day — tracks sends for idempotency."""
1364 |     __tablename__ = 'newsletter_sends'
1365 | 
1366 |     id = db.Column(db.Integer, primary_key=True)
1367 |     subject = db.Column(db.Text)
1368 |     resend_batch_id = db.Column(db.String(100))
1369 |     recipient_count = db.Column(db.Integer, default=0)
1370 |     open_count = db.Column(db.Integer, default=0)
1371 |     click_count = db.Column(db.Integer, default=0)
1372 |     sent_at = db.Column(db.DateTime, default=datetime.utcnow)
1373 | 
1374 |     __table_args__ = (
1375 |         db.Index('idx_newsletter_sends_at', 'sent_at'),
1376 |     )
1377 | 
1378 | 
1379 | class NewsletterCampaign(db.Model):
1380 |     """Tracks digest campaign sends with metadata."""
1381 |     __tablename__ = 'newsletter_campaigns'
1382 | 
1383 |     id = db.Column(db.Integer, primary_key=True)
1384 |     sent_at = db.Column(db.DateTime, default=datetime.utcnow)
1385 |     recipient_count = db.Column(db.Integer, default=0)
1386 |     failed_count = db.Column(db.Integer, default=0)
1387 |     top_headline = db.Column(db.String(300))
1388 |     status = db.Column(db.String(30), default='sent')  # sent | partial | failed
1389 | 
1390 |     __table_args__ = (
1391 |         db.Index('idx_newsletter_campaign_at', 'sent_at'),
1392 |     )
1393 | 
1394 | 
1395 | # =====================================
1396 | # COMMANDER SUBSCRIBER — Stripe API Key Auth
1397 | # =====================================
1398 | 
1399 | class CommanderSubscriber(db.Model):
1400 |     """Standalone Commander API subscriber. No User account required.
1401 |     API keys stored as SHA256 hash — plaintext never persisted after creation."""
1402 |     __tablename__ = 'commander_subscribers'
1403 | 
1404 |     id = db.Column(db.Integer, primary_key=True)
1405 |     email = db.Column(db.String(200), unique=True, nullable=False, index=True)
1406 |     stripe_customer_id = db.Column(db.String(120), index=True)
1407 |     stripe_subscription_id = db.Column(db.String(120), unique=True)
1408 |     stripe_session_id = db.Column(db.String(200))
1409 |     api_key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
1410 |     api_key_prefix = db.Column(db.String(16), nullable=False)  # first 12 chars for display
1411 |     active = db.Column(db.Boolean, default=True, nullable=False, index=True)
1412 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
1413 |     calls_today = db.Column(db.Integer, default=0, nullable=False)
1414 |     calls_month = db.Column(db.Integer, default=0, nullable=False)
1415 |     last_call_at = db.Column(db.DateTime)
1416 |     last_reset_date = db.Column(db.String(10))  # 'YYYY-MM-DD' for daily reset
1417 |     last_reset_month = db.Column(db.String(7))  # 'YYYY-MM' for monthly reset
1418 | 
1419 |     __table_args__ = (
1420 |         db.Index('idx_commander_keyhash_active', 'api_key_hash', 'active'),
1421 |     )
1422 | 
1423 |     @staticmethod
1424 |     def hash_key(raw_key):
1425 |         import hashlib
1426 |         return hashlib.sha256(raw_key.encode()).hexdigest()
1427 | 
1428 |     def reset_if_needed(self):
1429 |         """Reset daily/monthly counters if the date has changed."""
1430 |         today = datetime.utcnow().strftime('%Y-%m-%d')
1431 |         month = datetime.utcnow().strftime('%Y-%m')
1432 |         if self.last_reset_date != today:
1433 |             self.calls_today = 0
1434 |             self.last_reset_date = today
1435 |         if self.last_reset_month != month:
1436 |             self.calls_month = 0
1437 |             self.last_reset_month = month
1438 | 
1439 |     def increment_calls(self):
1440 |         """Increment call counters and update last_call_at."""
1441 |         self.reset_if_needed()
1442 |         self.calls_today = (self.calls_today or 0) + 1
1443 |         self.calls_month = (self.calls_month or 0) + 1
1444 |         self.last_call_at = datetime.utcnow()
1445 | 
1446 | 
1447 | # =====================================
1448 | # ORACLE SESSION — F1 Avatar System
1449 | # =====================================
1450 | 
1451 | class OracleSession(db.Model):
1452 |     __tablename__ = 'oracle_sessions'
1453 |     __table_args__ = (
1454 |         db.Index('idx_oracle_sessions_created', 'created_at'),
1455 |     )
1456 | 
1457 |     id = db.Column(db.Integer, primary_key=True)
1458 |     session_id = db.Column(db.Text, nullable=False)
1459 |     question = db.Column(db.Text, nullable=False)
1460 |     transcript = db.Column(db.Text)
1461 |     video_url = db.Column(db.Text)
1462 |     duration_seconds = db.Column(db.Float)
1463 |     voice_id = db.Column(db.String(60), default='cgSgspJ2msm6clMCkdW9')
1464 |     generation_ms = db.Column(db.Integer)
1465 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1466 |     user_id = db.Column(db.Integer, nullable=True)
1467 |     ip_hash = db.Column(db.String(64), nullable=True)
1468 | 
1469 | 
1470 | # =====================================
1471 | # MARKET BRIEFING ROOM (F2)
1472 | # =====================================
1473 | 
1474 | class MarketBriefing(db.Model):
1475 |     """Scheduled HeyGen Sarah video briefings — 3x daily at market-critical times."""
1476 |     __tablename__ = 'market_briefings'
1477 |     __table_args__ = (
1478 |         db.Index('idx_briefings_type_date', 'briefing_type', 'generated_at'),
1479 |         db.Index('idx_briefings_published', 'published', 'generated_at'),
1480 |         db.Index('idx_briefings_slot_date', 'briefing_type', 'scheduled_date'),
1481 |         # DB-level idempotency guard: only one non-failed briefing per slot per day
1482 |         db.UniqueConstraint('briefing_type', 'scheduled_date', name='uq_briefing_slot_date'),
1483 |     )
1484 | 
1485 |     id = db.Column(db.Integer, primary_key=True)
1486 |     title = db.Column(db.Text, nullable=False)
1487 |     briefing_type = db.Column(db.String(20), nullable=False)  # pre_market | open | close
1488 |     scheduled_date = db.Column(db.String(10))                 # ET date: YYYY-MM-DD (idempotency)
1489 |     script_text = db.Column(db.Text, nullable=False)
1490 |     video_url = db.Column(db.Text)
1491 |     thumbnail_url = db.Column(db.Text)
1492 |     heygen_video_id = db.Column(db.String(100))
1493 |     duration_seconds = db.Column(db.Float)
1494 |     btc_price_at_generation = db.Column(db.Float)
1495 |     status = db.Column(db.String(20), default='pending')  # pending|generating|completed|failed
1496 |     published = db.Column(db.Boolean, default=False)
1497 |     generated_at = db.Column(db.DateTime, default=datetime.utcnow)
1498 |     published_at = db.Column(db.DateTime)
1499 |     error_message = db.Column(db.Text)
1500 | 
1501 |     def to_dict(self):
1502 |         return {
1503 |             'id': self.id,
1504 |             'title': self.title,
1505 |             'briefing_type': self.briefing_type,
1506 |             'scheduled_date': self.scheduled_date,
1507 |             'video_url': self.video_url,
1508 |             'thumbnail_url': self.thumbnail_url,
1509 |             'duration_seconds': self.duration_seconds,
1510 |             'btc_price_at_generation': self.btc_price_at_generation,
1511 |             'status': self.status,
1512 |             'published': self.published,
1513 |             'generated_at': self.generated_at.isoformat() if self.generated_at else None,
1514 |             'published_at': self.published_at.isoformat() if self.published_at else None,
1515 |         }
1516 | 
1517 | # F6 MARKETING OS — MILESTONE + METRICS
1518 | # =====================================
1519 | 
1520 | class PerformanceMetrics(db.Model):
1521 |     """Daily performance metrics. One row per day. Upsert on write."""
1522 |     __tablename__ = 'performance_metrics'
1523 |     __table_args__ = (
1524 |         db.Index('idx_perf_metric_date', 'metric_date', unique=True),
1525 |     )
1526 | 
1527 |     id = db.Column(db.Integer, primary_key=True)
1528 |     metric_date = db.Column(db.Date, nullable=False, unique=True)
1529 |     page_views = db.Column(db.Integer, default=0)
1530 |     unique_visitors = db.Column(db.Integer, default=0)
1531 |     articles_published = db.Column(db.Integer, default=0)
1532 |     videos_rendered = db.Column(db.Integer, default=0)
1533 |     oracle_sessions = db.Column(db.Integer, default=0)
1534 |     briefings_generated = db.Column(db.Integer, default=0)
1535 |     newsletter_opens = db.Column(db.Integer, default=0)
1536 |     newsletter_clicks = db.Column(db.Integer, default=0)
1537 |     btc_price_open = db.Column(db.Float)
1538 |     btc_price_close = db.Column(db.Float)
1539 |     milestone_triggered = db.Column(db.String(100))  # NULL or milestone label
1540 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1541 | 
1542 | 
1543 | class MilestoneFired(db.Model):
1544 |     """Permanent record of every milestone that has fired. Never deleted."""
1545 |     __tablename__ = 'milestone_fired'
1546 |     __table_args__ = (
1547 |         db.Index('idx_milestone_price', 'price_threshold', unique=True),
1548 |     )
1549 | 
1550 |     id = db.Column(db.Integer, primary_key=True)
1551 |     price_threshold = db.Column(db.Integer, nullable=False, unique=True)  # e.g. 100000
1552 |     label = db.Column(db.String(100), nullable=False)                      # e.g. "SIX FIGURES"
1553 |     campaign = db.Column(db.String(100))                                   # e.g. "btc_100k"
1554 |     actual_price = db.Column(db.Float)                                     # price when triggered
1555 |     fired_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
1556 |     nostr_broadcast = db.Column(db.Boolean, default=False)
1557 |     newsletter_sent = db.Column(db.Boolean, default=False)
1558 |     episode_generated = db.Column(db.Boolean, default=False)
1559 | 
1560 | 
1561 | class PriceAlert(db.Model):
1562 |     """Public BTC price alerts — no auth required."""
1563 |     __tablename__ = 'price_alerts'
1564 |     __table_args__ = (
1565 |         db.Index('idx_price_alert_active_notified', 'active', 'notified'),
1566 |     )
1567 | 
1568 |     id = db.Column(db.Integer, primary_key=True)
1569 |     email = db.Column(db.String(255), nullable=False, index=True)
1570 |     price_target = db.Column(db.Float, nullable=False)
1571 |     direction = db.Column(db.String(10), nullable=False)  # "above" | "below"
1572 |     active = db.Column(db.Boolean, default=True)
1573 |     notified = db.Column(db.Boolean, default=False)
1574 |     email_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
1575 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1576 |     triggered_at = db.Column(db.DateTime)
1577 |     triggered_price = db.Column(db.Float)
1578 | 
1579 | 
1580 | class SponsorOutreach(db.Model):
1581 |     __tablename__ = "sponsor_outreach"
1582 | 
1583 |     id = db.Column(db.Integer, primary_key=True)
1584 |     company = db.Column(db.String(200), nullable=False)
1585 |     domain = db.Column(db.String(200), nullable=False, index=True)
1586 |     email = db.Column(db.String(200))
1587 |     category = db.Column(db.String(50))
1588 |     status = db.Column(db.String(50), default="prospect", index=True)
1589 |     subject = db.Column(db.String(500))
1590 |     body = db.Column(db.Text)
1591 |     sent_at = db.Column(db.DateTime)
1592 |     replied_at = db.Column(db.DateTime)
1593 |     deal_value = db.Column(db.Float)
1594 |     notes = db.Column(db.Text)
1595 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
1596 | 
1597 | 
1598 | # ── Auto-slug generation on insert ─────────────────────────────────────────
1599 | from sqlalchemy import event as _sa_event
1600 | 
1601 | @_sa_event.listens_for(Article, 'after_insert')
1602 | def _auto_slug_after_insert(mapper, connection, target):
1603 |     """Generate slug automatically after every Article insert."""
1604 |     if not target.slug and target.title and target.id:
1605 |         slug = Article.make_slug(target.title, target.id)
1606 |         # Use direct connection to avoid session issues
1607 |         connection.execute(
1608 |             Article.__table__.update()
1609 |             .where(Article.__table__.c.id == target.id)
1610 |             .values(slug=slug)
1611 |         )
1612 | 
```

### File: docs/cc_specs/cc_media_audit.md (124 lines)
```
   1 | Read VISUAL_DESIGN_SYSTEM.md and PIPELINE_LAWS.md.
   2 | Read templates/media_hub.html fully.
   3 | Read services/rss_service.py fully.
   4 | Then run utils/cross_llm_audit.py on templates/media_hub.html with these 8 questions.
   5 | 
   6 | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   7 | MEDIA PAGE — WORLD-CLASS BITCOIN MEDIA COMMAND CENTER
   8 | Goal: The definitive Bitcoin media hub. Every voice. Every signal.
   9 | One screen. No competitor comes close. Ship by Friday.
  10 | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  11 | 
  12 | FULL PODCAST RSS FEEDS TO AGGREGATE:
  13 | - Cypherpunk'd: https://anchor.fm/s/fa724db8/podcast/rss
  14 | - Protocol Pulse: https://feed.podbean.com/protocolpulse/feed.xml
  15 | - TFTC (Matt Odell): https://feeds.simplecast.com/mGJ8uw1O
  16 | - Stephan Livera: https://feeds.simplecast.com/KV8z39iS
  17 | - What Bitcoin Did: https://feeds.simplecast.com/tEJEubMT
  18 | - Bitcoin Audible: https://feeds.megaphone.fm/SWN4978045882
  19 | - Citadel Dispatch: https://feeds.simplecast.com/M6LkF8NN
  20 | - The Bitcoin Layer: https://feeds.simplecast.com/BdGT7E3F
  21 | - Simply Bitcoin: https://feeds.simplecast.com/7V5b8Zag
  22 | - Bitcoin Magazine Podcast: https://feeds.megaphone.fm/bitcoin-magazine
  23 | - Rabbit Hole Recap: https://feeds.simplecast.com/Dh1oHsHZ
  24 | - Preston Pysh / TIP: https://feeds.simplecast.com/WXOL8WUD
  25 | - Natalie Brunell Coin Stories: https://feeds.simplecast.com/6Z1iM0Fg
  26 | - Bitcoin Fundamentals: https://feeds.simplecast.com/WXOL8WUD
  27 | 
  28 | YOUTUBE CHANNELS:
  29 | - Bitcoin Magazine: UCvRRgjjKvabNkSP0w3QdW3A
  30 | - Coin Bureau: UCqK_GSMbpiV8spgD3ZGloSw
  31 | - What Bitcoin Did: UCBcRF18a7Qf58cCRy5xuWwQ
  32 | - Simply Bitcoin: UCm7SUL4HMiM3UFEWP-E_Qhg
  33 | - Robert Breedlove: UCFmHIftfI9HRaL6r3zScKOg
  34 | - Natalie Brunell: UCIl1wX8yxEjkbCFBKbhAqeg
  35 | - Bitcoin Audible: UCJz4rEsEHpx9ht7a5JIHh5g
  36 | 
  37 | AUDIT QUESTIONS for Gemini + GPT-4o + Grok (independently, then cross-validate):
  38 | 
  39 | 1. ARCHITECTURE: What is the optimal backend architecture for aggregating 
  40 |    15 RSS feeds + 7 YouTube channels + live X/Nostr KOL feeds simultaneously
  41 |    WITHOUT blocking Flask workers or degrading site performance?
  42 |    Consider: background jobs, Redis caching, SQLite caching, async fetching.
  43 |    What refresh interval per source type is optimal?
  44 | 
  45 | 2. D3 NETWORK GRAPH: Design the Bitcoin voice network topology visualization.
  46 |    Nodes = Bitcoin voices/channels. Edges = cross-references/mentions.
  47 |    How do we detect when voices reference each other (quote tweets, mentions)?
  48 |    What data structure backs this? How do we animate node pulses on new posts?
  49 |    What's the D3.js force simulation config for ~50 nodes to look stunning?
  50 |    How do we handle hover cards with live data without API hammering?
  51 | 
  52 | 3. LIVE TICKER: Design the hyperlinked scrolling ticker at the top.
  53 |    Each item must deep-link to the exact source (podcast episode, tweet, video).
  54 |    How do we handle link generation for RSS items, YouTube videos, X posts, Nostr?
  55 |    What's the smoothest CSS animation that doesn't stutter on mobile?
  56 |    How do we prioritize items (breaking news > new episode > tweet)?
  57 | 
  58 | 4. SIGNAL SCORE: Design a 0-100 Signal Score for all content.
  59 |    Inputs: our KOL sentiment pipeline, engagement metrics, topic relevance,
  60 |    source tier (Tier 1 = Odell/Livera/McCormack, etc).
  61 |    Formula that's backtestable against price action?
  62 |    How do we calculate this on ingest without API costs?
  63 | 
  64 | 5. CLIPS ENGINE: Design the automated Bitcoin media clip extraction system.
  65 |    When our sentiment pipeline flags a high-signal moment (>85% confidence):
  66 |    - YouTube: extract timestamp, generate 60-90s clip via yt-dlp + ffmpeg
  67 |    - Podcast: extract timestamp from transcript, clip audio
  68 |    - Overlay: Protocol Pulse branded animated waveform + quote text
  69 |    - Output: vertical 9:16 MP4 for sharing
  70 |    What's the queue architecture? GPU usage? Storage requirements?
  71 |    Can this run on our 4x RTX 4090 without interfering with render pipeline?
  72 | 
  73 | 6. EMBEDDED PLAYER: How do we embed podcast episodes without redirect?
  74 |    Options: native HTML5 audio element with RSS mp3 URL, Spotify embed,
  75 |    Apple Podcasts embed, custom player. Which works reliably for all 15 feeds?
  76 |    How do we handle DRM/protected content?
  77 | 
  78 | 7. ENGAGEMENT LAYER (alternative to blockchain wall):
  79 |    Instead of a literal drawing wall, what engagement features would make
  80 |    Bitcoin users ACTUALLY return daily and share with others?
  81 |    Think: streak tracking, signal accuracy scoring (did you call the move?),
  82 |    community price prediction market (Protocol Pulse-native, not Polymarket),
  83 |    "soundboard" of famous Bitcoin quotes triggered by price events,
  84 |    achievement badges for sovereign behaviors (node runner, self-custody, etc).
  85 |    Which 3 features have highest viral coefficient?
  86 | 
  87 | 8. CLAUDE ON INGEST: The AI-generated 30-word summaries for each episode.
  88 |    This uses the Anthropic API (Claude claude-sonnet-4-6), NOT local models.
  89 |    How do we batch-process RSS items efficiently to minimize API cost?
  90 |    What's the optimal prompt for a 30-word Bitcoin-native signal summary?
  91 |    How do we cache summaries so we only generate once per episode?
  92 |    Estimated monthly cost for 15 feeds × ~20 episodes/week?
  93 | 
  94 | AFTER AUDIT — BUILD PHASE 1 (Friday deadline):
  95 | 
  96 | PRIORITY ORDER:
  97 | 1. Background RSS aggregation service (15 feeds, 15min cache, SQLite storage)
  98 | 2. YouTube latest videos fetcher (7 channels, 1hr cache)  
  99 | 3. Three-column Feed Matrix on media_hub.html (podcasts | video | KOL+intel)
 100 | 4. Live scrolling ticker with hyperlinks (CSS animation, no JS libraries)
 101 | 5. Signal Score calculation on ingest
 102 | 6. Episode embedded player (HTML5 audio, direct RSS mp3 URL)
 103 | 7. AI summary generation (batch, cached, Anthropic API)
 104 | 
 105 | PHASE 2 (next week):
 106 | - D3 network topology graph
 107 | - Clips Engine
 108 | - Voice Index directory
 109 | - Engagement layer
 110 | 
 111 | DESIGN REQUIREMENTS:
 112 | - Extends base.html but overrides hero section completely
 113 | - Match existing media_hub.html glass morphism dark style
 114 | - JetBrains Mono for data, DM Sans for body
 115 | - Red/black/white Protocol Pulse brand
 116 | - Mobile-first responsive
 117 | - NO placeholder data anywhere — real feeds or loading skeletons
 118 | 
 119 | IMPORTANT: Run rss_service.py feeds first to see what data format we get.
 120 | Then design the DB schema for caching (ExternalFeed, ExternalEpisode tables).
 121 | Then build the routes: /media loads cached data, background job refreshes.
 122 | 
 123 | git add -A && git commit -m "feat(media): Bitcoin Media Command Center — RSS aggregator, Feed Matrix, ticker, signal scores" && git push
 124 | 
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
