# glm-5.3-flash (z-ai/glm-5.3-flash) 107 s finish=stop usage in 18626 / out 2817 usd~0.098 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0332 (ruling 32: snap outward)

## 1. What did they catch that I missed?

Honest accounting against the consensus:

- **K1 (SNAP_MAX_S drift vs package.SEG_MAX_S)** — I flagged the hard-coded 20.0 but did not note that the fix was already in the diff: `test_the_snap_limit_is_the_packagers_clip_limit` (test_ledger_build.py:504-506) asserts `LB.SNAP_MAX_S == PK.SEG_MAX_S`. I under-credited the diff. Agree, resolved.
- **K3 (is L-v 2's single-speaker rule blocking?)** — GLM's P1-2 was the sharpest question in Cycle 1: the 1.0 s marker margin leaves edge-adjacent speaker changes unmeasured *at the snap*, and the safety of that rests entirely on L-v 2 being a hard gate. The consensus answers it with code outside the diff (`transcript_truth.verify_segment: ok = cmp_["ok"] and turns["turn_change_inside"] is False`; `package_pin.REQUIRED_GATES` contains "second_pass"). I cannot verify that from the diff, but the consensus's citation is specific and consistent with the ruling's own text ("L-v 2 measures the speaker on the audio before the moment can be used"). I accept it as verified-by-consensus, noting it is outside my verification scope.
- **K4 (snap_risk mangles a non-list risk)** — I missed that the FIXED diff now raises TypeError explicitly (ledger_build.py:76-77) and that a test covers it (test:541-542). Resolved.

What I caught that they under-weighted: the **asymmetric strict inequality** in `marker_inside` (a marker at exactly `a+1.0` or `b-1.0` is *not* inside) and the fact that the test at :529 only exercises 0.5 s, never the 1.0 s boundary itself. That remains untested.

## 2. Agree / disagree on their key findings

| Finding | Verdict | Why |
|---|---|---|
| GLM P1-1 / K4 (non-list risk) | **Agree, resolved** | The fixed code raises TypeError at :76-77; `make()` counts it malformed; tested at :541-542. Fail-closed, L-j satisfied. |
| GLM P1-2 / K3 (L-v 2 backstop) | **Agree, with a caveat** | The consensus's citation is specific, but it is outside the diff. The ruling itself declares the 1.0 s margin "not a measurement at this stage; L-v 2 decides", so the design is internally consistent. Caveat: the *boundary* case (marker at exactly 1.0 s) is neither measured here nor provably measured by L-v 2 — see new finding N1. |
| GLM P1-3 (caption record changed between build and now) | **Agree it's a question, not a finding** | The cache key (`transcript_sha256`) is correct per the docstring; the staleness scenario is unverifiable from the diff. |
| GLM P1-4 / K1 (SNAP_MAX_S drift) | **Agree, resolved** | Test :504-506 pins the equality; the comment at :42 says "= package.SEG_MAX_S". |
| QWEN #2 (edge-time measurement) | **Agree** | `a, b` come from the snapped span's own word record (:112), the same clock `usable()` reads. Consistent. |
| QWEN #4 (`info["added"]` correctness) | **Agree** | Slice arithmetic at :120 is right; `E.spoken([])` → `""` is exercised by the test at :481 (`"after": ""`). |
| GROK (all P1s) | **Agree** | Its line-by-line confirms the ruling is implemented exactly, no more. |

## 3. New findings from this review

**N1 (P2) — the 1.0 s marker-window boundary is tested nowhere.** `marker_inside` (ledger_build.py:67) uses strict inequality: a marker at exactly `a + 1.0` or `b - 1.0` is *not* inside. The test at :529 exercises only `a + 0.5` and `b - 0.5`. If MARKER_EDGE_S's intent is "within 1.0 s of an edge counts as at-the-edge", the boundary case (exactly 1.0 s) silently falls to whichever convention the strict inequality picks, and no test pins it. Fail-open by declaration (L-v 2 decides), so P2, not P1 — but the ruling's "within 1.0 s" language and the code's "more than 1.0 s inside" are not the same predicate, and nothing catches a future edit that flips `<` to `<=`.

**N2 (P2) — `snap_risk`'s price check runs on every snapped moment, including rows whose risk list is absent.** At :79, `any((info or {}).get("snapped_words") or [])` — a row with `snapped_words = [0, 0]` (no snap) skips, correct. But a snapped row whose `risk` was `None` gets `out = []` then possibly `["price_prediction"]`. That is *correct* per the ruling (the miner flagged only the row's text; the snapped text is new), but it means the per-video cap (L-u, "at most one price prediction per video, counted from the moment's risk flags") now counts flags the miner never produced. If the cap's counter reads the *moment's* risk flags (it does, per the standing laws), a snapped moment can consume the video's one price-prediction slot on a flag the ledger's scores never ranked. This is exactly what the ruling intends ("Its price predictions: snap_risk()"), so it is not a bug — but it is a behavioral coupling between the snap and the cap that no test exercises end-to-end (the test at :533-542 tests `snap_risk` in isolation, never through `make()` → the cap). P2: the ruling is implemented, but the cap interaction is untested.

