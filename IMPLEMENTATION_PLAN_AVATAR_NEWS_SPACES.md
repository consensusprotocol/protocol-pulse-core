# Implementation Plan: Avatar, Partner YouTube, Spaces (Transcript), Breaking News Dual-Image

**Purpose:** One doc that ties together (1) 24/7 avatar + partner YouTube transcription + value-added commentary, (2) post-Space transcript tweets (tag speakers, quote best takes), (3) breaking-news dual-image posts (cover + branded logo) on X, IG, Nostr, and (4) how to get started.

---

## 1. Partner YouTube Channels — List and Avatar Use

The **designated partner YouTube list** lives in:

- **`core/config/supported_sources.json`** — canonical list (20 channels: Michael Saylor, Lyn Alden, Preston Pysh, Natalie Brunell, Peter McCormack, Robert Breedlove, Marty Bent, Saifedean Ammous, BTC Sessions, Simply Bitcoin, Bitcoin Magazine, Swan, Bitcoin Audible, Matt Odell, Pomp, Coin Bureau, The Bitcoin Layer, Bitcoin Rapid-Fire, Stephan Livera, River, Unchained).  
- **`core/services/youtube_service.py`** — `PODCAST_CHANNELS` (shorter list). Prefer **`supported_sources.json`** for the avatar pipeline so one config drives “partner channels we transcribe and comment on.”

**Avatar use:** For the 24/7 live avatar we will:

- **Transcribe** the **latest video** from each designated partner channel (or a subset) in near real time (e.g. when a new upload is detected, or on a schedule for “latest” per channel).
- **Add value-added commentary** (AI script): context, relevance to Bitcoin narrative, key quote or takeaway, sentiment.
- **Encourage viewers to watch the full clip** on the partner’s channel (clear CTA: “Watch the full conversation on [Channel] — link in description”).

So the avatar doesn’t just read headlines; it **reacts to partner content** and drives traffic to partners while staying on-brand.

**Implementation outline:**

- **Config:** Read `supported_sources.json` → `youtube_channels` (optionally filter by `featured: true` or tier).
- **Ingest:** Per partner channel, periodically (e.g. every 15–30 min) check “latest upload” via YouTube API; if new or not yet processed, fetch **transcript** (e.g. `youtube_transcript_api` or AssemblyAI for harder cases).
- **Script:** For each “new” partner video, pass to AI: transcript summary (or full if short) + channel name + title. Output: 60–90 sec avatar script that (a) summarizes the discussion, (b) adds Protocol Pulse insight/relevance, (c) ends with CTA: “Full conversation on [Channel name] — link below.”
- **Avatar:** Script goes into the same 24/7 Pulse pipeline (TTS + avatar face); stream shows “Partner Intel” segments alongside sentiment, X/Nostr, and Spaces.

---

## 2. X Spaces: Wait for Transcript, Then Tweet (Tag + Quote)

You want to **skip** metadata-only live tweets and **wait until the Space is over** and we have a **transcript** (e.g. via XSPACESTREAM or similar). Then:

- **Tweet** an **informative** summary that:
  - **Tags** the speakers (e.g. @handle).
  - **Quotes** their best takes (short, accurate quotes from transcript).
  - Drives trust and clicks (link to Space replay if available, or host’s follow-up).

**Flow:**

1. **Detect ended Space** (X API: Spaces search/lookup with `state=ended`, or webhook/cron that checks “was live, now ended”).
2. **Get transcript** via XSPACESTREAM (or your chosen provider) for that Space ID / replay URL. If the provider gives “speaker + text” segments, keep that.
3. **AI step:** Input = transcript (or summary) + speaker handles/names. Output = one tweet (or thread) that: (a) states what the Space was about, (b) tags 1–3 key speakers, (c) includes 1–2 short pull quotes (best takes), (d) link to Space or replay. Stay under 280 chars for a single tweet; if thread, first tweet = hook + link, reply = quotes + tags.
4. **Post** from Protocol Pulse account. Optional: like/RT the host’s own Space tweet for alignment.

**Cost:** X API Basic $200/mo + XSPACESTREAM (or similar) ~$7–65/mo + AI per Space (~$0.02–0.05). No live metadata-only tweets; all Space tweets are **post-Space, transcript-based, tag + quote**.

