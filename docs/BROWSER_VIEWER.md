# Run Protocol Pulse and open the browser viewer

Use this when working **locally** (MacBook or desktop with the repo open) to see the site in Cursor’s browser or your system browser.

---

## 1. Start the server

In a terminal (Cursor’s integrated terminal or system terminal), from the **project root** (`ProtocolPulse`):

```bash
# From project root – uses core/app and run_server
python run_server.py
```

Or from the `core/` directory with a venv:

```bash
cd core
.venv/bin/python app.py
```

The app will listen on **http://127.0.0.1:5000** (or the port shown in the terminal).

---

## 2. Open the browser viewer

**Option A – Cursor Simple Browser**

1. **View → Open View…** (or **Cmd+Shift+P** / **Ctrl+Shift+P**).
2. Type **Simple Browser** and run **“Simple Browser: Show”**.
3. Enter: **http://127.0.0.1:5000**
4. The Protocol Pulse site opens inside Cursor.

**Option B – System browser**

- Open Chrome/Safari/Firefox and go to: **http://127.0.0.1:5000**

---

## 3. If the viewer is blank or “not working”

- Confirm the server is running (you should see log lines in the terminal).
- Use exactly **http://127.0.0.1:5000** (or the port the server prints).
- If you changed the port (e.g. `PORT=5001 python run_server.py`), use that port in the URL.
- Hard refresh: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Windows).

---

## When you’re on Ultron (Remote-SSH)

If you opened the project **on Ultron** (SSH: ultron → Open Folder → `/home/ultron/protocol_pulse`), the server runs on Ultron. Then:

1. Start the server in the **remote** terminal (on Ultron).
2. In Cursor, use **Ports** (View → Ports): find port **5000** and click **“Open in Browser”** (or “Forward”), so the viewer opens to the forwarded port.

That way the site is served from the 4090s and you view it through the tunnel.
