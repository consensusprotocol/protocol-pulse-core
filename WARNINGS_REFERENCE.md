# Protocol Pulse — Startup Warnings Reference

When you run `python app.py`, you may see warnings. **The app still runs**; these features are optional or need config.

---

## Safe to ignore (optional features)

| Warning | Meaning | Fix (optional) |
|--------|--------|----------------|
| **XAI_API_KEY missing** | Grok AI narrative is off | Add `XAI_API_KEY` to `.env` if you use Grok |
| **GEMINI_API_KEY missing** | Gemini narrative is off | Add `GEMINI_API_KEY` to `.env` if you use Gemini (and `pip install google-genai` with Python 3.9+) |
| **OPENAI_API_KEY missing** | Header image generation uses defaults | Add `OPENAI_API_KEY` to `.env` for AI-generated images |
| **Substack service not available** | No Substack publishing | Install substack module if you publish there |
| **sendgrid / SendGrid not installed** | Newsletter signup disabled | `pip install sendgrid` + set `SENDGRID_API_KEY` if you want email signups |
| **PRINTFUL_API_KEY not configured** | Merch store disabled | Add Printful keys to `.env` for merch |
| **youtube_transcript_api not installed** | Transcript fetching disabled | `pip install youtube-transcript-api` if you need it |
| **GHL service not configured** | GoHighLevel (newsletter/CRM) off | Add `GHL_API_KEY` and `GHL_LOCATION_ID` to `.env` for GHL |
| **routes_social not loaded - selenium** | Social monitoring blueprint skipped | `pip install selenium` only if you use that feature |
| **Python 3.8 / google.api_core FutureWarning** | Python 3.8 is past EOL | Upgrade to Python 3.10+ when convenient (e.g. new venv) |

---

## Needs config (if you use the feature)

| Warning | Meaning | Fix |
|--------|--------|-----|
| **PRAW client_id missing** | Reddit integration won’t work | In `.env` or `praw.ini`: set Reddit app `client_id` and `client_secret` (and optionally `client_id` / `client_secret` env vars PRAW expects) |

---

## Summary

- **Core site, Smart Analytics, Premium Hub, articles, and most pages work without any of these.**
- Warnings only mean optional services (Grok, Gemini, OpenAI, Substack, SendGrid, Printful, Reddit, GHL, Selenium) are off until you add keys or install packages.
- To reduce log noise you can add the API keys you don’t use as empty in `.env` (e.g. `XAI_API_KEY=`) only if the app checks “missing” vs “empty”; otherwise leaving them unset is fine.
