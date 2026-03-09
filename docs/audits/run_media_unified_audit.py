#!/usr/bin/env python3
"""
Protocol Pulse — Media Unified Page Code Audit
Fires full JS+HTML at Gemini 2.5 Pro, GPT-4o, and Grok simultaneously.
Round 1: Bug hunt + architecture review
Round 2: Consensus synthesis + prioritized fix list
"""
import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path.home() / "protocol_pulse/.env")

JS   = (Path.home() / "protocol_pulse/static/js/media_unified_v4.js").read_text()
HTML = (Path.home() / "protocol_pulse/templates/media_unified.html").read_text()

# HTML structure facts extracted for context
HTML_FACTS = """
EXACT HTML ELEMENT IDs (complete):
relay-status-bar, nostr-feed, nostr-count, highlights-feed, signal-strength-gauge,
signal-breakdown, sig-sentiment, sig-spaces, sig-composite, signal-fill, telem-signal,
delta-count, delta-label, delta-items, delta-showme, health-nostr, health-nostr-col,
health-telemetry, health-sentiment, health-xspaces, health-highlights-col,
telem-fees, telem-mempool, telem-hashrate, telem-block, sentiment-dot, sentiment-num,
sentiment-why, lib-toggle, lib-full, cmd-overlay, cmd-input, cmd-results, health-strip

RELAY BAR (exact HTML):
<div class="mu-relay-status-bar" id="relay-status-bar">
  <div class="mu-relay-item" data-relay="relay.damus.io">  <!-- NO wss:// prefix -->
    <div class="mu-relay-dot" style="background:#555"></div>
    <span class="mu-relay-name">damus</span>
    <span class="mu-relay-status">OFFLINE</span>  <!-- class is mu-relay-status, NOT mu-relay-label -->
    <span class="mu-relay-count">0 notes</span>
  </div>
  <!-- same for nos.lol and relay.nostr.band -->
</div>

SIGNAL GAUGE (exact HTML):
<div id="signal-strength-gauge">
  <div class="mu-gauge-ring">
    <div class="mu-gauge-score" id="sig-composite">--</div>
  </div>
  <div id="signal-breakdown">
    <span class="mu-sig-val" id="sig-sentiment">--</span>  <!-- 70% weight label -->
    <span class="mu-sig-val" id="sig-spaces">--</span>      <!-- 30% weight label -->
  </div>
</div>
NOTE: signal-fill (#signal-fill) and telem-signal (#telem-signal) are in the TELEMETRY RIBBON at top, NOT the gauge section.

NOSTR_RELAYS in JS: ['wss://relay.damus.io', 'wss://nos.lol', 'wss://relay.nostr.band']
rm.sockets keys ARE wss:// prefixed. data-relay HTML attributes are NOT (no wss://).
"""

AUDIT_PROMPT = f"""You are performing a PRODUCTION CODE AUDIT on a live Bitcoin intelligence dashboard.

The page has 3 broken features that have NEVER worked despite multiple fix attempts:
1. NOSTR + X LIVE section — all relays show "OFFLINE 0 notes", no notes ever appear
2. VERIFIED HIGHLIGHTS — always blank despite API returning 27 items
3. SIGNAL STRENGTH GAUGE — always shows "--" / "LOADING", never updates

Your job: find every bug causing these failures. Be forensic and precise.

HTML STRUCTURE FACTS:
{HTML_FACTS}

COMPLETE JAVASCRIPT (media_unified_v4.js — {len(JS)} chars):
{JS[:18000]}

Return ONLY valid JSON (no markdown fences):
{{
  "verdict": "one sentence overall verdict on why these 3 features are broken",
  "critical_bugs": [
    {{
      "feature": "nostr|highlights|signal",
      "bug": "exact bug name",
      "location": "function name and approximate line",
      "root_cause": "precise technical explanation",
      "fix_before": "exact code that is wrong",
      "fix_after": "exact replacement code"
    }}
  ],
  "high_bugs": [same structure],
  "npub_assessment": "are the npub pubkeys in NOSTR_PUBKEYS valid hex for Nostr REQ filters? yes/no and why",
  "filter_assessment": "is isQualityNostrNote() filtering too aggressively? what would it reject?",
  "signal_gauge_assessment": "does updateSignalStrength() write to sig-sentiment, sig-spaces, sig-composite? what IDs does it actually write to?",
  "highlights_flow": "trace fetchHighlights() -> renderHighlights() - where does it break?",
  "score": 0
}}"""