---

## 3. Breaking News: Dual-Image Posts (Cover + Branded Logo)

For **breaking news** that we tweet/post about on **X, IG, and Nostr**:

- **Automatically** grab the **header/cover image** from the source (article, thread, or feed item we’re sharing).
- **Publish with two images** where the platform allows:
  1. **Image 1:** The **cover/header** (story image, OG image, or thumbnail).
  2. **Image 2:** **Protocol Pulse branded logo with a “Bitcoin pulse”** (e.g. logo + subtle heartbeat/pulse animation or static “pulse” graphic) so the post looks **official** and **on-brand**.

**Why two images:** First image = relevance and credibility (the actual news visual). Second = brand recognition and consistency across X, IG, Nostr.

**Implementation outline:**

- **Source of “breaking news”:** Your existing pipeline (e.g. articles, LaunchSequence, or a dedicated “breaking” feed). When we decide to post a given item:
  - **Cover image:** From `article.header_image_url`, or OG meta from source URL (`og:image`), or YouTube thumbnail if it’s a video, or first image from the page. Fallback: default news placeholder.
  - **Branded image:** A **single static or animated asset**: “Protocol Pulse logo + Bitcoin pulse” (e.g. logo + orange pulse ring or heartbeat line). Store at e.g. `static/images/pp-pulse-brand.png` (or .gif for subtle animation). Generate once; reuse for every breaking-news post.
- **X:** Up to 4 images per tweet. Use **2**: [cover, branded]. Order can be [cover, branded] so the news visual is first; or [branded, cover] if you want logo first (A/B test later).
- **Instagram:** Carousel supports multiple images. Post **2**: [cover, branded] (or [branded, cover]). If you only post single-image, use a **composite** (e.g. left half = cover, right half = branded) generated on the fly or pre-made template.
- **Nostr:** Depends on client. Many support multiple images (e.g. in content or as attachments). Same idea: attach cover + branded image when posting the same story.

**Technical notes:**

- **Fetching cover:** Use your existing `header_image_url` on Article, or a small utility: given URL, fetch page and parse `<meta property="og:image" content="...">` (or Twitter card image). Cache the image URL or download to temp file for upload.
- **Branded asset:** Create once (Figma/Canva/designer): logo + “pulse” element. Export PNG (or GIF). No need to regenerate per post.
- **Posting:** Extend your existing X (and any IG/Nostr) posting code to accept **multiple media URLs/files**; upload both, attach to post. For IG, use Graph API (or Buffer/Hootsuite if you use them) with carousel or single composite.

---

## 4. Other Inputs and Tips

- **Consistency:** Use the same **branded pulse asset** everywhere (X, IG, Nostr, and optionally in the 24/7 stream lower-third) so “pulse” = Protocol Pulse.
- **Hashtags:** You already avoid hashtags on X; keep that. IG and Nostr can follow the same policy or use 1–2 only if you see better discoverability.
- **Nostr:** If you use a NIP for images (e.g. in note content or as separate events), ensure the same two images (cover + branded) are referenced so the post looks identical in spirit across platforms.
- **Rights:** When using “cover” images from third-party articles, prefer sources that allow editorial use or use your own visuals where possible; fallback to “no image” or branded-only if in doubt.
- **Rate limits:** Dual-image posts = 2 media uploads per story. Stay within X/IG/Nostr rate limits; batch “breaking” posts so we don’t spike.

---

## 5. How to Get Started — Phased Roadmap

### Phase 1 — Foundation (no new spend)

1. **Partner list in core:** Done — **`core/config/supported_sources.json`** holds the 20 partner YouTube channels. Wire your YouTube service (or a small `partner_channels.py`) to **load from this file** for “designated partner channels” used by the avatar.
2. **Branded asset:** Create and drop **Protocol Pulse logo + Bitcoin pulse** (static or subtle animation) at `core/static/images/pp-pulse-brand.png` (or equivalent). Use it in dual-image posts and optionally in the stream.
3. **Breaking-news pipeline:** Identify **where** “breaking news” is decided (e.g. a specific feed, manual trigger, or LaunchSequence). Add a step: when we have a breaking item, (a) resolve **cover image** (from article/source URL/OG), (b) pass [cover_url, branded_logo_path] to the post function. Extend X post to **2 images**; then add IG and Nostr when ready.

