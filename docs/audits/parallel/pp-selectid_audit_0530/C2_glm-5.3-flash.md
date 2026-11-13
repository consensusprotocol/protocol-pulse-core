# glm-5.3-flash (z-ai/glm-5.3-flash) 131 s finish=stop usage in 17697 / out 3959 usd~0.112 (upper-bound price)

# pp-selectid — CYCLE 2 FINAL REVIEW

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **glm P0-2 (F1, the 5-word statement minimum).** I noted the one-word/two-word moment edge but never asked whether the *kept* words still satisfy the statement minimum. They do not always — "But Bitcoin wins now." keeps 3 canonical tokens. The fix (E.MIN_STATEMENT_TOKENS check in trim_variant, package.py:60-61) is correct and I missed the defect.
- **glm P0-8 (F2, trim_problems raising).** I flagged the id-keyed-maps question (P0-3) but not the simpler one: `float(s["start"])` on a missing/None/bool start raising a non-PinRefused exception out of `to_pin`. The fix (check every number first, package_pin.py:162-163) is right. Missed.
- **glm P0-10 (F3, no-canonical-token trim).** I never traced what `edges` does when `trimmed` has no canonical token. It now fails closed (transcript_truth.py:278-280) with a test. Missed.
- **glm P0-7 (F4, generator membership).** I did not examine the TRIM_WORDS membership mechanics at all. Fixed; noted.
- **qwen's P0-1** I had partially — I reasoned through the hook_onset question in Cycle 1 and concluded (as the consensus K2 later confirmed) that the variant's own `words[0]`/`start` are what get measured, so the trimmed cut IS what is judged. I did not state it crisply; qwen's confusion and the consensus's resolution both sharpened it.

What I got that they didn't: my P0-3 (the `~trim` id vs. the `a_by`/`fails`/`exc`/`optout`/`delivered`/`dup`/`rt_ok` maps) was the highest-risk item in Cycle 1 and the consensus did not resolve it. I now can, partially, from the diff — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**grok's P0 (rate=None ⇒ ok cannot be True) — DISAGREE, and the consensus (K1) is right.** `stand_alone_check` (package.py:582-584) builds its EDL with no `selection_lock`, so `trimmed_word(s)` (stand_alone.py:196-199) returns None for every segment, `need` never gains a trimmed entry via that path, and `trimmed_opener` never runs at the pin stage. The opener rule judges the trimmed text's own first word. `r["ok"]` can be True. grok's test-reading (test_medley.py:395-400) is correct; his mechanism is not. His *policy* point survives, however, as the real question — see below.

**qwen's P0-1 (onset measured on the original cut) — DISAGREE.** K2 is verified from the diff: `hook_onset_for` receives the variant, whose `words[0]` and `start` are the trimmed ones (package.py:65-66). The trimmed cut is measured.

**qwen's P0-2 (scorer_pending recorded but ok=False) — PARTIALLY AGREE.** The recording is honest (package.py:30, surfaced at package.py:121-122 into the sealed inventory row). But note the asymmetry: `scorer_pending` lists segments whose locks trim a word, yet at the pin stage the EDL carries no lock, so the list is computed from `m.get("trimmed_leading")` on the *package* segments — which is the right source. It is honest. What it does not do is distinguish "pending and would pass" from "pending and would fail"; nothing pretends otherwise. Agree it is honest; the deeper question is K5.

