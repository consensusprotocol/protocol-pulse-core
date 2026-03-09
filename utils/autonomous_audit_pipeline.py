#!/usr/bin/env python3
"""
PROTOCOL PULSE — AUTONOMOUS AUDIT + BUILD PIPELINE
====================================================
Full flow per feature:
  Claude Code builds → 3-LLM audit fires in parallel →
  Cycle 2 cross-pollination (each model sees others) →
  Winner determined → Claude Code second-pass prompt generated →
  Claude Code executes → git commit → PR-ready

Zero manual steps.
"""
import os, sys, json, time, threading, subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path.home() / "protocol_pulse/.env")
REPO = Path.home() / "protocol_pulse"

# ═══════════════════════════════════════════════════════════════════
# LLM CALLERS
# ═══════════════════════════════════════════════════════════════════

def call_gpt4o(prompt, model="gpt-4o", json_mode=True):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    kwargs = dict(model=model, messages=[{"role":"user","content":prompt}], max_tokens=3000)
    if json_mode: kwargs["response_format"] = {"type":"json_object"}
    resp = client.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content.strip()
    return json.loads(text) if json_mode else text

def call_grok(prompt, json_mode=True):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
    resp = client.chat.completions.create(
        model="grok-3-mini",
        messages=[{"role":"user","content":prompt}],
        max_tokens=3000
    )
    text = resp.choices[0].message.content.strip()
    for f in ["```json","```"]: text = text.replace(f,"")
    return json.loads(text.strip()) if json_mode else text.strip()

def call_gemini(prompt, json_mode=True):
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(model="gemini-2.5-pro-preview-03-25", contents=prompt)
        text = resp.text.strip()
        for f in ["```json","```"]: text = text.replace(f,"")
        return json.loads(text.strip()) if json_mode else text.strip()
    except Exception as e:
        # Fallback to old SDK
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        for f in ["```json","```"]: text = text.replace(f,"")
        return json.loads(text.strip()) if json_mode else text.strip()

def call_claude(prompt, model="claude-opus-4-5", json_mode=False):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))
    msg = client.messages.create(
        model=model, max_tokens=4000,
        messages=[{"role":"user","content":prompt}]
    )
    text = msg.content[0].text.strip()
    if json_mode:
        for f in ["```json","```"]: text = text.replace(f,"")
        return json.loads(text.strip())
    return text

# ═══════════════════════════════════════════════════════════════════
# CYCLE 1 — PARALLEL AUDIT
# ═══════════════════════════════════════════════════════════════════

def run_cycle1(feature_name, code_context, audit_prompt_template):
    """Fire all 3 LLMs in parallel against the code."""
    results = {}
    errors = {}

    def fire(name, fn, prompt):
        try:
            results[name] = fn(prompt)
            print(f"  [{name.upper()}] done — score={results[name].get('score','?')}", file=sys.stderr)
        except Exception as e:
            errors[name] = str(e)
            print(f"  [{name.upper()}] ERROR: {e}", file=sys.stderr)

    prompt = audit_prompt_template.replace("{{CODE}}", code_context)
    threads = [
        threading.Thread(target=fire, args=("gpt4o",  call_gpt4o, prompt)),
        threading.Thread(target=fire, args=("grok",   call_grok,  prompt)),
        threading.Thread(target=fire, args=("gemini", call_gemini, prompt)),
    ]
    print(f"[CYCLE1] Firing 3 LLMs in parallel for {feature_name}...", file=sys.stderr)
    for t in threads: t.start()
    for t in threads: t.join(timeout=90)
    print(f"[CYCLE1] Done. Got: {list(results.keys())} | Errors: {list(errors.keys())}", file=sys.stderr)
    return results, errors

# ═══════════════════════════════════════════════════════════════════
# CYCLE 2 — CROSS-POLLINATION
# ═══════════════════════════════════════════════════════════════════

def run_cycle2(cycle1_results):
    """Each model sees what the others said. Revise or confirm."""
    cycle2_results = {}
    errors = {}

    def fire_revision(name, fn, my_result, others):
        others_str = json.dumps(others, indent=2)[:4000]
        prompt = f"""You performed a code audit. Here were your findings:
{json.dumps(my_result, indent=2)[:2000]}

Here is what the OTHER auditors found:
{others_str}

Revise your findings. Do you AGREE, DISAGREE, or have ADDITIONS?
Produce a final refined verdict. Return ONLY valid JSON:
{{
  "final_verdict": "1-2 sentences",
  "confirmed_bugs": [same structure as before — bugs you still stand by],
  "new_bugs": [bugs you missed in cycle 1 that others found and you agree with],
  "disagree_with": [things others said that you think are wrong, and why],
  "confidence_score": 0-100,
  "priority_fixes": [
    {{"priority":"P0|P1|P2","feature":"...","fix":"...","before":"...","after":"..."}}
  ]
}}"""
        try:
            cycle2_results[name] = fn(prompt)
            print(f"  [CYCLE2/{name.upper()}] done confidence={cycle2_results[name].get('confidence_score','?')}", file=sys.stderr)
        except Exception as e:
            errors[name] = str(e)
            print(f"  [CYCLE2/{name.upper()}] ERROR: {e}", file=sys.stderr)

    threads = []
    for name, fn in [("gpt4o", call_gpt4o), ("grok", call_grok), ("gemini", call_gemini)]:
        if name not in cycle1_results: continue
        others = {k:v for k,v in cycle1_results.items() if k != name}
        t = threading.Thread(target=fire_revision, args=(name, fn, cycle1_results[name], others))
        threads.append(t)

    print("[CYCLE2] Running cross-pollination...", file=sys.stderr)
    for t in threads: t.start()
    for t in threads: t.join(timeout=90)
    print(f"[CYCLE2] Done. Got: {list(cycle2_results.keys())}", file=sys.stderr)
    return cycle2_results, errors

