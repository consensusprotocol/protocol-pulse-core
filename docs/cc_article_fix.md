Load ~/protocol_pulse/PIPELINE_LAWS.md first. Then fix the article pipeline in one pass.

CONTEXT:
- protocolpulse.io/articles returns 500
- /api/trigger-automation returns 500
- DB has 0 articles (pipeline never ran after Replit to Ultron migration)
- The robots_txt duplicate endpoint was just fixed (commit 784782d3)
- App loads successfully (confirmed via python3 app.py test import)
- The 500 happens at REQUEST TIME not import time

STEP 1 - DIAGNOSE:
Enable Flask debug mode temporarily to get the actual traceback:
  cd ~/protocol_pulse
  python3 -c "
import sys, traceback
sys.path.insert(0, '/home/ultron/protocol_pulse')
import os; os.chdir('/home/ultron/protocol_pulse')
from app import app
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
with app.test_client() as c:
    with app.app_context():
        try:
            r = c.get('/articles')
            print('STATUS:', r.status_code)
            if r.status_code == 500:
                print(r.data.decode()[-3000:])
        except Exception as e:
            traceback.print_exc()
" 2>&1 | grep -v "^INFO\|^WARNING\|^DEBUG" | tail -50

Do the same for trigger-automation with c.post('/api/trigger-automation').
Read the full traceback before touching any code.

STEP 2 - FIX THE 500s:
Fix whatever the traceback reveals. Common causes:
- Missing DB columns (run ALTER TABLE or flask db upgrade)
- Missing template variables passed to render_template
- Import errors inside route functions
- Missing .env keys causing NoneType errors

STEP 3 - RESTART AND VERIFY:
  kill -HUP $(pgrep -f "gunicorn.*app:app" | head -1) && sleep 6
  curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/articles
  Expected: 200

STEP 4 - BLAST 25 ARTICLES:
Once articles returns 200, immediately generate content:
  cd ~/protocol_pulse
  for i in $(seq 1 25); do
    result=$(curl -s -X POST http://localhost:5000/api/trigger-automation)
    echo "Article $i: $result" | head -c 100
    sleep 8
  done

Track progress:
  python3 -c "import sqlite3; c=sqlite3.connect('instance/protocol_pulse.db'); print(c.execute('SELECT COUNT(*) FROM articles').fetchone()[0], 'articles in DB')"

STEP 5 - VERIFY CRON EXISTS:
  crontab -l | grep -c trigger-automation
If 0: add it: (crontab -l; echo "0 */6 * * * curl -s -X POST http://localhost:5000/api/trigger-automation >> /home/ultron/protocol_pulse/logs/article_cron.log 2>&1") | crontab -

STEP 6 - VERIFY LIVE SITE:
  curl -s https://protocolpulse.io/articles -o /dev/null -w "%{http_code}"
  Expected: 200

Commit any code fixes:
  git add -A && git commit -m "fix(articles): resolve 500 on articles page and trigger-automation, seed 25 articles" && git push

Do not touch the video pipeline, assembler, tts_engine, or gemini_grade. Routes and DB only.
