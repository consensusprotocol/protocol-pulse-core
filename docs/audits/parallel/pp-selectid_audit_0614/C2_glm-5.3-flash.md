# glm-5.3-flash (z-ai/glm-5.3-flash) 156 s finish=stop usage in 9095 / out 2653 usd~0.067 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0614, second pass)

## 1. WHAT THEY CAUGHT THAT I MISSED

Honest accounting against my Cycle 1 output (which was truncated mid-(d), so my coverage of (d) was incomplete):

- **Grok's verification that the ruling_0612 note text matches the implemented lists verbatim** — I analyzed the ambiguity of "glm last, after Grok" but did not do the line-by-line confirmation that the note's wording ("after Grok and after ruling 96's deepseek, which stays second") now resolves it. Grok's read is correct and I should have stated it: the note as written (diff line 48) explicitly says deepseek "stays second", which settles the ordering question the ruling's original phrasing left open.
- **Qwen's systematic walk of all three step-A keys** (step_a_first, step_a_second, *and* the role default `context_verdict`). I focused on the two named kinds; qwen correctly noted the default list was also struck (diff lines 6–11) and that the test now pins it (line 88: `ch["context_verdict"] == [G, DS, X]`). I did not explicitly verify the default.
- **Claude's consensus verification of the Gemini leg** — that `proof_ly.FROZEN` is a *deny-list* ("local:", "anthropic:", "openai:", "openai_stt:"), so a `google:` leg survives `chains()`, and that the edit script asserted the back-end exists (key `GEMINI_API_KEY_MEDLEY`, min_out 8000) before writing. I flagged Gemini's resolution as the thing I could not verify from the diff; that is now closed by execution evidence (test passes, 518 tests green in dev02).

## 2. WHERE I AGREE / DISAGREE

**Grok — "No concrete input verifiable from diff that breaks rulings... SHIP: yes":** **Agree.** Every list in the diff matches the rulings as amended, and the test pins each one. Grok's finding that the *default* `coherence_verdict` is untouched (still Grok -> deepseek, per test line 98's `today` pin and the note's "NOT CHANGED" clause) is correct and matches ruling 96's own rule (a type goes back to Grok first until re-measured — moving value verdicts onto unmeasured glm data would *violate* ruling 96, not fix it).

**Qwen — clips-alone = [Grok, Gemini] is the correct reading:** **Agree, with the reasoning made precise.** "Plan B's other outside family" — Plan B's coherence list is Grok -> Gemini -> OpenAI -> Anthropic; Grok is already first, OpenAI/Anthropic are frozen legs (dropped by `proof_ly.chains()`), so Gemini is the *only* remaining outside family. There is no other defensible reading. Qwen's check that qwen and deepseek (both Heimdall) were removed, satisfying "NO Heimdall fallback," is also correct (diff lines 30–32).

**Qwen — "Does anything else need the change?":** **Agree with its conclusion.** The default `coherence_verdict` (used by the spotlight's closing-line and the medley's takeaway value verdicts) is deliberately unchanged — the ruling note (line 48, "NOT CHANGED: ... the replay has no data for them") now records this, which was glm's Cycle 1 condition. Residual risk (xAI down + deepseek writing → value verdicts fail closed, package blocked) is real but *documented and intentional*, and it is the same fail-closed behavior ruling 96 mandates. Not a defect.

**Glm — (a) the "glm last" ambiguity:** **Agree it existed, agree it's now resolved.** The note's added clause "which stays second" (line 48) plus the test pin (line 95: `[X, DS, G]`) makes the implemented order the only one consistent with both the ruling and ruling 96. Had glm *replaced* deepseek, ruling 96's coherence order would have been silently amended without a ruling — the implemented reading is right.

**Glm — (d) "no verdict becomes looser":** **Agree, and this is the strongest systemic check.** Concrete: coherence's new third leg glm only fires when Grok is down *or* wrote the text and deepseek likewise — i.e., where the old behavior was *no verdict at all* (fail closed, package fails). A verdict from glm where previously there was none is strictly tighter, not looser. Clips-alone: Gemini (an outside family, Plan B's #2) replaces qwen/deepseek; the ruling explicitly orders this, and the test (lines 96, 106, 108–109) pins both the happy path and the fail-closed exhaustion. Step A: qwen removed — qwen was ruling 96's *third* failover; removing a weaker leg cannot loosen a verdict, and the 06:12 ruling cites qwen's measured error rate (9 of 43 refusals let through) as the reason. No loosening anywhere.

