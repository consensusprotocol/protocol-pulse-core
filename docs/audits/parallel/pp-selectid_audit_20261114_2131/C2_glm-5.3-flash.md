# glm-5.3-flash (z-ai/glm-5.3-flash) 158 s finish=stop usage in 21725 / out 5237 usd_reported=0.001323 usd~0.144 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261114_2131 (final)

**Context:** I'm the second reviewer. My Cycle 1 output is referenced but not shown; I'll treat the Grok/QWEN findings and the consensus file as the Cycle 1 record and audit the FIXED diff fresh, then reconcile.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest, reviewing the fixed diff against the Cycle 1 record:

- **The `times()` spacing change (Grok/QWEN P3, diff line 238).** The `last - 0.25` → `last - 0.01` change is subtle: with `EVERY_S=1.0`, a clip of duration 5.0 now yields `[0.0, 1.0, 2.0, 3.0, 4.0, 4.95]` — the last frame at `dur-0.05`. I would likely have skimmed this as "cosmetic"; it's actually load-bearing for the "no gap exceeds a second" ruling, and the new test at line 651 (`assertLessEqual(max(b - a ...), 1.0 + 1e-9)`) pins it. Caught by them, correctly.
- **The `COLS` addition to the cache key (line 222).** Adding `COLS` to `key()`'s `inputs` is required for the "a hit is used only on the same sheet bytes" invariant once the sheet geometry changed. Easy to miss because the diff hunk is one line inside an unrelated-looking hunk.
- **The `test_medley.py` / `test_spotlight.py` fixture-version updates (lines 451, 588, 607).** These are not cosmetic: `layout_block` now *rejects* records whose `version != VERSION`, so every fixture that feeds `layout_block`/`clean_visual` through the new guard must carry `version: VP.VERSION` or the suite fails. If the fixtures had been missed, the tests would have been green-but-vacuous. They updated them; I'd have flagged the risk, they just did it.

What nobody caught in Cycle 1 that I should have: **the `sealed()`/`formats` interaction with `visual_for`'s conditional** (see new finding N1 below) — it's visible in the diff at lines 332 and 324 and neither reviewer traced it.

---

## 2. AGREE / DISAGREE ON THEIR KEY FINDINGS

**Grok P1 (version guard breaks frozen references / L-d, LAW 22) — DISAGREE, refuted by the consensus.** The consensus grep shows no reference/preview check path calls `layout_block`/`clean_visual`: the guard runs only at this builder's pin stage for new pins. Grok's finding was plausible but wrong; the consensus evidence (grep of `check_preview_reference.py`, `regression.sh`, `release_auth.py`, `pinned.py`, `run_fresh.py`) is decisive. I agree with the refutation.

**QWEN P1 (stripping `formats` leaves the seal valid) — DISAGREE, refuted.** `pin_seal` passes `formats=mp.get("formats")`; a stripped pin hashes a body without the key, so the digest differs. The test at lines 417–419 (`del dropped["moments_package"]["formats"]` → `assertNotEqual`) pins exactly this, and mutation F3 (recompute ignoring formats) is killed. QWEN's reasoning ("because the rest of the body is identical, the SHA will match") is simply wrong — omitting a key from a `json.dumps(sort_keys=True)` body changes the bytes. I agree with the refutation.

