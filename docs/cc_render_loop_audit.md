Read ~/protocol_pulse/docs/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md fully — this is the spec being audited.
Read ~/protocol_pulse/utils/cross_llm_audit.py fully — this is the audit engine you will use.
Read ~/protocol_pulse/overnight_render_loop.py lines 1-100 and lines 340-380 — understand the integration point.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RENDER IMPROVEMENT LOOP — CROSS-LLM ARCHITECTURE AUDIT
Goal: audit the GOSPEL spec before a single line of code is written.
Find every flaw, gap, failure mode, and token cost risk. Be brutal.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — REGISTER FEATURE IN FEATURE_MAP
Add to utils/cross_llm_audit.py FEATURE_MAP:
  "render-improvement-loop": ("RENDER_IMPROVEMENT_LOOP_GOSPEL.md", "main"),

Add to EXPLICIT_FILES:
  "render-improvement-loop": [
      "overnight_render_loop.py",
      "utils/cross_llm_audit.py",
      "video_pipeline_v3/assembler.py",
      "video_pipeline_v3/clip_extractor.py",
  ]

STEP 2 — BUILD THE AUDIT PROMPT
Before firing cross_llm_audit.py, build a custom audit prompt that asks
each model to answer these 8 questions independently and brutally:

Q1 — INTEGRATION RISK: The loop integrates with overnight_render_loop.py
via flag files (/tmp/render_fix_complete_iterN). What are the failure modes?
Race conditions? Flag file left over from previous iteration? Loop crash
that never writes the flag, blocking overnight loop forever?

Q2 — QWEN RELIABILITY: The loop assumes Qwen3:30b is running on Ollama
at localhost:11434. What happens if Ollama is down, model not loaded,
or Qwen returns malformed JSON? Does the loop degrade gracefully or
cascade-fail and kill the render cycle?

Q3 — CC SESSION DETECTION: The loop waits for CC slot by polling tmux.
But tmux session names from previous crashed sessions may still exist
as zombies. How does the loop distinguish a live CC session from a
dead one? What is the exact tmux command that proves a session is
actively running CC vs just existing as a shell?

Q4 — TOKEN COST REALITY: The gospel claims $2 soft limit per cycle.
Given the 4-6 failing dimensions typically seen (freeze, avatar, true_peak,
visual_polish, etc.), each requiring Qwen + 2 external LLM calls with
~2000 token payloads, what is the realistic per-cycle cost?
Is the $2 limit achievable or is it optimistic?

Q5 — DIMENSION_MAP COMPLETENESS: Review the DIMENSION_MAP in the gospel.
Which Gemini grade dimensions are MISSING from the map?
What happens when a new dimension appears in a grade that has no mapping?
Does the loop handle unknown dimensions gracefully?

Q6 — OVERNIGHT LOOP COUPLING: The minimal change to overnight_render_loop.py
is described as "check for flag file, wait up to 60 min". But overnight_render_loop.py
has a 14400s render timeout. If the improvement loop takes 90 min
(CC session can run long), does this blow the timeout? How should
timing be coordinated to avoid killing the render cycle mid-improvement?

Q7 — CONSENSUS FAILURE HANDLING: When LLMs disagree, the loop sends
a Telegram alert and skips the dimension. But if the 3 most critical
dimensions (avatar, freeze, visual_polish) all produce disagreement,
the loop commits nothing and the next iteration is identical to the last.
What mechanism prevents infinite identical render loops with no improvement?

Q8 — IMPLEMENTATION CORRECTNESS: The loop will write fix specs and fire CC.
But CC is Opus 4.6 — it reads the spec and uses its own judgment.
What guardrails ensure CC implements ONLY the exact patch and does not
refactor surrounding code, change function signatures, or introduce
new dependencies that break other pipeline stages? The spec says
"Do not refactor" but CC sometimes does anyway.

STEP 3 — FIRE CYCLE 1 AUDIT
Register the feature, then fire:
  cd ~/protocol_pulse
  python3 utils/cross_llm_audit.py --feature render-improvement-loop

Save cycle 1 output to:
  docs/audits/render_loop_audit_c1.json

STEP 4 — SYNTHESIZE CYCLE 1
Read all three model outputs. For each of the 8 questions:
  - What did Gemini say?
  - What did GPT-4o say?
  - What did Grok say?
  - What is the consensus finding?
  - What must be changed in the gospel before build?

Write synthesis to: docs/audits/render_loop_audit_c1_synthesis.md

STEP 5 — FIRE CYCLE 2
  python3 utils/cross_llm_audit.py --feature render-improvement-loop --cycle 2 --cycle1-results docs/audits/render_loop_audit_c1.json

Models now cross-examine each other's findings.
Save cycle 2 output to: docs/audits/render_loop_audit_c2.json

STEP 6 — FINAL SYNTHESIS + GOSPEL PATCH
Read cycle 2. Identify final consensus on every issue.
Update RENDER_IMPROVEMENT_LOOP_GOSPEL.md with:
  - Every failure mode identified and its mitigation
  - Revised token cost estimate
  - Missing DIMENSION_MAP entries added
  - Flag file race condition fix
  - CC guardrail language sharpened
  - Qwen fallback chain defined

Write patch to gospel in place. Do not create new file.

STEP 7 — WRITE BUILD SPEC
After gospel is patched by audit consensus, write the CC build spec:
  docs/cc_render_improvement_loop_build.md

This spec instructs CC to build render_improvement_loop.py from the
audited gospel. It will be fired as a SEPARATE CC session after this
audit session completes.

Format of build spec:
  - Read the gospel
  - Build render_improvement_loop.py to exact spec
  - Integrate minimally with overnight_render_loop.py (flag file only)
  - Test: simulate a grade JSON with 3 failing dims, verify loop runs
  - Regression: 0 FAILs
  - git commit -m "feat(pipeline): render_improvement_loop.py — autonomous grade-driven fix loop"
  - git push

DO NOT BUILD render_improvement_loop.py IN THIS SESSION.
This session's job is: audit → patch gospel → write build spec.
The build fires next.

STEP 8 — COMMIT AUDIT ARTIFACTS
git add docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md
git add docs/audits/render_loop_audit_c1.json
git add docs/audits/render_loop_audit_c2.json
git add docs/audits/render_loop_audit_c1_synthesis.md
git add utils/cross_llm_audit.py
git commit -m "audit(render-loop): cross-LLM architecture audit complete — gospel v1.1 patched"
git push
