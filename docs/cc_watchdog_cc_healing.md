Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/gospels/WATCHDOG_LLM_GOSPEL.md.
Read ~/protocol_pulse/services/local_watchdog.py in full.

TASK: Upgrade the watchdog to a fully autonomous self-healing system.
When a crash is detected that Qwen cannot fix, the watchdog must:
1. Write a CC fix spec automatically
2. Launch a CC session autonomously
3. Monitor the CC session
4. Restart the render loop when CC completes
5. Verify the fix worked
6. Telegram PBX with full status at every step

This closes the loop completely — no human intervention needed for any crash.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CROSS-LLM AUDIT FIRST (mandatory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["watchdog-cc-healing"] = ("WATCHDOG_LLM_GOSPEL.md", "main")
  EXPLICIT_FILES["watchdog-cc-healing"] = ["services/local_watchdog.py"]

cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature watchdog-cc-healing
[save C1 output]
python3 utils/cross_llm_audit.py --feature watchdog-cc-healing --cycle 2 --cycle1-results [C1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENT: AUTONOMOUS CC HEALING LOOP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADD function launch_cc_fix_session(crash_class, pattern, log_tail, affected_file):
    """Write spec and launch CC session to fix crash autonomously."""

    # 1. Build targeted CC spec from crash context
    spec_name = f"cc_watchdog_autofix_{int(time.time())}.md"
    spec_path = BASE / "docs" / spec_name

    spec_content = f"""Read ~/protocol_pulse/PIPELINE_LAWS.md first.

AUTONOMOUS WATCHDOG REPAIR — {pattern}
Triggered by: {crash_class} crash detected at {datetime.now().isoformat()}

CRASH LOG (last 50 lines):
{log_tail}

AFFECTED FILE: {affected_file}

TASK:
1. Read {affected_file} in full
2. Run cross_llm_audit.py --feature pipeline-day3-audit
3. Find the exact root cause of: {pattern}
4. Fix it. Only fix what the audit confirms broken.
5. python3 -m py_compile {affected_file} — must pass
6. bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
7. git add {affected_file} && git commit -m "fix(watchdog-auto): {pattern}" && git push
8. echo WATCHDOG_FIX_COMPLETE to signal completion
"""

    spec_path.write_text(spec_content)

    # 2. Kill any existing watchdog-fix session
    subprocess.run(["tmux", "kill-session", "-t", "watchdog_fix"], capture_output=True)
    time.sleep(1)

    # 3. Launch CC session with spec
    subprocess.run(["tmux", "new-session", "-d", "-s", "watchdog_fix"])
    subprocess.run([
        "tmux", "send-keys", "-t", "watchdog_fix",
        f"cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions",
        "Enter"
    ])
    time.sleep(5)
    subprocess.run([
        "tmux", "send-keys", "-t", "watchdog_fix",
        f"/read docs/{spec_name}",
        "Enter"
    ])

    # 4. Telegram alert
    send_telegram(
        f"🔧 <b>WATCHDOG AUTO-REPAIR LAUNCHED</b>\n"
        f"Crash: <code>{pattern}</code>\n"
        f"CC session: watchdog_fix\n"
        f"Monitoring for completion..."
    )

    # 5. Monitor CC session for up to 45 minutes
    deadline = time.time() + 2700
    while time.time() < deadline:
        time.sleep(60)
        pane = subprocess.run(
            ["tmux", "capture-pane", "-t", "watchdog_fix", "-p"],
            capture_output=True, text=True
        ).stdout
        if "WATCHDOG_FIX_COMPLETE" in pane or "regression_test" in pane.lower():
            break

    # 6. Restart render loop after fix
    subprocess.run(["pkill", "-f", "overnight_render_loop"])
    subprocess.run(["pkill", "-f", "daily_producer"])
    time.sleep(3)
    subprocess.run(["find", str(BASE), "-name", "*.pyc", "-delete"])
    subprocess.run([
        "tmux", "send-keys", "-t", "render_main",
        "cd ~/protocol_pulse && git pull && python3 overnight_render_loop.py --daemon",
        "Enter"
    ])

    send_telegram(
        f"✅ <b>WATCHDOG REPAIR COMPLETE</b>\n"
        f"Render loop restarted.\n"
        f"Next grade in ~90 minutes."
    )

WIRE IT INTO diagnose_and_patch():
After Qwen attempts a CLASS A/B fix and it fails (or for CLASS C crashes):
    if crash_class in ("A", "B", "C"):
        launch_cc_fix_session(crash_class, pattern, log_tail, affected_file)

ALSO ADD: scan producer_debug.log every reactive cycle (already committed
in previous fix — verify it's working correctly with the new logic).

ALSO ADD: after any crash detection, clear all .pyc files immediately:
    subprocess.run(["find", str(BASE), "-name", "*.pyc", "-delete"])
    subprocess.run(["find", str(BASE), "-name", "__pycache__", "-type", "d",
                    "-exec", "rm", "-rf", "{}", "+"], capture_output=True)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Simulate a crash:
  echo "KeyError: Name" >> /tmp/producer_debug.log
  python3 services/local_watchdog.py --mode reactive 2>&1 | tail -10
Verify:
  - Crash detected
  - CC session launched (tmux list-sessions | grep watchdog_fix)
  - Telegram sent
  - .pyc files cleared

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh
git add services/local_watchdog.py utils/cross_llm_audit.py
git commit -m "feat(watchdog): autonomous CC healing loop — detects crash, writes spec, launches CC, restarts render, Telegrams PBX at every step"
git push


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL REQUIREMENT: QWEN CONTEXT BIBLE INJECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The file ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md must be prepended to
every CC repair spec the watchdog generates. This gives Claude Code full
context: architecture, known failure patterns, grade A criteria, off-limits files.

In launch_cc_fix_session(), prepend the bible:
  bible = (BASE / "docs" / "QWEN_CONTEXT_BIBLE.md").read_text()
  spec_content = bible + "\n\n" + spec_content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL REQUIREMENT: PER-RENDER CONTEXT FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modify daily_producer.py to write /tmp/render_context_YYYYMMDD.json at the
START of every render (Step 1) and UPDATE it after every step completes or fails.

The write_render_context(step, status, error=None) function:
  import json
  from datetime import datetime
  ctx_path = f"/tmp/render_context_{datetime.now().strftime('%Y%m%d')}.json"
  # Load existing or create new
  try:
      with open(ctx_path) as f: ctx = json.load(f)
  except: ctx = {"episode_date": datetime.now().strftime("%Y-%m-%d"),
                  "steps_completed": [], "steps_failed": [], "render_start_time": datetime.now().isoformat()}
  if status == "ok":
      ctx["steps_completed"].append(step)
  else:
      ctx["steps_failed"].append({"step": step, "error": str(error), "timestamp": datetime.now().isoformat()})
  with open(ctx_path, "w") as f: json.dump(ctx, f, indent=2)

Call write_render_context(1, "ok") after Step 1, write_render_context(5, "fail", e) on exception, etc.

When watchdog detects crash, include render context in CC spec:
  import json
  ctx_file = f"/tmp/render_context_{datetime.now().strftime('%Y%m%d')}.json"
  render_ctx = ""
  try:
      render_ctx = json.dumps(json.load(open(ctx_file)), indent=2)
  except: pass
  spec_content = bible + "\n\nCURRENT RENDER CONTEXT:\n" + render_ctx + "\n\n" + crash_spec


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERMANENT IMPLEMENTATION REQUIREMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After building the CC healing loop, implement permanent auto-start:

1. Add to crontab (if not already present):
   @reboot /home/ultron/protocol_pulse/scripts/boot_startup.sh

2. Verify these crons exist (watchdog already has them but confirm):
   */1  * * * * python3 /home/ultron/protocol_pulse/services/local_watchdog.py --mode reactive
   */15 * * * * python3 /home/ultron/protocol_pulse/services/local_watchdog.py --mode health
   0 */6 * * *  python3 /home/ultron/protocol_pulse/services/local_watchdog.py --mode pattern

3. Add self-healing check to watchdog reactive mode:
   At the start of every reactive run, verify render loop is alive.
   If overnight_render_loop is dead AND it's between 8am-11pm ET:
     restart it automatically without waiting for a crash signal.

4. The watchdog is the FIRST thing checked in every new chat session.
   If not running — restart before any other work.
