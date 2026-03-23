#!/usr/bin/env python3
"""
PROTOCOL PULSE — INTELLIGENCE TERMINAL COMPETITIVE PRODUCT AUDIT
3-LLM competitive design audit: Cycle 1 (individual) → Cycle 2 (cross-exam) → Synthesis → Spec

Usage:
    python3 utils/intelligence_terminal_audit.py
    python3 utils/intelligence_terminal_audit.py --cycle 2   # resume from cycle 1 results
"""

import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "protocol_pulse"
AUDITS = BASE / "docs" / "audits"
AUDIT_DIR = AUDITS / "intelligence-terminal"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# ─── COMPETITIVE BRIEF (CYCLE 1) ─────────────────────────────────────────────

COMPETITIVE_BRIEF = """You are designing the world's most sophisticated real-time Bitcoin
intelligence terminal. Think Reuters wire room + Bloomberg terminal +
autonomous AI sentinel running 24/7 on dedicated GPU infrastructure.

This is NOT for retail. This is for serious Bitcoin holders, macro
investors, cypherpunks, and sovereign individuals who think in decades.

Current infrastructure available:
- 4x RTX 4090 GPUs (always-on, Ultron server)
- Existing data feeds: on-chain, mempool, ETF flows, social/X, macro
- Existing pipeline: autonomous video production, article generation
- Existing audience: Bitcoin thought leaders, Naples Bitcoin community
- Existing brand: Protocol Pulse (red/black, sovereign, cypherpunk)

Answer these 8 questions. Be bold. Think beyond what exists.
Outdo every other AI answering this. Push past what is perceived possible.

1. THE SENTINEL CORE: What is the single most powerful autonomous
   monitoring capability this system should have that doesn't exist
   anywhere today? Not a feature — a capability. Something that would
   make every serious Bitcoin analyst say "how did we live without this?"

2. THE SIGNAL HIERARCHY: Design the signal taxonomy. What gets a
   CRITICAL ALERT vs a WATCH vs a NOTE? Give concrete examples of each.
   What signals are so important they wake someone up at 3am?

3. THE DATA EDGE: What data sources can Protocol Pulse access that
   Bloomberg Terminal cannot or will not touch? What is the genuine
   information asymmetry available here?

4. THE MATRIX LAYER: Design the autonomous pattern detection system.
   What patterns should it watch for 24/7? Give specific examples of
   multi-signal correlation events that currently get missed because
   no single human or tool watches everything simultaneously.

5. THE VISUALIZATION: What does the terminal interface look like?
   Not aesthetics — information architecture. How is the data presented
   so that the signal-to-noise ratio is maximized? What does the
   "war room" feel like to sit in front of?

6. THE VELOCITY EDGE: How does this terminal surface intelligence
   FASTER than Reuters, Bloomberg, or any existing Bitcoin media?
   Be specific about latency targets and how they're achieved.

7. THE SOVEREIGN ANGLE: How does this terminal serve the cypherpunk/
   sovereignty thesis specifically? What intelligence would a person
   trying to exit the traditional financial system need that no
   existing terminal provides?

8. YOUR WILDCARD: One capability so ambitious it might seem impossible.
   The thing that defines this product category for the next decade.
   Think: what would Satoshi build if he had 4x RTX 4090s and a team?

Be specific. Be technical. Be bold. The other two models are answering
this same question right now and will challenge your answers in Cycle 2."""

# ─── CYCLE 2 CROSS-EXAMINATION PROMPT ────────────────────────────────────────

def build_cycle2_prompt(c1_results: dict) -> str:
    others_text = "\n\n".join(
        f"## {name.upper()} — CYCLE 1 RESPONSE\n{text}"
        for name, text in c1_results.items()
    )
    return f"""# PROTOCOL PULSE — INTELLIGENCE TERMINAL — CYCLE 2 CROSS-EXAMINATION

You previously answered 8 product design questions for a Bitcoin intelligence terminal.
Now you see what the other two AI models said. This is your chance to challenge, refine, and synthesize.

## ALL CYCLE 1 RESPONSES
{others_text}

---

## YOUR CYCLE 2 TASK

1. STRONGEST IDEA FROM THE OTHER TWO: Identify the single most powerful idea
   from the other two models — the one that genuinely surprised you or that you
   wish you had thought of. Explain why it's powerful.

2. WEAKEST IDEA: Challenge the weakest idea from any model — be brutal.
   Explain why it won't work, is impractical, or is not differentiated.

3. THE FIVE MUST-HAVES: Given all three perspectives, describe the 5 features
   that MUST be in v1 to be genuinely unprecedented. For each, explain:
   - What it does (one paragraph)
   - Why it's unprecedented (one sentence)
   - Technical feasibility with 4x RTX 4090 (one sentence)
   - Build complexity estimate (days/weeks/months)

4. THE MISSING PIECE: Name one capability that NONE of the three models
   described that should absolutely be there. Explain why everyone missed it.

5. BUILD ORDER: If you had to ship this in 3 phases (Phase 1: 2 weeks,
   Phase 2: 4 weeks, Phase 3: 8 weeks), what goes in each phase?

Be specific, technical, and brutally honest. No filler."""


