# Hosting & protocolpulse.io

**Cursor does not host websites.** It’s an editor/IDE; it runs on your machine and has no servers to point a domain at.

To get **protocolpulse.io** live:

1. **Choose a host** (you’re no longer on Replit), for example:
   - **Railway** – simple Flask deploy, free tier, then paid
   - **Render** – free tier for web services, then paid
   - **Fly.io** – good for containers, free allowance
   - **VPS** (DigitalOcean, Linode, etc.) – you run `gunicorn`/`nginx` yourself

2. **Point Namecheap DNS at that host**
   - For **Railway / Render / Fly**: they give you a hostname (e.g. `yourapp.up.railway.app`). In Namecheap for `protocolpulse.io`:
     - Add a **CNAME** record: `www` → `yourapp.up.railway.app` (or whatever they give you).
     - For the **root** domain (`protocolpulse.io`), many hosts support an **ALIAS/ANAME** or “root CNAME”; otherwise use their **A** record IP if they provide one.
   - For a **VPS**: create **A** records for `@` and `www` to your server’s IP.

3. **SSL**  
   Hosts like Railway/Render/Fly provide HTTPS. On a VPS, use **Let’s Encrypt** (e.g. Certbot) with nginx.

4. **App config**  
   Set `FLASK_ENV=production`, use `gunicorn` (or the host’s recommended WSGI server), and put secrets in env vars (no `.env` in repo).

Once the app is deployed somewhere, you only need to update DNS at Namecheap to point protocolpulse.io to that deployment.

---

## Deploy on Render (consensusprotocol/protocol-pulse-core)

1. **Connect the repo**
   - Go to [dashboard.render.com](https://dashboard.render.com) → New → Web Service.
   - Connect **GitHub** and select repo **consensusprotocol/protocol-pulse-core** ([github.com/consensusprotocol/protocol-pulse-core](https://github.com/consensusprotocol/protocol-pulse-core)).
   - Render will use `render.yaml` in the repo root (this repo’s root is the app: `app.py`, `requirements.txt`).

2. **Build & start (from render.yaml)**
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn -b 0.0.0.0:$PORT app:app`
   - **Environment:** `FLASK_ENV=production`, `PYTHON_VERSION=3.12`

3. **Environment variables**
   - In Render → your service → Environment, add the same keys you use in `core/.env` (API keys, DB URL, etc.). Do **not** commit `.env`; paste values in the Render UI.

4. **Custom domain**
   - In Render → your service → Settings → Custom Domains, add `protocolpulse.io` and `www.protocolpulse.io`.
   - Render will show the CNAME target (e.g. `protocol-pulse-core-xxxx.onrender.com`). In Namecheap, set:
     - **CNAME** `www` → that target.
     - For root `@`, use Render’s root domain instructions (often an A/ALIAS record or their proxy).
