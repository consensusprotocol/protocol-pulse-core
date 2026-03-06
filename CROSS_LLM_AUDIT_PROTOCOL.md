# PROTOCOL PULSE — CROSS-LLM FORENSIC AUDIT PROTOCOL
# Automated Multi-Model Analysis & Consensus Execution System
# Trigger phrase: "Run a cross-LLM audit on [target]"
# Status: GOSPEL. This process runs whenever PBX requests a forensic analysis.
# Created: 2026-03-06

---

## WHAT THIS IS

When PBX says "run a cross-LLM audit" or "give me a forensic analysis" or
"I want a full codebase snapshot for cross-analysis," this protocol activates.

It produces a comprehensive analysis document, fires it to 3 external LLMs
(Gemini, ChatGPT, Grok), collects their outputs, runs a second consensus cycle,
and then auto-drafts a Claude Code execution session from the final consensus.

The goal: eliminate blind spots, validate quality, and surface enhancements
that any single model would miss — then EXECUTE the consensus immediately.

---

## THE TRIGGER

PBX says any of:
- "Run a cross-LLM audit on [feature/codebase/pipeline]"
- "Give me a forensic analysis snapshot of [target]"
- "I want to cross-analyze [target] with other LLMs"
- "Full stack audit for [target]"

Claude responds by executing this protocol automatically.

---

## PHASE 1: GENERATE THE AUDIT PACKAGE (Claude does this)

### Step 1.1: Pull the actual code
Claude pulls ALL relevant code from Ultron via relay:
- Every file in the target feature's directory
- All related config files (feature_flags.json, channels.yaml, etc.)
- All related gospel docs that govern this feature
- Recent git log (last 20 commits touching these files)
- Current cron jobs that interact with this feature
- Any known bugs or pending fixes from PRODUCT_BACKLOG.md

### Step 1.2: Generate the Audit Package document
Claude creates a single markdown document containing:

```markdown
# PROTOCOL PULSE — FORENSIC AUDIT PACKAGE
# Target: [feature name]
# Generated: [timestamp]
# Purpose: Cross-LLM analysis for maximum quality assurance

## CONTEXT
[Brief description of what this feature does, why it matters,
and what quality standard it needs to meet]

## GOVERNING RULES
[Paste relevant sections from gospel docs — the LAWS that
this code must obey]

## FULL CODEBASE
[Every file, with line numbers, complete — not excerpts]

### File: [filename] ([line count] lines)
```python
[full file contents]
```

### File: [next filename]...

## CURRENT STATE
- Last successful run: [timestamp]
- Known issues: [list from backlog]
- Recent changes: [git log excerpt]
- Quality metrics: [any available scores/measurements]

## WHAT WE NEED FROM YOU
Perform a forensic analysis of this codebase and its governing rules.
We are sharing your output with other leading LLMs (Gemini, ChatGPT,
Grok) for cross-analysis. Put your best work forward.

Specifically:
1. FUNCTIONALITY AUDIT: Does the code actually implement what the
   rules/laws say it should? Where are the gaps?
2. QUALITY AUDIT: What is amateur-level vs professional-level?
   What would a top-5 YouTube channel or Bloomberg-grade product
   do differently?
3. BUG DETECTION: Find bugs, race conditions, silent failures,
   edge cases that will break in production.
4. MISSING CAPABILITIES: What does 2026 cutting-edge technology
   make possible that we haven't implemented? What are we leaving
   on the table?
5. OPTIMIZATION: Where is the code inefficient, redundant, or
   over-engineered? What can be simplified?
6. HONEST ASSESSMENT: If our code and rules are sound and
   represent the best possible implementation, say so. Do not
   suggest changes for the sake of suggesting them. Only recommend
   changes that would materially improve the product.

Rate the overall implementation: [X/100]
Rate each subsystem individually.
Provide a prioritized action plan.
```

