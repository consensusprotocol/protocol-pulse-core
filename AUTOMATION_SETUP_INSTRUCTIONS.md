# PROTOCOL PULSE - AUTOMATION SETUP INSTRUCTIONS

## ✅ WHAT'S BEEN FIXED

1. **Created robust automation system** with database-backed locking and error tracking
2. **Added AutomationRun table** to track every execution
3. **Built idempotent automation worker** (`automation_worker.py`) that prevents duplicate runs
4. **Added health check endpoint** at `/health/automation` for monitoring
5. **Tested successfully** - just generated article #16 with full tracking

---

## 🚀 HOW TO SET UP CONTINUOUS AUTOMATION

### Option 1: Create a Replit Workflow (RECOMMENDED)

**Steps:**
1. In your Replit project, click the **Tools** button (wrench icon) in the left sidebar
2. Click **"Add Workflow"** or **"New Workflow"**
3. Configure the workflow:
   - **Name:** `Article Automation`
   - **Command:** `python3 automation_worker.py`
   - **Schedule:** Every 15 minutes (use cron expression: `*/15 * * * *`)
4. Click **"Save"** and **"Enable"**

Your automation will now run every 15 minutes automatically!

---

### Option 2: Manual Background Runner

If you prefer manual control, run this command in Replit Shell:

```bash
# Run automation in background with logging
nohup bash -c 'while true; do python3 automation_worker.py; sleep 900; done' > /tmp/automation.log 2>&1 &
```

To stop it:
```bash
pkill -f automation_worker.py
```

---

## 📊 MONITORING AUTOMATION

### Check Health Status
```bash
curl http://localhost:5000/health/automation
```

### View Automation Logs (Database)
```sql
SELECT * FROM automation_run ORDER BY started_at DESC LIMIT 10;
```

### View Recent Articles
```sql
SELECT id, title, created_at FROM article ORDER BY created_at DESC LIMIT 5;
```

---

## 🔍 HOW IT WORKS

1. **Replit Workflow** calls `automation_worker.py` every 15 minutes
2. **automation_worker.py** acquires a database lock to prevent duplicates
3. **services/automation.py** generates a fresh breaking news article
4. **Article is saved** to database with `published=True`
5. **Attempts Substack publishing** (currently blocked by CAPTCHA - user must manually verify Substack login once)
6. **Lock is released** with success/failure status
7. **Health check** monitors last run time and status

---

## ⚠️ KNOWN LIMITATIONS

### Substack Auto-Publishing
Substack now requires CAPTCHA verification. To fix:
1. Go to https://substack.com/sign-in
2. Sign in with your Substack credentials
3. Complete the CAPTCHA once
4. Auto-publishing should resume

Alternatively, you can disable Substack auto-publishing by commenting out the Substack code in `services/automation.py`.

---

## 🛠️ TROUBLESHOOTING

### Automation Not Running
```bash
# Check if workflow is enabled in Replit Tools panel
# OR manually run:
python3 automation_worker.py
```

### Check Lock Status
```sql
SELECT * FROM automation_run WHERE finished_at IS NULL;
```

### Clear Stuck Locks
```sql
UPDATE automation_run SET finished_at = NOW(), status = 'timeout' WHERE finished_at IS NULL;
```

---

## 📈 CURRENT STATUS

- ✅ Web server running on port 5000
- ✅ All AI APIs connected (Grok, Gemini, OpenAI)
- ✅ Database operational with PostgreSQL
- ✅ Automation system tested and working
- ✅ Health monitoring active at `/health/automation`
- ✅ Article #16 successfully generated via automation
- ⏳ Waiting for Replit Workflow to be enabled

**Next step:** Create the Replit Workflow as described in Option 1 above!

---

END OF SETUP INSTRUCTIONS
