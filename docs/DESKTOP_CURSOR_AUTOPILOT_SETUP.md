# Desktop Cursor: Autopilot setup (copy-paste instructions)

Use this **entire block** in Cursor on your desktop: open a new chat, paste it, and send. Cursor will apply the settings so the agent can run with minimal approval prompts.

---

## Copy from here (paste into Cursor chat on desktop)

```
Configure this Cursor installation for autopilot: I want the agent to execute jobs (edit files, run terminal commands) without stopping for my approval every time.

Do the following:

1) Find and open the Cursor User settings.json:
   - On Windows: %APPDATA%\Cursor\User\settings.json (e.g. C:\Users\<YourUsername>\AppData\Roaming\Cursor\User\settings.json)
   - On macOS: ~/Library/Application Support/Cursor/User/settings.json

2) Add or update these keys in that file (merge with existing settings; do not remove other keys):
   - "cursor.chat.enableYoloMode": true
   - "cursor.chat.autoApplyChanges": true
   - "cursor.chat.reviewChanges": "autorun"

3) If I use Remote-SSH to a host named "ultron", also set:
   - "remote.SSH.remotePlatform": { "ultron": "linux" }

4) Save the file. If the file or parent folder does not exist, create it first.

Apply these changes now. Use the correct path for this machine (Windows or macOS).
```

---

## What these settings do

| Setting | Effect |
|--------|--------|
| `cursor.chat.enableYoloMode`: true | Agent can run tools (terminal, file writes) without asking for confirmation each time. |
| `cursor.chat.autoApplyChanges`: true | Agent can apply edits to files without you approving every change. |
| `cursor.chat.reviewChanges`: "autorun" | Review-changes flow runs in auto-run mode instead of stopping for approval. |
| `remote.SSH.remotePlatform` | Tells Cursor that the host "ultron" is Linux (for Remote-SSH). |

**Note:** With yolo mode on, the agent can run commands and edit files automatically. Use only in a workspace you trust. You can turn these off later in Cursor Settings (Cmd+Shift+J → Chat → disable “Enable yolo mode” and adjust “Review changes”).

---

## If you prefer doing it by hand

1. **Open Cursor Settings:** `Cmd+Shift+J` (Mac) or `Ctrl+Shift+J` (Windows).
2. Go to **Features → Chat**.
3. Under **Automation**, enable **“Enable yolo mode”**.
4. Enable **“Auto-Apply to files outside context”** (if shown).
5. Under **Beta** or **Review**, set **“Review changes”** to **Auto-run** (if available).
6. Reload the window if prompted.