### Step 1.3: Deliver to PBX
Claude presents the Audit Package as a downloadable file and says:

"Here's your Cross-LLM Audit Package for [target]. Paste this into:
1. Gemini (Google AI Studio or gemini.google.com)
2. ChatGPT (chatgpt.com)
3. Grok (grok.com or x.com/i/grok)

Then paste all three outputs back to me for the consensus cycle."

---

## PHASE 2: FIRST ANALYSIS CYCLE (External LLMs)

PBX pastes the Audit Package into each LLM. Each LLM produces:
- Functionality audit
- Quality assessment with score
- Bugs found
- Missing capabilities
- Optimization opportunities
- Honest verdict
- Prioritized action plan

PBX collects all three outputs and pastes them back to Claude.

---

## PHASE 3: CONSENSUS COMPILATION (Claude does this)

### Step 3.1: Synthesize
Claude reads all three external LLM outputs and creates:

```markdown
# CROSS-LLM CONSENSUS REPORT — CYCLE 1
# Target: [feature]
# Models: Gemini, ChatGPT, Grok

## AGREEMENT (all 3 models agree):
[List items where all three identified the same issue or strength]

## MAJORITY (2 of 3 agree):
[Items where 2 models flagged something the third missed]

## UNIQUE INSIGHTS (only 1 model caught this):
[Novel observations from individual models — often the most valuable]

## CONFLICTS (models disagree):
[Where recommendations contradict each other — Claude provides tiebreaker]

## SCORES:
| Subsystem | Gemini | ChatGPT | Grok | Average | Claude Assessment |
|-----------|--------|---------|------|---------|-------------------|
| ...       | X/100  | X/100   | X/100| X/100   | X/100             |

## VALIDATED STRENGTHS (code is already excellent here):
[What all models agree is sound and should NOT be changed]

## CONSENSUS ACTION PLAN (prioritized):
| # | Action | Source | All Agree? | Impact | Effort |
|---|--------|--------|-----------|--------|--------|
| 1 | ...    | GPT+Gem| Yes       | High   | Low    |
| 2 | ...    | Grok   | No (unique)| Medium | Medium |
```

### Step 3.2: Deliver Consensus Report
Claude presents the Consensus Report to PBX and says:

"Here's the Cycle 1 Consensus. Want to run Cycle 2 (final audit)
or should I draft the execution session now?"

---

## PHASE 4: SECOND ANALYSIS CYCLE (Final Audit)

If PBX approves Cycle 2:

### Step 4.1: Generate the Cycle 2 Package
Claude creates a new document containing:
- The original Audit Package (code + rules)
- ALL outputs from Cycle 1 (Gemini, ChatGPT, Grok)
- Claude's Consensus Report from Cycle 1
- Specific questions for the final round:

```markdown
# FINAL AUDIT — CYCLE 2
# You previously analyzed this codebase. Now you have access to
# what the other LLMs said. Here is the full Cycle 1 output.

## YOUR PREVIOUS ANALYSIS:
[Their Cycle 1 output]

## OTHER MODELS' ANALYSES:
[All other outputs]

## CLAUDE'S CONSENSUS:
[The synthesis]

## FINAL ROUND INSTRUCTIONS:
1. Review the other models' findings. What did they catch that you missed?
2. Review their recommendations. Do you agree or disagree? Why?
3. Given the FULL picture, what is the DEFINITIVE action plan?
4. What is the single highest-leverage change that would most
   elevate this product?
5. Is there anything ALL models missed?
6. Final honest rating: [X/100]

This is the last round. Make it count.
```

### Step 4.2: PBX collects final outputs
PBX pastes Cycle 2 package into all three LLMs, collects outputs.

### Step 4.3: Final Consensus
Claude produces:

```markdown
# FINAL CROSS-LLM CONSENSUS — DEFINITIVE
# Target: [feature]
# Cycles: 2 (initial + final)

## DEFINITIVE ACTION PLAN:
[Ordered list of changes, validated by 2+ cycles of 3+ models]

## EXECUTION-READY CLAUDE CODE PROMPT:
[The actual prompt to fire into Claude Code on Ultron]
```

