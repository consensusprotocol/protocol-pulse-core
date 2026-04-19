---
name: cross-llm-audit
description: "Enforce the 2-cycle cross-LLM audit before any pipeline code change. Use when about to edit any file in video_pipeline_v3/, oracle/, services/, or core/; when a user requests a fix, patch, refactor, or optimization in the pipeline; when the session goal includes touching daily_producer, assembler, clip_selector, clip_extractor, tts_engine, render_narrator, render_social, render_intro_outro, render_clip, render_data, audio_master, transitions, lower_thirds, or any agent/skill definition. Do NOT use for website route edits, content writes, doc updates, or pure git ops."
metadata:
  version: 1.0.0
  author: PBX
  mcp-server: none
compatibility: "Ultron only. Requires Ollama at localhost:11434 with Qwen3; OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY in env; respects CUDA_VISIBLE_DEVICES GPU isolation."
---

# Cross-LLM Audit Skill

Authority: CROSS_LLM_AUDIT_LAW.md (repo root). This skill operationalizes that law.
Implementation: utils/cross_llm_audit.py

## Workflow Overview

```
1. Register feature in FEATURE_MAP (utils/cross_llm_audit.py)
2. Qwen pre-filter (local, $0) -- reads all files, identifies candidates
3. Cycle 1: parallel dispatch to Gemini + GPT-4o + Grok
   - Payload = Qwen's pre-filtered findings (max 120 lines)
   - Save results to docs/audits/{feature}/C1_*.md + c1.json
4. Synthesize Cycle 1 consensus (Claude)
5. Cycle 2: cross-examination -- each LLM sees what the others said
   - Save results to docs/audits/{feature}/C2_*.md + c2.json
6. Synthesize final consensus
7. Implement ONLY consensus fixes, priority order
8. Verify: regression_test.sh must show zero FAILs
```

See references/ for detailed sub-flows of each step.

## Decision Tree

```
Qwen confidence >= 0.85 AND zero external LLM disagreement?
  YES --> skip Cycle 2, implement directly
  NO  --> run full 2-cycle audit

Feature in HIGH_STAKES list?
  YES --> mandatory full 2-cycle, no shortcuts
  NO  --> if average Cycle 1 score > 85, may skip Cycle 2
```

## Consensus Definition

Consensus requires ALL THREE conditions:
1. Same file identified
2. Same function identified
3. Same root cause described

By Qwen PLUS at least 1 external LLM (Gemini, GPT-4o, or Grok).
Vague agreement ("could be improved") is NOT consensus.
"Similar area" is NOT consensus. Pin it to file:function:cause or reject.

## Priority Ordering (Critical-First)

| Priority | Score Range | Action |
|----------|------------|--------|
| CRITICAL | 0/10 | Fix immediately. Blocks everything. |
| HIGH | 1-4/10 | Fix before merge. No other work until resolved. |
| MEDIUM | 5-7/10 | Fix in second pass if clearly beneficial. |
| LOW | 8-9/10 | NEVER touch while any CRITICAL or HIGH exists. |

Focus on biggest score impact, not most interesting technical problem.

## Token Budget Gates

| Limit | Amount | Action |
|-------|--------|--------|
| Soft | $2 per improvement cycle | Log warning, continue |
| Hard | $5 per improvement cycle | Pause execution, send Telegram alert |

Qwen runs locally at $0/call. External LLMs receive only pre-filtered
payloads (max 120 lines), not full files. This keeps costs controlled.
See references/token-budget.md for Telegram integration and FEATURE_MAP registry.

## Anti-Hallucination Rule

Every audit prompt MUST include this exact instruction:
"Only report issues you can verify from the code/data provided. Do not speculate."

Audit findings without file:line citations are automatically rejected.
Grade dimensions with "assumed acceptable" notes = GRADING FAILURE, re-grade required.

## Running the Audit

```bash
# Via wrapper script
bash .claude/skills/cross-llm-audit/scripts/run-audit.sh FEATURE_NAME

# Direct invocation
cd ~/protocol_pulse && python3 utils/cross_llm_audit.py --feature FEATURE_NAME
```

## Audit Artifacts

All outputs saved to ~/protocol_pulse/docs/audits/{feature}/:
- AUDIT_PACKAGE.md -- code sent to LLMs
- C1_GEMINI.md, C1_GPT4O.md, C1_GROK.md -- Cycle 1 raw outputs
- C1_CONSENSUS.md -- Claude synthesis of Cycle 1
- C2_*.md -- Cycle 2 cross-examination outputs
- FINAL_CONSENSUS.md -- definitive action plan

## Reference Files

- references/qwen-first.md -- Qwen3 Ollama setup, pre-filter rules, 120-line payload cap
- references/cycle-1-parallel.md -- parallel dispatch, prompt template, payload size limits
- references/cycle-2-cross-exam.md -- cross-examination mechanics, contradiction resolution
- references/consensus-synthesis.md -- consensus rules, vague agreement rejection
- references/token-budget.md -- soft/hard limits, Telegram wiring, FEATURE_MAP registry
- references/test-triggers.md -- positive/negative trigger examples, verification procedure

## What This Skill Does NOT Do

- Does NOT replace CROSS_LLM_AUDIT_LAW.md (that remains the supreme authority)
- Does NOT auto-merge branches (PBX reviews PRs manually)
- Does NOT fire for website route edits, content writes, doc updates, or git-only ops
- Does NOT skip the audit for "small" changes -- every pipeline touch gets audited
