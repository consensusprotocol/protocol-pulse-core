# Work from any device

The app code lives on GitHub. Use this to pick up the project on another machine (e.g. office desktop, second laptop).

---

## One-time per device

1. **Clone the repo**
   ```bash
   git clone https://github.com/consensusprotocol/protocol-pulse-core.git
   cd protocol-pulse-core
   ```
   (If you already have the repo, just `cd` into it and run `git pull origin main`.)

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Add your secrets (do not commit)**
   - Copy your **`.env`** from a device that already has it (e.g. USB, secure share, password manager), and put it in the **`protocol-pulse-core`** folder (same folder as `app.py`).
   - Or create a new `.env` with the same keys and paste values from your password manager or Render’s Environment tab.
   - See **RENDER_ENV_KEYS.md** for the list of variable names.

4. **Run the app locally**
   ```bash
   python run.py
   ```
   Or: `flask run` (with `FLASK_APP=app` if needed). Default: http://127.0.0.1:5000

---

## Daily workflow on any device

- **Get latest code:** `git pull origin main`
- **Run locally:** `source .venv/bin/activate` then `python run.py` (or `flask run`)
- **Push your changes:** `git add ... && git commit -m "..." && git push origin main`  
  Render will auto-deploy from `main` if you have that enabled.

---

## Notes

- **`.env`** is in `.gitignore` and is not in the repo. You must copy it to each device yourself (or recreate it from Render/env keys).
- **Media** (e.g. under `static/video/`, `static/audio/`) is not in the repo. If you need it locally, copy from your backup (e.g. `~/ProtocolPulse-media-archive`) into `static/`; the live site on Render doesn’t need those files unless you re-upload them.
- **Database:** Local SQLite is in `instance/` (gitignored). Each device has its own DB unless you point `DATABASE_URL` at a shared Postgres (e.g. Neon or Render).
