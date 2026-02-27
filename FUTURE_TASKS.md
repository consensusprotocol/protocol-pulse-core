# Future Tasks — Protocol Pulse

Notes for future self (or AI) on features to build. Pick from this list when planning next work.

---

## The "Avatar Live-Stream" Page (Cinema Mode)

**Status:** Not started — build when ready for the 24/7 avatar.

**Context:** If you're building a 24/7 avatar, it needs a dedicated "Stage." Don't just embed a YouTube player. Build a **custom Cinema Mode landing page**.

### Upgrade (vs plain embed)

- **Not:** A simple YouTube embed.
- **Yes:** A dedicated Cinema Mode landing page that wraps the stream and adds live metadata.

### UI Design — Three Core Elements

1. **Transcription Sidebar**  
   A real-time scrolling transcript of what the avatar is saying (e.g. live captions / transcript alongside the player).

2. **Sentiment Gauge — "Heartbeat" Line**  
   A literal "heartbeat" line that fluctuates based on the sentiment of the current discussion (e.g. a line or waveform that reacts to positive/negative/neutral sentiment in the transcript or audio).

3. **"Watch Source" Button**  
   A prominent button that **lights up** when the avatar is discussing a partner channel (Saylor, Alden, etc.), allowing the user to **support the partner with one click** (e.g. open partner’s stream or channel).

### Implementation Hooks (when you build it)

- Reuse or extend any existing **live** or **avatar** routes/templates (e.g. under `/live`, `/avatar`, or a new `/stage`).
- Transcript: real-time from whatever pipeline feeds the avatar (e.g. TTS input, or post-Whisper if you capture audio).
- Sentiment: run sentiment on rolling transcript windows and drive the heartbeat UI.
- Partner detection: tag segments or topics with partner IDs (Saylor, Alden, etc.) so the "Watch Source" button can show the right link and highlight when that partner is being discussed.

---

## Sovereign Tier ($100/mo) — "Digital Intelligence Agency" (Post–4090s)

**Status:** Not started — **build once dual 4090s are installed.** This tier sells **Information Sovereignty** and **Time**, not just "information." At $100/mo, users expect a proprietary tool running on your GPU stack.

### Positioning

People don't pay $100 for "news." They pay for **The Edge**. Position this as a professional-grade weapon in the "War for Information": your hardware giving them speed.

---

### 1. The "Personal Pulse" Analyst (Direct GPU Access)

- **Feature:** A private, voice-activated version of the Pulse avatar in the user's dashboard (dedicated "lane" on your 4090 server).
- **Unique value:** User asks e.g. *"Sarah, summarize the last 4 hours of Michael Saylor's mentions and compare it to whale inflows on Coinbase."* The avatar generates a **bespoke video brief** (local GPU) just for that user.
- **Proprietary edge:** On-demand AI video intelligence synthesized from live Bitcoin data — differentiated from generic 24/7 stream.

---

### 2. The "Nostr Shadow-Feed" (Ultra-Low Latency Signal)

- **Feature:** Proprietary algorithm on your server that identifies "alpha" on Nostr by tracking zaps and posts of the top ~500 Bitcoin developers and OGs.
- **Unique value:** Premium users see a **Signal Heatmap** that predicts news cycles 15–30 minutes before they trend on X.
- **Design:** Terminal-style view — high-speed matrix of incoming data with a **Confidence Score** for every breaking rumor.

---

### 3. "The Dossier" Interactive Alpha

- **Feature:** The existing 33 Dossier images become **Live Intelligence Assets** (no longer static).
- **Unique value:** Charts show **live-calculated proprietary metrics**, e.g. "Fiat Debasement" becomes the user's **real-time purchasing power** (local currency + spending habits vs. Bitcoin holdings).
- **Design:** High-end interactive "X-Ray" views; users can slide through historical shocks and see how their current portfolio would have performed.

---

### 4. Autonomous "Pulse" Alerts (Grok-Engineered)

- **Feature:** "The Pulse Wire" — private, ultra-high-conversion briefs to phone or Telegram.
- **Difference:** Not "BTC up 2%." Example: *"Grok identifies a major liquidity trap at $72k. 40% of long-interest we tracked in the last 2 hours is retail FOMO. Whale defense thinning. Watch for the flush."*

---

### Sovereign Tier Feature Matrix

| Feature | Standard (Free) | Sovereign ($100/mo) |
| --- | --- | --- |
| **Live Stream** | 24/7 Global Feed | **Personalized On-Demand Briefs** |
| **Data Access** | Public Charts | **Live Dossier Metrics (Proprietary)** |
| **Alerts** | Standard Price/News | **Grok "Signal vs. Noise" Wire** |
| **GPU Power** | Shared / Cloud | **Dedicated 4090 "Intelligence Lane"** |
| **The Dossier** | View Only | **Full Interactive Strategy Builder** |

---

### Project Outline for Cursor (Sovereign Tier Infrastructure)

Use this when you start building the value-gate (after 4090s are in place).

**1. Access control**
- Stripe / BTCPay Server gateway for **$100/mo** subscription.
- DB: `user_tier` (or extend existing tier) to distinguish **Standard** vs **Sovereign**.

**2. Proprietary data layer**
- **DossierLive** module: pull real-time data from the node to populate the 33 Dossier charts.
- Secure API endpoint **only for Sovereign** users to request **Bespoke Video Briefs** from the local 4090 pipeline.

**3. Design upgrades**
- **Sovereign Dashboard:** High-end, dark-themed "Command Center" UI for paid users. **Gold and deep red** accents (distinct from standard white/red).
- **Live Wire:** WebSockets-based live feed for Grok-drafted "Signal Wire."

**4. Personal AI agent**
- **PersonalAnalyst** component: sidebar chat/avatar that sends user queries to the server LLM (Llama 3 / Grok API) and triggers bespoke briefs on the 4090 pipeline.

---

### Next step (optional)

- Draft a **Sovereign Tier pitch page** — high-end, invitation-to-elite-intelligence-circle copy.

---

*Last updated: Feb 2026. Add new tasks below this section.*
