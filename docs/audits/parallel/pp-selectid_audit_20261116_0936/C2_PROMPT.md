# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0936
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 64 s finish=stop usage in 6023 / out 881 usd_reported=0.000296 usd~0.031 (upper-bound price)

The code change is a minimal string update to align the `STAND_ALONE_NOTE` constant with RULING 120.

1.  **Ruling Compliance**: The string in `pipeline/package_pin.py` is updated from `"stand-alone affirmed on the calibrated floor (3.0)"` to `"a clip passed stand-alone on the calibrated bar"`. This matches the verbatim requirement of RULING 120 (no leading capital, no trailing full stop).
2.  **Scope**: The diff is limited strictly to this constant and the corresponding assertions in `tests/package/test_medley.py`. No logic, thresholds (the 3.0 floor remains), or seals were modified.
3.  **Test Coverage**: `TestRuling119StandAloneFloor` is updated to ensure the new string is correctly applied to the `moments_package` and the resulting pin.

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 48 s finish=stop usage in 5673 / out 1937 usd_reported=0.000414 usd~0.046 (upper-bound price)

# AUDIT: pp-selectid-20261116_0936 — C1_STEP.diff

## Scope reviewed
Three changed lines: one constant (`STAND_ALONE_NOTE` in `pipeline/package_pin.py`) and two expected-string assertions in `tests/package/test_medley.py`. All surrounding context lines are unchanged context, not edits.

## Check (1) — the note is exactly the ruling's words
RULING 120 quotes the line verbatim as `"a clip passed stand-alone on the calibrated bar"` and specifies "no capital, no full stop, as quoted". The new constant (diff line 10) is byte-for-byte that string: lowercase `a`, hyphenated `stand-alone`, no terminal punctuation. The comment correctly cites RULING 120. **Pass.**

## Check (2) — nothing else changed
- `STAND_ALONE_FLOOR` (3.0), `STAND_ALONE_FLOOR_SCORER`, `STAND_ALONE_FLOOR_DIGEST` are untouched context lines (5–8).
- The explanatory comment block (lines 11–13) is untouched.
- In the test file, only the two expected-string literals changed (lines 22–23 and 29–30). The structural assertions — `floor == 3.0`, `segments == [1]`, `ruling == "119"`, `assertIsNone` on the unmarked case, and `package_sha256` equality between plain and marked pins (confirming the note lives outside the seal) — are unchanged.
- No threshold, digest, verdict field, or gate logic is touched. This satisfies M1 (smallest diff) and does not alter any gate's accept/reject behaviour (LAW 20 intact — this is a label, not a threshold).
- The description's claim that `telegram.STAND_ALONE_BAR_NOTE` is updated in its own audited delta is consistent: since the telegram exact-shape check compares the mark's note against its own constant, any divergence would fail closed at runtime rather than silently pass — acceptable, and outside this diff's scope.

**Pass.**

## Check (3) — the tests pin it
Both places where the note's exact text is asserted (`TestRuling119StandAloneFloor`'s tuple equality and the `to_pin` marked-package assertion) were updated to the new string. A future edit to the constant that drifts from the ruling's words will fail both assertions. The reported control run (262 passed) and 10/10 mutation kills corroborate. **Pass.**

## Findings

- **[P3]** The diff alone cannot prove that no *other* file still references the retired string `"stand-alone affirmed on the calibrated floor (3.0)"` (e.g., a doc, a ledger template, or a stale test outside `test_medley.py`). The package description asserts the telegram side is handled in a separate audited delta, but a repo-wide grep for the old string should be part of the merge gate so a leftover reference cannot print a stale line. Not a defect in this diff; a verification step.

- **[P3]** LAW 22 (v2f byte-identical re-render): the note is outside the seal and `package_sha256` is asserted unchanged, so the frozen reference is unaffected — but this rests on the note never being an input to render bytes. Worth one line in `regression.sh` output confirming step for v2f still passes with this delta applied, since the diff itself contains no such evidence.

- **[P3]** Cosmetic: the new comment `# RULING 120: the mark, the Telegram note's line` is slightly telegraphic compared with the surrounding comment style; harmless.

No P0 or P1 findings. The change is exactly the ruling's string, exactly three lines, correctly pinned by tests, and touches no gate, threshold, digest, or seal.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 5745 / out 3332 usd_reported=0.002643 usd~0.067 (upper-bound price)

I have reviewed the provided code delta against the governing laws and the specific instructions for RULING 120.

### Analysis

1.  **RULING 120 Compliance (The Note Text)**:
    *   **Requirement**: The note must be exactly "a clip passed stand-alone on the calibrated bar" (no capital, no full stop).
    *   **Code**: `STAND_ALONE_NOTE = "a clip passed stand-alone on the calibrated bar"` in `pipeline/package_pin.py`.
    *   **Test**: `tests/package/test_medley.py` asserts `m["note"]` equals `"a clip passed stand-alone on the calibrated bar"`.
    *   **Verdict**: Compliant. The text matches the ruling verbatim.

