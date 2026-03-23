Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/cc_commander_premium.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: COMPETITIVE CROSS-LLM PRODUCT AUDIT
Protocol Pulse Commander — $29/month Premium
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is not a code audit. This is a PRODUCT audit.
The goal: make this the most advanced, most talked-about Bitcoin
intelligence product on the internet. Something people pay for
without hesitation and tell every Bitcoiner they know about.

STEP 1 — REGISTER FEATURE IN AUDIT ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to utils/cross_llm_audit.py FEATURE_MAP and EXPLICIT_FILES:
  "commander-product-audit": ("VISUAL_DESIGN_SYSTEM.md", "main")
  EXPLICIT_FILES["commander-product-audit"] = [
      "docs/cc_commander_premium.md",
      "templates/commander_dashboard.html",
      "docs/VISUAL_DESIGN_SYSTEM.md",
  ]

STEP 2 — CYCLE 1: INDIVIDUAL AUDITS (competitive brief)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature commander-product-audit

Each model (Gemini, GPT-4o, Grok) receives this prompt:

---AUDIT PROMPT FOR EACH MODEL---
You are auditing a premium Bitcoin intelligence product called
Protocol Pulse Commander ($29/month). Read the spec carefully.

Your job is NOT to validate what's there. Your job is to CHALLENGE it.
Push harder. Think bigger. What would make this so good that serious
Bitcoin holders talk about it unprompted?

Answer these questions:

1. KILLER FEATURE GAP: What one feature is missing that would make
   this genuinely irreplaceable? Something no competitor has.
   Be specific. Not "better UX" — a concrete feature.

2. WHAT WOULD MAKE SOMEONE CANCEL: Identify the weakest feature in
   the current spec. The one that feels like padding. Cut it or
   replace it with something sharper.

3. THE VIRAL MOMENT: What specific thing would make a user screenshot
   this and post it on X with "this is insane"? Design for that moment.

4. CYPHERPUNK AUTHENTICITY CHECK: Does this product feel like it was
   built BY a Bitcoiner FOR Bitcoiners? Or does it feel like a fintech
   product with Bitcoin branding? Be brutal.

5. THE $29 QUESTION: At $29/month, what is the one thing that makes
   this obviously worth it vs free alternatives? Would you pay for it?

6. TECHNICAL EDGE: What data source, API, or real-time feed could
   Protocol Pulse access that competitors can't or won't — that would
   make the intelligence genuinely superior?

7. RETENTION MECHANIC: What feature makes someone open this EVERY DAY
   rather than just when they remember to? Not a notification — a
   genuine pull mechanic.

8. YOUR WILDCARD: One idea completely outside the spec. Something
   bold. Something that might seem crazy but could be the thing
   that defines this product.

Be opinionated. Be direct. Disagree with the spec if you think
it's wrong. The goal is the best possible product, not validation.
---END AUDIT PROMPT---

STEP 3 — CYCLE 2: CROSS-EXAMINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature commander-product-audit --cycle 2 --cycle1-results [C1_OUTPUT]

In Cycle 2, each model sees the others' answers and must:
1. Identify the single best idea from the other two models
2. Challenge the weakest idea from the other two models
3. Synthesize: given all three perspectives, what are the 3 features
   that MUST be built vs 3 that should be cut or deprioritized?

STEP 4 — SYNTHESIZE CONSENSUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After both audit cycles, synthesize:

MUST BUILD (all 3 models agree):
  List features with strongest cross-model consensus

STRONG CONTENDERS (2 of 3 models agree):
  List with rationale

CUT OR DEPRIORITIZE (2+ models flagged as weak):
  List with rationale

WILDCARD ADDITIONS (high-risk/high-reward ideas):
  List the most compelling wildcards from all 3 models

STEP 5 — REWRITE THE SPEC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Based on the full audit consensus, rewrite cc_commander_premium.md
with the improved feature set. This becomes the definitive build spec.

Rules for the rewrite:
- Keep what the audit confirmed is strong
- Cut what the audit flagged as weak
- Add the consensus "killer features"
- Add at least one wildcard that at least 2 models agreed on
- Every feature must answer "why would someone pay $29/month for this
  specifically, when they can get something similar for free?"
- The spec must be buildable — not a vision doc, an engineering spec

Save the rewritten spec to:
  ~/protocol_pulse/docs/cc_commander_premium_v2.md

STEP 6 — AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Save full audit output to:
  ~/protocol_pulse/docs/audits/commander_product_audit_2026-03-22.md

Format:
## Cycle 1 — Individual Model Audits
[Each model's full answers]

## Cycle 2 — Cross-Examination
[Each model's cross-examination responses]

## Consensus Summary
[Must build / Strong contenders / Cut / Wildcards]

## Revised Feature Set
[Final feature list with rationale for each inclusion/exclusion]

STEP 7 — COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add docs/cc_commander_premium_v2.md docs/audits/commander_product_audit_2026-03-22.md
git commit -m "feat(commander): cross-LLM product audit complete — v2 spec with consensus features"
git push

DO NOT build any code in this session.
This session's only output is the audit report and the v2 spec.
The build happens in the next dedicated CC session using the v2 spec.

QUALITY BAR FOR THIS AUDIT:
The v2 spec should make someone reading it think:
"I can't believe this doesn't exist yet."
If it doesn't hit that bar — do another cycle.
