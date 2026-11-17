# Heimdall audit

**Question:** Review this diff. ORCHESTRATOR RULING 138 (3) (11:40 ET Nov 17), verbatim: "In the Telegram note for a flagged package, each flag is one plain sentence PBX can judge in five seconds (what the checker doubted, about which clip), no codes." RULING 137 (2): "HARD: words, speaker credit, cut mid-word, crop through a face or burned text, layout that cannot render, runtime, attestation and the review-path delivery; SOFT: everything else, flagged in the note." RULING 136: a SOFT gate "scores and FLAGS, it does not refuse". The diff (1) rewords every render-side flag as one sentence naming the version and, where the gate report says which, the clip; (2) makes V1's credits row HARD again (speaker credit): a V1 that did not pass holds when ANY model did not affirm the credits row (said no, left it out, or gave no answer); V1's other rows stay SOFT flags; (3) makes a SOFT row's MALFORMED execution evidence a blocker (the attestation is HARD); a SOFT row that measured nothing (well-formed, 0 samples or SKIPPED) is a flag "did not measure anything", never a pass.

FACTS (unchanged code, not in the diff):
- GATE_REPORT.json (bound by digest at authorise) holds rows[fmt], evidence[fmt][row] = {"executed": verdict != "SKIPPED", "samples": int} written by run_fresh's put(), notes, and per-gate detail: "G16" a list of {"segment", "errors", "in": {"pass"}, "out": {"pass"}}; "G19" {fmt: [{"segment", "pass"}]}; "G14_16x9" / "G14_9x16" lists of samples {"label", "status"}; "L-c" {fmt: {"g3c_failed_edges": [[segment, side], ...]}}; "G9" {fmt: {"gate": {"luma_ok", "audio_ok"}}}; "V1" {fmt: {"ok", "error"?, "per_model": {model: {"rows": {row: {"answer", "why", "ok"}}}}, "boundaries"?, "letterbox_per_shot"?}}. G8's production table is NOT in the report.
- edl.json (bound): "hook" {"channel", ...}, "clips" [{"index": 1..n, "channel", ...}]; segment labels are "hook" and "clip_01".."clip_NN".
- blockers(fmt, rows, evidence) feeds attest() and authorise() (and run_fresh's run verdict); authorise() is the last check before telegram.deliver_run sends anything; it re-derives the verdict and the flags and compares them with ATTESTATION.json.
- edl_rules' reasons name segments as "hook", "clip_02", "clip_2" or "clip 2"; ruling 37's R1 reason contains "non-hook clip".

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

CHECKS:
H1. Can a HARD row, V1's credits row (a model said no / left it out / no V1 answer), or malformed evidence on any row ever reach PBX (attest ALL_PASS or PASS_WITH_FLAGS, or authorise ok)?
H2. Is a SOFT row that failed always said as a flag, and one that measured nothing always said as "did not measure anything" (never silent, never a pass, never a doubt it did not have)?
H3. Are the flags attest writes exactly the flags authorise re-derives from the same bound files (the report, the EDL, the pin)? Can they differ for the same bytes?
H4. Does every flag name the right clip (or "a clip" when the report names none), the right version ("In the 16:9 version", "In both versions"), and carry no code (no row ids, rule ids, law ids, "ruling", snake_case)?
H5. Can any malformed report detail, EDL or pin record crash attest, authorise, say(), the note or the validate stage?
H6. Does anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0018
## Consensus findings (majority of panel agrees)
- **[high] pipeline/release_auth.py:159** flags() does not filter out hard rows, so hard rows that fail are incorrectly reported as flags.
  - evidence: `def flags(fmt, rows, evidence, report=None, edl=None):
    """RULINGS 136 / 137: {row: plain words} for one format's SOFT rows that did not pass, or ran without execution
    evidence (never measured `
  - fix: Add a check to only process rows that are in the soft set: e.g., soft = INVENTORY[fmt] & soft; for k, v in rows.items(): if k not in soft: continue; ...
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
