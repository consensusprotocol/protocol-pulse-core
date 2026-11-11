# Batch 7 (V1 per-cut check + channel list, reply brace repair, G19 EDGE SHOTS, batch-6 consensus fixes) — dispositions

Audited: the working-tree diff on top of staged batch 6 (pipeline/). Cross-LLM GPT-4o + Gemini (Grok blocked
by the xAI ceiling); Heimdall deepseek + qwen27b, one chunk per file.

## Implemented
- Heimdall stand_alone [high, consensus]: a non-Bitcoin story whose affected object gave no content words
  fell back to Bitcoin/BTC, so a Bitcoin aside could pass as its clip. Now: the affected object's words, else
  the headline's, else an EMPTY set (no segment names the subject: fail closed). Tests: headline words used;
  'AI' gives the empty set; a Bitcoin aside fails it.
- Heimdall verify_pack [medium, consensus]: the recomputed panel verdict (next-shot line excluded) was
  vacuously true with no models; now `bool(per) and ...`.
- Heimdall test_edge_shots [medium, consensus]: the run-6 must-fail now also requires a non-empty list of
  foreign-shot times.
- Cross-LLM P1/P2: G19 returns False overall when a record is missing (asserted); an unexpected exception in
  a replay is a HOLD with its reason and VERDICT.txt (tested); two missing final braces are closed and a
  partial reply still fails the verdict (tested); a hard link that fails (another device) falls back to a
  copy.

## Rejected, with evidence
- Heimdall run_fresh [high] "G19 is not in run_gates_overall, so a run can pass with a G19 failure": the
  verdict is verdict_for(rows) and rows[fmt]["G19_edge_shots"] is a row (FAIL -> HOLD); run_gates_overall is
  the legacy run_gates (G1-G15) summary and excludes G16/G17/G18 the same way.
- Cross-LLM UNIQUE-1/2 (two ffmpeg grabs per cut; a test variable name): performance / cosmetic, not changed.
- Cross-LLM P2-6 "cross-device copies in CI": the replay copy lives next to the run (same filesystem); the
  link failure now falls back to a copy anyway.
