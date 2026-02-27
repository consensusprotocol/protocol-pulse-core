# Render environment variables checklist

Copy each **value** from your local `core/.env` into Render's **Environment** tab.  
In Render: **Environment** → **Add Environment Variable** → paste the **key** below and the **value** from your .env.

**Do not commit your .env file or paste secrets into this repo.**

**Render is safe for API keys:** env vars are encrypted, not shown in logs or build output, and only visible to you in the dashboard. You can add all of them.

---

## Set these first (required)

| Key | Where to get the value |
|-----|------------------------|
| `FLASK_ENV` | Type exactly: **`production`** (not in your .env; set it only on Render). |
| `SESSION_SECRET` | Your local **core/.env** → line `SESSION_SECRET=...` — copy the value. Or generate a new one: `openssl rand -hex 32` in a terminal. |

Add these two in Render **Environment** before anything else. Then add the rest (see below or use “Add from .env” with your full .env).

---

## Only these are required for the app to run

The app **starts and runs** with just these. Everything else is optional and only enables specific features (tweets, Stripe, YouTube, etc.). If a key is missing, that feature is disabled; the app does not crash.

| Key | Notes |
|-----|--------|
| `FLASK_ENV` | Set to `production`. |
| `SESSION_SECRET` | **Required in production.** Use a long random string (e.g. from `openssl rand -hex 32`). The app has a dev default but you must override it on Render. |
| `DATABASE_URL` | Optional. Default is SQLite; for production you’ll usually want a Render (or Neon) PostgreSQL URL. |
| `PORT` | Do **not** set on Render — Render sets it automatically. |

So at minimum you can add only: **FLASK_ENV**, **SESSION_SECRET**, and optionally **DATABASE_URL** (if you use Postgres).

---

## Database (pick one)

- **SQLite (simplest):** Keep `DATABASE_URL=sqlite:///protocol_pulse.db` – data will not persist across deploys unless you add a persistent disk.
- **PostgreSQL (recommended for production):** In Render create a **PostgreSQL** database, then add `DATABASE_URL` with the **Internal Database URL** Render shows. Your app already supports `DATABASE_URL` for SQLAlchemy.

---

## API keys — add only for features you use

Add these **only if** you use the corresponding feature on the deployed site. Missing keys simply disable that feature.

| Key |
|-----|
| `XAI_API_KEY` |
| `OPENAI_API_KEY` |
| `ANTHROPIC_API_KEY` |
| `GEMINI_API_KEY` |
| `ASSEMBLYAI_API_KEY` |
| `CAPTIONS_API_KEY` |
| `ELEVENLABS_API_KEY` |
| `HEYGEN_API_KEY` |
| `GHL_API_KEY` |
| `GHL_LOCATION_ID` |
| `GITHUB_TOKEN` |
| `NOSTR_PRIVATE_KEY` |
| `PRINTFUL_API_KEY` |
| `REDDIT_CLIENT_ID` |
| `REDDIT_CLIENT_SECRET` |
| `REDDIT_USER_AGENT` |
| `STRIPE_SECRET_KEY` |
| `STRIPE_WEBHOOK_SECRET` |
| `SUBSTACK_EMAIL` |
| `SUBSTACK_PASSWORD` |
| `SUBSTACK_PUBLICATION_URL` |
| `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_CHAT_ID` |
| `YOUTUBE_API_KEY` |
| `YOUTUBE_CLIENT_ID` |
| `YOUTUBE_CLIENT_SECRET` |
| `YOUTUBE_REFRESH_TOKEN` |

---

## X (Twitter) – if you use tweet posting / Spaces

Add these if your app uses them (see .env.example):

| Key |
|----|
| `TWITTER_API_KEY` |
| `TWITTER_API_SECRET` |
| `TWITTER_ACCESS_TOKEN` |
| `TWITTER_ACCESS_TOKEN_SECRET` |
| `TWITTER_BEARER_TOKEN` |

---

## Neon Postgres (if you use Neon instead of Render Postgres)

| Key |
|----|
| `PGDATABASE` |
| `PGHOST` |
| `PGPASSWORD` |
| `PGPORT` |
| `PGUSER` |

If you use Neon, you can set `DATABASE_URL=postgresql://PGUSER:PGPASSWORD@PGHOST:PGPORT/PGDATABASE` instead of separate PG* vars if your app builds the URL from them.

---

## Quick method: add all keys at once

1. Open your local **core/.env** in a text editor.
2. In Render → your service → **Environment** → **Add from .env**.
3. Paste the **contents** of your .env (key=value lines; you can remove the `PORT=5000` line so Render’s PORT is used).
4. Click **Add** — Render will create every variable.
5. Add **`FLASK_ENV`** = **`production`** manually (it’s usually not in .env). If you didn’t have `SESSION_SECRET` in the paste, add it too (see “Set these first” above).
6. Trigger a **Manual Deploy** so the new env is used.

Do this only from your machine; don’t commit .env or paste it anywhere public.
