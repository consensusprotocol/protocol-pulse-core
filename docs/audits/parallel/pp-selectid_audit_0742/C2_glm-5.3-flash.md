# glm-5.3-flash (z-ai/glm-5.3-flash) 39 s finish=stop usage in 26484 / out 2235 usd~0.113 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0829 (final)

## 1. What they caught that I missed

- **grok's P0 framing of the runtime/R4 change** (package.py:15-42): I treated the 0.40→0.45 share and the new estimate as a disclosed ruling-9 change; grok correctly stressed it *alters the acceptance region* (63-word package: R4 41.0%→38.9%, now PASS on r4, caught only by the runtime gate at 72.41 s). The consensus disposition answers it (the deployed edl_rules reads 0.45; the package still fails 60-70 s), so it's disclosed, not a defect — but I under-weighted that the *runtime* gate, not r4, is now what refuses it. That coupling is fragile: any future content shrink that lands under 70 s silently accepts what the old gate refused.
- **glm's P1-1 replayed `any()` semantics** (package.py:160, vo_fidelity.py:350): I noted the tri-state but not that `any(reps)` reports `replayed=True` when even one of three runs replayed — a 2-fresh/1-replayed majority reads as "replayed". Honest enough (per-run truth is in `majority.runs`), but the top-level field is misleading. I'd have called it P2; glm did.
- **grok's P2 on duplicate violations** in `majority`'s merged list: the `seen` set dedupes by (slot, rule, detail) across runs — actually it does dedupe globally (line 338-341), so grok's "duplicates from minority runs" concern is largely answered; only violations differing in `detail` wording duplicate. Partially agree.

## 2. Agree / disagree

- **glm P0-1 (unknown-slot violation dropped)**: agree with the consensus *refutation* — `check_verdict` raises on a slot not in `by_slot` → slot "-", unmeasured → fail vote. The C1 H1 hardening (`whole(v)` fails every slot) closes it. Disagree with glm's residual doubt.
- **glm P0-2 (VO_S[0] units in content_range, line 60)**: agree it's unverifiable from the diff; `VO_S[1] * WPS` at line 90 implies VO_S is w/s, and `RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo` subtracts a rate from seconds unless VO_S[0] is seconds. Carried over from old code, so likely VO_S is (min_s, max_wps) — but it's the one remaining unit question nobody resolved. Keep P1-uncertain.
- **qwen P0-3 (mirror faithfulness)**: agree, downgraded to P1→resolved: pin_and_verify.py:394-397 copies the *deployed* pinned.py/edl_rules.py/config.py and runs `edl_rules.rule_r4` on the real pin — that's the strongest possible faithfulness check and nobody else noted it.
- **grok P1 (algebra proof)**: resolved by `test_the_r4_word_bounds_invert_runtime_and_the_share_exactly` (test_angles.py:807-822) — sweeps content 15-50 s × 1-4 VO lines, checks the bound passes and one word either side fails. That's the exhaustive proof grok asked for. Agree it's now adequate; note it tests `r4_max_vo_words`/`min_vo_words` but *not* `content_range`'s upper bound (line 60), which remains untested.

## 3. New findings (this cycle)

