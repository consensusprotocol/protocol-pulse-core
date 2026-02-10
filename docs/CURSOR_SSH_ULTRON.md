# Connect Cursor to Ultron (4090 server)

Use Ultron so **all agent runs, scripts, and builds use the 4090s** instead of your MacBook or desktop. See [Use 4090s for all workload](#use-4090s-for-all-workload-macbook--desktop) below.

Your `~/.ssh/config` already has the **ultron** host configured:

- **Host shortcut:** `ultron`
- **HostName:** 192.168.1.175
- **User:** ultron
- **ServerAliveInterval:** 60 (keeps connection alive during long renders)

---

## How to connect (no green icon needed)

### Option A: Command Palette (most reliable)

1. In Cursor, press **`Cmd + Shift + P`** (Mac) to open the Command Palette.
2. Type: **`Remote-SSH: Connect to Host`**
3. Choose **`ultron`** from the list (or type `ultron` and press Enter).
4. A new Cursor window will open. If prompted, enter the **ultron** user’s password for the server.
5. When connected, the **bottom-left** of the window will show **`SSH: ultron`** (or a remote icon).

### Option B: Status bar icon (if you see it)

- Look at the **very bottom-left** of the Cursor window for a small **`><`** or remote/connection icon.
- Click it → **Connect to Host...** → **ultron**.

---

## Verify the connection

1. With **SSH: ultron** showing in the bottom-left, open the Terminal in Cursor: **`Ctrl + \``** (backtick) or **View → Terminal**.
2. Run:
   ```bash
   nvidia-smi
   ```
3. You should see the dual 4090 table. Bridge is working.

---

## Optional: passwordless login (SSH key)

On your **MacBook** (local terminal, not Cursor’s remote terminal):

```bash
# Generate key if you don’t have one
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy key to Ultron (use your ultron password when asked)
ssh-copy-id -i ~/.ssh/id_ed25519.pub ultron@192.168.1.175
```

Then add to `~/.ssh/config` for the ultron host:

```
IdentityFile ~/.ssh/id_ed25519
```

After that, **Connect to Host → ultron** in Cursor won’t ask for a password.

---

## If “ultron” doesn’t appear in the list

1. **Cmd + Shift + P** → **Remote-SSH: Open SSH Config File**
2. Choose **`/Users/pbe/.ssh/config`**
3. Confirm the `Host ultron` block is there (it already is). Save and try **Connect to Host** again.

---

## Windows: same project, in sync

To work on **the exact same project** from Windows Cursor and keep it in sync with your Mac:

1. **SSH config on Windows**  
   - Open or create `C:\Users\<YourUsername>\.ssh\config`.  
   - Add the same block (use the same IP as above):
     ```
     Host ultron
         HostName 192.168.1.175
         User ultron
         ServerAliveInterval 60
     ```
   - Save the file.

2. **Connect from Windows Cursor**  
   - **Ctrl+Shift+P** → **Remote-SSH: Connect to Host** → **ultron**.  
   - Enter the ultron password when prompted.

3. **Open the project on Ultron**  
   - After connecting, use **File → Open Folder** and choose the project path on the server (e.g. `/home/ultron/protocol_pulse` if you cloned or copied the repo there).  
   - You’re now editing the **same files** as when you connect from the Mac to ultron. One copy of the project, two machines; no sync needed.

4. **If the project isn’t on Ultron yet**  
   - On Ultron (e.g. in a terminal over SSH): clone or copy the repo to a path like `/home/ultron/protocol_pulse`.  
   - Then from Mac or Windows Cursor, Connect to Host → ultron and Open Folder → that path.

**Note:** The AI in Cursor doesn’t “follow” you between Mac and Windows—each session is separate. What stays the same is the **project** (same repo and rules on Ultron), so whichever machine you use, you’re working on the same codebase and Cursor can use the same rules and context there.

---

## Use 4090s for all workload (MacBook + Desktop)

To keep your MacBook (and desktop) cool and offload **all rendering and processing** to the 4090s:

### What runs on the 4090s when you do this

- **All terminal commands** the agent runs (e.g. `python`, `pip`, `npm`, tests, scripts) run **on Ultron**.
- **All file reads/writes** are on Ultron’s disk; the agent edits files there.
- **Any GPU work** you run (e.g. `python gpu_test.py`, Medley, training) uses the 4090s.

So: **always open the project on Ultron**, not the local folder. Then Cursor’s integrated terminal is a **remote** terminal on Ultron, and every command the agent runs executes on the 4090s machine. Your laptop only runs the Cursor UI and SSH; heavy compute is on Ultron.

### What does *not* run on your 4090s

- **Cursor’s own AI** (Chat, Composer, Agent “brain”) runs on **Cursor’s cloud** (their servers). Cursor does not support pointing that at your own GPU server. So the LLM inference is already not on your MacBook—it’s in the cloud. You can’t move that to Ultron with normal Cursor settings.

### How to set it up (MacBook and Desktop)

1. **Connect to Ultron first:** **Cmd+Shift+P** (Mac) or **Ctrl+Shift+P** (Windows) → **Remote-SSH: Connect to Host** → **ultron**.
2. **Open the project on Ultron:** **File → Open Folder** → `/home/ultron/protocol_pulse` (or wherever the repo lives on Ultron).
3. Work in **that** window. The bottom-left should show **SSH: ultron**. Any terminal you open (e.g. **View → Terminal**) is on Ultron; anything the agent runs there uses the 4090s.

If you open a **local** folder (e.g. `/Users/pbe/ProtocolPulse` on the Mac), the terminal and agent commands run **on your Mac**, so the CPU/fans will spin up. For maximum offload, always use **Connect to Host → ultron** and **Open Folder** on the remote path.

---

## Quick reference

| Step              | Action                                      |
|-------------------|---------------------------------------------|
| Open Command Palette | `Cmd + Shift + P` (Mac) / `Ctrl + Shift + P` (Windows) |
| Connect to Ultron | **Remote-SSH: Connect to Host** → **ultron** |
| Open SSH config   | **Remote-SSH: Open SSH Config File**        |
| Verify GPUs       | In remote terminal: `nvidia-smi`            |
