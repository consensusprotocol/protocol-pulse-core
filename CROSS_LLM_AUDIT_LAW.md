# PROTOCOL PULSE — CROSS-LLM AUDIT LAW
# Status: SUPREME LAW. Governs ALL feature builds. Cannot be overridden.
# Every Claude Code session reads this first. Every gospel references this.
# Created: 2026-03-09
#
# THE ONE-LINE VERSION:
# Build code -> fire cross_llm_audit.py (Gemini+GPT4o+Grok parallel, 2 cycles) -> second pass -> merge.
# NEVER skip. NEVER audit specs. NEVER merge without FINAL_CONSENSUS.md existing.
# NEVER paste Gemini keys in Claude.ai chat (Google scans and invalidates instantly).
# Add Gemini key via SSH to Ultron only: ssh ultron then edit ~/protocol_pulse/.env

# PROTOCOL PULSE — POST-BUILD LLM AUDIT PROTOCOL
# Status: GOSPEL. This runs AFTER every Claude Code feature session.
# The audit target is ACTUAL PRODUCTION CODE, not specs.
# Created: 2026-03-09
# Trigger: After every feature branch produces its first complete build

---

## THE RULE

**Build code first. Audit code second. Never audit specs.**

The sequence is:
1. Gospel doc defines what to build (done)
2. Claude Code session builds full working frontend + backend (one session per feature)
3. THIS PROTOCOL runs on the resulting code
4. Gemini + Grok + ChatGPT review the actual code
5. Claude synthesizes consensus
6. Second Claude Code pass incorporates improvements
7. Branch is PR-ready

This protocol is NOT optional. Every feature gets it before merging to main.

---

## PHASE 1: GENERATE THE CODE AUDIT PACKAGE

After a Claude Code session completes, Claude (in this chat) runs:

```bash
# Pull all new/modified files from the feature branch
cd ~/protocol_pulse
git diff main..feature/BRANCH_NAME --name-only
```

Then for each file, pull the full content via relay. Assemble into a single
audit package document with this structure:

---

### AUDIT PACKAGE TEMPLATE

```markdown
# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: [Feature Name]
# Branch: feature/[branch-name]
# Build date: [date]
# Auditors: You are [Gemini / Grok / ChatGPT] — other models will also review this
# Purpose: Pre-merge quality gate. Find everything wrong before this ships.

---

## WHAT THIS FEATURE DOES
[2-paragraph description of what was built, what problem it solves,
and what the user experience looks like end-to-end]

## THE LAWS THIS CODE MUST OBEY
[Paste the full LAWS section from the gospel doc]
The code MUST comply with every law above. Flag any violation.

## TECHNOLOGY CONSTRAINTS
- Python 3.12, Flask, SQLite (SQLAlchemy ORM)
- Ubuntu 24.04 on Ultron (2x RTX 4090, 93GB RAM)
- All CSS animations only — NO Three.js, no WebGL
- FFmpeg for video, ElevenLabs for TTS, Wav2Lip for lip sync (F1 only)
- The site serves ~1000 concurrent users at peak
- Every DB query must have an index on the sort/filter column

## THE CODE

### File: [filename] ([N] lines)
[complete file contents with line numbers]

### File: [next file]
[complete contents]

[...every new/modified file...]

## WHAT WE NEED FROM YOU

You are performing a forensic code review. Be brutally honest.
Other top AI models are reviewing this same code — we'll compare your outputs.
The developer who wrote this will not be present. There is no ego to protect.
Only quality matters.

### 1. CORRECTNESS AUDIT
Does the code do what it claims to do?
- Walk through the main user flow step by step
- Find logic errors, off-by-one errors, wrong variable names
- Find places where the code will silently fail without error
- Find race conditions (multiple requests hitting same resource)
- Find N+1 query problems (DB queries inside loops)

### 2. LAW COMPLIANCE AUDIT
Check every LAW from the governing spec above.
For each law: COMPLIANT / VIOLATION / PARTIALLY COMPLIANT + explanation.
Be specific — cite line numbers.

### 3. SECURITY AUDIT
- SQL injection vectors (even with ORM — check raw queries)
- Authentication bypasses
- Rate limiting gaps (can a single user exhaust API limits?)
- Secret exposure (are any API keys, tokens, or passwords in the code?)
- Input validation gaps (user-supplied data that hits DB or shell)

### 4. FRONTEND QUALITY AUDIT
- Does the UI match the spec layout?
- Are there any hardcoded values that should be dynamic?
- Will it break on mobile viewport?
- Are there any JS errors that would prevent the page from functioning?
- Is the loading/error/empty state handled for every async operation?

### 5. BACKEND QUALITY AUDIT
- Are all DB operations wrapped in try/except with proper rollback?
- Are all external API calls (ElevenLabs, HeyGen, EDGAR, Bitnodes) 
  handled with timeout, retry, and graceful degradation?
- Does the cron job handle failure without crashing the service?
- Are there memory leaks (large objects created per request, not freed)?

### 6. WORLD-CLASS GAP ANALYSIS
This code needs to be the best Bitcoin intelligence product on the internet.
What would Bloomberg Terminal, Coinbase, or a top-5 crypto media product do
differently here? What's missing that would make this genuinely impressive?
Do not pad this section — only include changes that would materially elevate
the product. If the code is already excellent in a given area, say so.

### 7. SCORING
Rate each subsystem 0-100:
- Backend logic: X/100
- Frontend/UI: X/100  
- Error handling: X/100
- Security: X/100
- Performance: X/100
- Law compliance: X/100
- Overall: X/100

### 8. PRIORITY ACTION PLAN
List every fix, improvement, and addition — sorted by impact:
| Priority | Change | File:Line | Reason | Impact |
|----------|--------|-----------|--------|--------|
| P0 CRITICAL | ... | ... | Will break in prod | Fix immediately |
| P1 HIGH | ... | ... | Degrades quality | Fix before merge |
| P2 MEDIUM | ... | ... | Enhancement | Fix in second pass |
| P3 LOW | ... | ... | Polish | Nice to have |

### 9. ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be?
```

