# glm-5.3-flash (z-ai/glm-5.3-flash) 125 s finish=stop usage in 18060 / out 3343 usd~0.104 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0734)

## 1. WHAT THEY CAUGHT THAT I MISSED

Honest accounting against my Cycle 1 output (reconstructed from the consensus):

- **grok's "cleared as by_id" question (no_voice → fixed_caption_gates, package.py:246-248):** I did not explicitly verify that `cleared` is the correct `by_id` for the no-voice path. The consensus resolution is right — `nv_order` picks the added clip *from* `cleared` (line 147: `m = cleared.get(mid)`), and `segs` are cleared moments, so every moment_id in `order` resolves in `cleared`. I missed stating this; it's sound.
- **grok's "where does pk['no_voice']['added_clip'] come from" (test line 328):** I didn't trace the fields→assemble_medley copy. The consensus answer (fields carry `"no_voice": {..., "added_clip": added, ...}` unchanged; assemble_medley copies it) is consistent with the diff at lines 218-220, where `fields` includes the no_voice dict. Missed by me, resolved correctly.
- **glm's (b) — the `a_use(pk3)` → inline dict-comp change (line 56):** I likely treated the extraction as trivially safe. glm correctly flagged it as needs-verification; the consensus refutation (a_use *is* that comprehension; the voiced-path tests + M19 kill coverage) is convincing, but the flag itself was sharper than my treatment.

What I caught that they mostly didn't: the (C) trigger's reliance on `lone_slot(cheap + fid["violations"])` semantics, and the (d) determinism question — which glm and qwen both worked through, and which the consensus correctly downgraded to "latent, not proven."

## 2. WHERE I AGREE / DISAGREE

**glm (d) — nv_order called twice, state may diverge.** *Agree, with a sharpening.* The diff shows the in-loop call at line 274 and no_voice's call at line 176. Between them: the `break` exits the loop, and the consensus says nothing runs in between. But there IS one intervening mutation glm only gestured at: the in-loop call itself. `nv_order` mutates its *own* `plan` dict (`plan["registered_skipped"].append(...)` at line 158), not the closure state — so `dropped`/`doomed`/`held_map`/`cleared` are untouched. I verified from the diff: between line 274's call and the `break` at 277, only `v_novoice = val` runs. After the loop, the code between the loop end and `no_voice()` is not shown in the diff — that's the residual gap. **Verdict: agree it's needs-verification, but the diff-visible window is mutation-free.** The cheaper fix: have the value-loss branch pass `nv_plan` into `no_voice()` instead of letting it recompute. That eliminates the question entirely.

**glm (c) — refused list drops context violations.** *Agree, minor.* Line 245: `refused = [... for v in cheap + fid["violations"]]` — `cx["violations"]` excluded. But the guard at line 240 requires `cx["ok"]` for the fallback to fire, so context violations are empty by construction when the record is written. glm's own "record-keeping only" verdict stands. No action needed.

**glm (b) / grok 1 — extraction equivalence for rewrite_alone.** *Agree with the consensus refutation.* One residual: the old code's `man` (line 72 of old) — the new helper rebuilds it at line 49 from `pk3["segments"]` and `ctx.now`. If the old `man` was built from `pk` (pre-rewrite) rather than `pk3`, the channels list could differ when the rewrite changes nothing (it doesn't — same segments). Equivalent. Also note the helper's `why` parameter: rewrite_alone passes `"the fixed caption (ruling 65 b)"` (line 80), matching the old `build_pk(line, "the fixed caption (ruling 65 b)")` — the vo_kind prefix `f"{pk.get('vo_kind')}; {why}"` (line 45) vs old `build_pk`'s second arg. If `build_pk` did NOT prepend vo_kind, the note string changed. **Cannot verify from the diff — needs-verification, cosmetic (note text only, not gating).**

**grok 2 — cleared vs by_id interchangeability.** *Agree with consensus refutation* (see §1).

**grok 3 — added_clip provenance.** *Agree with consensus refutation.*

