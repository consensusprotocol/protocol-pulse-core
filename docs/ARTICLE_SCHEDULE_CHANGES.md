# Article delete + new draft schedule — where to see the changes

Use **Cmd+P** (Mac) or **Ctrl+P** (Windows/Linux) in Cursor, then type the path to open the file.

---

## 1. New script: delete all articles

**File:** `scripts/delete_all_articles.py` (new file, full content is the change)

- Run with: `./venv/bin/python scripts/delete_all_articles.py --dry-run` or `--confirm`
- Deletes all `Article` rows and dependent rows (LaunchSequence, SentimentReport, SarahBrief, EmergencyFlash)

---

## 2. Scheduler changes: `services/scheduler.py`

**Open:** `services/scheduler.py`

| What | Line numbers |
|------|--------------|
| New env flag + UTC windows | **30–35** |
| New tasks in `TASKS` dict | **53–54** |
| `cypherpunk_loop` disabled when new schedule on | **247–255** |
| `article_draft_burst_4` (4 articles every 15 min, UTC 00–07) | **257–273** |
| `article_draft_hourly_1` (1 article/hour, UTC 12–23) | **275–286** |
| Scheduler registration: burst + hourly vs cypherpunk | **439–444** |

---

## Quick open in Cursor

1. **Cmd+P** / **Ctrl+P** → type `delete_all_articles` → open `scripts/delete_all_articles.py`
2. **Cmd+P** / **Ctrl+P** → type `scheduler.py` → open `services/scheduler.py`, then go to line **30** (or **257**) to see the new logic

---

## Git

- `scripts/delete_all_articles.py` is **untracked** (new file). It will appear in the Source Control sidebar under "Untracked".
- `services/scheduler.py` is **modified**. In Source Control, click it to see the diff.

To see the diff in terminal: `git diff services/scheduler.py`