# ═══════════════════════════════════════════════════════════════════
# WINNER + SECOND-PASS PROMPT GENERATION
# ═══════════════════════════════════════════════════════════════════

def determine_winner_and_generate_prompt(feature_name, cycle1, cycle2, code_context):
    """Claude synthesizes all findings, picks winner, generates Claude Code prompt."""
    synthesis_prompt = f"""You are the final synthesizer in a multi-LLM code audit pipeline.

FEATURE: {feature_name}
CYCLE 1 RESULTS (initial audit):
{json.dumps(cycle1, indent=2)[:4000]}

CYCLE 2 RESULTS (cross-pollination — each model saw the others):
{json.dumps(cycle2, indent=2)[:4000]}

Your tasks:
1. Determine the WINNER — which auditor was most accurate, complete, and actionable overall
2. Synthesize a CONSENSUS FIX LIST — every P0/P1 fix with exact before/after code
3. Generate a CLAUDE CODE SECOND-PASS PROMPT — a complete, precise prompt that a Claude Code agent
   will execute autonomously to fix every consensus issue. This prompt must:
   - Reference exact file paths on Ultron (~/protocol_pulse/)
   - Show exact code to replace (before/after)
   - Include the git commit command at the end
   - Be self-contained — zero ambiguity

Return ONLY valid JSON:
{{
  "winner": "gpt4o|grok|gemini",
  "winner_reason": "...",
  "consensus_verdict": "...",
  "priority_fixes": [
    {{
      "priority": "P0|P1|P2",
      "feature": "...",
      "fix_description": "...",
      "before": "exact wrong code",
      "after": "exact correct code",
      "agreed_by": ["gpt4o","grok"]
    }}
  ],
  "claude_code_prompt": "COMPLETE PROMPT FOR CLAUDE CODE SECOND PASS — must be production-ready, specific, include file paths and git commit",
  "confidence": 0-100
}}"""

    print("[SYNTH] Generating winner + Claude Code prompt...", file=sys.stderr)
    result = call_claude(synthesis_prompt, model="claude-opus-4-5", json_mode=True)
    print(f"[SYNTH] Winner: {result.get('winner')} | Confidence: {result.get('confidence')}", file=sys.stderr)
    return result

# ═══════════════════════════════════════════════════════════════════
# CLAUDE CODE EXECUTOR
# ═══════════════════════════════════════════════════════════════════

def execute_claude_code(second_pass_prompt, session_name, feature_name):
    """Launch Claude Code in tmux with the second-pass prompt."""
    prompt_file = REPO / f"docs/audits/{feature_name}_second_pass_prompt.md"
    prompt_file.write_text(second_pass_prompt)
    print(f"[CLAUDE CODE] Prompt written to {prompt_file}", file=sys.stderr)

    # Write an automated instruction file
    auto_script = REPO / f"docs/audits/{feature_name}_auto_execute.sh"
    auto_script.write_text(f"""#!/bin/bash
cd ~/protocol_pulse
unset ANTHROPIC_API_KEY
# Feed the prompt file to claude non-interactively
claude --dangerously-skip-permissions -p "$(cat {prompt_file})" 2>&1
echo "[AUTO-EXECUTE] Done"
""")
    auto_script.chmod(0o755)

    cmd = f"tmux new-session -d -s {session_name} 'bash {auto_script} > /tmp/{feature_name}_cc.log 2>&1; echo CC_DONE >> /tmp/{feature_name}_cc.log' && echo LAUNCHED"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"[CLAUDE CODE] Session launched: {result.stdout.strip()}", file=sys.stderr)
    return str(prompt_file)

