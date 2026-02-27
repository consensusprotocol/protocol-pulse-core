# Value Stream — Use Case & Functionality

Use this document to communicate to other LLMs what the Value Stream page is for and what it does.

---

## Use case (what problem it solves)

**Problem:** Content discovery is driven by engagement metrics (likes, shares, comments) that reward viral and low-quality content. Creators and curators who surface genuinely valuable content don’t get a direct economic signal or reward.

**Solution:** Value Stream is a **decentralized content curation feed powered by Bitcoin (sats)**. Users submit links from any platform (X/Twitter, YouTube, Nostr, Reddit, etc.). Other users **“zap”** (send small amounts of sats) to content they find valuable. Ranking is driven by **economic signal** (sats + zaps), not engagement farming. Curators who submit content that gets zapped **earn a share** (e.g. 10%) of those zaps.

**Who it’s for:**
- **Curators** — People who find and share high-value links and want to be rewarded when others value that content.
- **Readers** — People who want a feed ranked by “real money” signal (sats) instead of likes/shares.
- **Creators** — Original authors (when linked) can receive a portion of zaps via Lightning.

**High-level value:** Turn “attention” and “engagement” into a **value-for-value** loop: pay a little to signal what’s worth surfacing; curators and (optionally) creators earn from that signal.

---

## Core functionality

### 1. **Curate content**
- User pastes a **URL** from any supported platform (Twitter/X, YouTube, Nostr, Reddit, Stacker News, or generic web).
- Optional **title** can be provided.
- Submit stores the link as a **curated post** and associates it with the curator (if logged in).
- **Duplicate URLs** are deduplicated (same URL returns existing post).

### 2. **View the feed**
- Feed lists curated posts ordered by **signal score** (see below).
- **Platform filters:** All platforms, X/Twitter, YouTube, Nostr, Reddit, Stacker News.
- Each card shows: platform badge, title (link to original), optional content preview, **total sats**, **zap count**, **signal score**, curator name, and a **Zap** button.

### 3. **Zap content**
- “Zap” = send **sats** (Bitcoin’s smallest unit) to signal that the content is valuable.
- **In-browser:** If the user has a WebLN-compatible wallet (e.g. Alby), the Zap button requests a Lightning invoice (via LNURL) and triggers a payment. On success, the zap is recorded and the post’s sats/zap count/signal score update.
- **Backend:** Invoice is created from the **creator’s or curator’s Lightning address** (or a default). The `/api/value-stream/zap/<post_id>` endpoint records the zap and updates post and curator stats.

### 4. **Leaderboard: Top Curators**
- Sidebar shows **top curators** by curator score (and/or total sats received, total zaps).
- Displays: rank, display name, verification badge (if any), score, total sats received, number of zaps.

### 5. **Browser extension**
- Promo for a **browser extension** that lets users zap and curate from any website (not just this page).
- Links to `/extension` for download/setup.

### 6. **“How it works”**
- Four-step explanation: **Curate** (share links) → **Zap** (send sats to signal value) → **Rise** (content surfaces by economic signal) → **Earn** (curators get e.g. 10% of zaps to content they share).

---

## Key concepts (for other LLMs)

| Concept | Meaning |
|--------|---------|
| **Curated post** | A single submission: URL, platform, optional title/preview, linked to a curator. Stored in DB with `total_sats`, `zap_count`, `signal_score`. |
| **Curator** | A user (Value Creator) who submits links. Can earn a share of zaps to content they curated. |
| **Creator** | The original author of the content (optional; distinct from curator). Can receive a share of zaps (e.g. via Lightning address). |
| **Zap** | A small Lightning payment (sats) sent to signal value. Recorded as a ZapEvent; updates post totals and curator stats. |
| **Signal score** | Numeric score used to rank posts. Formula: `(total_sats * 0.001 + zap_count * 10) * time_decay * decay_factor`. Newer and more-zapped content ranks higher. |
| **Platform** | Source of the link: e.g. `twitter`, `youtube`, `nostr`, `reddit`, `stacker_news`, `web`. Used for filtering and display. |
| **Lightning / LNURL** | Invoice for zapping is created via LNURL-p (e.g. `user@domain`). WebLN in the browser can send the payment. |

---

## User flows (summary)

1. **Curator flow:** Open Value Stream → paste URL (optional title) → Submit → post appears in feed; when others zap it, curator earns a split.
2. **Reader / zapper flow:** Open Value Stream → browse feed (optionally filter by platform) → click Zap on a post → approve payment in wallet → zap is recorded, feed updates.
3. **Anonymous curation:** User can submit without logging in; post is stored with no curator (or a default). Logged-in users are linked as curator so they can earn.

---

## What the page does NOT do yet (gaps / scope for improvement)

- **No real split payouts** — Zap is recorded and totals update, but automatic splitting of sats to curator/creator (e.g. 10% / 90%) and actual Lightning payouts are not fully implemented.
- **No Nostr/WebLN identity** — Curators are identified by site login (e.g. Twitter handle) or anonymous; no Nostr pubkey or NIP-05 in the main flow yet.
- **No URL metadata fetching** — Submitting a URL does not auto-fetch title/description/thumbnail from the link (could use oEmbed or similar).
- **No real-time updates** — Feed updates on reload; no live stream of new posts or zaps on the Value Stream page itself (SSE exists for Signal Terminal, not this page).
- **No moderation** — No reporting, allowlists, or spam/abuse handling.
- **No zap amount choice on page** — Default is fixed (e.g. 1000 sats); user cannot pick amount before Zap without changing the flow.

---

## One-paragraph summary for other LLMs

**Value Stream** is a Bitcoin/Lightning-native content curation feed. Users submit URLs from any platform (X, YouTube, Nostr, Reddit, etc.); the feed is ranked by **signal score** (sats + zaps + time decay). Viewers can **zap** (send sats via Lightning/WebLN) to signal value; curators earn a share of zaps. The page provides: curate form, ranked feed with platform filters, Zap buttons (WebLN), top curators leaderboard, extension promo, and a “How it works” explainer. Backend: Flask + SQLAlchemy (ValueCreator, CuratedPost, ZapEvent), LNURL for invoices, and APIs for submit, zap, invoice, curators, and register. The goal is to make discovery and curation **value-for-value** instead of engagement-based.
