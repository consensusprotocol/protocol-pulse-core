Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPETITIVE LLM PRODUCT AUDIT
Protocol Pulse Intelligence Terminal
"Reuters meets Bloomberg meets Matrix Sentinel"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUCT VISION:
The world's most sophisticated autonomous Bitcoin intelligence platform.
Not a dashboard. Not a news aggregator. A living, breathing intelligence
system that watches everything simultaneously — on-chain, macro, geopolitical,
social, institutional — and surfaces signal before anyone else sees it.

Reuters: real-time verified wire intelligence, breaking as it happens.
Bloomberg: professional-grade terminal depth, data no retail platform has.
Matrix Sentinel: autonomous pattern detection, threat awareness, 24/7 vigilance.

Built on Protocol Pulse infrastructure (Ultron: 4x RTX 4090, always-on).
Audience: serious Bitcoin holders, cypherpunks, sovereign individuals.
The people who already pay for Bloomberg but want something that thinks
with a Bitcoin brain, not a TradFi brain.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGISTER IN AUDIT ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to utils/cross_llm_audit.py:
  FEATURE_MAP["intelligence-terminal"] = ("VISUAL_DESIGN_SYSTEM.md", "main")
  EXPLICIT_FILES["intelligence-terminal"] = [
      "docs/VISUAL_DESIGN_SYSTEM.md",
      "services/morning_brief.py",
      "video_pipeline_v3/daily_producer.py",
  ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE 1 — INDIVIDUAL COMPETITIVE AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature intelligence-terminal

Each model (Gemini, GPT-4o, Grok) receives this competitive brief:

---COMPETITIVE BRIEF---
You are designing the world's most sophisticated real-time Bitcoin
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
this same question right now and will challenge your answers in Cycle 2.
---END BRIEF---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE 2 — CROSS-EXAMINATION (models challenge each other)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature intelligence-terminal --cycle 2 --cycle1-results [C1]

Each model sees the other two's answers and must:
1. Identify the single most powerful idea from the other two — the one
   that genuinely surprised them
2. Challenge the weakest idea — be brutal, explain why it won't work
3. Synthesize: given all three perspectives, describe the 5 features
   that MUST be in v1 to be genuinely unprecedented
4. Name one capability that NONE of the three models described that
   should be there

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE 3 — SYNTHESIS + SPEC OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After both cycles, synthesize into a definitive product spec:

MUST HAVE (all 3 models converged):
STRONG CONTENDERS (2 of 3 agreed):
BOLD WILDCARDS (at least 1 model championed strongly):
CUT (2+ models flagged as weak/not differentiated):

Then write the full product spec to:
~/protocol_pulse/docs/intelligence_terminal_v1_spec.md

The spec must answer:
- What does it do that nothing else does?
- What does it look like (interface, information architecture)?
- What does it feel like to use it at 6am before markets open?
- What data sources power it?
- What autonomous capabilities run 24/7?
- What makes someone tell every Bitcoiner they know about it?
- What is the build order (what ships first)?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAVE OUTPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs/audits/intelligence_terminal_audit_2026-03-23.md — full audit
docs/intelligence_terminal_v1_spec.md — the definitive build spec

git add docs/audits/intelligence_terminal_audit_2026-03-23.md
git add docs/intelligence_terminal_v1_spec.md
git commit -m "feat(intel-terminal): cross-LLM competitive audit + v1 spec — Reuters/Bloomberg/Matrix Sentinel"
git push

IMPORTANT: Do not ask for confirmation before committing.
Run git add, commit, and push automatically.
