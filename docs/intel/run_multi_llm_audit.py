#!/usr/bin/env python3
"""
Protocol Pulse Intel Dashboard - Multi-LLM Audit Runner
Fires spec at Gemini 2.5 Pro, GPT-4o, and Grok simultaneously.
Synthesizes with Claude. Writes final report.
"""
import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime

SPEC_PATH = Path.home() / "protocol_pulse/docs/intel/INTEL_DASHBOARD_AUDIT_SPEC.md"
spec = SPEC_PATH.read_text()

AUDIT_PROMPT = """You are performing a senior technical architecture review of a Bitcoin intelligence dashboard.

This is a PRE-BUILD AUDIT. Your job is forensic - find weaknesses before they become bugs.

Be direct. Be specific. Prioritize ruthlessly. Rate each concern: CRITICAL / HIGH / MEDIUM / LOW.

Focus your review on:
1. The Sentinel Algorithm - is the multi-factor weighting formula mathematically sound? Edge cases? Gaming risks?
2. Behavioral analytics - are the archetype classifications and churn model defensible?
3. WebSocket architecture - scalability on Replit? Failure modes?
4. Stripe integration gaps - what critical webhook scenarios are missing?
5. Database schema - missing indexes, N+1 query risks, data integrity issues?
6. Missing data sources - what real-time Bitcoin signals are we not collecting?
7. Priority verdict - what is the single highest-leverage thing to ship first?

Return ONLY valid JSON, no markdown fences:
{
  "verdict": "one sentence overall verdict",
  "critical_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  "high_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  "medium_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  "algorithm_verdict": "detailed assessment of the Sentinel formula",
  "missing_data_sources": ["list of important missing signals"],
  "ship_first": "what to build first and why",
  "moat_assessment": "is this genuinely defensible IP or easily replicated?",
  "score": 0
}

THE SPEC:
""" + spec[:12000]

results = {}
errors = {}

def call_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-pro")
        resp = model.generate_content(AUDIT_PROMPT)
        text = resp.text.strip()
        if "```" in text:
            lines = text.split("\n")
            text = "\n".join(l for l in lines if not l.strip().startswith("```"))
        results["gemini"] = json.loads(text)
        print("[GEMINI] Done - score:", results["gemini"].get("score"))
    except Exception as e:
        errors["gemini"] = str(e)
        print(f"[GEMINI] ERROR: {e}")

def call_gpt4o():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-5.4",
            messages=[{"role": "user", "content": AUDIT_PROMPT}],
            response_format={"type": "json_object"},
            max_completion_tokens=3000,
        )
        results["gpt4o"] = json.loads(resp.choices[0].message.content)
        print("[GPT-4o] Done - score:", results["gpt4o"].get("score"))
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"[GPT-4o] ERROR: {e}")

def call_grok():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": AUDIT_PROMPT}],
            response_format={"type": "json_object"},
            max_completion_tokens=3000,
        )
        results["grok"] = json.loads(resp.choices[0].message.content)
        print("[GROK]  Done - score:", results["grok"].get("score"))
    except Exception as e:
        errors["grok"] = str(e)
        print(f"[GROK]  ERROR: {e}")

print(f"[AUDIT] Firing at {datetime.now().strftime('%H:%M:%S')} - all 3 LLMs in parallel...")
threads = [
    threading.Thread(target=call_gemini),
    threading.Thread(target=call_gpt4o),
    threading.Thread(target=call_grok),
]
for t in threads: t.start()
for t in threads: t.join()

print(f"[AUDIT] Completed: {list(results.keys())} | Errors: {list(errors.keys())}")

# Synthesize with Claude
if results:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    parts = []
    for name, data in results.items():
        parts.append(f"## {name.upper()}\n{json.dumps(data, indent=2)[:3000]}")
    
    synthesis_prompt = """Synthesize this multi-LLM architecture audit into a final report.

Three LLMs independently reviewed the Protocol Pulse Intel Dashboard spec:

""" + "\n\n".join(parts) + """

Errors: """ + json.dumps(errors) + """

Write a final audit report with these sections:
1. CONSENSUS ISSUES - things 2+ LLMs flagged (these are highest priority)
2. UNIQUE INSIGHTS - important points only one LLM caught  
3. DISAGREEMENTS - where they diverged and who is right
4. SENTINEL ALGORITHM VERDICT - final consensus on the weighting formula
5. FINAL BUILD ORDER - ordered list, most important first
6. GREEN LIGHT STATUS - is this ready to build, or what must change first?

Be decisive. This is the final gate before execution."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    synthesis = msg.content[0].text
    print("[CLAUDE] Synthesis complete")
else:
    synthesis = "CRITICAL: No LLM responses. Check API keys.\nErrors: " + json.dumps(errors)

# Write reports
out_dir = Path.home() / "protocol_pulse/docs/intel"
out_dir.mkdir(parents=True, exist_ok=True)

json_path = out_dir / "MULTI_LLM_AUDIT_RESULTS.json"
json_path.write_text(json.dumps({
    "generated_at": datetime.now().isoformat(),
    "results": results,
    "errors": errors,
    "synthesis": synthesis,
}, indent=2))

scores = {k: v.get("score","?") for k,v in results.items() if isinstance(v,dict)}
score_lines = "\n".join(f"- {k.upper()}: {v}/100" for k,v in scores.items())
llm_status = "\n".join(f"- {k}: {chr(10003) if k in results else chr(10007) + ' ' + errors.get(k,'?')}" for k in ["gemini","gpt4o","grok"])

md_content = f"""# Intel Dashboard — Multi-LLM Audit Results
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## LLMs Queried
{llm_status}

## Scores
{score_lines}

## Synthesis

{synthesis}
"""
md_path = out_dir / "MULTI_LLM_AUDIT_RESULTS.md"
md_path.write_text(md_content)

print(f"[AUDIT] Reports written to {out_dir}")
print("=" * 60)
print("SYNTHESIS PREVIEW:")
print(synthesis[:1200])
print("=" * 60)
print("AUDIT_COMPLETE")
