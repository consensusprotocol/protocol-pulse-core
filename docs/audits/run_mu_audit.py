#!/usr/bin/env python3
import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path.home() / "protocol_pulse/.env")

JS   = (Path.home() / "protocol_pulse/static/js/media_unified_v4.js").read_text()

HTML_FACTS = """
EXACT HTML IDs: relay-status-bar, nostr-feed, nostr-count, highlights-feed,
signal-strength-gauge, signal-breakdown, sig-sentiment, sig-spaces, sig-composite,
signal-fill, telem-signal, health-nostr, health-nostr-col, health-highlights-col

RELAY BAR HTML:
<div id="relay-status-bar">
  <div class="mu-relay-item" data-relay="relay.damus.io">  <!-- NO wss:// -->
    <div class="mu-relay-dot"></div>
    <span class="mu-relay-name">damus</span>
    <span class="mu-relay-status">OFFLINE</span>  <!-- class=mu-relay-status NOT mu-relay-label -->
    <span class="mu-relay-count">0 notes</span>
  </div>
</div>

SIGNAL GAUGE HTML:
<div id="signal-strength-gauge">
  <div id="sig-composite">--</div>
  <div id="signal-breakdown">
    <span id="sig-sentiment">--</span>
    <span id="sig-spaces">--</span>
  </div>
</div>
NOTE: signal-fill and telem-signal are in telemetry ribbon, NOT in gauge section.

NOSTR_RELAYS in JS: wss://relay.damus.io, wss://nos.lol, wss://relay.nostr.band
rm.sockets keyed WITH wss://. data-relay HTML has NO wss:// prefix.
"""

PROMPT = """You are auditing broken production JavaScript for a Bitcoin intelligence dashboard.

3 features are broken and have NEVER worked:
1. NOSTR FEED — all relays show OFFLINE, 0 notes
2. VERIFIED HIGHLIGHTS — always blank (API returns 27 items)
3. SIGNAL GAUGE — always shows -- and LOADING

HTML STRUCTURE:
""" + HTML_FACTS + """

FULL JS:
""" + JS[:16000] + """

Return ONLY valid JSON (no markdown, no code fences):
{
  "verdict": "one sentence on root causes",
  "npub_bug": "are npub strings valid hex for Nostr REQ authors filter? yes/no and why this matters",
  "signal_bug": "does updateSignalStrength() write to sig-sentiment/sig-spaces/sig-composite? or different IDs?",
  "highlights_bug": "trace fetchHighlights to renderHighlights - where exactly does it break?",
  "critical_bugs": [
    {
      "feature": "nostr or highlights or signal",
      "bug": "name",
      "location": "function",
      "root_cause": "why",
      "fix_before": "wrong code",
      "fix_after": "correct code"
    }
  ],
  "high_bugs": [],
  "score": 0
}"""

results = {}
errors = {}

def call_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(PROMPT)
        text = resp.text.strip()
        for fence in ["```json", "```"]:
            text = text.replace(fence, "")
        results["gemini"] = json.loads(text.strip())
        print("[GEMINI] Done score=" + str(results["gemini"].get("score","?")), file=sys.stderr)
    except Exception as e:
        errors["gemini"] = str(e)
        print("[GEMINI] ERROR: " + str(e), file=sys.stderr)

def call_gpt4o():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": PROMPT}],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )
        results["gpt4o"] = json.loads(resp.choices[0].message.content)
        print("[GPT4o] Done score=" + str(results["gpt4o"].get("score","?")), file=sys.stderr)
    except Exception as e:
        errors["gpt4o"] = str(e)
        print("[GPT4o] ERROR: " + str(e), file=sys.stderr)

def call_grok():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-3-mini",
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=3000,
        )
        text = resp.choices[0].message.content.strip()
        for fence in ["```json", "```"]:
            text = text.replace(fence, "")
        results["grok"] = json.loads(text.strip())
        print("[GROK] Done score=" + str(results["grok"].get("score","?")), file=sys.stderr)
    except Exception as e:
        errors["grok"] = str(e)
        print("[GROK] ERROR: " + str(e), file=sys.stderr)

print("[AUDIT] Firing Round 1 in parallel...", file=sys.stderr)
threads = [threading.Thread(target=f) for f in [call_gemini, call_gpt4o, call_grok]]
for t in threads: t.start()
for t in threads: t.join(timeout=90)
print("[AUDIT] Round 1 complete. Got: " + str(list(results.keys())), file=sys.stderr)

# Round 2 synthesis
synth_prompt = """Synthesize these 3 code audits into a consensus prioritized fix list.

AUDIT RESULTS:
""" + json.dumps(results, indent=2)[:8000] + """

Return ONLY valid JSON:
{
  "consensus_verdict": "2 sentences on root causes",
  "winner": "gemini or gpt4o or grok",
  "winner_reason": "why most accurate",
  "priority_fixes": [
    {
      "priority": "P0 or P1 or P2",
      "feature": "nostr or highlights or signal",
      "fix": "description",
      "before": "exact wrong code",
      "after": "exact correct code",
      "agreed_by": ["gemini","gpt4o"]
    }
  ],
  "missed_by_all": "bugs none caught"
}"""

synthesis = {}
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": synth_prompt}]
    )
    text = msg.content[0].text.strip()
    for fence in ["```json", "```"]:
        text = text.replace(fence, "")
    synthesis = json.loads(text.strip())
    print("[SYNTH] Done winner=" + str(synthesis.get("winner","?")), file=sys.stderr)
except Exception as e:
    synthesis = {"error": str(e)}
    print("[SYNTH] ERROR: " + str(e), file=sys.stderr)

output = {"timestamp": datetime.now().isoformat(), "round1_results": results, "round1_errors": errors, "synthesis": synthesis}
out_path = Path.home() / "protocol_pulse/docs/audits/media_unified_audit.json"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(json.dumps(output, indent=2))
print(json.dumps(output))