**qwen's (d) analysis — the new medley call.** *Agree, and this is the strongest point in their output.* `nv_order`'s candidate check (lines 152-155) validates durations/limits but NOT the joins; `no_voice` then runs `medley(router, order, ...)` (line 207) which can fail → `return None` (line 209-210). The in-loop decision "a no-voice line-up exists → skip the rewrite" is therefore *optimistic*: the rewrite is forfeited even if the added-clip line-up fails its medley. Is that (A)-compliant? (A) says the no-voice shape is ONE shape; the builder's reading, stated on STATE, says "a no-voice line-up that then fails a gate ends the line-up, as on ruling 3's path" — and ruling 3's path behaves exactly this way. So it's consistent, and test `test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite` (lines 339-349) pins it. *Agree with the implemented semantics; no defect.*

**qwen's truncated output.** Its condition 1 (seed 7 in fixed_caption_gates' context call) is cut off mid-sentence in the consensus. The helper passes `7` at line 55, matching the old line 76's literal `7`. Resolved.

## 3. NEW FINDINGS (Cycle 2)

**N1. The (C) guard admits a cheap failure on a NON-caption slot when fid is also failing on caption only — actually, the inverse: a cheap TITLE failure alone blocks the fallback, correctly, but a cheap failure *plus* a fid caption failure where the cheap violation is on the title yields `lone_slot(cheap + fid["violations"])` mixing slots → None → hold. Correct. However: when `cheap` is non-empty AND `lone_slot(cheap) == "caption"` but `fid["ok"]` is False with violations on the TITLE, the merged list has caption+title → no fallback → hold. Also correct.** What nobody flagged: the guard at line 240 requires `fid.get("measured")` — but when `cheap` alone is non-empty and fid passed, `fid.get("measured")` must be True from the earlier paid_gates call; if `paid_gates` was skipped (the `if cheap:` early-return at line 225-229 was REMOVED — now `if cheap and lone_slot(cheap) != "caption"`), then when cheap fails on caption alone, execution *continues* to the exclusion/paid_gates block (lines 230-233) — wait, checking: line 226 `if cheap and lone_slot(cheap) != "caption":` returns; otherwise falls through to the exclusion block and `paid_gates` at 233. So a caption-only cheap failure now pays for paid_gates BEFORE the fallback — one extra paid call vs. the voiced ruling-65 path where... actually in rewrite_alone the fallback also runs after fid. Consistent. But: **if `cheap` fails on caption alone AND the exclusion/paid_gates block is skipped** (the `if` at line 230 — condition not shown in the diff), then `fid` retains its value from... where? In no_voice, `fid` is first bound at line 233 inside the paid_gates block. If that block is skipped, `fid` is UNBOUND at line 239's `if cheap or not fid["ok"]` → NameError. The consensus (glm condition 1) said "fid, cx = paid_gates(...) runs unconditionally inside the with block; every earlier exit returns None" — but the diff at 226-233 shows the cheap early-return now *conditionally* skips, and the paid_gates call is inside an `if` whose condition (line 230) is not in the diff. **If that condition can be False while cheap failed on caption alone, fid/cx are unbound → NameError at line 239/240.** glm's Cycle-1 resolution assumed unconditional; the new `lone_slot` early-return at 226 makes the fall-through path NEW. Needs-verification: what is the `if` at line 230's condition, and can it be False when `cheap and lone_slot(cheap) == "caption"`? If it's `if not cheap:` or similar, the new fall-through skips paid_gates and line 239 reads unbound fid. This is my strongest new finding.

**N2. `note["caption_fallback"]["written"]` (line 249) records `fields["caption"]["text"]` — but `fields` was built with the *latest write's* caption; after `fixed_caption_gates` returns, `pk` is reassigned (line 246) and the sealed package's caption is the fixed line. The record correctly preserves what was written vs. fixed. No defect — noting the record is the only trace of the written line, since pk's caption is overwritten.** (Confirms grok-3's provenance question in reverse: the *written* line survives only in the note.)