# ═══════════════════════════════════════════════════════════════════
# MAIN — FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run_pipeline(feature_name, code_context, audit_prompt_template, run_claude_code=False):
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"[PIPELINE] Starting: {feature_name}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    ts = datetime.now().isoformat()
    report = {"feature": feature_name, "timestamp": ts}

    # CYCLE 1
    c1_results, c1_errors = run_cycle1(feature_name, code_context, audit_prompt_template)
    report["cycle1"] = {"results": c1_results, "errors": c1_errors}

    if not c1_results:
        print("[PIPELINE] No cycle 1 results — aborting", file=sys.stderr)
        return report

    # CYCLE 2
    c2_results, c2_errors = run_cycle2(c1_results)
    report["cycle2"] = {"results": c2_results, "errors": c2_errors}

    # SYNTHESIS + WINNER + CLAUDE CODE PROMPT
    synthesis = determine_winner_and_generate_prompt(feature_name, c1_results, c2_results, code_context)
    report["synthesis"] = synthesis

    # Save report
    out = REPO / f"docs/audits/{feature_name}_full_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[PIPELINE] Full report saved: {out}", file=sys.stderr)

    # EXECUTE CLAUDE CODE (second pass)
    if run_claude_code and synthesis.get("claude_code_prompt"):
        prompt_path = execute_claude_code(
            synthesis["claude_code_prompt"],
            session_name=f"cc_{feature_name[:8]}",
            feature_name=feature_name
        )
        report["claude_code_launched"] = True
        report["prompt_path"] = prompt_path
        print(f"[PIPELINE] Claude Code launched. Monitor: tail -f /tmp/{feature_name}_cc.log", file=sys.stderr)
    else:
        # Just print the prompt for manual review/execution
        print(f"\n[PIPELINE] CLAUDE CODE PROMPT (second pass):", file=sys.stderr)
        print("─"*60, file=sys.stderr)
        print(synthesis.get("claude_code_prompt","(none generated)"), file=sys.stderr)

    print(f"\n[PIPELINE] WINNER: {synthesis.get('winner')} — {synthesis.get('winner_reason','')}", file=sys.stderr)
    print(f"[PIPELINE] P0 fixes: {len([f for f in synthesis.get('priority_fixes',[]) if f.get('priority')=='P0'])}", file=sys.stderr)

    return report

# ═══════════════════════════════════════════════════════════════════
# RUN — MEDIA UNIFIED PAGE (using existing cycle1 results as starting point)
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", default="media_unified")
    parser.add_argument("--resume-from-cycle1", action="store_true", help="Skip cycle1, use saved results")
    parser.add_argument("--execute", action="store_true", help="Actually launch Claude Code")
    args = parser.parse_args()

    JS   = (REPO / "static/js/media_unified_v4.js").read_text()
    HTML = (REPO / "templates/media_unified.html").read_text()

    CODE_CONTEXT = f"""=== media_unified_v4.js ({len(JS)} chars) ===
{JS[:15000]}

=== HTML IDs (exact): relay-status-bar, nostr-feed, nostr-count, highlights-feed,
signal-strength-gauge, signal-breakdown, sig-sentinel, sig-spaces, sig-composite,
signal-fill, telem-signal, health-nostr, health-nostr-col, health-highlights-col ===

=== RELAY BAR: data-relay has NO wss:// prefix. rm.sockets keys DO have wss:// ===
=== SIGNAL GAUGE: sig-composite, sig-sentiment, sig-spaces are the gauge IDs ===
=== updateSignalStrength() currently only writes to signal-fill + telem-signal ===
=== NOSTR_PUBKEYS in JS are npub (bech32) NOT hex — Nostr REQ authors needs hex ==="""

    AUDIT_PROMPT = """You are auditing broken production JS for a Bitcoin dashboard.

3 features are broken:
1. NOSTR FEED — always OFFLINE, 0 notes (WebSocket connects but no notes appear)
2. HIGHLIGHTS — blank (API returns 27 items but nothing renders)  
3. SIGNAL GAUGE — always "--" (updateSignalStrength() doesn't update gauge IDs)

CODE:
{{CODE}}

Return ONLY valid JSON:
{
  "verdict": "root causes in 2 sentences",
  "npub_bug": "are npub bech32 strings valid hex for Nostr REQ authors? yes/no + impact",
  "signal_bug": "what IDs does updateSignalStrength() write to vs what IDs the gauge has",
  "highlights_bug": "exact break point in fetchHighlights->renderHighlights chain",
  "critical_bugs": [
    {"feature":"nostr|highlights|signal","bug":"name","location":"function",
     "root_cause":"why","fix_before":"wrong code","fix_after":"correct code"}
  ],
  "high_bugs": [],
  "score": 0
}"""

    if args.resume_from_cycle1:
        # Load existing cycle1, skip straight to cycle2
        saved = json.loads((REPO / "docs/audits/media_unified_audit.json").read_text())
        c1 = saved.get("round1_results", {})
        c2_results, c2_errors = run_cycle2(c1)
        synthesis = determine_winner_and_generate_prompt(args.feature, c1, c2_results, CODE_CONTEXT)
        report = {"feature": args.feature, "timestamp": datetime.now().isoformat(),
                  "cycle1": {"results": c1, "errors": saved.get("round1_errors",{})},
                  "cycle2": {"results": c2_results, "errors": c2_errors},
                  "synthesis": synthesis}
        out = REPO / f"docs/audits/{args.feature}_full_report.json"
        out.write_text(json.dumps(report, indent=2))
        if args.execute and synthesis.get("claude_code_prompt"):
            execute_claude_code(synthesis["claude_code_prompt"], f"cc_{args.feature[:8]}", args.feature)
        print(json.dumps(report, indent=2))
    else:
        report = run_pipeline(args.feature, CODE_CONTEXT, AUDIT_PROMPT, run_claude_code=args.execute)
        print(json.dumps(report, indent=2))
