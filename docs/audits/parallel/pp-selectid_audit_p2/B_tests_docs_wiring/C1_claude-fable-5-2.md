# claude-fable-5-2 (effort high) 465 s stop_reason=end_turn usage=in 52110 / out 44044

**Reviewer note:** I am Claude, not one of the three models named in the header; record that if the audit trail depends on which models reviewed.

**Scope limit:** the diff contains the design doc, the R7 patch text, tests and harnesses only. None of the reviewed modules (`providers.py`, `moments.py`, `package.py`, `vo_fidelity.py`, `context_integrity.py`, `package_pin.py`, `transcript_truth.py`, `moments_gate_adapter.py`, `model_providers.json`) is in it. For Q1–Q4 I can only verify what the tests pin and what the doc and patch state. The Flask/DB/load rules do not apply (no routes, no queries).

## Scores

| Q | Score | Basis |
|---|---|---|
| Q1 fail-open | 35 | The decision rules of the context gate and the fidelity verdict are tested well. `package.build`, which composes the gates, has no test, and the R7 wiring checks two self-reported flags. |
| Q2 vendor separation | 45 | The router honours `avoid_vendor` on a single call. Nothing covers writer failover, a rewrite by a fallback writer, precomputed step A, or coherence. |
| Q3 verbatim / model text | 40 | Mostly unverifiable here. One visible path (`pin["label"]` into the EDL) is unexplained. |
| Q4 deterministic rules | 30 | Of the rules asked about, only PRICE_NOW, `current_levels` and DUPLICATE have a test here; the other nine have none. |
| Q5 tests + R7 | 50 | The patch refuses the cases the smoke test exercises. It accepts several it does not exercise, and some assertions are vacuous. |

## FINDINGS

### P0

**P0-1. The pin's gate evidence is self-reported and bound to nothing (R7 patch).**
```
edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
           moments_checks=mp.get("checks"))
```
- The sha is copied, never recomputed. `smoke_r7.py` shows this: it runs `pin["moments_package"]["checks"].update(vo_fidelity_ok=True, context_integrity_ok=True)` after `to_pin`, and `build_edl` accepts the result.
- Nothing ties `pin["segments"]` to the package's segments.
- Failing input: change `segments[1].approved_text/start/end` to another sentence of the same video, or edit `edl_vo.intro` or `title`, and leave `checks` alone. The EDL builds and carries `moments_checks` saying both gates passed.
- R7 item 4 then tells release authorisation to trust `edl["moments_checks"]`. That conflicts with L-j ("on exactly the bytes") and with R7's own L-t line ("any change after the gates re-runs them").
- I cannot see whether a later stage re-verifies. R7 gives no patch for `release_auth` or `run_fresh`, and item 2 ("TONIGHT") runs before items 3–4 exist.

**P0-2. The wiring requires two of the hard gates; the second recognition pass is not requested.**
- `moments_vo` checks only `vo_fidelity_ok` and `context_integrity_ok`. Design §4b also lists DUPLICATE, PRICE_NOW, runtime and L-v 2 as hard. The diff does not show whether these are folded into the two flags.
- R7 item 3's production call is `package.build(router, mined["moments"], sources, ctx, delivered=…, optout=…)`, with no `truth_dir`.
- `proof_packages.py` shows `truth_dir=None` by default, with help text "run law L-v 2's second recognition pass".
- So, as specified, a package reaches the pin without L-v 2, and nothing downstream asks for evidence of it. Design §8 admits L-v 1/2 are open.

### P1

**P1-1. Truthiness instead of exact values (R7 patch).**
- Code: `if not mp.get("checks", {}).get("vo_fidelity_ok") or not …`.
- Failing input: `{"vo_fidelity_ok": "false", "context_integrity_ok": "uncertain"}` is accepted, as is `{"ok": false}` in either slot. L-l and L-j require exact `True` / `'PASS'`.
- `"checks": null` raises `AttributeError`, not `PinError`.

**P1-2. A malformed package silently becomes a plain pin (R7 patch).**
- `if isinstance(mp, dict):` means `"moments_package": []`, a string or `null` falls through to `_generate_vo_script`. A machine pin then renders as an ordinary pinned run with no `moments_checks` (M12).
- `v = mp.get("edl_vo") or {}` means a missing `edl_vo` yields `{"intro": None, "bridges": []}`. The gates judged a package with a VO; the render has none.
- The EDL keeps `"mode": "pinned"`. Nothing marks it as machine-decided for downstream gates that may assume a human approved a pin.

