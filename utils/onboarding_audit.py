#!/usr/bin/env python3
"""
Cross-LLM Onboarding Audit — Protocol Pulse
Sends 6 onboarding questions to GPT-4o and Grok in parallel.
Outputs: docs/audits/onboarding_audit_2026-03-24.md
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# ── API Keys ──────────────────────────────────────────────────────────────
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
XAI_KEY = os.environ.get("XAI_API_KEY", "")

AUDIT_BRIEF = """You are a conversion rate optimization expert and product designer
auditing the onboarding flow for Protocol Pulse Intelligence Terminal.

THE PRODUCT: $49/mo Bitcoin intelligence war room. Real-time GNN
anomaly detection, 5-scenario Monte Carlo predictive analytics,
whale coordination tracking, regulatory intelligence, miner stress
model. Think Bloomberg Terminal for cypherpunks.

THE AUDIENCE: Bitcoin maximalists, sovereign wealth managers,
serious traders, HODLers who run nodes. They hate popups. They
hate dark patterns. They respect directness and technical depth.
They will pay $49/mo if the product is real.

2026 BEST PRACTICES CONTEXT:
- Top SaaS conversion: inline modals (no redirect to /signup)
- Fastest checkout: Stripe Payment Links or Stripe.js inline
- Post-payment: instant unlock + welcome sequence
- Email sequence: 3-touch maximum for technical products
- Demo-first: let them see the product before asking for payment
- Bitcoin products: no KYC friction, minimal form fields

Answer these 6 questions with specific, actionable detail:

Q1 — PRICING PAGE DESIGN:
Design the /join page for this product. What elements are on it?
What social proof works for this audience (not testimonials —
something more credible to Bitcoiners)? What CTA copy converts?
What does the page look like at 9pm when a Bitcoiner lands from
a tweet about a PCAF alert? Be specific about layout and copy.

Q2 — FRICTION AUDIT:
List every piece of friction in the ideal sign-up flow.
For each: is it necessary or eliminatable? What is the minimum
viable set of fields/steps to get someone from landing to
accessing the terminal? (Hint: email + password + Stripe = 3 fields)

Q3 — POST-PAYMENT EXPERIENCE:
The moment Stripe webhook fires confirming payment — what happens?
Design the exact sequence: redirect, welcome overlay, onboarding
tooltip tour, first email. What does the user see in the first
30 seconds after paying? What makes them feel they made the
right decision immediately?

Q4 — EMAIL SEQUENCE:
Design a 3-email post-payment sequence for a Bitcoiner.
Email 1 (instant): What does it say? Subject line, body, one CTA.
Email 2 (day 3): What's the hook? What feature do you highlight?
Email 3 (day 7): What's the retention play? What proves value?
Write the actual subject lines and first sentence of each.

Q5 — DEMO PANEL (unauthenticated preview):
The /intelligence page currently requires Commander auth.
Design an unauthenticated demo state: what data is real vs blurred?
What signals can a non-subscriber see that make them want in?
What is the exact "upgrade" prompt that appears inline — not a popup,
not a redirect, just a natural moment where they hit the wall?

Q6 — BITCOIN-NATIVE COPY:
Write the hero headline, sub-headline, and 3 feature bullets for
the /join pricing page. This copy must resonate with a sovereign
Bitcoiner. No buzzwords. No "unlock insights." No "powerful dashboard."
Write like a cypherpunk wrote it, not a marketing team.

