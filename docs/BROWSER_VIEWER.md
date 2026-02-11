# Run Protocol Pulse and open the browser viewer

Use this when working **locally** (MacBook or desktop with the repo open) to see the site in Cursor’s browser or your system browser.

**The app runs on port 5001** (so it doesn’t conflict with macOS AirPlay on 5000).

---

## 1. Start the server

**In Cursor’s terminal** (`` Ctrl+` `` or View → Terminal), from the **project root**:

```bash
python3 run_server.py
```

Leave that terminal open. When you see `Running on http://127.0.0.1:5001`, the server is ready.

**Or use the task (if you have .vscode/tasks.json):** **Cmd+Shift+P** → **Tasks: Run Task** → **Start Protocol Pulse (browser on :5001)**.

---

## 2. Open the browser viewer

**Option A – Cursor Simple Browser (recommended)**

1. **Cmd+Shift+P** (Mac) or **Ctrl+Shift+P** (Windows).
2. Type **Simple Browser** and choose **“Simple Browser: Show”**.
3. When asked for the URL, enter exactly: **http://127.0.0.1:5001**
4. Press Enter. The Protocol Pulse site should load inside Cursor.

**Option B – System browser**

- Open Safari/Chrome/Firefox and go to: **http://127.0.0.1:5001**

---

## 3. If the viewer is blank or “not working”

- **Server must be running first.** In the terminal you should see `Running on http://127.0.0.1:5001`. If not, run `python3 run_server.py` from the project root.
- **Use port 5001.** The URL must be **http://127.0.0.1:5001** (not 5000).
- **Hard refresh:** **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Windows).
- If port 5001 is in use, run `PORT=5002 python3 run_server.py` and open **http://127.0.0.1:5002** in the browser.

---

## When you’re on Ultron (Remote-SSH)

If you opened the project **on Ultron** (SSH: ultron → Open Folder → `/home/ultron/protocol_pulse`), the server runs on Ultron. Then:

1. Start the server in the **remote** terminal (on Ultron).
2. In Cursor, use **Ports** (View → Ports): find port **5000** and click **“Open in Browser”** (or “Forward”), so the viewer opens to the forwarded port.

That way the site is served from the 4090s and you view it through the tunnel.
