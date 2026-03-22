Load ~/protocol_pulse/PIPELINE_LAWS.md first. Two tasks. Do not touch video pipeline files.

TASK 1 — Fix article generation to use Claude (Anthropic) as PRIMARY provider:

Context:
- OPENAI_API_KEY has insufficient_quota (exhausted)
- GEMINI content key returns 403 (flagged as leaked — different from GEMINI_API_KEY used for grading which works fine)
- ANTHROPIC_API_KEY in .env is valid and working
- services/content_generator.py has fallback chain: OpenAI → Gemini → Anthropic (lines 690-710)
- Both primary providers are dead so fallback to Anthropic IS happening — but something prevents it

First diagnose why Anthropic fallback fails:
  cd ~/protocol_pulse
  python3 -c "
  import sys, os, logging
  logging.basicConfig(level=logging.WARNING)
  sys.path.insert(0, '/home/ultron/protocol_pulse')
  os.chdir('/home/ultron/protocol_pulse')
  from app import app
  with app.app_context():
      from services.automation import generate_article_with_tracking
      from app import db
      db.session.execute(db.text('DELETE FROM automation_run'))
      db.session.commit()
      result = generate_article_with_tracking(force=True)
      print('RESULT:', result)
  " 2>&1 | grep -v "^INFO" | tail -30

If Anthropic fallback IS working — great, blast 50 articles:
  python3 -c "
  import sys, os, time, logging
  logging.basicConfig(level=logging.WARNING)
  sys.path.insert(0, '/home/ultron/protocol_pulse')
  os.chdir('/home/ultron/protocol_pulse')
  from app import app, db
  from services.automation import generate_article_with_tracking
  import sqlalchemy as sa
  with app.app_context():
      for i in range(50):
          db.session.execute(sa.text('DELETE FROM automation_run'))
          db.session.commit()
          r = generate_article_with_tracking(force=True)
          count = db.session.execute(sa.text('SELECT COUNT(*) FROM articles')).scalar()
          print(f'[{i+1}/50] {"OK: " + r.get("title","")[:50] if r.get("success") else "FAIL: " + str(r)[:60]} | Total: {count}')
          time.sleep(3)
  "

If Anthropic fallback is NOT working — fix content_generator.py:
  In the generate_content() method, swap the order so Anthropic is tried FIRST:
    1. Try Anthropic (generate_content_anthropic)
    2. Try Gemini as fallback
    3. Try OpenAI as last resort
  This ensures the working key is always used.
  Then blast 50 articles as above.

TASK 2 — Set up auto-grader watcher:
  Write ~/protocol_pulse/render_grade_watcher.py:
  - Polls every 60s for a new pulse_check mp4 with today's date
  - When it finds one that is >200MB AND newer than 30min ago AND not yet graded:
    - Runs: python3 gemini_grade.py output/YYYY-MM-DD/pulse_check_YYYYMMDD.mp4
    - Saves grade to logs/auto_grade_result.txt
    - Logs: "[WATCHER] Grade: X/100 — {verdict}"
  - Stop watching after Grade A is achieved
  Launch in tmux: tmux new-session -d -s grade_watcher && tmux send-keys -t grade_watcher "python3 ~/protocol_pulse/render_grade_watcher.py" Enter

Commit any code changes:
  git add services/content_generator.py render_grade_watcher.py
  git commit -m "fix(articles): prioritize Anthropic for content gen; feat(pipeline): auto grade watcher"
  git push

Do NOT touch assembler.py, tts_engine.py, overnight_render_loop.py, or gemini_grade.py.