**Grok P2 (tail_variant mutates caller's `moments` dict) — AGREE, and it's FIXED.** Lines 124–131: `for_pool` now appends `dict(m, derived_from={...})` — a copy — and the test at line 559 (`assertNotIn("derived_from", m)`) pins the caller's record untouched. Resolved.

**Grok P2 (RENDER_16X9_ONLY hard-coded) — PARTIALLY AGREE.** It's still a module constant (line 167), not a config flag. But the comment (lines 167–170) documents the flip-in-one-audited-change contract, and the test at line 691 uses `mock.patch.object(VP, "RENDER_16X9_ONLY", True)` — so the flag is *testable* at its current seam. Downgrade to P3; the "one audited change" framing is consistent with this codebase's governance style. QWEN's P3 agrees.

**Grok P3 (ROLE_RE verb false positives: "hosts 500 people", "Bitcoin anchors the economy") — PARTIALLY AGREE, now worse than they said.** The consensus says the hyphen/plural stripping was replaced by `canon.canon_tokens(w)[-1]` — so "hosts" → "host", "anchors" → "anchor". But the regex still matches the *verb* "hosts" in "The event hosts 500 people", and the gate then demands the cited clip's words contain "host". QWEN's P2. The new test at lines 518–520 (`test_words_that_only_contain_a_role_are_not_roles`) tests "He is hosting nothing." — which passes only because "hosting" → "host" via canon... wait, "hosting" → canon → "host"? If canon strips "ing" it's caught by the `\b...s?\b` regex? No: "hosting" doesn't match `hosts?` — the regex requires "host" or "hosts" exactly. "hosting" doesn't match. So "He is hosting nothing." has no ROLE_RE match, `roles` is empty, no ROLE violation — the test passes *vacuously* (no role word at all, so it tests nothing about the role gate). That's a weak test, not a defect. Still: "The event hosts 500 people" → "hosts" matches → canon → "host" → if the clip's words lack "host", ROLE fires. Real, but fail-closed, so P2.

**Grok P3 (ROLE_RE is an ad-hoc normalizer outside canon, L-k) — AGREE, resolved.** The consensus says the comparison now uses `canon.canon_tokens(w)[-1]` (line 354), and the test at 512–516 pins canonical comparison ("an ANALYST" vs "Analyst here."). The plural "analysts" → "analyst" via canon... the test at line 516 says "analysts" IS another word (ROLE fires). So canon does NOT strip plurals — "analysts" → "analysts" ≠ "analyst". Consistent. Resolved as designed; the L-k concern is answered by routing through canon.

**Grok P3 (test_role_claims example-driven) — AGREE, still true.** Lines 491–495 iterate 6 lines × 4 slots; "commentator", "panelist", "interviewer", "economist", "presenter" have no test. P3.

**QWEN #4 (times() edge case) — AGREE, correct.** Their trace is right; the 0.01 change is safe.

**QWEN #5 (formats_of "intersection") — AGREE, correct.** Any-16x9-only → `["16x9"]` is the correct intersection of {16x9, 9:16} sets. Their reasoning is sound.

**QWEN's answers to (1) and (2) — AGREE.** (1) `layout_block` (line 313) holds any record where `formats(rec)` is truthy while `RENDER_16X9_ONLY` is False, and `clean_visual` (line 91) requires `not VP.layout_block(v)`, so a 16:9-only clip is never clean → never packaged → never sealed. (2) ROLE: fail-closed both directions — no role word → `roles` empty → no check → no violation; role word without cited-clip support → `bad` non-empty → `V("ROLE", ...)`.

---

## 3. NEW FINDINGS (nobody caught these in Cycle 1)

**[P1] N1 — `visual_for` computes `formats` on a record that lacks the model's `burned_in` truncation, and `sealed()` carries `formats` only if the key exists — but the *conditional* at line 332 means a 16:9-only verdict whose `formats()` returns `["16x9"]`... actually, trace it:**

Line 332: `**({"formats": formats(dict(v, measured=True))} if formats(dict(v, measured=True)) else {})`. `formats()` returns `["16x9"]` or `None`; the conditional adds the key only when truthy. Fine. But `sealed()` (line 324) copies `"formats"` from the record *if present* — and `layout_block`'s hold (line 313) reads `formats(rec)`, which re-derives from `burned_in`, NOT from the sealed `formats` key. So the *derivation* is duplicated: `formats()` is the single source of truth, and `sealed()`'s copied key is decorative at the visual-record level. That's consistent, not a bug. **However:** `package_pin.formats_of` (line 28–31) reads `s["visual"]["formats"]` — the *sealed* key — while `visual_pin.formats()` derives from `burned_in`. Two functions, same name, different inputs. If a future record carries `burned_in` with a cut caption but the sealed `formats` key was stripped (e.g., by an older `sealed()`), `formats_of` returns None and the pin seals as both-formats while `layout_block` would have held it. Today the chain is consistent (both written in this diff), but the invariant "the sealed `formats` key agrees with `burned_in`" is enforced nowhere — no test pins that `sealed()`'s output, fed to `formats_of`, matches `formats()`'s derivation. **P2** (a consistency invariant, not a today-bug; the diff's own tests exercise both sides but never the join).

**[P2] N2 — `check()`'s caption-`at` truncation `[:TILES]` (line 265) silently drops frame times.** `sorted({round(float(a), 2) for a in x["at"]})[:TILES]` — a caption showing at 50+ times (a 35 s clip, one a second, animated word-by-word) yields up to 40+ times; the truncation keeps the first 40 sorted. Harmless for the gate (formats() reads `in_9x16`, not `at`), but the *flag* carries a silently-truncated `at` (line 281), and the prompt promises "the frame times it shows in". The record's `burned_in_truncated` flag exists for exactly this and is NOT set when `at` is truncated. Minor honesty gap in the sealed record. P3.

