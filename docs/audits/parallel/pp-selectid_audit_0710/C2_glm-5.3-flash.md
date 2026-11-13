# glm-5.3-flash (z-ai/glm-5.3-flash) 134 s finish=stop usage in 17861 / out 3724 usd~0.109 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0710 (trimmed-cut acoustic measure, ruling 33 part 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the three Cycle 1 outputs:

- **GLM's P1-2 / the consensus's K3** — the synthesised `trim` record's `why` provenance. I noted the wrapper's synthesised record in Cycle 1 but did not trace *which* early-return paths could reach it. The consensus's K3 does that trace correctly: every early return of `_measure` (no source audio, words not inside the window, `edge_plan` raising, no cuttable IN) happens **on the trimmed cut's path** when `trimmed` is set, so the copied `why` is genuinely about the trimmed cut, not the hook lead. I missed that the "no cut before the hook" message was *also* rewritten in this diff (diff lines 77–79) to say "no cut after the trimmed word 'So': …" — so the misleading-`why` concern is narrower than GLM thought. I agree with the no-change verdict, but GLM's instinct to check the funnel's consumption of that string was right.
- **Grok's P2 on `trimmed_boundary`'s k<0 case** — I did not explicitly connect that `k < 0` (trimmed word is the window's first word) returns `valid: False` with "not the word before the lock", which is exactly the K1 assumption's failure mode. Grok flagged it; nobody traced it to a concrete scenario. I do, below (new finding N2).
- **Qwen's P0-1 (provenance)** — I took the "verbatim, AST-verified" claim at face value in Cycle 1. The consensus's K1 rebuts it with `git show c6605895` line numbers (718/730/743). I cannot re-run that command (no tools), so I record it as *verified-by-assertion*, not independently. Qwen's finding was a misread, but its *method* — demand the evidence, not the claim — was the right discipline and I under-applied it.

What nobody missed, and I confirm: the funnel's `mom()`/`tx()` changes are report-only; `build` never reads funnel.py.

## 2. AGREE / DISAGREE

| # | Finding | Verdict | Why |
|---|---|---|---|
| A1 | GLM P1-1 (margin direction: pin measures the window's decode, render its own) | **Agree, correctly graded P1-note** | Both directions of decode divergence are bounded by the extra 10 ms hop; the pin stage can only be stricter. Fail-closed, L-m/L-j compliant. No action. |
| A2 | GLM P1-2 / K3 (synthesised `trim`'s `why`) | **Agree with the resolution** | K3's path trace is correct: every early return is on the trimmed path, and the "no cut" message now names the trimmed word. The residual risk is only the `edge_plan`-raised case, where the `why` is the planning exception — which *is* about the trimmed cut. No change needed. |
| A3 | GLM P1-3 (fallback `{"measured": False, "why": "no trimmed-cut record"}` in `build`) | **Agree, and it's the strongest finding in the set** | `hook_onset_for`'s except-branch (package.py, diff lines 109–110) stores a record with **no `trim` key**; the comprehension's fallback (diff line 131) then excludes the moment with `measured: False`. Correct (fail-closed), and — GLM's point — the *old* rule also excluded it (hook lead not pass), so no behaviour change. But note: the fallback's `why` ("no trimmed-cut record") is now the *only* evidence PBX sees for that exclusion, and it's true. Verified: no path lets a trimmed moment through with a missing/failed `trim`. |
| A4 | Qwen P0-1 (provenance of `_cut_head`/`_head_tail_of`/`hook_lead_at`) | **Disagree (it's a P2, not P0)** — the consensus's K1 rebuts it with the render's line numbers | I cannot independently re-verify (no tools), but the consensus's citation is specific and checkable. Even if Qwen were right, the functions are exercised by the new tests on real decoded audio, so the provenance question affects documentation, not behaviour. |
| A5 | Qwen P0-2 (pin measures the *uncut* source, not the cut audio) | **Disagree** — K2 is correct | `SL.trimmed_onset(sa.path, cut_in, fade_in_ms)` → `hook_lead_at` → `_cut_head(src, c, fade_ms)` runs ffmpeg `-ss c` on `sa.path`: it decodes **from the cut**, with the clip's fade applied. The measure *is* the audio as cut. Qwen confused the *file* (the L-v 2 window) with the *signal* (the cut portion of it). |
| A6 | Qwen P1-3 (the "hook lead decides only the hook" comment) | **Agree — and it's already fixed** | Diff lines 133–134 now say exactly what Qwen asked for: the hook lead decides only whether a trimmed clip may OPEN the medley, never whether it may play as a clip. F1 implemented. |
| A7 | Qwen P2-6 (test doesn't check the fade) | **Agree — and it's already fixed** | Diff line 403–404: `SL.FADE_MIN_S * 1000 - 1e-6 <= fade_in_ms <= SL.VALLEY_FADE_S * 1000 + 1`. F2 implemented. The `+1` slack (int rounding) is acceptable; it cannot admit an out-of-law fade because `accepted_cut` itself enforces the bounds. |
| A8 | Grok's "no P0, no P1, SHIP: yes" | **Agree with the verdict, not the thoroughness** | Grok's P2s are accurate but it graded the `trim`-record-on-every-path guarantee as satisfied without noting the except-branch gap that GLM's P1-3 covers. Grok's review is the least deep of the three; its SHIP verdict happens to be right. |

## 3. NEW FINDINGS (this cycle)

**N1 — P2, `pipeline/hook_onset.py` diff lines 92–96: when the trimmed cut fails, `rec["pass"]` is forced to False but `rec["lead_ms"]`/`cut_in`/`pad_s` still describe the *hook* cut, and `rec["why"]` is overwritten.**
Scenario: a trimmed moment whose hook lead is 200 ms (pass) but whose trimmed cut fails. The record becomes `{"pass": False, "lead_ms": 200, "cut_in": <hook's>, "trim": {...fail...}, "why": "the trimmed cut: ..."}`. The `passed_lead=ok` key preserves the lead verdict — good — but any consumer reading `lead_ms`/`cut_in` as *the* clip's numbers now reads the hook's cut, while `pass` describes the trimmed cut. In `build`, the prescreen's `hook_onset` entry (package.py diff lines 123–125) prints `why` — which is now the trimmed-cut reason, so a trimmed moment that failed the *hook lead* but passed the *trim* shows the hook-lead reason (correct), while one that failed the *trim* shows the trim reason (correct). Verified: the prescreen strings are right in both directions; only the raw record's `cut_in`/`lead_ms` are ambiguous about which cut they describe. P2: no gate changes, evidence only.

**N2 — P2, `pipeline/sentence_law.py` diff lines 165–171 + the stated assumption K1: on the pin stage's window, `k < 0` (trimmed word = window's first word) fails with "not the word before the lock" even when the render, on the full transcript, would pass it.**
The window is `[start − 4 s, end + 1.5 s]`, so the trimmed word is the window's first word only if the moment starts within 4 s of the video's head — rare but real (a cold-open "So…"). In that case `trimmed_boundary` returns `valid: False` → `edge_plan`'s IN is not cuttable → `_measure` returns "no cut after the trimmed word 'So': the trimmed word 'So' is not one of … or not the word before the lock ('<file head>')" → the moment is excluded at any place. The render, on the full word record, would see the preceding word and pass. **This makes the pin stage stricter than the render** — permitted, fail-closed, and the `why` names the mechanism, so PBX can overturn it. But the stated assumption (K1) says eligibility already verified the sentence-start on the full record and the variant inherits it; that inheritance does NOT extend to the *k<0* case, because the window's `words` list (built at diff line 65, indices relative to the window) genuinely has no word before the trimmed one. The assumption's *other* half (the untrimmed sentence's start) IS inherited, as stated. So: the assumption holds for what it claims, but the k<0 divergence is a real, if rare, stricter-than-render case that nobody in Cycle 1 traced to the window's actual word list. P2: documented divergence, fail-closed, no change required — but the `why` string should ideally distinguish "no word before it in the window" from "not the word before the lock" so PBX doesn't overturn the wrong thing.

**N3 — P2, `tests/package/test_hook_onset.py` diff lines 398–405: the passing test asserts `1.95 <= cut_in < 2.40` but never asserts the cut sits inside the *quiet run* `q` that `trimmed_boundary` measured, only inside the word gap.**
`edge_plan`'s trimmed branch (diff lines 207–209) intersects the word gap with the quiet run: `lo, hi = max(lo, q["start"]), min(hi, round(q["end"] - LEAD_MIN_S, 3))`. The test's assertion (line 402) checks the weaker constraint. In this synthetic fixture the two coincide (the room tone spans the whole gap), so the test passes for the right reason here — but it would not catch a regression where the quiet-run intersection is dropped. P2: test-coverage note, not a defect.

**N4 — P2, `pipeline/package.py` diff lines 129–132: the `trim_cut` comprehension's `for t in [m["hook_onset"].get("trim") or {...}]` trick means a trimmed moment whose `hook_onset` record itself is missing (not just `trim`) is silently handled by the fallback.**
`m["hook_onset"]` — if a moment in `cleared` somehow lacked the key, this raises KeyError. But `cleared` is populated only after `hook_onset_for` ran for every usable moment (the cache guarantees the key), so this cannot fire. Verified: no path. Noted so the next auditor doesn't re-derive it.

**N5 — P2, `tests/package/test_medley.py` diff lines 482–492: the new `rig2` case (clean trim, bad hook lead → stays as a clip) is the *only* test of the F1 comment's claim, and it asserts presence in the angle prompt, not the prescreen.**
`out2["prescreen"]["trim_cut"]` is asserted empty (line 491) — correct, since `trim_cut` only collects trim failures. But nothing asserts `out2["prescreen"]["hook_onset"]["b~trim"]` says FAIL (the hook-lead reason) while the moment remains offered. If someone later "fixes" `build` to exclude on hook-lead failure again (the old rule), this test catches it via the angle-prompt assertion (line 492) — so the regression guard exists, just indirectly. Acceptable.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| sentence_law.py (copied functions) | pass (provenance taken on trust) | pass, provenance *verified-by-assertion* (K1's git citation; I cannot re-run it) | The consensus's specific line-number citation upgrades my confidence one notch, not to certainty. |
| hook_onset.py (trim_onset, measure wrapper) | pass | pass, with N1's evidence-ambiguity noted | The K3 path-trace closed my Cycle 1 uncertainty about the synthesised record's `why`. |
| package.py (build's new rule) | pass | pass | A3's no-behaviour-change verification (old rule also excluded those moments) removes my last doubt. |
| funnel.py | pass (report-only) | pass | Nothing new; confirmed nobody's changes touch `build`. |
| tests | pass | pass, with N3/N5 coverage notes | The F2 fade assertion landed; the quiet-run-intersection gap (N3) is new. |

No score changed direction. The diff was already sound; this cycle added evidence, not defects.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (GLM's P1-1/P1-2/P1-3 are all verified fail-closed, no-change; the consensus's K2/K3 rebuttals hold.)

**P2 MEDIUM**
1. `pipeline/hook_onset.py` diff lines 92–96 (N1): when the trim fails, `cut_in`/`lead_ms` describe the hook's cut while `pass`/`why` describe the trimmed cut. Add `trim_cut_in`/`trim_fade_in_ms` at the record's top level, or rename. Evidence clarity only; no gate changes.
2. `pipeline/sentence_law.py` diff lines 165–171 (N2): the k<0 (window-head) case's `why` should distinguish "no word before it in this window" from "not the word before the lock", so PBX overturns the right thing. Fail-closed; the divergence (stricter than the render) is permitted.
3. `tests/package/test_hook_onset.py` diff line 402 (N3): assert the cut sits inside `trimmed_boundary`'s quiet run, not just the word gap — the fixture currently can't distinguish the two.
4. `tests/package/test_medley.py` diff lines 491–492 (N5): add the direct assertion that a clean-trim/bad-lead moment's prescreen `hook_onset` entry shows the hook-lead FAIL while it stays offered — the current guard is indirect (angle-prompt presence).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

N1's record disambiguation: when the trimmed cut fails, the record's `cut_in`/`lead_ms` still describe the hook's cut while `pass`/`why` describe the trimmed one — one renamed key (or a `trim_cut_in`) makes the evidence match the verdict, which is exactly what PBX reads to overturn a HOLD.

## 7. PRODUCTION READY?

**Yes with conditions** — both conditions are evidence-clarity, not gates:

1. **N1**: when the trimmed cut fails, the record must not leave `cut_in`/`lead_ms` ambiguous about which cut they describe (add the trimmed cut's own numbers, or qualify the existing keys). No gate logic changes.
2. **N2**: the k<0 `why` must distinguish "no word before it in this window" from "not the word before the lock" so the prescreen's evidence is actionable. Fail-closed either way; this is a string, not a rule.

Everything else — the copied functions' usage (the render's exact sequence: `edge_plan(trimmed={"word": ...})` → `accepted_cut` → `trimmed_onset`, with the pin's one-frame margin making it only stricter), the fail-closed guarantees (`trim` present on every path, exceptions never a pass, the `build` fallback), the untrimmed invariance (the old `edge_plan` path is bit-identical when `trimmed is None`, and the tests exercise it), and the funnel's report-only status — I verified from the diff and it holds. The 05:48 build's two real trimmed moments are now measured exactly as the render measures them, one stricter. Ship it.