**P1-3. `package.build` has no test in this diff.**
- This is the composition Q1 asks about: three rewrites, plain-VO fallback, drop-and-repack, coherence, L-v 2, ranking.
- Only the live-model proof drivers call it. Coherence has no test at all.
- Arithmetic worth testing: `test_angles` accepts a 40 s line-up as in range. The plain VO in the fixtures is about 9 words (3.5 s at 2.6 words/s). 40 + 7.4 + 3.5 ≈ 51 s, below 60. Either the plain fallback cannot ship there or runtime is not applied to it; no test says which.

**P1-4. "Ran on nothing" inputs are untested (`test_gates.py`).**
- `Canned(fidelity_verdict=[{"claims": []}])`: "every claim yes" is vacuously true.
- Claims covering only one of several lines.
- `relations=[]` for a cross-video pair.
- `referents: []` on text with pronouns.
- A missing C pair or B takeaway (only a missing A excerpt is tested).
- `support: [{"segment": "m1", "words": "Bitcoin"}]`: a one-token verbatim run.
- `{"segment": "manifest", "words": "<anything>"}`: only the positive manifest case is tested.
- `VF.check(...)` is called without `current_levels`; whether PRICE_NOW is then skipped or rejects is unpinned.

**P1-5. Missing speaker measurement counts as usable (`test_moments.py`).**
- `pm()` sets `"speaker": {"turn_change_inside": None}`.
- `test_over_20_s_…` asserts `[m["moment_id"] for m in ok] == ["f"]`, so an unmeasured moment is usable.
- That is "missing data produces a pass" (M12) unless L-v 1 authorises it; that law is not in my package.

**P1-6. Vendor separation is tested only for the easy case.**
- `test_a_clean_package_passes…` asserts `all(v == "openai" for _, v in r.calls)`. This proves the argument is forwarded. It does not check call count or roles, and `Canned` always replies with vendor `"fake"`, so the gate's handling of a same-vendor reply is never exercised.
- No test covers: writer attempt 1 on vendor X, failover, rewrite on vendor Y, verdict avoiding Y.
- No test covers step A, which runs "once (package-independent)" before any writer exists.
- `test_the_shipped_config…` compares only `chain[0]` against `chain[0]`, and omits `coherence_verdict` and `exclusion_verdict`.
- Heimdall is a gateway, so a config `vendor` label may not identify the underlying model's vendor. Unverifiable here.
- Failover on a contract violation: the tests show failover only on `Unavailable`. I cannot confirm the negative.

**P1-7. Vacuous or tautological assertions.**
- `test_a_short_clip_only_as_the_punchline`: `if seg and any(...)` passes when `seg` is `None` or omits `d`.
- `test_at_most_one_price_prediction_per_video`: every possible set contains both predictions, so a correct implementation returns `[]` and the loop body never runs. It also passes if `[]` is returned for any other reason. Add a fourth non-prediction moment and `assertTrue(sets)`.
- `lo, hi = PK.content_range()` is used as its own oracle in two tests. The 60–70 s / FIXED_S / WPS constants are never asserted as literals.
- Every `pm(...)` call uses `hook=True, clip=True`, so role eligibility in the packager is never exercised.
- `({"angles": []}, "angles")` matches almost any message.

**P1-8. `yield_table.py` fails open and reports unread verdicts.**
- A missing oracle directory gives `mp = 0`, so `defect = "DEFECT (L-n)" if mp and not pk else ""` reports no defect. `day = run.replace("fresh_", "")` yields `20261106_213852`; if the oracle is keyed by date, every row reads 0.
- `gates = "VO fidelity PASS, context integrity PASS"` is a literal, not read from `pk["checks"]`.
- This table is a DONE criterion.

**P1-9. Governance I cannot audit.**
- R7 item 4 replaces the same-event/topic gates for one run class, and `moments.py` / `package.py` are a new selection mechanism.
- Against the laws supplied (LAW 20/M2, M1), both need explicit authority.
- The laws cited for them (L-n through L-x) are not in the package given to reviewers.

### P2

- **Doc contradicts tests:**
  - §4b says "4-8 cleared moments"; `test_angles` accepts three and expects `"3-8"`.
  - R7.4 says "every segment names it by rule"; §3 says "within one sentence of a Bitcoin mention".
  - Step A's `time_ok` is tested but not in §6.
  - R7.5 covers a hook under 8 s at R5 but not the punchline clip under 8 s.