**N3. Test-coverage gap, (C) × (A) interaction:** no test exercises the fixed-caption fallback when the no-voice line-up has an ADDED clip AND the caption fails (test_c_ruling_3s_no_voice_path_takes_the_fixed_caption_too, lines 490-506, does cover ruling 3 + added clip z + UPPER caption — actually it does; withdrawn). Instead: **no test covers `registered_skipped` surfacing through the (A) value-loss path** (nv_order lines 157-159 → note line 177-178); the ruling-3 path's registry-skip note key changed from `note.setdefault("registered_skipped", [])` (old, only when why_not written) to unconditional-when-nonempty (line 177). Old code: the key appeared only via the why_not branch's `note.get("registered_skipped")` — actually old also set it during the search. Behaviour: old wrote the key only when the search ran (content < nv_lo); new writes it whenever plan carries it — same, since plan only populates it in the same branch. Equivalent; the note key just moved. Withdrawn as a defect; noting the (A)-path+registry-skip combination is untested.

**N4. `test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption` (line 412) stubs CI.check_contexts globally (monkeypatch at module level, restored in finally).** If tests run in parallel or the rig's paid_gates path also calls CI, the stub's `{"ok": True, ...}` masks real context failures in *other* assertions of the same test. Single-threaded unittest: fine. No defect.

**N5. Line 335: `self.assertNotIn("takeaway_value", pk["gates"])`** — pins that the no-voice package seals no takeaway_value gate. Consistent with (A) (the takeaway never ships). Good.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| (A) one-shape implementation | pass | pass | qwen's medley-fail-ends-lineup trace confirms semantics match the stated reading; tests 319-349 pin it |
| (C) fixed-caption gating | pass | pass w/ caveat | N1: fid/cx binding when the cheap early-return falls through — the one unresolved binding question |
| Extraction (b) | pass | pass | consensus refutation + M19 kill; residual: vo_kind note-string prefix, cosmetic |
| (d) determinism | pass | pass | diff-visible window mutation-free; residual: code between loop end and no_voice() unseen |
| Tests | pass | pass | (A)-path + registered_skipped untested (N3, minor) |

## 5. FINAL PRIORITY LIST

- **P1 (HIGH):** package.py:226-239 — verify the `if` guarding `paid_gates` (line 230, condition not in diff) cannot be False when the new fall-through from `if cheap and lone_slot(cheap) != "caption"` (line 226) occurs; otherwise `fid`/`cx` are unbound at line 239 → NameError. Concrete input: a no-voice line-up whose cheap checks fail on the caption slot alone, with whatever condition makes line 230's `if` skip. If the condition is e.g. `if not cheap:` this fires on the (C) happy path — yet the (C) tests pass, so it likely does not; still, the diff does not show it. **Must confirm before ship.**
- **P2 (MEDIUM):** package.py:274/176 — pass `nv_plan` into `no_voice()` rather than recomputing; removes the (d) divergence question and the unseen-bridge risk.
- **P2 (MEDIUM):** package.py:45 vs old build_pk — confirm the vo_kind-prefix note string is unchanged (cosmetic; affects records/pins only).
- **P2 (MEDIUM):** tests — add the (A) value-loss + registered_skipped (ruling 66) combination; currently nothing pins that the note surfaces on the ruling-91 path.

## 6. SINGLE HIGHEST-LEVERAGE CHANGE

Resolve the fid/cx binding question at package.py:226-239 — it is the only finding that could produce a crash (not a wrong pin) on the new (C) fall-through path, and one look at the unseen line-230 condition settles it.

## 7. PRODUCTION READY?

**Yes with conditions:**
1. Confirm the line-230 guard: show that when `cheap` fails on the caption slot alone (the (C) trigger), execution reaches `paid_gates` (or that `fid`/`cx` are otherwise bound) before line 239. If the guard skips paid_gates in that case, bind `fid, cx` defaults or restructure the early-return.
2. (Recommended, not blocking) Pass `nv_plan` from the value-loss branch into `no_voice()` to make the (d) decision single-sourced.

Everything else — the (A) one-shape semantics, the extraction, the (C) trigger, the mutation kills, the consensus refutations of grok's three mediums — I verified and sign off.