- **N1 (P1): `content_range` upper bound (package.py:60) is untested and possibly unit-inconsistent.** `RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo`: if `VO_S[0]` is a w/s floor (as line 90's `VO_S[1] * WPS` suggests), the subtraction mixes units. Concrete failure: `content_range(2)` returns an upper bound too small (or too large) by |VO_S[0] − VO_S[0]·WPS| seconds; a builder picking content at that bound lands outside 60-70 s or fails r4. Nobody resolved this in C1; the new inversion test doesn't cover it.
- **N2 (P2): `once_then_majority` (package.py:139-149) votes on the *gate-level* `ok(result)`, while `VF.majority` votes per-slot — the fidelity path runs both.** In run_given_package.py:545-553, `once_then_majority` decides whether to replay on `verdict.ok`; if the first run's verdict.ok is False because of *one* slot, all three runs happen, then `VF.majority` may pass that slot 2-1 while another slot's 1-2 fail is recorded — consistent, but the *gate* then reads `merged["verdict"]["ok"]`, which requires `not failed` (no slot failed by majority). Correct, just note the two voting layers can disagree: `once_then_majority`'s `passed` (line 547's lambda) is discarded for fidelity. No wrong result, but the discarded `passed` invites future drift. P2.
- **N3 (P2): `with_votes` (package.py:155) picks the first *passing* run's record as the gate's evidence, but `VF.majority`'s merged verdict is built from `runs[0]`'s deterministic layer and claims.** For fidelity, the driver returns `merged` (not `with_votes`), so this is consistent; for exclusion/context/coherence, `with_votes` returns a *single run's* record while the gate passed on a majority — the inventory's `by`/`replayed`/`n` come from that one run, with votes bolted on. If the first run's `measured`/`replayed` differ from the majority's, the inventory row's `measured` (e.g. exclusion: `all(e.get("measured")...)` at line 210) reads the *merged* exc dict, which is the chosen run — a 2-1 majority where the chosen run is unmeasured would show measured=False while votes say 2 pass. Verify: `ok(e)` in once_then_majority requires `measured` for a pass vote, so the chosen passing run is measured. Self-consistent. Downgrade to note.
- **N4 (P2): `self_repair` (transcript_truth.py:239-252) requires `r.get("speaker") is not None` — a missing label is "not the same speaker" (fail-closed, good), but `edges()` (line 264) then skips nothing and reports the *pre-repair* word as `before`; the IN's `ok` then depends on whether that skipped-adjacent token ends in TERMINAL.** With a repair present but speaker labels missing, the IN fails even though the geometry is identical to the passing case. Fail-closed, disclosed by the ruling's "a missing label is not the same speaker". Not a defect; recorded.

## 4. Revised scores

| Subsystem | C1 | C2 | Why |
|---|---|---|---|
| package.runtime / R4 algebra | B+ | A− | inversion test added; only content_range's upper bound (line 60) remains untested/unit-uncertain |
| vo_fidelity.majority | A− | A | glm's unknown-slot doubt refuted + hardened (H1); votes/splits reach the inventory |
| transcript_truth.self_repair | B+ | A− | ruling-8 test is thorough (exactly-one, same-speaker, prefix, full-repetition-excluded); heuristic now exact (`fw == fst`) |
| driver (run_given_package) | B | B+ | majority plumbing honest; N2's discarded `passed` is the only wart |
| pin_and_verify | — | A | deployed-code verification, the strongest faithfulness evidence in the diff |

## 5. Final priority list

- **P0**: none.
- **P1-1** — package.py:60: `content_range` upper bound mixes `VO_S[0]` (w/s?) into a seconds expression; untested. Add it to the inversion test's sweep or confirm VO_S[0] is seconds.
- **P1-2** — package.py:15-42: the 63-word package's acceptance moved from r4-FAIL to runtime-FAIL. Disclosed, but add an assertion (or a STATE note) that the *runtime* gate is now the sole refuser, so a future share/estimate tweak doesn't silently accept it.
- **P2-1** — package.py:160 / vo_fidelity.py:350: top-level `replayed` = `any(reps)`; a 2-fresh/1-replayed majority reports replayed=True. Prefer `all(reps)` or expose the list.
- **P2-2** — run_given_package.py:545-553: fidelity's `once_then_majority` `passed` is computed then discarded; document or drop it.
- **P2-3** — grok's residual: merged `violations` can carry near-duplicate details differing only in wording; the `seen` key (vo_fidelity.py:338) could normalize `detail`.

## 6. Single highest-leverage change

Resolve the `VO_S[0]` unit question in `content_range` (package.py:60) — it's the only remaining arithmetic nobody has verified, and it feeds the builder's search space.

## 7. Production ready?

**Yes with conditions**: (a) confirm or test the `content_range` upper bound (P1-1); (b) record that the 63-word package is now refused by the runtime gate, not r4 (P1-2). Everything else — majority, self-repair, the deployed-code pin verification — is ready.

SHIP: yes with conditions