2.  **Scope of Change (Smallest Diff / Law 20)**:
    *   **Requirement**: Only the note constant and its corresponding test expectations should change. The floor (3.0), scorer digests, and logic must remain unchanged.
    *   **Code**: The diff shows changes only to the `STAND_ALONE_NOTE` string constant and two string assertions in the test file.
    *   **Verdict**: Compliant. No logic, thresholds, or hashes were modified.

3.  **Governing Laws Check**:
    *   **LAW 20 / M2**: Gate thresholds are constants. The floor `3.0` is unchanged. The note is metadata, not a gate threshold.
    *   **M12 FAIL CLOSED**: Not applicable to this specific string change, as it doesn't alter data processing or failure modes.
    *   **L-k ONE CANONICAL FORM**: The note is a static string for display/Telegram, not a text comparison for speech/word matching. No violation.
    *   **L-j RELEASE IS AUTHORISED**: The change is in `package_pin.py` which is part of the pinning/attestation logic. The test `test_medley.py` verifies the pin structure. Since the `package_sha256` is asserted to be identical to the plain pin (line 31 of diff: `self.assertEqual(marked["package_sha256"], plain["package_sha256"])`), and the note is explicitly stated to be "outside the seal" in the context description, this change does not invalidate existing attestations or break the hash chain of the sealed content.

4.  **Potential Issues**:
    *   **Telegram Integration**: The context states: "the integrator's Telegram note prints that note... reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`... changed in its own audited delta."
    *   **Risk**: If `telegram.STAND_ALONE_BAR_NOTE` is *not* updated in the same commit/branch to match `package_pin.STAND_ALONE_NOTE`, the "exact-shape check" mentioned in the context ("so the two cannot differ") will fail at runtime or in integration tests.
    *   **Audit Scope**: The provided diff *only* contains `pipeline/package_pin.py` and `tests/package/test_medley.py`. It does *not* contain `pipeline/telegram.py` or `tests/telegram/test_*.py`.
    *   **Conclusion**: The prompt states "Files: pipeline/package_pin.py (one constant), tests/package/test_medley.py (two expected strings)." and "changed in its own audited delta." This implies the Telegram change is handled elsewhere or in a separate file not shown here. However, as an auditor of *this* package, I must flag that if the Telegram constant is not synchronized, the system will break. But since the prompt explicitly says the Telegram change is "in its own audited delta" and this package is just the "DELTA of the stand-alone floor... that RULING 120 makes," I will assume the synchronization is handled by the integrator's separate change.
    *   **Wait**: The prompt says "You are one of... [AI models]... review this." and "THE CODE (every new and modified file)". If `telegram.py` was modified, it should be here. If it wasn't modified, then the "exact-shape check" relies on the two constants being equal. If `package_pin.STAND_ALONE_NOTE` changes but `telegram.STAND_ALONE_BAR_NOTE` does not, the check fails.
    *   **Re-reading Context**: "the integrator's Telegram note prints that note... reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`... changed in its own audited delta." This phrasing suggests the Telegram constant *is* changed, but perhaps in a different file/commit that is part of the "integrator's" work, while this "pp-selectid" branch only handles the pin.
    *   **However**, the "Governing Laws" and "What this feature does" section implies a holistic view. If I am auditing the *merge* of this feature, and the Telegram constant is not updated in *this* diff, but the code relies on them being identical, this is a **P1** risk if the other change is not guaranteed to land simultaneously.
    *   **But**, the prompt explicitly lists the files in this diff: `pipeline/package_pin.py` and `tests/package/test_medley.py`. It does *not* list `pipeline/telegram.py`.
    *   **Assumption**: The "integrator's delta" is a separate, already-audited or concurrent change. The prompt asks me to check: "(1) the note is exactly the ruling's words; (2) nothing else changed; (3) the tests p

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_0936 (RULING 120's note: the delta of the stand-alone floor)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0034 of Heimdall, not capped.

A CORRECTION TO THE QUESTION: it gave a typed time for the integrator's agreement ("09:47 ET"), which was wrong (this audit
began at 09:36 ET by the clock); QUESTION.txt now says "after ruling 120". No bearing on the code.