---

## PHASE 2: DISTRIBUTE TO 3 LLMs

PBX pastes the full audit package into:
1. **Gemini 2.5 Pro** (Google AI Studio — free) — strongest at architecture
2. **Grok** (grok.com) — strongest at API verification + current info
3. **ChatGPT o3** (chatgpt.com) — strongest at frontend + UX critique

Each model gets the IDENTICAL package. Do not modify between models.
Tell them nothing about what the other models said until Phase 3.

---

## PHASE 3: CONSENSUS SYNTHESIS (Claude does this)

PBX pastes all 3 outputs back. Claude produces:

```markdown
# CONSENSUS REPORT — [Feature Name]
# Models: Gemini 2.5 Pro + Grok + ChatGPT o3

## UNANIMOUS FINDINGS (all 3 agree — highest confidence)
[Items every model flagged — fix these unconditionally]

## MAJORITY FINDINGS (2 of 3 agree)
[Fix these unless there's a strong reason not to]

## UNIQUE INSIGHTS (only 1 model caught this)
[Often the most valuable — evaluate case by case]

## SCORE CONSENSUS
| Subsystem | Gemini | Grok | GPT | Average |
|-----------|--------|------|-----|---------|
| ...       |  X/100 | X/100| X/100| X/100 |

## CONFLICTS (models disagree)
[Claude provides tiebreaker with reasoning]

## VALIDATED (all models agree this is already excellent — do NOT change)
[These are strengths to preserve]

## FINAL ACTION PLAN (sorted by consensus priority)
[Only includes items with 2+ model agreement, plus unique high-impact items]
```

---

## PHASE 4: SECOND CLAUDE CODE PASS

Claude drafts the execution prompt for the second build pass:

```
Read ~/protocol_pulse/docs/gospels/[FEATURE]_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/[FEATURE]_CONSENSUS.md.

This is the SECOND PASS for feature [X].
The first build was reviewed by 3 independent AI models.
Below is the consensus action plan. Implement every P0 and P1 item.
For P2 items, use your judgment — only implement if it clearly
improves the product without adding complexity.

CONSENSUS ACTION PLAN:
[paste the prioritized list]

VALIDATED (do not touch these — all models confirmed they're excellent):
[paste the validated list]

After implementing: run regression_test.sh — zero FAILs required.
git add -A && git commit -m "feat([feature]): post-audit second pass — [N] consensus improvements"
git push origin feature/[branch]
```

---

## PHASE 5: PR REVIEW + MERGE

After second pass:
- Claude reviews the final diff one more time
- If clean: `git merge feature/[branch] → main`
- If issues remain: targeted third pass (rare)

---

## AUDIT TRACKING

Every completed audit gets stored at:
`~/protocol_pulse/docs/audits/[FEATURE]_AUDIT_PACKAGE.md` — the package sent to LLMs
`~/protocol_pulse/docs/audits/[FEATURE]_GEMINI.md` — Gemini's raw response
`~/protocol_pulse/docs/audits/[FEATURE]_GROK.md` — Grok's raw response  
`~/protocol_pulse/docs/audits/[FEATURE]_GPT.md` — ChatGPT's raw response
`~/protocol_pulse/docs/audits/[FEATURE]_CONSENSUS.md` — Claude's synthesis

This creates a permanent audit trail for every feature.

---

## ACCELERATED PATH (when you need speed)

For lower-stakes features (B1 Newsletter, F5 Node Watch):
- Single LLM audit (Gemini only) instead of 3
- Skip Phase 4 second pass if score > 85/100 across the board
- Still store the audit doc

For high-stakes features (F1 Avatar, V30 Terminal API, V22 Pipeline):
- Full 3-model audit, mandatory
- Phase 4 second pass always runs
- No shortcuts

---

## THE GOLDEN RULE

**A feature is not "done" when Claude Code finishes.**
**A feature is done when 2+ external models have reviewed the code**
**and the consensus improvements have been implemented.**

This is what separates a rushed internal tool from a world-class product.