### Phase 2 — Spaces (post-transcript tweets)

1. **X API:** Add credentials to `core/.env`; implement Spaces **search + lookup** (state=live and state=ended) in `x_service` or a small `spaces_service`.
2. **Transcript:** Subscribe or integrate **XSPACESTREAM** (or similar) for **ended** Spaces. When a Space ends, get transcript (or summary) and map speaker segments to X handles where possible.
3. **Tweet job:** When transcript is ready for Space X, run AI: input transcript + speakers → output tweet (with @mentions and 1–2 quotes). Post from Protocol Pulse; optionally RT host’s Space tweet.
4. **No live metadata-only tweets;** all Space tweets are after the fact, transcript-based, tag + quote.

### Phase 3 — Avatar + partner YouTube

1. **Avatar script pipeline:** Aggregate sentiment + top X/Nostr + (when available) Spaces summary + **partner YouTube segment**. For partner segment: from `supported_sources.json`, take latest video per channel (or featured only), fetch transcript, generate “value-added commentary” script + CTA to watch full clip on partner channel.
2. **Transcription:** Use `youtube_transcript_api` for partner videos where available; fallback to AssemblyAI (or your 2× 490s + Whisper later) for no-caption videos.
3. **Stream:** Run script through TTS + avatar (Heygen/D-ID or local 2× 490s). Output 24/7 stream (YouTube Live / Twitch / custom). Partner “Intel” blocks alternate with sentiment, X/Nostr, and Spaces.

### Phase 4 — Polish

- **IG + Nostr dual-image:** Ensure both platforms get the same 2-image treatment (cover + branded) for breaking news.
- **Analytics:** Track which partner clips and which Space tweets drive the most clicks; double down on formats that convert.
- **Local GPU:** Move avatar rendering and optional Whisper to 2× 490s to cut recurring API cost.

---

## 6. Summary

| Feature | What we do |
|--------|------------|
| **Partner YouTube + avatar** | Transcribe **designated partner channels** (list in `core/config/supported_sources.json`). Avatar gives **value-added commentary** and **CTA to watch full clip** on partner’s channel. |
| **X Spaces** | **Wait until Space is done**; get **transcript** (e.g. XSPACESTREAM). Then tweet **informative** post with **tags** and **quoted best takes**; no metadata-only live tweets. |
| **Breaking news (X, IG, Nostr)** | **Grab cover/header** from the story; post with **two images**: (1) **cover**, (2) **branded logo + Bitcoin pulse**. Same treatment across platforms where possible. |
| **Get started** | Phase 1: partner list + branded asset + dual-image posting (X first). Phase 2: Spaces + transcript → tweet. Phase 3: Avatar + partner YouTube in the Pulse stream. Phase 4: IG/Nostr + analytics + local GPU. |

Use **`core/config/supported_sources.json`** as the single source of truth for partner YouTube channels. Add or remove channels there.

---

## 7. Pulse Intelligence Platform (Multi-Product)

The same data layer can power multiple products: **Morning Brief** newsletter, **Pulse Score** index, **Pulse Alerts** (SMS/Telegram), **API-as-a-Service**, **Thought Leader Tracker**, **Partner Amplification**. Priority after Phase 1–4: Morning Brief → Pulse Score → Alerts + API. Design DB and aggregates so all products read from the same sources (SentimentSnapshot, CollectedSignal, WhaleTransaction, etc.).

---

## 8. Phase 1 Implemented

- **Source logic:** `supported_sources_loader.py` + `content_generator.get_partner_youtube_channel_ids()`.
- **Brand:** `static/images/brand/` + README; fallback to `protocol-pulse-logo.png`.
- **Dual-image:** `x_service.post_dual_image_news(text, cover_url, dry_run=False)`.
- **Transcript stub:** `transcript_service.py` (YouTube, Space stub, summarize_for_tweet stub).
- **Dry-run:** `GET/POST /admin/api/dry-run-dual-image-news?article_id=<id>` returns draft without posting.