**Glm's (c) test-ordering walkthrough (lines 108–120):** **Agree.** I traced it independently: X down from Router construction; line 108 adds GEM → clips-alone spent → None (line 109, correct); line 110 adds G → coherence: X down, DS writes (family skip), G down → None (line 111, correct); line 112 restores G/GEM but X stays down → step_a_first picks G (not the writer, not down), step_a_second excludes glm's family → [X, DS] → DS (line 117, correct — two Heimdall families); line 118 `r.down.clear()` also clears X → step_a_second now reaches X (line 120, correct). One subtlety glm noted that I confirm: `r.down.clear()` at line 118 wipes the "xAI answering nothing" scenario, so the final assertion tests "Grok answers" — which is exactly what the comment on line 120 says. Consistent, no defect.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> tests/package/test_ledger_build.py:89 (the NotIn assertion) is narrower than its comment.** Line 89: `assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])`. This only covers keys *prefixed* `context_verdict:step_a` — i.e., `step_a_first` and `step_a_second`. That is sufficient today because the only step-A callers name their kind (the ruling: "every step-A call names its kind"), so the role default `context_verdict` (line 88, also pinned qwen-free) is unreachable by a step-A call. But the guarantee "no qwen on any step-A path" rests on *two* mechanisms: the prefix filter (lines 86–87, 89) *and* the "no live caller" fact, which is a property of the call sites, not of this test. If a future step-A call ever used the bare role (the note itself says the default list exists as "the role's default" for exactly that possibility), line 88's pin would still catch it — so this is defense-in-depth, not a gap. Concrete failure scenario: none. Informational; no change required.

**<medium> tests/package/test_ledger_build.py:112 (`del r.down[G], r.down[GEM]`) restores state by deletion, not by snapshot.** If a future edit adds another downed back-end earlier in the test (say, a third model), the `del` pair silently misses it and lines 113–117's "two Heimdall families" scenario gains an extra unstated constraint. Today the only downed entries are X (from construction, intentionally kept), GEM, and G — all accounted for. Fragility, not a defect. Informational.

**<medium> ruling_96 note (diff line 47) now ends with a period-only change (trailing punctuation, no textual edit).** Line 46→47: the only change to ruling_96's string is... none — the diff shows the line rewritten solely to add the trailing comma/`+` continuation for the new `ruling_0612` key. Verified: the ruling_96 text at line 47 is character-identical to line 46's. No ruling-96 semantics were touched. Informational; confirms the note "Every other list is ruling 96's, unchanged" (line 48) is true of the *strings* too, not just the lists.

**Nothing new at <critical> or <high>.** The combined Cycle 1 analysis plus this pass found no defect that any ruling, list, or test contradicts.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Ruling (1) coherence gap (list + note + test) | A− (ambiguity unresolved) | A | Note now states "stays second" explicitly (line 48); test pins [X, DS, G] (line 95) and the fail-closed exhaustion (lines 110–111). |
| Ruling (1) clips-alone (Gemini leg) | B+ (Gemini resolution unverified by me) | A | Closed by execution: FROZEN deny-list lets `google:` survive `chains()`; back-end + key asserted; test lines 96, 106, 108–109. |
| Ruling (2) qwen struck from step A | A− (default list not explicitly checked by me) | A | All three keys pinned qwen-free (lines 86–89); NotIn guard at 89; no step-A caller uses the bare role. |
| (d) Loosening risk | A− (my analysis was truncated) | A | Completed: every changed leg is appended where the old behavior was fail-closed, or removed per ruling with measured cause. No weaker model decides where a stronger one did. |
| Test rigor / fragility | — | A− | New: state restoration by `del` (line 112) and the prefix-scoped NotIn (line 89) are slightly brittle; both correct today. |

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM (all informational; none block ship):**
  1. `tests/package/test_ledger_build.py:112` — restore Router down-state from a saved copy (`r.down = saved`) rather than paired `del`; prevents silent scenario drift if the test grows.
  2. `tests/package/test_ledger_build.py:89` — the qwen-free guarantee for step A spans the two named kinds (line 89) *plus* the default (line 88) *plus* the "no live caller" convention; if a step-A call ever uses the bare role, the note (line 48) should say so. Documentation-only.
  3. `pipeline/model_providers.json:48` — the value-verdict residual risk (xAI down + deepseek writing → spotlight/medley value verdicts fail closed, package blocked) is documented but unresolved pending the orchestrator's answer (STATE 06:14, question B). Track it; do not fix here.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing in the code — the highest-leverage item is getting the orchestrator's answer to STATE 06:14 question B (whether the value verdicts' default Grok -> deepseek list should gain a fallback), because it is the only remaining fail-closed gap in the coherence family and it is explicitly out of scope for this diff.

## 7. PRODUCTION READY?

**Yes.** No conditions required to ship. (If conditions are mandatory: (1) the three P2 informational items above are noted, not fixed; (2) question B stays open with the orchestrator, as the diff's own note records.)

**SHIP: yes**