**glm P0-1 (variant's end never recomputed) — DISAGREE (K3).** The kept words still end at `w1`; `end` is unchanged by construction and `duration_s = end − new start` (package.py:66). The contract binds start/end to the kept words; they do.

**glm P0-3 (the `~trim` id vs. the id-keyed maps) — AGREE, still the best finding, and still unresolved by the diff.** Here is what the diff lets me verify: `trims` is built from `no_role` moments (package.py:91), appended to `ms` (line 92), and `ad_read`/`cleared`/`hook_onset`/`trim_cut` all operate on the combined list, so those stages see the variant. But `a_by`, `fails`, `exc`, `dup`, `rt_ok`, `delivered`, `optout` are *parameters* to `build()` — their provenance is not in the diff. If any of them is keyed by moment_id and built upstream of the variant's creation, the variant (id `t~trim`) is invisible to it. The test at test_medley.py:435-448 monkeypatches `trim_variant` and passes `no_hook={"b~trim"}` — which proves the *Rig* knows `~trim` ids, and proves `trim_cut` catches a variant, but does NOT prove `a_by`/`fails`/`exc`/`optout`/`delivered`/`dup`/`rt_ok` resolve `~trim` ids, because the Rig constructs those maps itself and the test never exercises a variant surviving to `cleared` via the real `a_by` path. **The 113-moment rebuild (item 42) will answer this empirically, but the diff alone does not.** This remains my top finding.

**glm's other findings (P0-4, P0-5, P0-6, P0-9) — AGREE with the consensus's resolutions (K4, K1).** They are misreadings or guarded.

**K5 (pending at the render) — AGREE it is defensible, with one caveat.** Item 42 says "use it now"; the stated assumption (no GPU at the pin stage) is explicit in the brief; the render holds a refused pin at validate before any cut, costing a run slot. L-m/L-j are honored: nothing measured is recorded as pending, not as a pass, and the sealed row says so (package.py:121-122). The caveat: the *render's* check_edl with rate=None fails trimmed segments closed, so a pin whose trimmed segments would fail the scorer seals ok — the pin stage seals a verdict it never obtained, by the orchestrator's own ruling. That is exactly the "EXCEPT where the orchestrator has ruled otherwise" clause. Defensible. But the sealed record should make the *divergence* unmistakable — see §3, new finding.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P1). `scorer_pending` is computed, but nothing in the sealed record distinguishes a trimmed segment the pin-stage opener rule PASSED from one it would have failed.** At the pin stage the EDL has no selection_lock, so `check_edl` judges the trimmed text's own first word (e.g. "Bitcoin" — passes as a plain opener). At the render, the lock IS present, so `trimmed_opener` runs and requires the scorer. Two different judgments, both called "opener", one sealed. The sealed row carries `scorer_pending` (good), but the row's `opener: PASS` for a trimmed segment is the *pin-stage* judgment, not the render's. A reader of the pin alone cannot tell that the render will re-judge. Fix: in the inventory row (package.py:118-122), when `scorer_pending` is non-empty, annotate the affected rows' opener why with "pending at the render" — or at minimum, the `rows` comprehension should mark them. One line. Nobody caught this.

**N2 (P2). `trim_variant`'s guard order (package.py:54-59).** `toks[w0 + 1]` is evaluated in the `try` (line 54) before the `w1 <= w0` check (line 58) — but it is inside the `try/except (KeyError, IndexError, ...)` (line 55), so an IndexError fails closed to None. Correct-by-exception, as I noted in Cycle 1; the consensus did not record it. Not a defect; recorded for the record.

**N3 (P2). `trim_problems`' `num` lambda (package_pin.py:162) excludes bools, but `0 <= float(u) < float(st)` also accepts `u`/`st` where `st` comes from `s.get("start")` — a segment with NO `start` key at all but WITH both trim keys passes the both-or-neither check, then `num(None)` is False, so it is refused. Correct. But a segment with `start=0.0` and `untrimmed_start=0.0` is refused (0 < 0 fails) — is that the contract? The render says `0 <= untrimmed_start < start`, so yes, `untrimmed_start=0.0, start=0.0` is correctly refused. Verified, not a defect. However: the test at test_medley.py:429 passes `start=None` and asserts `trim_problems` returns a list — but `to_pin`'s refusal path (package_pin.py:176) is only tested for the three `bad` dicts at line 424, none of which has a missing/None start. The F2 fix's *refusal* path (not just the problems-list path) is untested. Minor.

**N4 (P2). `edges`'s trimmed-IN branch (transcript_truth.py:266-269): when `tw` is truthy and `heard == tw`, `j -= 1` — then `prev = ws[j]["text"] if j >= 0 else None` and `t_open = float(ws[j + 1]["start"])`. If the trimmed word is the recogniser's FIRST word (j becomes −1), `prev` is None and `t_open = ws[0]["start"]` — the trimmed word's own start. Then the IN rule's "file head" branch must handle `prev is None`. The consensus (K4) says the existing IN rule applies. I cannot verify the IN rule's body from the diff (it is above the shown hunk), so: **uncertain, flagged, not guessed.** If the IN rule requires `prev` non-None, a trimmed word at the file's head fails IN. The test at test_angles.py:325-329 covers a pause before "But", not the file-head case. Untested path.

**N5 (P2). `test_speakers.py:461-463`: the new `continue` skips a SEALED_LATER key when NO segment carries it — correct for the conditional trim keys, but it also silently skips any *future* conditional key. Acceptable; noted.