results = {{}}
errors = {{}}

def call_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(AUDIT_PROMPT)
        text = resp.text.strip()
        if "```" in text:
            lines = text.split("\n")
            text = "\n".join(l for l in lines if not l.strip().startswith("```"))
        results["gemini"] = json.loads(text)
        print("[GEMINI] Done - score:", results["gemini"].get("score"), file=sys.stderr)
    except Exception as e:
        errors["gemini"] = str(e)
        print(f"[GEMINI] ERROR: {e}", file=sys.stderr)

def call_gpt4o():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": AUDIT_PROMPT}],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )
        results["gpt4o"] = json.loads(resp.choices[0].message.content)
        print("[GPT-4o] Done - score:", results["gpt4o"].get("score"), file=sys.stderr)
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"[GPT-4o] ERROR: {e}", file=sys.stderr)

def call_grok():
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )
        resp = client.chat.completions.create(
            model="grok-3-mini",
            messages=[{"role": "user", "content": AUDIT_PROMPT}],
            max_tokens=3000,
        )
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            lines = text.split("\n")
            text = "\n".join(l for l in lines if not l.strip().startswith("```"))
        results["grok"] = json.loads(text)
        print("[GROK] Done - score:", results["grok"].get("score"), file=sys.stderr)
    except Exception as e:
        errors["grok"] = str(e)
        print(f"[GROK] ERROR: {e}", file=sys.stderr)

# ── ROUND 1: Fire all 3 in parallel ──────────────────────────────────
print("[AUDIT] Round 1: Firing Gemini + GPT-4o + Grok in parallel...", file=sys.stderr)
threads = [
    threading.Thread(target=call_gemini),
    threading.Thread(target=call_gpt4o),
    threading.Thread(target=call_grok),
]
for t in threads: t.start()
for t in threads: t.join(timeout=90)

round1 = {"results": results.copy(), "errors": errors.copy()}
print(f"[AUDIT] Round 1 done. Got: {list(results.keys())} | Errors: {list(errors.keys())}", file=sys.stderr)

# ── ROUND 2: Synthesis ───────────────────────────────────────────────
synthesis_prompt = f"""You received 3 independent code audits of the same broken JavaScript file.
Synthesize into a CONSENSUS PRIORITIZED FIX LIST.

ROUND 1 RESULTS:
{json.dumps(results, indent=2)[:8000]}

For each fix the auditors agreed on or that is clearly correct:
Return ONLY valid JSON:
{{
  "consensus_verdict": "1-2 sentence summary of root causes",
  "winner": "gemini|gpt4o|grok — which auditor was most accurate and thorough",
  "winner_reason": "why",
  "priority_fixes": [
    {{
      "priority": "P0|P1|P2",
      "feature": "nostr|highlights|signal|other",
      "fix": "description",
      "before": "exact wrong code",
      "after": "exact correct code",
      "confidence": "high|medium|low",
      "agreed_by": ["gemini","gpt4o","grok"] subset
    }}
  ],
  "missed_by_all": "any bugs none of them caught that you can see",
  "final_score": 0
}}"""

try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    synthesis_text = msg.content[0].text.strip()
    if "```" in synthesis_text:
        lines = synthesis_text.split("\n")
        synthesis_text = "\n".join(l for l in lines if not l.strip().startswith("```"))
    synthesis = json.loads(synthesis_text)
    print("[SYNTHESIS] Done - winner:", synthesis.get("winner"), file=sys.stderr)
except Exception as e:
    synthesis = {"error": str(e)}
    print(f"[SYNTHESIS] ERROR: {e}", file=sys.stderr)

# ── OUTPUT ───────────────────────────────────────────────────────────
output = {
    "timestamp": datetime.now().isoformat(),
    "round1": round1,
    "synthesis": synthesis
}

out_path = Path.home() / "protocol_pulse/docs/audits/media_unified_audit.json"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(json.dumps(output, indent=2))
print(json.dumps(output, indent=2))