**[P3] N3 — `test_the_stills...` (line 653) `self.assertEqual(len(VP.times(60.0)), VP.TILES)` — with EVERY_S=1.0 and TILES=40, a 60 s clip generates 60+2 candidate times, truncated to 40; the test pins the count but not WHICH 40.** The "first and last always kept" property is pinned for ≤35 s spans (line 650) but not for the >TILES truncation path. A regression that keeps the first 40 and drops the last frame would pass. P3.

**[P2] N4 — the ROLE gate's `shows` set (line 356) is built from `meta` — but `meta` here is the *manifest* (channels + date), not the cited clip's show.** Trace: `shows = {t for n in meta for t in canon.canon_tokens(n)}`. If `meta` is `{"channels": [...], "date": "2026-11-14"}`, then `canon_tokens("2026-11-14")` yields... whatever canon does to a date string. If it yields "2026", "11", "14" or "20261114", those tokens join the `shows` set — harmless (a role word would never be "2026"). But if `meta` iteration yields the *date string* and canon returns it as one token, also harmless. The real question: does the show-credit exemption (test at 504–510) work when the *line* names the show but the *manifest* doesn't list that channel? Test at 507 passes "Analyst Answers" in `meta["channels"]` AND in the line. If a line credits a show whose name contains a role word but the channel isn't in the manifest... the test doesn't cover it. Fail-closed (ROLE fires), so P3. Actually — wait, the consensus says "a role word inside a show or channel name the line credits is no claim (manifest_terms)". If `meta` is the manifest, `manifest_terms` presumably extracts channel names; the test's `MAN` includes the channel. The exemption depends on the manifest listing the channel, which the NEEDS_SOURCE/manifest machinery already guarantees for credited shows. Fail-closed. P3.