**N6 (P1, verification note).** The `trimmed` dict in `out` (package.py:101) maps parent→variant id. But `no_role` still lists the parent as excluded, and the variant appears in `ms` — so `out["usable"]` (n_usable, line 87) is counted BEFORE the variants are appended. The variant therefore adds to the working set but not to the reported "usable" count. Is that intended? The comment says "out['usable'] keeps its meaning" — defensible (usable = miner's moments, not variants), but the 113-rebuild report ("how many of the 113 come back") will read this number. If the orchestrator expects variants counted, the report undercounts. Flag for the report's interpretation, not a code defect.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| trim_variant (package.py:39-71) | 7/10 | 8.5/10 | F1 (statement minimum) fixed; my P0-3 id-map question remains open but the variant survives to `cleared` in the Rig test; end/duration contract verified (K3). |
| edges/verify_segment (transcript_truth.py) | 8/10 | 8/10 | F3 fixed, fail-closed verified; N4 (file-head + trim) still untested and unverifiable from the diff. |
| stand_alone.py sync | 8.5/10 | 9/10 | grok's mechanism objection disproved (K1); the sync to c6605895 is faithful; N1 (the two-judgments-both-called-opener issue) is a presentation gap, not a logic one. |
| package_pin.py (seal/refuse) | 8/10 | 9/10 | F2 fixed with the number-first guard; the both-or-neither and 0≤u<st contract verified against the render's stated rule; the F2 *refusal* path untested (N3) — minor. |
| build() integration | 6.5/10 | 7.5/10 | The variant reaches `cleared` and `trim_cut` (test:435-448); the `a_by`/`fails`/`exc`/`optout`/`delivered`/`dup`/`rt_ok` provenance remains the one thing the diff cannot prove; `usable` undercount (N6) noted. |
| Tests | 7/10 | 8/10 | F1-F4 each tested; the file-head+trim IN path and the F2 refusal path are the two remaining gaps. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
- None new. (My Cycle 1 P0-3 — the `~trim` id vs. the upstream id-keyed maps — is *resolved-or-not* by the 113-rebuild, not by this diff; I downgrade it to P1-with-verification, since the Rig test shows the variant surviving to `cleared` and the maps' provenance is outside the diff.)

**P1 HIGH**
1. **package.py:118-122 + 582-584 (N1):** the sealed stand_alone row's `opener: PASS` for a trimmed segment is the pin-stage judgment (no lock, no scorer); the render will re-judge with the scorer. Annotate the affected rows (or the row's why) with "pending at the render" when `scorer_pending` is non-empty, so the sealed record itself states the divergence. One line; makes K5's defensible reading *visible in the artifact*.
2. **package.py:91-97 (my Cycle 1 P0-3, unresolved):** before the 113-rebuild, verify that `a_by`, `fails`, `exc`, `optout`, `delivered`, `dup`, `rt_ok` resolve `~trim` ids (or that the variant is re-registered under its new id wherever those maps are built). If any is keyed by parent id only, the feature silently does nothing on the real pool — the Rig test does not exercise this path.

**P2 MEDIUM**
3. **transcript_truth.py:266-273 + test_angles.py:315-338 (N4):** add the file-head case — a trimmed word that is the recogniser's FIRST word (j = −1, prev = None). If the IN rule's body requires `prev`, this fails IN; the diff does not show the IN rule's body, so this is a must-verify, not a found defect.
4. **test_medley.py:424-430 (N3):** add a `to_pin` refusal (not just a `trim_problems` truthiness) for a segment with both trim keys and a missing/None `start` — the F2 fix's refusal path.
5. **package.py:87, 101 (N6):** confirm with the orchestrator whether the 113-rebuild's "how many come back" counts variants; `out["usable"]` does not.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Verify — before the 113-rebuild, not after — that the variant's `~trim` moment_id resolves in every id-keyed map (`a_by`, `fails`, `exc`, `optout`, `delivered`, `dup`, `rt_ok`) on the real pool; if it does not, ruling 33 part 2 silently ships nothing, and no test in this diff would notice.

## 7. PRODUCTION READY?

**Yes with conditions.**

1. (P1-1) Annotate the sealed stand_alone rows' opener why with the pending-at-the-render divergence when `scorer_pending` is non-empty — the pin must *state* its own divergence, not merely list the labels.
2. (P1-2) Empirically confirm, on the 113-moment pool, that `~trim` ids resolve in `a_by`/`fails`/`exc`/`optout`/`delivered`/`dup`/`rt_ok` — report the count of variants that reached `cleared`, not just `out["trimmed"]`.
3. (P2-3) Add the file-head+trim IN test (or confirm from the IN rule's body that `prev is None` takes the file-head branch).
4. (P2-4) Add the `to_pin`-level refusal test for a None/missing `start` under both trim keys.

The (a)/(c)-at-the-pin, (b)-pending-at-the-render split honors L-m/L-j and is a defensible reading of item 42; the seal, the refusal contract, and the untrimmed/legacy paths are unchanged and correctly guarded. With conditions 1-2 discharged, ship.