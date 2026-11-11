# Heimdall audit

**Question:** DEC-10 d (orchestrator 2026-11-11: 'Where the inter-sentence gap is short, cut at the envelope minimum with a 2-frame audio fade rather than rejecting the clip. A clip is rejected for edges only if (i) 85 % edge-word duration, (ii) no audible part of the neighbouring word, or (iii) sentence-complete locked words cannot be met.') The Nov 10 recut HELD in run_fresh.stage_cut because cut_accept's M19-era timing checks (cut_out needs a genuine pause with >= 60 ms ahead; cut_in needs a boundary dip in the prior 100 ms) rejected the two edges the sentence-law cutter placed at the envelope minimum (flagged valley_in / valley_out in cuts_final.json). Change: for an edge flagged valley, stage_cut keeps the M19 reading in CUT_ACCEPTANCE.json but leaves the verdict to the very next stage, G16 (stage_sentence_law: legal range + neighbour_clear with the cut's own fades; a failure HOLDs before anything renders). Every other edge and every human-pinned table are unchanged. Find real defects only: can a valley edge now pass without the c-ii check, can a non-valley edge skip cut_accept, can the flag be set by anything other than the cutter, does any stage between stage_cut and G16 consume the cut? (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0079
## Consensus findings (majority of panel agrees)
- **[high] pipeline/run_fresh.py:433** The code sets the top-level pass to True for a valley edge, so stage_cut accepts the edge without the c-ii check. The verdict is not left to G16; it is pre-approved. If G16 consumes CUT_ACCEPTANCE.json and trusts the pass field, the valley edge can pass without neighbour_clear. Even if G16 re-checks, pass: True is misleading and violates the stated design.
  - evidence: `d[s] = {"pass": True, "m19": d[s], "judged_by": "G16 neighbour_clear (DEC-10 c-ii)"}`
  - fix: Do not set pass: True. Use a deferred/pending status, e.g. d[s] = {"pass": None, "m19": d[s], "judged_by": "G16 neighbour_clear (DEC-10 c-ii)"}, and adjust ok to treat None as not a failure (e.g. ok = all(d[s]["pass"] is not False for s in ("in","out"))), so G16 must resolve the pending verdict.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