- **Possible silent repair:** `angle(["a","e","zz"])` is rejected with "3-8", not as a fabricated id. Test `["a","b","c","zz"]`; if it passes, an unknown id is being dropped silently.
- **`ab_verdicts` is not blinded** the way `run_exam_record.blind` is. `origin`, nested `provenance` and the real `id` reach the gate, and those tables drive L-x chain ordering.
- **`proof_packages.run_one` with `--want 2`:** each `write_pin` targets the same `MOMENTS_PIN.json`, then `os.replace` moves it to `_alt1`. The top package's pin is gone, assuming the fixed filename the rename code implies.
- **Spend guard overshoots:** the test pins $20 spent against `limit_usd=15`.
- **`smoke_r7.py` is single-use:** once R7 is applied the patch no longer applies, and no standing unit test for `moments_vo` remains.
- **Bridge validation:** `after_clip: True` or `1.0` passes `in idx`, and two bridges with the same `after_clip` are accepted.
- **L-l:** `quotable=3.0` is rejected, though L-l lists an integral float as a harmless variation. This fails closed.
- **Harness hard-codes names:** `"local:gemma3:27b"` appears in `ab_roles.py`. `ENV = "/home/ultron/protocol_pulse/" + "." + "env"` looks written to dodge a scanner; explain or remove.

## Q3: what the diff shows

- `"topic": pin["label"], "angle": f"Pinned: {pin.get('headline') or pin['label']}"`. What `package_pin.to_pin` puts in `label` / `headline` is not shown. If it is the model's angle sentence and anything renders `topic`, that is model text on screen that the fidelity gate never checked. Please confirm.
- `smoke_r7` fakes `"approved_text_similarity": 1.0`. If the real locator accepts a similarity below 1, the words the gates judged can differ from the words cut. The moment's `transcript_sha256` is not checked in the patch.
- Whether the plain VO's topic labels (assigned by the miner) pass the fidelity gate is not shown.

## Q4: concrete inputs

These follow from the design text; the code is not shown, so they are inputs to test, not proven failures.

- **QUOTE and verdict support.** Source "I don't think Bitcoin is going to zero"; quoted run "Bitcoin is going to zero". It is a verbatim run, and the meaning is reversed.
- **ATTRIBUTION.** The fixtures use `speaker` = channel name ("Stephan Livera"). "Natalie Brunell says X" passes when her guest said X. "Attribution is to the show" does not protect eponymous channels.
- **NUMBER.** "Number words <= 10 without a unit are counts": source "four ETFs", VO "seven ETFs" passes. This loosens a rule despite "no rule loosened" (LAW 20). Also "dropped to $73,000" against VO "climbed to $73,000".
- **NAME.** Skipping sentence-initial and Title Case: the title "BlackRock Dumps Bitcoin" has no NAME check and no listed framing verb. The "9-case check" is not in the diff.
- **RELATION.** The test line "One voice calls Bitcoin undervalued while it found support" passes across two videos. "because", "after" and "in response" are likely to pass too.
- **FRAMING.** The closed list misses "torches", "blasts", "debunks", "panics".
- **TIME / PRICE_NOW.**
  - "ETF outflows hit $1.3 billion" from a 60 h source is neither a time word nor a price.
  - Bridges are outside PRICE_NOW.
  - "From the 2022 low, Bitcoin is now at 126K": does the history marker clear it?
- **`current_levels`.** "Bitcoin is down forty percent from its 126 thousand high" is present tense and under 24 h old. If 126000 becomes a current level, R8's own title passes again. Also "Gold is trading at four thousand dollars", and an empty levels list.
- **DUPLICATE.**
  - As stated, only the adjacent line and the title are checked. An intro repeating clip_02 passes, and R8 case 2 says the intro repeated clip_03.
  - A one-word swap every four tokens passes.
  - The title branch and the 4-versus-5 token boundary are untested.
  - The test labels the intro "before hook", while the D1 law implies the hook starts playback. If the intro actually precedes clip_01, it is compared with the wrong neighbour.

## Q5: R7 verdict

- **Refuses:** a bridge after the last clip, a bridge after the hook (0 is not in `idx`), an empty intro, and a false context flag. Only the first and last are tested.
- **Plain pin:** unchanged by construction (same key order), apart from one discarded `_generate_vo_script` call on moments pins.
- **Does not refuse:** P0-1, P1-1 and P1-2 above.
- The hunk header counts (20 / 45) match the patch as shown.

## Single highest-leverage change

Seal the package at the pin boundary, the way `release_auth` seals the finals.

- `build_edl` recomputes `package_sha256` over the segments (`video_id`, `start`, `end`, `text`, `transcript_sha256`), `edl_vo`, title, caption and an exact gate inventory.
- The inventory covers fidelity (deterministic and verdict), DUPLICATE, PRICE_NOW, context A/B/C, runtime and L-v 2. Each row must be exactly `'PASS'` with executed evidence.
- It refuses any non-dict package, and any pin segment that is not the package's.
- Ship it with an offline mutation-family test that drives `package.build` through a canned router: one failed, unreadable, empty or raising gate per case, asserting no package comes out.