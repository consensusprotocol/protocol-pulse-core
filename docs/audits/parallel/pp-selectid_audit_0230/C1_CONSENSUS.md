# Audit 0230 (pp-ingest R12: probe_due claims the slot), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no finding); qwen3.8-27b SHIP yes with conditions; glm-5.3-flash SHIP yes with
conditions. No critical, no high.

- Condition, qwen and glm: pp-ingest should pass a non-empty `who`. MET by pp-ingest's own message (02:3x ET):
  - its watcher loads the module once at start and passes who="pp-ingest probe" from the restart that takes this
    commit (a two-line change, audited on its side);
  - until then the claim works with who="" (the argument is optional).
- Condition, glm: say what anchors the next due time. IMPLEMENTED in probe_due's docstring:
  - the later stamp decides;
  - probe_result re-stamps last_probe_utc when the probe reports (answer-anchored);
  - a claimer that never reports leaves its claim's stamp (claim-anchored).
  The behaviour is unchanged.
