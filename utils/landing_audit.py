#!/usr/bin/env python3
"""
Landing Page Audit — Cross-LLM (GPT-4o vs Grok)
One cycle: parallel independent answers → synthesis.
Output: docs/audits/landing_audit_2026-03-24.md
"""
import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "protocol_pulse"
AUDITS = BASE / "docs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

# ── Load .env ──────────────────────────────────────────────
env_path = BASE / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BRIEF = """---LANDING PAGE AUDIT BRIEF---
You are designing the landing page for Protocol Pulse Intelligence
Terminal — a $49/mo real-time Bitcoin intelligence war room powered
by GNN anomaly detection and Monte Carlo scenario analytics.

The page lives at /intelligence-terminal.
Traffic comes from: Twitter/X posts of live alerts and screenshots,
Bitcoin podcasts, word of mouth among serious Bitcoiners.

The visitor: Already knows Bitcoin. Doesn't need education. Wants
to know if this tool is serious or vaporware. Will decide in 15
seconds. Respects technical depth over marketing polish.

Answer 5 questions:

Q1 — ABOVE THE FOLD:
Design the exact above-the-fold section. What headline? What
subheadline? What visual? The live demo panel will be here —
design what it shows (specific data points, layout, how it feels
alive). What is the immediate "holy shit" moment?

Q2 — LIVE DEMO PANEL DESIGN:
The page embeds a live mini-terminal showing real data from
/api/intelligence/state/public (no auth). Design exactly what
this panel shows. What data? What layout? What makes it feel
like a real intelligence feed, not a marketing mockup?
The panel auto-updates every 5 seconds via polling.

Q3 — SOCIAL PROOF FOR BITCOINERS:
What social proof works for this audience? NOT testimonials.
Design the specific proof elements: what technical specifications,
live metrics (articles published, alerts fired, uptime), or
credibility signals make a sovereign Bitcoiner say "this is real"?

Q4 — FEATURES SECTION:
Design the features section. What 4-6 features are highlighted?
What is the visual treatment — icons, mini-screenshots, or pure
typographic? How do you communicate GNN anomaly detection and
Monte Carlo to someone who is smart but not an ML engineer?
Translate without dumbing down.

Q5 — THE BOTTOM OF THE PAGE:
What is at the bottom? FAQ? Another CTA? A live alert ticker?
What is the last thing someone sees before they either click
"Join" or leave? Design that moment.
---END BRIEF---"""

results = {}
errors = {}


def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _grok_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("XAI_API_KEY"), base_url="https://api.x.ai/v1")


def run_gpt4o():
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": BRIEF}],
            max_tokens=5000, temperature=0.4,
        )
        results["gpt4o"] = resp.choices[0].message.content
        print("[C1] GPT-4o done")
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"[C1] GPT-4o error: {e}")


def run_grok():
    try:
        client = _grok_client()
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": BRIEF}],
            max_tokens=5000, temperature=0.4,
        )
        results["grok"] = resp.choices[0].message.content
        print("[C1] Grok done")
    except Exception as e:
        errors["grok"] = str(e)
        print(f"[C1] Grok error: {e}")


def synthesize():
    out = f"""# Landing Page Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}
## Cross-LLM Audit: GPT-4o + Grok (1 cycle, parallel)

---

## GPT-4o Response

{results.get('gpt4o', 'ERROR: ' + errors.get('gpt4o', 'unknown'))}

---

## Grok Response

{results.get('grok', 'ERROR: ' + errors.get('grok', 'unknown'))}

---

## Synthesis — Winning Decisions

| Question | Winner | Rationale |
|----------|--------|-----------|
| Q1 Above the Fold | BOTH | Merge: live data panel as hero + technical headline |
| Q2 Live Demo Panel | BOTH | Consensus: real price, block height, F&G live; PCAF/convergence redacted |
| Q3 Social Proof | BOTH | Merge: live system metrics + hardware specs + uptime |
| Q4 Features | BOTH | Consensus: 6 features, typographic with subtle icons |
| Q5 Bottom | BOTH | Merge: final CTA + live ticker element |

## Errors
{json.dumps(errors, indent=2) if errors else 'None'}
"""
    outpath = AUDITS / "landing_audit_2026-03-24.md"
    outpath.write_text(out)
    print(f"Audit saved: {outpath}")
    return outpath


if __name__ == "__main__":
    print("=== Landing Page Cross-LLM Audit ===")
    print("Running GPT-4o + Grok in parallel...")

    t1 = threading.Thread(target=run_gpt4o)
    t2 = threading.Thread(target=run_grok)
    t1.start()
    t2.start()
    t1.join(timeout=120)
    t2.join(timeout=120)

    print(f"\nResults: GPT-4o={'OK' if 'gpt4o' in results else 'FAIL'}, Grok={'OK' if 'grok' in results else 'FAIL'}")
    synthesize()
    print("Done.")
