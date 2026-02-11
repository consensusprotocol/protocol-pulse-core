# Protocol Pulse — Ghost Curation Extension

Overlay Value Stream onto X (Twitter). See Alpha signals, zap from the timeline, leave the noise for the giants.

## What it does

- **Ghost overlay on X**: On twitter.com and x.com, tweets from the Protocol Pulse KOL list get a subtle high-voltage red border.
- **Signal High**: If 3+ Alpha-seekers have zapped that post, the border glows stronger.
- **Pulse Zap button**: One-click zap (WebLN) without leaving the timeline. Payment is recorded on Protocol Pulse; optional X reply notifies the author.
- **Alpha count**: Shows “⚡ N Alpha-seeker(s)” when others have already signaled that post.

## Install

1. Chrome or Brave: open `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, select the folder containing this `manifest.json`.
2. Ensure the backend URL is set (popup → “Save backend URL”). Default: `https://protocolpulse.com`.
3. Install a WebLN wallet (e.g. [Alby](https://getalby.com)) to zap from the timeline.

## Backend

The extension calls your Protocol Pulse backend (or Ultron) for:

- `GET /api/value-stream/kol-list` — Alpha list (X handles) for overlay.
- `GET /api/value-stream/signal-check?url=...` — Zap count and post_id for a tweet URL.
- `POST /api/value-stream/submit` — Add tweet to Value Stream (body: `{ "url": "..." }`).
- `POST /api/value-stream/invoice/:post_id` — Create Lightning invoice (body: `{ "amount_sats": N }`).
- `POST /api/value-stream/confirm-zap` — Confirm payment after WebLN (body: `{ "post_id", "amount_sats", "payment_hash" }`).

CORS must allow requests from the extension (e.g. allow your backend origin or use a proxy).

## Files

- `manifest.json` — Extension manifest (content script on twitter.com, x.com).
- `content.js` — Injects Shadow DOM overlay (border, Alpha count, Zap button); uses KOL list and signal-check.
- `background.js` — Service worker: `getOrigin`, `fetch` (so API calls avoid CORS from the page).
- `popup.html` / `popup.js` — Popup UI: backend URL, curate/zap from current tab.
- `content.css` — Legacy styles (floating button); Ghost UI is in content.js Shadow DOM.

## Sovereign Parasite

You are not building a competitor. You are overlaying Protocol Pulse onto existing habits: strip-mining high-value users (Bitcoiners / Alpha-seekers) and leaving the noise for the giants.