**[P2] N5 — `proof_ledger.directives()` (lines 370–377) — the new dual-form acceptance.** The condition: `((isinstance(d.get("ends"), str) and d["ends"].strip() and "reseal" not in d) or (d.get("reseal") is True and "ends" not in d))`. A directive with BOTH `ends` and `reseal: true` is dropped (the test at 575–577 pins this: `dict(good, parent="2"*20, ends="...Roth IRA.")` — wait, that dict has BOTH `ends` AND `reseal: true` (inherited from `good` via `dict(good, ...)`), and it's expected to be DROPPED. And `dict(good, parent="1"*20, reseal="yes")` has BOTH `ends` (from good) AND `reseal="yes"` (not exactly True) → dropped. Correct: both-rows dropped, "yes" dropped. But note `dict(good, parent="1"*20, reseal="yes")` — `good` has `reseal: True`; overriding with `reseal="yes"` gives `reseal="yes"`, and `"ends" not in d` is False (good has ends) → first branch: `"reseal" not in d` is False → fails; second: `reseal is True` fails ("yes" is not True) → dropped. ✓. And the both-rows case: `ends` present, `reseal` present-True → branch 1: `"reseal" not in d` False → fails; branch 2: `"ends" not in d` False → fails → dropped. ✓. The strictness is right and the test pins it. But: **a *variant* directive (with `ends`) that also carries a stray `reseal: false` key is silently dropped** — `"reseal" not in d` is False, and branch 2 needs `reseal is True` → dropped. A variant row with `reseal: false` (a perfectly reasonable "explicitly not a reseal" annotation) fails closed. P3, fail-closed, but the "both: never guessed" comment (line 576) suggests intent; the `reseal: false`-on-a-variant case is an untested edge. P3.

**[P2] N6 — `test_formats.py` line 411: `only["segments"][1]["visual"] = dict(only["segments"][1].get("visual") or {}, formats=["16x9"])` — this injects `formats` into the *segment's* visual record directly, bypassing `visual_pin.sealed()`.** So the test proves `formats_of`→`seal`→`pin_seal` round-trips, but NOT that a real `visual_for`-produced record, passed through `sealed()`, carries `formats` into the segment. The join (N1) is again untested end-to-end: `visual_for` → record → `sealed()` → segment → `formats_of` → seal. The consensus's refutation of glm P1-33 asserts the chain "visual_for → m["visual"] → sealed() → the segment → package_pin.formats_of" — but no test in this diff exercises it. **This is the highest-leverage missing test.** P2.

**[P3] N7 — `spotlight.inventory`'s `format=str((src_rec.get("layout") or {}).get("layout") or "").upper() or None` (line 111).** If `layout` is already "CONVERSATION" (uppercase), `.upper()` is a no-op; if it's "conversation", it's uppercased. But the consensus (refuting glm P1-5) says `check_layout` validates against LAYOUTS — so the value is already canonical. The `.upper()` is defensive; `or None` maps `""` → None. Fine. But: the gate row's key is `format` while the record's key is `layout` — a naming inconsistency that will confuse the integrator's format-aware release (which keys on "formats"). P3.

**[P3] N8 — the prompt's face-margin rule ("a tenth of the frame's width from either edge") is asserted nowhere in `check()`'s contract** — `check()` validates `in_9x16 ∈ IN_9X16` but never the margin. Grok's Cycle 1 P3 (LLM variance on the "whole/cut" verdict) stands; the margin is prompt-only, unverifiable. Fail-closed via the hold. P3.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| package_pin (seal/formats) | — | PASS | QWEN's P1 refuted with evidence; test 417–419 + mutation F3 killed. `formats`-in-body-when-present is byte-identical for old pins (test 426–429: the frozen spotlight recomputes). |
| visual_pin (visual-3) | — | PASS w/ notes | Version guard, hold, formats() derivation all correct; N1's join untested, N2's `at` truncation silent. |
| vo_fidelity (ROLE) | — | PASS w/ notes | Canon-routed, fail-closed both directions; verb-matching (Grok P3) remains a real false-positive source, P2. |
| tail_variant + proof_ledger (reseal) | — | PASS | Mutation fixed (copy, not in-place); directive parsing strict, both-rows dropped, test 571–578 pins it. |
| spotlight (clean_visual, gate row) | — | PASS | burned_caption exempt; format recorded; `.upper()` defensive but harmless. |
| Tests | — | GOOD, one gap | Thorough; the visual_for→sealed→formats_of→seal end-to-end join (N1/N6) is the missing test. |

Nothing changed my assessment materially; the Cycle 1 P1s were both refuted, so the diff is stronger than the Cycle 1 record suggested.

---

## 5. FINAL PRIORITY LIST

- **[P1] — none.** Both Cycle 1 P1s (Grok's version-guard/L-d, QWEN's seal-stripping) are refuted by the consensus evidence and by the tests/mutations. No new P1 found.
- **[P2] N1/N6 — the untested join: `visual_for` → record → `sealed()` → segment → `package_pin.formats_of` → `seal`.** Add one test: a `visual_for`-shaped record with a cut caption, passed through `sealed()`, into a segment, through `to_pin`, asserting `mp["formats"] == ["16x9"]` AND that the sealed `formats` key agrees with `visual_pin.formats()`'s derivation from the same `burned_in`. (test_formats.py, after line 419.)
- **[P2] ROLE_RE verb false positives** (vo_fidelity.py, line 344–346; Grok P3/QWEN P2): "The event hosts 500 people" fails when the clip's words lack "host". Fail-closed, so it blocks valid lines. Either require noun context or accept the flakiness documented.
- **[P3] N2 — `at` truncation past TILES is silent** (visual_pin.py, line 265): set `burned_in_truncated` (or a dedicated flag) when any item's `at` is cut.
- **[P3] N3 — the >TILES truncation path of `times()` is untested for "last kept"** (test_visual_pin.py, line 653).
- **[P3] N5 — a variant directive carrying `reseal: false` is dropped** (proof_ledger.py, lines 374–375); fail-closed, untested edge.
- **[P3] N7 — gate key `format` vs record key `layout` vs package key `formats`** (spotlight.py line 111, package_pin.py line 73): three spellings, one concept. Document or align before the integrator's format-aware release.
- **[P3] Grok — test_role_claims covers 6 of 11 role words** (test_role_claims.py, lines 491–495): "commentator", "panelist", "interviewer", "economist", "presenter" untested.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the end-to-end test of the formats chain — `visual_for`'s record → `sealed()` → the segment → `formats_of` → `seal` → `pin_seal` — because every other guarantee in this diff (the 16:9-only ruling, the hold, the integrator's recompute) depends on that one untested join, and it is exactly where the two same-named `formats` functions (visual_pin's derivation vs package_pin's consumption of the sealed key) could silently diverge.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

1. **Before merge:** add the end-to-end formats-join test (N1/N6) — the sealed `formats` key must provably agree with `visual_pin.formats()`'s derivation, through `to_pin`, for a cut-caption record.
2. **Before the integrator's format-aware release (not this merge):** (a) flip `RENDER_16X9_ONLY` in the same audited change that seals the first 16:9-only pin, as the comment at visual_pin.py:167–170 promises; (b) resolve the ROLE_RE verb false-positives or document the accepted flakiness; (c) align the `format`/`layout`/`formats` spelling (N7).
3. **No P0/P1 outstanding.** Both Cycle 1 P1s are refuted with evidence; the diff's own tests plus the killed mutations (F3, the stripped-formats case, the reseal-copy case) cover the ruling's guarantees. The frozen spotlight pin recomputes to its own sha (test 426–429), so no existing pin is disturbed.

P1_OR_WORSE: 0