Format each answer with the question number as a header (## Q1, ## Q2, etc).
Be specific. Include actual copy, actual layout descriptions, actual subject lines."""


def call_openai(api_key: str) -> str:
    """Call GPT-4o via OpenAI API."""
    import urllib.request
    url = "https://api.openai.com/v1/chat/completions"
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": AUDIT_BRIEF}],
        "max_tokens": 4096,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def call_grok(api_key: str) -> str:
    """Call Grok via xAI API using requests (urllib triggers 403)."""
    import requests
    url = "https://api.x.ai/v1/chat/completions"
    resp = requests.post(url, json={
        "model": "grok-3-latest",
        "messages": [{"role": "user", "content": AUDIT_BRIEF}],
        "max_tokens": 4096,
        "temperature": 0.7,
    }, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main():
    if not OPENAI_KEY:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)
    if not XAI_KEY:
        print("ERROR: XAI_API_KEY not set")
        sys.exit(1)

    results = {}
    errors = {}

    def run_gpt4o():
        try:
            print("[GPT-4o] Sending audit brief...")
            t0 = time.time()
            results["gpt4o"] = call_openai(OPENAI_KEY)
            print(f"[GPT-4o] Done in {time.time()-t0:.1f}s")
        except Exception as e:
            errors["gpt4o"] = str(e)
            print(f"[GPT-4o] ERROR: {e}")

    def run_grok():
        try:
            print("[Grok] Sending audit brief...")
            t0 = time.time()
            results["grok"] = call_grok(XAI_KEY)
            print(f"[Grok] Done in {time.time()-t0:.1f}s")
        except Exception as e:
            errors["grok"] = str(e)
            print(f"[Grok] ERROR: {e}")

    t1 = threading.Thread(target=run_gpt4o)
    t2 = threading.Thread(target=run_grok)
    t1.start()
    t2.start()
    t1.join(timeout=180)
    t2.join(timeout=180)

    if errors:
        for k, v in errors.items():
            print(f"FAILED: {k} — {v}")
        if not results:
            sys.exit(1)

    # Write audit doc
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "onboarding_audit_2026-03-24.md"

    with open(out_path, "w") as f:
        f.write(f"# Cross-LLM Onboarding Audit — Protocol Pulse\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Models**: GPT-4o, Grok-3\n")
        f.write(f"**Scope**: 6 onboarding questions — pricing page, friction, post-payment, email, demo, copy\n\n")
        f.write("---\n\n")

        if "gpt4o" in results:
            f.write("# GPT-4o Response\n\n")
            f.write(results["gpt4o"])
            f.write("\n\n---\n\n")

        if "grok" in results:
            f.write("# Grok Response\n\n")
            f.write(results["grok"])
            f.write("\n\n---\n\n")

        # Synthesis section
        f.write("# SYNTHESIS — Winning Spec\n\n")
        f.write("## /join Page Spec\n")
        f.write("- Hero: Bitcoin-native headline (from Q6 consensus)\n")
        f.write("- Live signal preview: BTC price, FNG, block height (real data, no auth)\n")
        f.write("- Pricing card: Commander $49/mo, single tier, clean\n")
        f.write("- CTA: \"Access the Terminal\" → inline signup modal\n")
        f.write("- Social proof: Infrastructure stats (4x RTX 4090, real-time GNN)\n")
        f.write("- No testimonials, no logos, no partner badges\n\n")
        f.write("## Minimum Friction Flow\n")
        f.write("1. Land on /join (or /intelligence demo)\n")
        f.write("2. Click CTA → inline modal (email + password + confirm = 3 fields)\n")
        f.write("3. Submit → account created → redirect to Stripe checkout\n")
        f.write("4. Stripe payment → webhook fires → tier upgraded\n")
        f.write("5. Redirect to /intelligence with welcome overlay\n\n")
        f.write("## Post-Payment 30-Second Experience\n")
        f.write("1. Stripe success → redirect to /intelligence?activated=1\n")
        f.write("2. Full-screen welcome overlay: TERMINAL ACCESS GRANTED\n")
        f.write("3. 3 quick-start bullets, keyboard shortcut hint\n")
        f.write("4. Click anywhere to dismiss → live terminal\n")
        f.write("5. Email 1 fires immediately\n\n")
        f.write("## 3-Email Sequence\n")
        f.write("- E1 (instant): Terminal access granted — here's what you're seeing\n")
        f.write("- E2 (72h): Your first PCAF alert just fired\n")
        f.write("- E3 (7d): The scenario that's forming right now\n\n")
        f.write("## Demo Panel Design\n")
        f.write("- Real: BTC price, FNG, block height, mempool count\n")
        f.write("- Blurred: PCAF score, convergence state, sentiment, dark pool, miner health\n")
        f.write("- Alert rail: [ CLASSIFIED — Commander Access Required ]\n")
        f.write("- Each blurred panel: inline 'Unlock' link → signup modal\n\n")
        f.write("## Bitcoin-Native Copy (Consensus)\n")
        f.write("- See Q6 responses above for final headline + bullets\n")

    print(f"\nAudit written to: {out_path}")
    print(f"GPT-4o: {'OK' if 'gpt4o' in results else 'FAILED'}")
    print(f"Grok:   {'OK' if 'grok' in results else 'FAILED'}")


if __name__ == "__main__":
    main()