**N3 (P2) — `caps_v` caches `None` failures.** At :143-144, if `caption_source` returns `(None, why)` for a sha, that `None` is cached and every subsequent row with the same sha skips the lookup. That is *correct* (same record, same failure) but it means one transient store read failure at build time silently marks every row of that transcript as "no caption record" → no marker measurement at the snap → all deferred to L-v 2. Fail-closed overall (L-v 2 decides), so P2, informational.

**N4 (P2) — funnel.py's stage-0 regex duplicates the reason-string format.** funnel.py:249 parses `not_anchored` why-strings with `re.search(r"\((\d+) word\(s\) before (?:it|the anchored text),? and (\d+) after", why)`. That regex must track ledger_build.py:111's f-string (`"snapped outward to whole sentences ({left} word(s) before the anchored text, {right} after)"`) — note the diff's why-string at :111 says "before the anchored text" while the *old* format (which the regex's `(?:it|the anchored text)` alternation accommodates) said "before it". The alternation covers both, so it works today, but the coupling is by string-matching, not by constant. P2, test-infra only; funnel.py is explicitly not depended on by pipeline code.

**N5 (P2, informational) — the ruling's "same single speaker" is checked only by marker, never by the record's own speaker labels.** The word record's tokens may carry speaker labels (funnel_pre_edge.py:440 reads `w_.get("speaker")`), yet `reanchor` never consults them; the snap's speaker check is exclusively the caption-marker heuristic plus the L-v 2 backstop. If the word record's speaker labels are trustworthy, a cheap, stronger check was available and not taken. Not a defect — the ruling specifies the marker check — but worth noting as the one place where the implementation does less than the data allows.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| reanchor snap logic (20 s, marker, added-words) | pass | pass | Unchanged; N1's boundary case is the only softness, and it fails open by declaration. |
| snap_risk / L-u price cap coupling | pass (untested) | pass w/ note | N2: correct per ruling, but the cap interaction is only unit-tested, never through make() → the cap. |
| Non-list risk handling | fail-open (glm's finding) | pass | Fixed in this diff (:76-77), tested (:541-52). |
| SNAP_MAX_S drift | risk | pass | Test :504-506 pins it. |
| L-v 2 backstop for edge-adjacent speakers | unverifiable | pass by consensus | K3's citation is specific; outside my diff scope, noted as such. |
| Funnel tools | not assessed | pass | Read-only, replay=True, no pipeline dependence; N4's string coupling is test-infra only. |

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH** — none. (K3, the L-v 2-is-blocking question, is the only candidate; the consensus's citation resolves it outside the diff, and the ruling's own text declares the deferral. I do not have grounds to contradict it from the diff alone.)

**P2 MEDIUM**
1. **N1** — ledger_build.py:67 + test:529: the 1.0 s marker-window boundary (marker at exactly `a+1.0`/`b-1.0`) is untested; the ruling's "within 1.0 s" and the code's "more than 1.0 s inside" are different predicates. Add a boundary test pinning the strict-inequality convention.
2. **N2** — ledger_build.py:79 + :130: the snapped-moment → price-prediction → per-video-cap (L-u) interaction is unit-tested only in isolation; no test drives a snapped moment through `make()` to the cap. Add one.
3. **N3** — ledger_build.py:143-144: a `None` from `caption_source` is cached per sha; one failed read marks all of that transcript's rows as unmeasured-at-snap. Fail-closed via L-v 2; document or log it.
4. **N4** — funnel.py:249: the stage-0 reason regex is coupled to ledger_build.py:111's f-string by literal text. Test-infra only; acceptable, note it.
5. **N5** — informational: the word record's own speaker labels (visible at funnel_pre_edge.py:440) are never consulted at the snap; the ruling's "same single speaker" rests entirely on the caption-marker heuristic + L-v 2.

## 6. The single highest-leverage change

Add the boundary test for the 1.0 s marker window (N1) — it is the only place where the ruling's stated predicate and the code's actual predicate differ, and a one-line test pins the convention permanently.

## 7. Production ready?

**Yes with conditions** — both conditions are test additions, not code changes:

1. **N1**: a test that a marker at exactly `a + MARKER_EDGE_S` (and `b - MARKER_EDGE_S`) is *not* inside, pinning the strict-inequality convention the ruling's "within 1.0 s" language currently leaves ambiguous.
2. **N2**: a test that a snapped moment's `snap_risk`-added `price_prediction` actually reaches and is counted by the per-video cap (L-u) through `make()`, not just in isolation.

Everything else — the ruling's implementation, the 20 s limit, the marker deferral to L-v 2, the non-anchoring rows staying out, the verbatim snapped text, the unchanged dedup and window path, `snap_risk`'s add-only behavior — verifies from the diff and its tests. The consensus's K3 (L-v 2 as a blocking gate) is accepted on the strength of its citation, which I cannot independently check from the diff; if that citation is wrong, the 1.0 s margin becomes the weakest joint, which is exactly why N1's boundary test matters.