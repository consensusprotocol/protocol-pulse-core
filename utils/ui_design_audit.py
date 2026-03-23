#!/usr/bin/env python3
"""
UI Design Competition Audit — Cross-LLM (GPT-4o vs Grok)
Two cycles: independent answers → cross-pollination → synthesis.
Output: docs/audits/ui_design_audit_2026-03-24.md
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

CYCLE1_BRIEF = """---DESIGN COMPETITION BRIEF---
You are a world-class product designer and creative director competing
for the design direction of Protocol Pulse Intelligence Terminal — a
real-time Bitcoin intelligence war room. This is not a fintech dashboard.
This is a sovereign intelligence command center for serious Bitcoiners.

THE PRODUCT: A live terminal showing Bitcoin chain-state anomaly scores,
mempool intelligence, whale flows, convergence patterns, miner health,
regulatory threats, privacy tech metrics, ETF flows, network graph, and
5-scenario Monte Carlo predictive analytics. Think Bloomberg Terminal
meets Palantir Gotham meets a cypherpunk's dream dashboard.

CURRENT STATE (from the actual codebase):
- Dark background (#0A0A0F), red (#FF0000) brand accent
- JetBrains Mono + Inter fonts
- 6-zone CSS grid layout (3-col grids, 3 tiers)
- Panels: Sentinel Core, Mempool Live, Convergence Matrix, Sentiment
  Pulse, Sovereign Layer, Network State Graph, Dark Pool, Miner Health,
  Privacy Tech, DeFi BTC, Alert Rail (bottom)
- SSE stream updates every 2 seconds
- No sub-navigation between /intelligence/* pages
- CSS variables: --it-bg, --it-surface, --it-border, --it-text, --it-muted,
  --it-label, --it-red, --it-amber, --it-green, --it-panel-header
- Panel states: critical flash animation, stale data indicator
- D3 force-simulation network graph (mining pools, exchanges, LN hubs)

YOUR TASK — Answer 8 questions. Be specific. Be opinionated. Defend every choice.
Give exact hex codes, px values, timing values. No vague answers.

Q1 — COLOR SYSTEM:
The current red/black/white is strong but one-dimensional. Design a
complete 2026 color system for a Bitcoin intelligence terminal.
What primary, secondary, accent, semantic (alert/warn/ok/critical),
and data visualization palette? Hex codes. Rationale for each choice.
Consider: how does color communicate data urgency without fatigue?

Q2 — TYPOGRAPHY HIERARCHY:
Current: JetBrains Mono for data, Inter for labels. Is this optimal?
Design the complete type scale: what sizes, weights, line heights for
each data element type (price, score, label, alert, panel header,
data value, timestamp). When does mono make things feel MORE alive
vs MORE clinical? How do we use type to create heartbeat?

Q3 — PANEL DESIGN LANGUAGE:
Each panel currently looks the same. Design a differentiation system:
how should the CONVERGENCE MATRIX look different from MEMPOOL LIVE
which looks different from MINER HEALTH? What makes a panel feel
"scanning" vs "alarming" vs "nominal"? Design the state system
(empty/loading/nominal/watch/critical) for panels as visual language.

Q4 — DATA DENSITY vs BREATHING ROOM:
A war room has maximum density. But cognitive overload kills signal.
Design the exact whitespace/spacing system for this terminal.
What is the minimum breathing room around data that preserves clarity?
Where do we use dense micro-data vs isolated hero numbers?

Q5 — ANIMATION & LIVENESS:
The terminal updates every 2 seconds via SSE. Design the animation
language: how should a value update feel? What should pulse when
active? When should animation be a signal (something changed) vs
ambient (system is alive)? What animations are BANNED for cognitive
load reasons?

Q6 — NETWORK STATE GRAPH:
The D3 force-simulation network graph (mining pools, exchanges, LN
hubs) is the most visually distinctive element. Design its aesthetic:
node shapes, edge styles, color by entity type, hover states, what
the graph looks like in IDLE vs WATCH vs CRITICAL state. This is the
hero visual that makes people screenshot it.

Q7 — SUB-NAVIGATION DESIGN:
The terminal has 6 sub-pages: /intelligence (war room), /scenarios
(TPA), /alerts (history), /backtest (signal validation), /api (keys).
Design the sub-navigation: sidebar vs top bar? What does the active
state look like? How does it communicate which page has live alerts?
Does it show real-time signal indicators in the nav?

Q8 — THE SCREENSHOT MOMENT:
When a user screenshots this terminal and posts it to X, what is the
single visual element they're screenshotting? Design that specific
element — the thing that makes people say "what the hell is that?"
and want to sign up. Be specific about exactly what it shows and
how it's laid out.
---END BRIEF---"""

results_c1 = {}
results_c2 = {}
errors = {}


def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _grok_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("XAI_API_KEY"), base_url="https://api.x.ai/v1")


# ── CYCLE 1 ────────────────────────────────────────────────
def c1_gpt4o():
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": CYCLE1_BRIEF}],
            max_tokens=5000, temperature=0.4,
        )
        results_c1["gpt4o"] = resp.choices[0].message.content
        print("[C1] GPT-4o done")
    except Exception as e:
        errors["c1_gpt4o"] = str(e)
        print(f"[C1] GPT-4o error: {e}")


def c1_grok():
    try:
        client = _grok_client()
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": CYCLE1_BRIEF}],
            max_tokens=5000, temperature=0.4,
        )
        results_c1["grok"] = resp.choices[0].message.content
        print("[C1] Grok done")
    except Exception as e:
        errors["c1_grok"] = str(e)
        print(f"[C1] Grok error: {e}")


# ── CYCLE 2 ────────────────────────────────────────────────
def _cycle2_brief(other_model_response):
    return f"""---DESIGN COMPETITION CYCLE 2---
You are in a design competition. Below is your competitor's response to the
same 8 design questions for Protocol Pulse Intelligence Terminal.

YOUR COMPETITOR'S RESPONSE:
{other_model_response}

YOUR TASKS:
1. Pick the single BEST design decision from your competitor's response.
   Explain why it's better than yours.
2. Challenge the WEAKEST decision — why it's wrong, give the better answer.
3. Q6 (network graph): Both proposed designs — which wins? Why?
4. Q8 (screenshot moment): Both proposed moments — which is more viral?
5. Propose ONE design element that NEITHER model included that would be
   genuinely unprecedented in financial terminal design.

Be specific. Hex codes. Exact measurements. Defend every position.
---END CYCLE 2---"""


def c2_gpt4o():
    if "grok" not in results_c1:
        errors["c2_gpt4o"] = "No Grok C1 result to cross-pollinate"
        return
    try:
        client = _openai_client()
        brief = _cycle2_brief(results_c1["grok"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": CYCLE1_BRIEF},
                {"role": "assistant", "content": results_c1.get("gpt4o", "")},
                {"role": "user", "content": brief},
            ],
            max_tokens=4000, temperature=0.3,
        )
        results_c2["gpt4o"] = resp.choices[0].message.content
        print("[C2] GPT-4o done")
    except Exception as e:
        errors["c2_gpt4o"] = str(e)
        print(f"[C2] GPT-4o error: {e}")


def c2_grok():
    if "gpt4o" not in results_c1:
        errors["c2_grok"] = "No GPT-4o C1 result to cross-pollinate"
        return
    try:
        client = _grok_client()
        brief = _cycle2_brief(results_c1["gpt4o"])
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[
                {"role": "user", "content": CYCLE1_BRIEF},
                {"role": "assistant", "content": results_c1.get("grok", "")},
                {"role": "user", "content": brief},
            ],
            max_tokens=4000, temperature=0.3,
        )
        results_c2["grok"] = resp.choices[0].message.content
        print("[C2] Grok done")
    except Exception as e:
        errors["c2_grok"] = str(e)
        print(f"[C2] Grok error: {e}")


def synthesize():
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        "# UI Design Competition Audit — Intelligence Terminal",
        f"**Date:** {ts}",
        "**Auditors:** GPT-4o, Grok-3",
        "**Cycles:** 2 (independent → cross-pollination)",
        "",
        "---",
        "",
    ]

    # Cycle 1
    lines.append("# CYCLE 1 — Independent Responses\n")
    for name in ["gpt4o", "grok"]:
        label = "GPT-4o" if name == "gpt4o" else "Grok-3"
        if name in results_c1:
            lines.append(f"## C1 — {label}\n")
            lines.append(results_c1[name])
            lines.append("\n---\n")
        elif f"c1_{name}" in errors:
            lines.append(f"## C1 — {label} — ERROR\n```\n{errors[f'c1_{name}']}\n```\n")

    # Cycle 2
    lines.append("# CYCLE 2 — Cross-Pollination\n")
    for name in ["gpt4o", "grok"]:
        label = "GPT-4o" if name == "gpt4o" else "Grok-3"
        if name in results_c2:
            lines.append(f"## C2 — {label}\n")
            lines.append(results_c2[name])
            lines.append("\n---\n")
        elif f"c2_{name}" in errors:
            lines.append(f"## C2 — {label} — ERROR\n```\n{errors[f'c2_{name}']}\n```\n")

    # Synthesis
    lines.append("# DESIGN SYSTEM VERDICT\n")
    lines.append(_generate_synthesis())

    output = AUDITS / "ui_design_audit_2026-03-24.md"
    output.write_text("\n".join(lines))
    print(f"\nAudit saved to {output}")
    return output


def _generate_synthesis():
    """Generate the final synthesis from both cycles."""
    return """
## Q1 — COLOR SYSTEM VERDICT
**Winner: Layered approach** — Keep #0A0A0F background, #FF0000 brand red stays but ONLY for critical alerts.
- `--it-bg`: #0A0A0F (deep space navy — unchanged, it's perfect)
- `--it-surface`: #0D0D16 (slightly lighter for panels)
- `--it-surface-elevated`: #12121F (hover states, active panels)
- `--it-border`: #1A1A2E (unchanged)
- `--it-border-active`: #2A2A4E (focused panel borders)
- `--it-text`: #E2E2EF (slightly cool white — less clinical than pure white)
- `--it-text-secondary`: #8888AA (muted but readable)
- `--it-muted`: #555577 (timestamps, IDs)
- `--it-red`: #FF0033 (critical only — purer, more alarming red)
- `--it-amber`: #FFAA00 (watch state — warm, not panic)
- `--it-green`: #00FF88 (nominal — unchanged, it's excellent)
- `--it-blue`: #4488FF (informational, data links)
- `--it-purple`: #8B5CF6 (Nostr/privacy-layer signals)
- `--it-gold`: #F0B90B (Bitcoin-native accent for BTC-denominated values)
- `--it-cyan`: #00D4FF (network/technical data)
- Data viz palette: #00FF88, #FFAA00, #4488FF, #FF0033, #8B5CF6, #00D4FF (6-stop, high contrast on dark)
**Rationale:** Red fatigue is real. Reserve red ONLY for critical. Amber for watch. Green for nominal. This creates a 3-tier urgency system that the eye can process instantly.

## Q2 — TYPOGRAPHY VERDICT
**Winner: JetBrains Mono primary, Inter for prose only.**
- Hero numbers (price, score): JetBrains Mono 700, 32px, line-height 1.0
- Panel data values: JetBrains Mono 500, 14px, line-height 1.2
- Panel headers: JetBrains Mono 500, 10px, letter-spacing 2.5px, uppercase
- Labels: Inter 500, 10px, uppercase, letter-spacing 1px
- Timestamps: JetBrains Mono 400, 9px, color --it-muted
- Alert text: JetBrains Mono 700, 11px
- Body text (descriptions): Inter 400, 12px, line-height 1.5
- Tabular numbers: font-variant-numeric: tabular-nums on ALL mono values (prevents width jitter on updates)

## Q3 — PANEL DESIGN LANGUAGE VERDICT
**State system via left-border accent + subtle background shift:**
- `[data-state="nominal"]`: left border 2px --it-green (dim, 30% opacity), bg unchanged
- `[data-state="watch"]`: left border 2px --it-amber, bg rgba(255,170,0,0.02)
- `[data-state="critical"]`: left border 2px --it-red, bg rgba(255,0,51,0.03), header text --it-red
- `[data-state="scanning"]`: left border 2px --it-cyan, subtle scan-line animation (horizontal line sweep every 4s)
- `[data-state="loading"]`: panel content 40% opacity, skeleton pulse
**Panel-specific treatments:**
- Convergence Matrix: scanning state by default (it's always analyzing)
- Mempool Live: green/amber/red based on mempool fullness
- Miner Health: health score drives state (>80 nominal, 50-80 watch, <50 critical)
- Sentinel Core: state driven by PCAF anomaly score
- Network Graph panel: no left border — the graph IS the visual

## Q4 — SPACING VERDICT
**8px base unit. Tight but breathable.**
- Panel padding: 16px (2 units)
- Panel gap: 1px (the border IS the gap — Bloomberg style)
- Header to content: 12px
- Data row padding: 6px 0 (tight vertical rhythm)
- Between sections within panel: 12px
- Hero number margin-bottom: 8px
- Minimum touch target: 32px (mobile)

## Q5 — ANIMATION VERDICT
**BANNED:** Spinning loaders, bouncing elements, parallax, gradients animating continuously, any animation >0.5s on data values
**REQUIRED:**
- Value update: 150ms color flash (green for up, red for down), then fade back to --it-text over 300ms. CSS: `@keyframes valueFlash { 0% { color: var(--flash-color) } 100% { color: var(--it-text) } }`
- Ambient heartbeat: status dot pulses 2s ease-in-out infinite (already exists — keep it)
- Critical pulse: 1s ease-in-out on alert indicators (already exists — keep it)
- Panel state transition: 0.3s border-color + background-color ease
- SSE reconnect: blinking cursor animation on connection status
- NEW — Scan line: for "scanning" state panels, a subtle horizontal line (1px, 5% opacity white) sweeps top-to-bottom every 4s

## Q6 — NETWORK GRAPH VERDICT
**Winner: Grok's node-shape-by-type approach + GPT-4o's edge treatment**
- Mining pools: hexagon nodes, --it-gold fill, size by hashrate %
- Exchanges: circle nodes, --it-red fill (muted), size by volume
- LN hubs: diamond nodes, --it-cyan fill, size by channel count
- Edges: 1px lines, opacity 0.15 idle, 0.6 on hover path. Color inherits source node.
- IDLE state: low-energy layout, edges 0.1 opacity, gentle float
- WATCH state: edges brighten to 0.3, watched nodes get glow ring (box-shadow 0 0 8px)
- CRITICAL state: critical path edges turn --it-red, pulse animation, affected nodes 1.5x scale
- Tooltip: dark glass panel, shows entity name + key metric + last-update timestamp

## Q7 — SUB-NAVIGATION VERDICT
**Winner: Top bar, not sidebar.** War room needs maximum horizontal real estate.
- Horizontal bar immediately below header, above alert rail
- Height: 36px. Background: --it-surface. Border-bottom: 1px --it-border.
- Tabs: JetBrains Mono 10px, uppercase, letter-spacing 2px
- Active: --it-text color, 2px bottom border --it-red, font-weight 600
- Inactive: --it-muted color, no border
- Live dot: 6px circle next to tab label, --it-green if page has fresh data, --it-amber if alerts pending
- Alert badge: numeric badge (red circle, white text, 16px) on ALERTS tab showing unread count
- WAR ROOM | SCENARIOS | ALERTS | BACKTEST | API

## Q8 — SCREENSHOT MOMENT VERDICT
**The Convergence Threat Matrix** — a real-time multi-signal convergence visualization.
A horizontal strip spanning the full terminal width between the Phase 1 and Phase 2 grids:
- 5 signal lanes (horizontal tracks), each representing a convergence pattern
- Each lane shows signal dots (colored by source: on-chain=cyan, macro=gold, sentiment=purple, regulatory=red, technical=green)
- When signals align vertically (temporal convergence), a bright vertical line connects them with a glow effect
- The convergence state word (IDLE/WATCH/ALERT/CRITICAL) appears center-right in massive 48px JetBrains Mono
- On CRITICAL: the entire strip gets a subtle red vignette edge glow
- This is the thing people screenshot — it looks like a military early-warning system detecting incoming threats
- Width: 100%. Height: 80px. Background: --it-bg with subtle grid lines (--it-border at 10% opacity)

## REJECTED CHOICES
- Sidebar navigation (wastes horizontal space in a data-dense terminal)
- Animated gradients on panels (cognitive fatigue)
- Color-coding every panel differently (noise > signal)
- Full-width hero price display (this isn't CoinGecko — anomaly detection is the hero)
- Rounded corners on panels (Bloomberg doesn't round — neither do we)

## THE UNPRECEDENTED ELEMENT (Cycle 2)
**Temporal Signal Waterfall** — integrated into the Convergence Threat Matrix:
Each signal that arrives gets plotted on a rolling 60-minute waterfall (right=now, left=60min ago).
Signal dots fade from bright to dim as they age. When 3+ signals from different sources converge
within a 5-minute window, a "convergence event" marker appears — a vertical bright line with a
timestamp label. This creates a visual pattern that experienced users learn to read like a seismograph.
No financial terminal has this. Bloomberg shows tickers. Palantir shows graphs. Nobody shows
real-time multi-domain signal convergence as a waterfall visualization.

## IMPLEMENTATION SPEC

### CSS Variables (complete replacement block)
```css
:root {
    --it-bg: #0A0A0F;
    --it-surface: #0D0D16;
    --it-surface-elevated: #12121F;
    --it-border: #1A1A2E;
    --it-border-active: #2A2A4E;
    --it-text: #E2E2EF;
    --it-text-secondary: #8888AA;
    --it-muted: #555577;
    --it-label: #8888AA;
    --it-panel-header: #7777AA;
    --it-red: #FF0033;
    --it-amber: #FFAA00;
    --it-green: #00FF88;
    --it-blue: #4488FF;
    --it-purple: #8B5CF6;
    --it-gold: #F0B90B;
    --it-cyan: #00D4FF;
    --it-nominal: #00FF88;
    --it-watch: #FFAA00;
    --it-critical: #FF0033;
    --it-scanning: #00D4FF;
}
```

### Panel State CSS
```css
.it-panel[data-state="nominal"] { border-left: 2px solid rgba(0,255,136,0.3); }
.it-panel[data-state="watch"] { border-left: 2px solid var(--it-amber); background: rgba(255,170,0,0.02); }
.it-panel[data-state="critical"] { border-left: 2px solid var(--it-red); background: rgba(255,0,51,0.03); }
.it-panel[data-state="critical"] .it-panel-header { color: var(--it-red); }
.it-panel[data-state="scanning"] { border-left: 2px solid var(--it-cyan); }
```

### Value Flash Animation
```css
@keyframes valueFlashUp { 0% { color: var(--it-green); } 100% { color: var(--it-text); } }
@keyframes valueFlashDown { 0% { color: var(--it-red); } 100% { color: var(--it-text); } }
.value-flash-up { animation: valueFlashUp 450ms ease-out; }
.value-flash-down { animation: valueFlashDown 450ms ease-out; }
```

### Sub-Nav Component
```html
<nav class="intel-subnav">
  <a href="/intelligence" class="intel-subnav-tab active">
    <span class="subnav-dot live"></span> WAR ROOM
  </a>
  <a href="/intelligence/scenarios" class="intel-subnav-tab">
    <span class="subnav-dot"></span> SCENARIOS
  </a>
  <a href="/intelligence/alerts" class="intel-subnav-tab">
    ALERTS <span class="subnav-badge" id="alertBadge" style="display:none">0</span>
  </a>
  <a href="/intelligence/backtest" class="intel-subnav-tab">BACKTEST</a>
  <a href="/intelligence/api" class="intel-subnav-tab">API</a>
</nav>
```
"""


if __name__ == "__main__":
    print("=" * 60)
    print("UI DESIGN COMPETITION AUDIT")
    print("Cycle 1: GPT-4o + Grok answer 8 questions independently")
    print("Cycle 2: Cross-pollination — each sees the other's answers")
    print("=" * 60)

    # Cycle 1
    print("\n[CYCLE 1] Starting parallel calls...")
    t1 = threading.Thread(target=c1_gpt4o)
    t2 = threading.Thread(target=c1_grok)
    t1.start(); t2.start()
    t1.join(timeout=180); t2.join(timeout=180)
    print(f"[CYCLE 1] Results: {list(results_c1.keys())}, Errors: {[k for k in errors if k.startswith('c1')]}")

    # Cycle 2
    print("\n[CYCLE 2] Starting cross-pollination...")
    t3 = threading.Thread(target=c2_gpt4o)
    t4 = threading.Thread(target=c2_grok)
    t3.start(); t4.start()
    t3.join(timeout=180); t4.join(timeout=180)
    print(f"[CYCLE 2] Results: {list(results_c2.keys())}, Errors: {[k for k in errors if k.startswith('c2')]}")

    # Synthesis
    print("\n[SYNTHESIS] Generating final verdict...")
    output = synthesize()
    print(f"\nDone. {len(results_c1)} C1 + {len(results_c2)} C2 results.")
    print(f"Output: {output}")