qwen's one P1, "telegram.py's STAND_ALONE_BAR_NOTE is not in this diff; if the two texts differ the integrator's check
refuses the mark": TRUE THAT THE TWO MUST MATCH, and not a defect of this diff: that constant lives in the integrator's tree
(its half, its own audited delta, landed after this one in the agreed order). qwen itself notes "If the Telegram change is
its own audited delta, this code is correct in isolation". AT LANDING the match is CHECKED, not assumed: before this half
lands, the integrator's branch's telegram.STAND_ALONE_BAR_NOTE is read (read only) and must equal package_pin.STAND_ALONE_NOTE
byte for byte, or nothing lands. No change to the code.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_0936/C2_STEP.diff (34 lines)
```
   1 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
   2 | index 9514e96..3c5ca7d 100644
   3 | --- a/pipeline/package_pin.py
   4 | +++ b/pipeline/package_pin.py
   5 | @@ -161,7 +161,7 @@ STAND_ALONE_FLOOR = 3.0                # RULING 119 (1) (orchestrator 08:25 ET N
   6 |  #   weights, both compared exactly: under any other the floor is the render's own SCORER_MIN.
   7 |  STAND_ALONE_FLOOR_SCORER = "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53"   # its scorer_sha
   8 |  STAND_ALONE_FLOOR_DIGEST = "a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203"   # gemma3:27b's digest
   9 | -STAND_ALONE_NOTE = "stand-alone affirmed on the calibrated floor (3.0)"   # the pin's mark, one plain line in the note
  10 | +STAND_ALONE_NOTE = "a clip passed stand-alone on the calibrated bar"   # RULING 120: the mark, the Telegram note's line
  11 |  #   The render's validate (stand_alone.check_edl) re-asks the scorer ALONE, at 3.5, only for the clips that need asking
  12 |  #   (a clip after the hook opening on a conjunction or reply fragment, a trimmed clip) and never reads this side's
  13 |  #   verdict: the floor holds there only through the integrator's half (validate affirms exactly the marked segments),
  14 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  15 | index 93403e8..44b611a 100644
  16 | --- a/tests/package/test_medley.py
  17 | +++ b/tests/package/test_medley.py
  18 | @@ -1773,13 +1773,13 @@ class TestRuling119StandAloneFloor(unittest.TestCase):
  19 |          segs = [{"text": "Bitcoin d.", "scorer_verdict": idx["d"]}, {"text": self.OPENER, "scorer_verdict": idx["a"]}]
  20 |          m = PK.stand_alone_mark(segs)
  21 |          self.assertEqual((m["note"], m["floor"], m["segments"], m["ruling"]),
  22 | -                         ("stand-alone affirmed on the calibrated floor (3.0)", 3.0, [1], "119"))
  23 | +                         ("a clip passed stand-alone on the calibrated bar", 3.0, [1], "119"))
  24 |          self.assertIsNone(PK.stand_alone_mark(segs[:1]))                # every affirmation on the render's own bar
  25 |          base = TA.TestPinAndTruth.pk(None)
  26 |          plain = package_pin.to_pin(copy.deepcopy(base), "r")["moments_package"]
  27 |          marked = package_pin.to_pin(dict(copy.deepcopy(base), stand_alone_bar=m), "r")["moments_package"]
  28 |          self.assertNotIn("stand_alone_bar", plain)
  29 | -        self.assertEqual(marked["stand_alone_bar"]["note"], "stand-alone affirmed on the calibrated floor (3.0)")
  30 | +        self.assertEqual(marked["stand_alone_bar"]["note"], "a clip passed stand-alone on the calibrated bar")
  31 |          self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal
  32 |  
  33 |  
  34 | 
```

---

pp-selectid: the DELTA of the stand-alone floor (audit 20261116_0842, cleared) that RULING 120 makes. Files:
pipeline/package_pin.py (one constant), tests/package/test_medley.py (two expected strings).

RULING 120 (orchestrator 09:40 ET Nov 16), verbatim: "YES. The stand-alone floor of 3.0 lands, BOTH HALVES TOGETHER, when
both audits have cleared, exactly as you and the integrator describe: only on the measured scorer code and weights, only on
the marked segments, marked on the pin and in the Telegram note in one plain line ('a clip passed stand-alone on the
calibrated bar'). Reason: it is PBX's own approved clips (41f29b1f) that sit at 3.0; PBX reviews every video before it
publishes; the preview's two clips at 2.0 are NOT admitted and the floor never goes under 3."

THE CHANGE: the pin's mark (moments_package.stand_alone_bar, outside the seal) carries its note, and the integrator's
Telegram note prints that note as one plain line (telegram.BAR_MARKS; its exact-shape check of the mark reads the same text
from its own constant telegram.STAND_ALONE_BAR_NOTE, so the two cannot differ; changed in its own audited delta). The note
was "stand-alone affirmed on the calibrated floor (3.0)"; it is now exactly the ruling's words, "a clip passed stand-alone
on the calibrated bar" (no capital, no full stop, as quoted; agreed with the integrator after ruling 120). Nothing else changes:
the floor (3.0), the exact scorer code and weights digest, affirmed_verdict, scorer_verdicts, stand_alone_mark's other
fields (floor, the full scorer_sha, segments, ruling "119") and the seal are as audited in 20261116_0842 (unchanged guards:
package_pin.affirmed_verdict, package.scorer_verdicts, package.stand_alone_mark, package_pin.to_pin; not in this diff).

TESTS: test_medley TestRuling119StandAloneFloor and Ruling56: 11 pass; mutations F1-F10 after a control run (262 passed):
10 of 10 killed.

PLEASE CHECK: (1) the note is exactly the ruling's words; (2) nothing else changed; (3) the tests pin it.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
