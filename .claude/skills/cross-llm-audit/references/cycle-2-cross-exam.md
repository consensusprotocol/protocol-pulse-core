# Cycle 2: Cross-Examination

Authority: CROSS_LLM_AUDIT_LAW.md Phase 3-4
Implementation: utils/cross_llm_audit.py build_cycle2_prompt()

## Purpose

In Cycle 2, each LLM sees what the OTHER two models said in Cycle 1.
This creates adversarial review -- models can challenge, validate,
or refine each other's findings.

## When Cycle 2 Runs

Cycle 2 is MANDATORY when:
- Feature is in HIGH_STAKES list (f1-avatar-oracle, v30-terminal-api, etc.)
- Average Cycle 1 score across all models is below 85/100

Cycle 2 is SKIPPED when:
- Feature is NOT high-stakes AND average score > 85
- Qwen confidence >= 0.85 AND zero external disagreement

## Cross-Exam Prompt Structure

Each model receives:
1. Their OWN Cycle 1 output ("what you said before")
2. The OTHER two models' Cycle 1 outputs (truncated to 5000 chars each)
3. Claude's Cycle 1 consensus synthesis (truncated to 3000 chars)
4. The original code (same as Cycle 1)
5. Cycle 2 instructions: validate, challenge, refine

## Cycle 2 Instructions

Models are asked to:
1. VALIDATE -- which of the other models' findings do you agree with?
2. CHALLENGE -- which findings do you disagree with and why?
3. REFINE -- update your own assessment based on what others found
4. NEW ISSUES -- did reading others' analyses reveal issues you missed?
5. PRIORITY RERANK -- given all perspectives, reorder the action plan

## Contradiction Resolution

When models contradict each other:
1. Claude synthesis identifies the specific contradiction
2. Claude provides tiebreaker with reasoning
3. If 2 of 3 models agree, majority wins
4. If all 3 disagree, Claude makes the call with justification
5. Unresolved conflicts are logged for PBX manual review

## When to Escalate

Escalate to PBX (Telegram alert + pause) when:
- All 3 models find CRITICAL (0/10) issues in the same area
- Token budget exceeds $5 hard limit
- 2+ models flag a security vulnerability
- Consensus cannot be reached on a P0 item after both cycles

## Winner Determination

After Cycle 2, Claude determines which model provided the best analysis:
- Accuracy: did their Cycle 1 findings hold up in Cycle 2?
- Depth: did they find issues others missed?
- Actionability: were recommendations specific and implementable?
- Completeness: did they cover all sections?

The winner is noted in the final consensus report.
This tracks model quality over time for future audit calibration.

## Output Storage

- C2_GEMINI.md, C2_GPT4O.md, C2_GROK.md
- FINAL_CONSENSUS.md (includes winner + definitive action plan)
- Second-pass prompt ready to fire into Claude Code