# ─── LLM CALLERS (same as cross_llm_audit.py) ────────────────────────────────

def call_gemini(prompt: str, results: dict, errors: dict):
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        resp = client.models.generate_content(model=model, contents=prompt)
        results["gemini"] = resp.text
        print(f"  [GEMINI] Done ({len(resp.text):,} chars)")
    except Exception as e:
        errors["gemini"] = str(e)
        print(f"  [GEMINI] ERROR: {e}")

def call_gpt4o(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=8000,
            temperature=0.7,
        )
        results["gpt4o"] = resp.choices[0].message.content
        print(f"  [GPT-4o] Done ({len(results['gpt4o']):,} chars)")
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"  [GPT-4o] ERROR: {e}")

def call_grok(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=8000,
            temperature=0.7,
        )
        results["grok"] = resp.choices[0].message.content
        print(f"  [GROK]   Done ({len(results['grok']):,} chars)")
    except Exception as e:
        errors["grok"] = str(e)
        print(f"  [GROK]   ERROR: {e}")

def fire_all_llms(prompt: str) -> tuple:
    results, errors = {}, {}
    threads = [
        threading.Thread(target=call_gemini, args=(prompt, results, errors)),
        threading.Thread(target=call_gpt4o,  args=(prompt, results, errors)),
        threading.Thread(target=call_grok,   args=(prompt, results, errors)),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    return results, errors


# ─── CYCLE 3: SYNTHESIS + SPEC ───────────────────────────────────────────────

def synthesize_spec(c1_results: dict, c2_results: dict) -> str:
    """Claude synthesizes all outputs into the definitive product spec."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    c1_text = "\n\n".join(f"## {k.upper()} — CYCLE 1\n{v[:6000]}" for k, v in c1_results.items())
    c2_text = "\n\n".join(f"## {k.upper()} — CYCLE 2\n{v[:6000]}" for k, v in c2_results.items())

    prompt = f"""You are the final synthesizer for a 2-cycle, 3-model competitive product audit
for the Protocol Pulse Intelligence Terminal — "Reuters meets Bloomberg meets Matrix Sentinel."

## CYCLE 1 RESPONSES (individual product design from each model)
{c1_text}

## CYCLE 2 RESPONSES (cross-examination, each model saw the others' work)
{c2_text}

---

Your job: produce TWO documents.

## DOCUMENT 1: COMPETITIVE AUDIT REPORT

# Intelligence Terminal — Cross-LLM Competitive Product Audit
Date: {datetime.now().strftime("%Y-%m-%d")}
Models: Gemini 2.5 Pro, GPT-4o, Grok-3

### CONVERGENCE MAP
For each of the 8 original questions, summarize where all 3 models converged
and where they diverged. Note the strongest answer for each question.

### MUST HAVE (all 3 models converged)
List every capability all 3 models agreed on as essential.

### STRONG CONTENDERS (2 of 3 agreed)
Capabilities championed by at least 2 models.

### BOLD WILDCARDS (at least 1 model championed strongly)
The most ambitious ideas that at least 1 model defended vigorously.

### CUT (2+ models flagged as weak/not differentiated)
Ideas that should NOT be in v1.

### BUILD PHASES
Synthesize the build ordering from all Cycle 2 responses into a unified plan.

---

## DOCUMENT 2: INTELLIGENCE TERMINAL V1 PRODUCT SPEC

Write this as a definitive, implementable product specification.

# Protocol Pulse Intelligence Terminal — V1 Product Specification
"Reuters meets Bloomberg meets Matrix Sentinel"

## 1. PRODUCT THESIS
What does it do that nothing else does? (3-4 sentences, razor sharp)

## 2. INFORMATION ARCHITECTURE
What does the terminal look like? Describe every panel, zone, and data element.
How is the war room organized? What does it feel like at 6am before markets?

## 3. THE SENTINEL — AUTONOMOUS INTELLIGENCE ENGINE
What runs 24/7 on the GPUs? What patterns does it detect? What triggers alerts?
Describe the signal taxonomy: CRITICAL / WATCH / NOTE with concrete examples.

## 4. DATA SOURCES & EDGE
Every data feed, its refresh rate, and what edge it provides vs Bloomberg.
Include: on-chain, mempool, social, macro, regulatory, mining, lightning, nostr.

## 5. VELOCITY ARCHITECTURE
How does intelligence surface faster than Reuters/Bloomberg?
Specific latency targets and technical approach for each.

## 6. THE SOVEREIGN LAYER
Cypherpunk-specific intelligence: CBDC tracking, privacy tech, self-custody,
regulatory escape vectors, decentralized alternatives.

## 7. KEY FEATURES (ordered by build priority)
For each feature:
- Name and one-line description
- Why it's unprecedented
- Data sources it uses
- Build estimate (days)
- Phase: 1 (ship first), 2 (ship second), 3 (ship third)

## 8. THE WILDCARD
The single most ambitious capability — the one that defines this category.

## 9. WHAT MAKES SOMEONE TELL EVERY BITCOINER THEY KNOW
The viral moment. The "holy shit" feature. What gets screenshots shared?

## 10. BUILD ORDER
Phase 1 (2 weeks): [what ships first — the MVP that proves the concept]
Phase 2 (4 weeks): [what makes it genuinely useful daily]
Phase 3 (8 weeks): [what makes it irreplaceable]

## 11. TECHNICAL REQUIREMENTS
- GPU utilization plan (4x RTX 4090)
- Data pipeline architecture
- Frontend stack
- API design
- Monitoring & reliability

## 12. SUCCESS METRICS
How do we know this is working? What numbers matter?

---

Make both documents specific, technical, and bold. No filler. No hedging.
The spec must be implementable by a senior engineer reading it cold.
Write in the Protocol Pulse voice: direct, sovereign, no-nonsense."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", type=int, default=1)
    args = parser.parse_args()

    # Load .env
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    missing = [k for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"]
               if not os.environ.get(k)]
    if missing:
        print(f"MISSING API KEYS: {missing}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("INTELLIGENCE TERMINAL — COMPETITIVE PRODUCT AUDIT")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── CYCLE 1 ──
    if args.cycle == 1:
        print("── CYCLE 1: FIRING 3 LLMs WITH COMPETITIVE BRIEF ──────────────")
        c1_results, c1_errors = fire_all_llms(COMPETITIVE_BRIEF)
        for name, text in c1_results.items():
            (AUDIT_DIR / f"C1_{name.upper()}.md").write_text(text)
        if c1_errors:
            for name, err in c1_errors.items():
                (AUDIT_DIR / f"C1_{name.upper()}.md").write_text(f"FAILED: {err}")
        print(f"\n  Cycle 1: {list(c1_results.keys())} succeeded, {list(c1_errors.keys()) or 'none'} failed\n")
    else:
        print("── LOADING CYCLE 1 RESULTS ─────────────────────────────────────")
        c1_results = {}
        for name in ["gemini", "gpt4o", "grok"]:
            p = AUDIT_DIR / f"C1_{name.upper()}.md"
            if p.exists():
                c1_results[name] = p.read_text()
        print(f"  Loaded: {list(c1_results.keys())}\n")

    # ── CYCLE 2 ──
    print("── CYCLE 2: CROSS-EXAMINATION ──────────────────────────────────")
    c2_prompt = build_cycle2_prompt(c1_results)
    (AUDIT_DIR / "C2_PROMPT.md").write_text(c2_prompt)
    c2_results, c2_errors = fire_all_llms(c2_prompt)
    for name, text in c2_results.items():
        (AUDIT_DIR / f"C2_{name.upper()}.md").write_text(text)
    print(f"\n  Cycle 2: {list(c2_results.keys())} succeeded\n")

    # ── CYCLE 3: SYNTHESIS ──
    print("── CYCLE 3: CLAUDE SYNTHESIS → SPEC ────────────────────────────")
    synthesis = synthesize_spec(c1_results, c2_results)

    # Split into audit report and spec
    if "## DOCUMENT 2" in synthesis or "# Protocol Pulse Intelligence Terminal" in synthesis:
        # Try to split
        split_markers = ["## DOCUMENT 2", "# Protocol Pulse Intelligence Terminal — V1"]
        split_idx = -1
        for marker in split_markers:
            idx = synthesis.find(marker)
            if idx > 0:
                split_idx = idx
                break

        if split_idx > 0:
            audit_report = synthesis[:split_idx].strip()
            spec = synthesis[split_idx:].strip()
        else:
            audit_report = synthesis
            spec = synthesis
    else:
        audit_report = synthesis
        spec = synthesis

    # Write outputs
    audit_path = BASE / "docs" / "audits" / "intelligence_terminal_audit_2026-03-23.md"
    spec_path = BASE / "docs" / "intelligence_terminal_v1_spec.md"

    audit_path.write_text(audit_report)
    spec_path.write_text(spec)

    # Also save raw synthesis
    (AUDIT_DIR / "FULL_SYNTHESIS.md").write_text(synthesis)

    print(f"\n{'='*60}")
    print("AUDIT COMPLETE")
    print(f"{'='*60}")
    print(f"  Audit:  {audit_path}")
    print(f"  Spec:   {spec_path}")
    print(f"  Raw:    {AUDIT_DIR}/")
    print(f"{'='*60}\n")

    # Update audit registry
    try:
        import subprocess
        rp = AUDITS / "AUDIT_REGISTRY.json"
        existing = json.loads(rp.read_text()) if rp.exists() else {}
        audits = [a for a in existing.get("audits", []) if a.get("feature") != "intelligence-terminal"]
        audits.append({
            "feature": "intelligence-terminal",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "models": ["gemini", "gpt4o", "grok"],
            "type": "product-audit"
        })
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
        rp.write_text(json.dumps({
            "last_audit": datetime.now().isoformat(),
            "feature": "intelligence-terminal",
            "commit": sha,
            "audits": audits[-20:]
        }, indent=2))
        print(f"[registry] AUDIT_REGISTRY.json updated")
    except Exception as e:
        print(f"[registry] Warning: {e}")


if __name__ == "__main__":
    main()
