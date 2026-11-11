# Heimdall audit

**Question:** Second pass on the batch-8c consensus finding (a deferred valley edge was recorded pass: True). DEC-10 d: an edge the sentence-law cutter placed at its envelope minimum (cuts_final valley_in / valley_out) is rejected only by (i)-(iii); stage_cut now records it pass: None with its M19 reading and deferred_to G16, which is the very next stage (legal range + neighbour_clear with the cut's own fades, HOLD before any render) and recomputes from cuts_final.json + edl.json (it never reads CUT_ACCEPTANCE.json). Every non-valley edge must have a truthy cut_accept pass (missing = fail). Report only real defects you can quote.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0109
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/run_fresh.py:432** The code unconditionally defers every valley edge, even if `check_cut_acoustics` already passed it or failed it for reasons other than (i)-(iii). DEC-10 d only permits deferral for an edge rejected only by (i)-(iii).
  - evidence: `if c.get(f"valley_{s}"):
    d[s] = {"pass": None, "m19": d[s],
            "deferred_to": "G16 neighbour_clear (DEC-10 c-ii)"}`
  - fix: Only overwrite `d[s]` when the edge was actually rejected by (i)-(iii), e.g. check that the original `d[s].get("pass")` is false and that the failure reason is one of (i)-(iii); otherwise preserve the original pass value.
  - raised by deepseek:F2; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [critical] A deferred valley edge is still recorded as pass True at the edge level. The new `ok` expression short-circuits any valley edge to True, and `rec["pass"]` is then set to that `ok`, so the consensus finding (deferred valley edge recorded pass: True) is not fixed. (agree: 0)

## Added in cross-examination (not voted on)
- none
