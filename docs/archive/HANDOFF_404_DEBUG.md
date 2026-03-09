# Protocol Pulse – 404 on `/` – Handoff for LLM / Human Debugging

## Goal

When running the Flask app and visiting `http://127.0.0.1:5000/` (or 5001), the **root URL should return 200** and show the Protocol Pulse homepage. Currently it returns **404 Not Found**.

---

## What’s Already Been Done

- **Circular imports**: Replaced `from models import ...` with `import models` and `models.Article`, etc., in `core/routes.py`, `core/app.py`, and services.
- **Optional API keys**: Grok, Gemini, image service, etc. log warnings and set `client = None` instead of raising when keys are missing.
- **Optional services**: Substack, RSS, newsletter, fact_checker use try/except; missing modules don’t crash startup.
- **Duplicate block in `routes.py`**: A second, nearly identical block of imports and service init (and a second `admin_required`) at lines 69–128 was **removed**. Only one such block remains (top of file).
- **Missing template**: The index route renders `index.html`, but that file did not exist. A minimal `core/templates/index.html` was **added** (extends `base.html`, shows title, Today’s Signal, featured/recent articles).
- **Debug endpoint**: `GET /debug-routes` was added. It returns JSON listing all registered URL rules. Use it to confirm whether the **process actually serving the request** has `/` (and `debug_routes`) registered.

---

## Why 404 (Most Likely)

- The **same codebase**, when loaded in a single process (e.g. `python app.py` from `core/`), **does** register `@app.route('/')` and `index()`. Introspecting `app.url_map` in that process shows `/` in the list.
- So the 404 almost certainly means one of:
  1. **Wrong process on the port**  
     Another Flask app (e.g. `flask run` from repo root without `FLASK_APP=core.app:app`, or an old/other project) is bound to 5000/5001. That app has no `/` route → 404.
  2. **Stale process**  
     An old Python process is still running and wasn’t restarted after fixes. It doesn’t have the updated routes or the new `index.html`.

So the fix is: **ensure the only thing listening on the port is the app started by `core/app.py`**, and that you’ve restarted it after the changes above.

---

## How to Run (Single Source of Truth)

- **Working directory**: `core/` (the directory that contains `app.py`, `routes.py`, `models.py`).
- **Command**:
  ```bash
  cd /Users/pbe/ProtocolPulse/core
  PORT=5001 .venv/bin/python app.py
  ```
- **Do not** rely on `flask run` from the repo root unless you set `FLASK_APP` to `core.app:app` and run from a context where `core` is on the Python path; otherwise a minimal Flask app with no routes can be served → 404.

Before starting, free the port:

```bash
lsof -i :5000
lsof -i :5001
# If something is listening, kill those PIDs: kill -9 <PID>
```

---

## Verify Which App Is Running

1. Start the app as above.
2. In another terminal:
   - `curl -s http://127.0.0.1:5001/debug-routes`  
     You should see JSON with `"app": "Protocol Pulse"` and a `"rules"` array that includes `{"rule": "/", ...}` and `{"rule": "/debug-routes", ...}`.
   - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/`  
     Should be `200` (if you get 404, the process on 5001 is not this app or not restarted).
3. Open `http://127.0.0.1:5001/` in a browser; you should see the Protocol Pulse homepage (minimal index with Today’s Signal and article links).

If `/debug-routes` returns 404, then the server on that port is **not** the Protocol Pulse app from `core/app.py`.

---

## Codebase Summary (Relevant to 404 and Startup)

### Entrypoint: `core/app.py`

- Loads `.env` from `core/` (directory of `app.py`).
- Creates a single Flask app: `app = Flask(__name__)`.
- Then:
  ```python
  with app.app_context():
      import models
      db.create_all()
      import routes
  ```
- So **routes are registered only when `import routes` runs**; that happens inside `app.app_context()` and registers all `@app.route(...)` in `routes.py` (including `@app.route('/')` and `@app.route('/debug-routes')`).
- Run: `app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000), debug=True)` when `__name__ == "__main__"`.

### Routes: `core/routes.py`

- `from app import app, db` and `import models` (no `from models import ...`).
- Single block of service imports and inits, then `admin_required`, then template filter `clean_preview`, then:
  - `@app.route('/debug-routes')` → `debug_routes()` → JSON of `app.url_map.iter_rules()`.
  - `@app.route('/')` → `index()` → `render_template('index.html', featured_articles=..., recent_articles=..., ...)`.
- No other file in this project defines a second `Flask(__name__)` or a competing `/` route.

### Models: `core/models.py`

- `from app import db`; defines `User`, `Article`, `Podcast`, etc. Used in routes as `models.Article`, etc.

### Templates

- `core/templates/base.html` – base layout.
- `core/templates/index.html` – **now present**; extends `base.html`, uses `featured_articles`, `recent_articles`, `todays_signal`, etc.
- `core/templates/dashboard.html`, `article_detail.html`, etc. for other routes.

### Services (optional / resilient)

- Under `core/services/`: AI, Reddit, content generator/engine, Substack, RSS, newsletter, Printful, price, YouTube, node, GHL, etc. Many have optional imports or optional API keys; failures don’t prevent `import routes` from completing.

---

## Checklist for Next Debugger / User

- [ ] No other Flask/Python server is bound to 5000 or 5001 (`lsof -i :5000`, `lsof -i :5001`; kill if needed).
- [ ] Start **only** with: `cd /Users/pbe/ProtocolPulse/core && PORT=5001 .venv/bin/python app.py`.
- [ ] Hit `http://127.0.0.1:5001/debug-routes`; confirm JSON includes `"/"` and `"/debug-routes"`.
- [ ] Hit `http://127.0.0.1:5001/`; expect 200 and the Protocol Pulse index page.
- If `/debug-routes` returns 404, the responder is not this app → track which process is bound to the port and how it was started (and avoid `flask run` from repo root without correct `FLASK_APP`).

---

## Switching Cursor Agent / LLM

You can change which model Cursor uses for the agent:

- **Cursor Settings** → **Models** (or **Cursor Settings** → **Agent**): choose a different model for “Agent” or “Composer” (e.g. another Claude or GPT model). The exact menu name can vary by Cursor version.
- You can also paste this handoff doc (and the file contents below) into another LLM (e.g. in a new chat or another tool) for a second opinion.

---

## Key File Paths (for copy-paste into another LLM)

- Entrypoint: `core/app.py`
- Routes (and `/`, `/debug-routes`): `core/routes.py` (large file; search for `@app.route('/')` and `debug_routes`)
- Models: `core/models.py`
- Index template: `core/templates/index.html`
- Base template: `core/templates/base.html`

End of handoff.