---

## PHASE 5: AUTO-EXECUTE (Claude Code on Ultron)

Claude automatically:
1. Takes the Definitive Action Plan
2. Drafts a comprehensive Claude Code prompt incorporating ALL consensus fixes
3. Fires it into the autonomous-build tmux session on Ultron
4. The prompt explicitly references which LLM suggested each change
5. Includes acceptance tests for each fix
6. Runs regression test after completion
7. Reports results to PBX

The prompt structure:
```
Read [relevant gospel docs].

This session implements the DEFINITIVE action plan from a 2-cycle,
4-model cross-LLM forensic audit. Every change below was validated
by multiple AI models and approved by PBX.

FIXES (in priority order):
1. [Fix] — Source: all models agree — Acceptance: [test]
2. [Fix] — Source: GPT+Gemini consensus — Acceptance: [test]
3. [Fix] — Source: Grok unique insight, validated Cycle 2 — Acceptance: [test]
...

VALIDATED (do NOT change these):
- [Feature X] — all models confirm this is sound
- [Feature Y] — consensus: already best-in-class

After all fixes: run regression_test.sh, git push, report results.
```

---

## RULES FOR THIS PROTOCOL

### What makes a good audit:
- COMPLETE code (never excerpts — models need full context)
- COMPLETE rules (paste the actual gospel doc sections)
- HONEST framing (don't bias the models toward any conclusion)
- COMPETITIVE framing ("other LLMs will see your output" motivates quality)

### What to filter OUT from external LLM outputs:
- Grok's tendency toward buzzword vaporware (quantum, neuralink, DAO tokens)
  → Keep only the actionable, implementable suggestions
- Generic "best practices" that don't apply to our specific architecture
- Suggestions that conflict with our gospel docs (our laws take precedence
  unless the LLM makes a compelling case to UPDATE the law)

### When to run this protocol:
- Before any major feature launch (video pipeline, Terminal, newsletter)
- After 3+ iterations of the same feature with diminishing returns
- When PBX says "I feel like we're missing something"
- Quarterly: full-stack audit of the entire platform

### When NOT to run this protocol:
- For quick bug fixes (just fix the bug)
- For purely cosmetic changes (just make the change)
- When the feature is too early-stage to benefit from scrutiny

---

## ESTIMATED TIME PER CYCLE

| Phase | Who | Time |
|-------|-----|------|
| Phase 1: Generate Audit Package | Claude | 5-10 min |
| Phase 2: External LLM analysis | PBX + 3 LLMs | 15-30 min |
| Phase 3: Consensus compilation | Claude | 5-10 min |
| Phase 4: Cycle 2 (optional) | PBX + 3 LLMs + Claude | 20-30 min |
| Phase 5: Auto-execute | Claude Code on Ultron | 1-3 hours |

**Total: ~1-2 hours for the analysis, then autonomous execution.**

---

## FUTURE AUTOMATION (when APIs available)

Eventually, this entire protocol can be automated:
1. Claude generates audit package
2. Claude calls Gemini API, ChatGPT API, Grok API simultaneously
3. Claude compiles consensus automatically
4. Claude runs Cycle 2 automatically
5. Claude fires execution session

PBX just says "cross-audit the video pipeline" and gets a coffee.
Comes back to a fully upgraded system with detailed report.

Prerequisites:
- Gemini API key (Google AI Studio — free tier available)
- ChatGPT API key (OpenAI — paid)
- Grok API key (xAI — when available)
- Automation script: utils/cross_llm_audit.py

---

*This protocol turns Protocol Pulse into a self-improving system.
Every major feature gets the combined intelligence of 4+ AI models
before shipping. No blind spots. No echo chambers. Just consensus-driven
engineering excellence.*
