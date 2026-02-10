# Keep Mac, Desktop, and Ultron in sync

The repo is on GitHub: **https://github.com/consensusprotocol/protocol-pulse-core**

---

## What was just done (MacBook)

- All current work was committed and **pushed to `main`** (commit: *Sync: full codebase for Mac/Desktop/Ultron*).
- The `core/` folder is now part of the main repo (no nested git).

---

## Sync your **Desktop** (Windows Cursor)

**Option A – Work on the project on Ultron (recommended)**  
1. In Windows Cursor: **Ctrl+Shift+P** → **Remote-SSH: Connect to Host** → **ultron**.  
2. **File → Open Folder** → choose the project path on Ultron (e.g. `/home/ultron/protocol_pulse`).  
3. On Ultron (in a terminal over SSH), run **once** to get the latest from GitHub:
   ```bash
   cd /home/ultron/protocol_pulse   # or your actual path
   git pull origin main
   ```
   After that, you’re editing the same files as on the Mac; “sync” = just **git pull** on Ultron when the Mac (or anyone) has pushed.

**Option B – Clone the repo on the Windows machine**  
1. On Windows, open a terminal (PowerShell or Command Prompt).  
2. Clone and open in Cursor:
   ```bash
   git clone https://github.com/consensusprotocol/protocol-pulse-core.git
   cd protocol-pulse-core
   ```
   Then in Cursor: **File → Open Folder** → select `protocol-pulse-core`.  
3. To get the latest after you or someone else pushes from the Mac:
   ```bash
   git pull origin main
   ```

---

## Sync **Ultron** (4090 server)

If the project is already on Ultron (e.g. `/home/ultron/protocol_pulse`):

```bash
cd /home/ultron/protocol_pulse
git pull origin main
```

If the project is **not** on Ultron yet:

```bash
cd /home/ultron
git clone https://github.com/consensusprotocol/protocol-pulse-core.git protocol_pulse
cd protocol_pulse
```

Then from **Mac or Desktop Cursor**: Connect to Host → **ultron**, and **Open Folder** → `/home/ultron/protocol_pulse`.

---

## Workflow from here

| Who pushes | Where to pull |
|------------|----------------|
| You from MacBook | On Ultron: `git pull origin main`. On Windows (if local clone): `git pull origin main`. |
| You from Desktop (local clone) | Commit and push from Windows, then on Mac: `git pull origin main`, and on Ultron: `git pull origin main`. |
| You from Desktop (editing on Ultron) | Edit on Ultron, then from Ultron terminal: `git add -A && git commit -m "..." && git push origin main`. Then on Mac: `git pull origin main`. |

So: **one repo on GitHub** = single source of truth. Mac, Desktop, and Ultron stay in sync by **pull** (and **push** when you make changes on that machine).
