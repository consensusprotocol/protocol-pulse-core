# glm-5.3-flash (z-ai/glm-5.3-flash) 171 s finish=stop usage in 22498 / out 4881 usd~0.141 (upper-bound price)

# pp-selectid — CYCLE 2 AUDIT (speakers + batch + SEALED_LATER)

Scope note: I can only verify what the diff shows. `providers.py`, `package.py`, `eligibility.py`, `proof_ly.py`'s `meter`/`reply_meter`, and the store's `meta.json` schema are outside the diff; anything depending on their internals is marked uncertain.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **GLM's P1-1 (exception breadth in `attribute`)** — I flagged it as "verify against providers.py" but did not note that the fix was already visible in the diff: the `except Exception` at speakers.py:279-282 (diff lines 279-282) catches *everything*, and the test at test_speakers.py:768-773 proves a bare `RuntimeError` degrades to `unknown, measured=False`. GLM's concern is resolved in this diff; I under-credited that.
- **GLM's P1-2 (markdown fences)** — I said "verify whether the router strips fences; if not, systematic unknown bias." The diff answers it: `_json()` (speakers.py:223-229) strips a ```json fence, and test_speakers.py:762-766 proves it. I missed that the fix was in the reviewed code.
- **GROK's P2 on the intermediate JSON write** (package written before `attribute_package`, then overwritten) — I did not raise this. It's real but benign: `seal()` (proof_batch.py:407-421) re-reads the file, attributes, writes back, then pins from the same in-memory `pk`, so the file and the pin agree; the only exposure is a concurrent reader of the intermediate file, which the single-process driver doesn't have. GROK's proposed "must add speaker record before any intermediate JSON write" is already satisfied by the write-back at proof_batch.py:416-417.
- **QWEN's P1 on `_norm` substring matching** — I did not examine the normalization closely. Their "I wrote a book. About deflation" example is correct: `_norm` collapses punctuation, so a non-contiguous-in-original-text phrase can match. But note their example is actually *wrong* in one direction: "i wrote a book about deflation" IS a contiguous substring of the normalized "i wrote a book about deflation i said" — the words are in order. The failure they describe (re-ordered words) would NOT match; only punctuation-bridged phrases match. So the finding is weaker than stated: the basis is still a word-contiguous phrase in the original, just possibly spanning a sentence boundary. That's arguably within "verbatim, case and punctuation aside" as the docstring (speakers.py:184-186) claims. Partially agree; severity P2 at most.

What they caught that I also caught (cross-confirmation, no credit either way): the `to_pin`-vs-`check()` enforcement gap (GLM P1-3, QWEN P1-1) — now addressed by the new `speaker_problems` (K1).

## 2. WHERE DO I AGREE OR DISAGREE?

**K1 (to_pin shape-only check) — AGREE, and the fix is correct.** The new `speaker_problems` (package_pin.py:62-83) now requires: name non-empty, people list, measured bool, every person with name+line+role ∈ {host,guest,other}, a named speaker's line/basis non-empty, AND the named speaker present in `people` with the *same* line and role. That last clause (lines 79-82) is the one GLM wanted and QWEN wanted; it's there. The 4 new must-fail shapes in test_speakers.py:811-821 (people=[], wrong line, wrong role, role="speaker") each exercise a distinct branch. Verified: each of the 9 shapes in the test hits a different `elif` arm or the final `any(...)` clause. One residual: `speaker_problems` still cannot verify the *content* of `line`/`basis` against the source — but that's `check()`'s job at attribution time, and the evidence is sealed for the reader. Correct division of labor; I agree with the consensus disposition.

**K2 (unmeasured record reaches the pin) — AGREE with the disposition, one caveat.** The retry (proof: test_speakers.py:775-788, seeds [7,8] asserted) is real. The caveat: the retry condition at speakers.py:291 is `sp["why"].startswith("not measured")`. That's a *string-prefix* test on a message assembled at line 282 as `f"not measured: {type(e).__name__}: ..."`. It works, but it's fragile: if `check()`'s own `why` (set at lines 255, 257) ever legitimately began with "not measured", or if the failure message format changes, the retry silently stops happening. Also note: the *non-exception* failure paths (no source lines, no word record — lines 269, 272) return `why` NOT starting with "not measured", so they are NOT retried. That's correct (nothing to retry — no call was made, `r.calls == []` asserted at test line 795), but it's implicit, not documented. P2.

**K3 (role never verified against text) — AGREE, documented, correctly kept.** The role is the verdict's reading; code verifies name∈line, which is the checkable part. The docstring (speakers.py:133-135) now says so explicitly. Fine.

**SEALED_LATER (the integrator's ruling-1 fallout) — AGREE, this is the subtlest change and it's right.** The mechanism: `body_of` (package_pin.py:50-54) adds a SEALED_LATER key only `if k in s`. Earlier pins' segments lack `speaker` (and possibly the ruling-1 fields), so their seals recompute. The test at test_speakers.py:836-859 asserts (i) every existing MOMENTS_PIN*.json recomputes (n ≥ 6), and (ii) dropping ANY SEALED_LATER key from a new pin changes the digest. Both directions are tested. One subtlety verified: a new pin always carries all three because `to_pin` (line 98-103) copies `s.get("time_sensitive")`, `s.get("source_published_at")`, `s.get("speaker")` unconditionally — so a new pin's segments always have the keys, even when the *values* are None. Wait — that's the interesting case: `s.get("time_sensitive")` returns None if absent, but the key IS written into the pin segment (line 101), so `k in s` is True for new pins even when the value is None. For OLD pins, the key is absent entirely. So the discriminator is key-presence, not value. That's exactly what makes old pins recompute. Correct, but it means: **a new pin whose segment genuinely lacks `time_sensitive` (value None) seals differently from an old pin with the same logical content** — which is intended (new pins are self-identifying) but worth stating. No defect.

**GROK's concurrency P2 — DISAGREE with severity.** Single-process driver; the intermediate write is overwritten before the pin is made from the same object. Not a defect; at most a note.

**QWEN's memorial-mention P2 — AGREE, correctly dispositioned as documented.** "people" = named in the source's own lines, by definition (docstring line 133). A memorial mention IS a naming. Fine.

## 3. NEW FINDINGS (Cycle 2)

**N1 (P2) — `speaker_problems` accepts `measured: False` with a *named* speaker.** package_pin.py:71-82: the `measured` flag is checked only as `type(...) is not bool`; nothing requires `measured=True` when `name != "unknown"`, nor `name == "unknown"` when `measured=False`. A record `{"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me", "basis": "When I wrote it", "people": [jeff], "measured": False}` passes `speaker_problems` and seals. Is that wrong? Under the consensus reading ("unknown claims nothing; a named record with measured=False shouldn't exist per attribute()'s construction"), it's a laxness, not a leak: `attribute()` (line 283) only sets a name when `measured=True` (the success return), and the failure return (line 282) is always `name=UNKNOWN`. So the invariant holds by construction, but the *pin* doesn't enforce it. Since L-j says fail closed and the pin is the enforcement point, this is a P2: the record's self-claim (`measured`) is sealed but never cross-checked against its shape. Concrete scenario: a future refactor of `attribute()` returns a named record with measured=False (e.g. "measured from a replayed reply, confidence low") — the pin would silently accept it, and the reader couldn't distinguish. Nobody in Cycle 1 caught this.

**N2 (P2) — `_json` fence-stripping is one-sided.** speakers.py:226-228: if the reply starts with ```` ``` ````, it splits off the first line and cuts at the LAST ```` ``` ````. But a reply like ```` ```json\n{...} ```` (fence opened, never closed — a truncated reply) yields `t = t[:t.rfind("```")]` → since there's no closing fence, `rfind` returns -1... wait, check: `"```" in t` is the guard, so if there's no closing fence, `t` is kept whole — which then still contains the leading fence remnants? No: the first line was already split off (line 227), so `t` = `{...}` possibly with trailing whitespace. Actually for a truncated reply ```` ```json\n{...} ````, after line 227, t = `{...}`; the guard `"```" in t` is False, so t stays. Fine. But for a reply like ````text\n```json\n{...}\n``` ```` (a fence inside a fence, or a leading "text" line), the first line "text" is dropped and the rest parses. And for a reply that *ends* with a fence but doesn't *start* with one (e.g. `{...}\n``` `), the trailing fence is NOT stripped and `json.loads` fails → caught → unknown. Fail-closed, so P2, but the asymmetry (leading fence handled, trailing-only fence not) means a model that emits the closing fence without the opening one loses a good reply. Nobody caught this. Low impact: the retry (seed 8) gives it a second chance, and the failure is recorded in `why`.

**N3 (P2) — `attribute_package`'s retry doubles the cost of a *deterministic* failure.** speakers.py:291-292: the retry fires whenever `why` starts with "not measured", which includes *deterministic* failures (e.g. a chain whose env var is missing — every call fails the same way). For a 3-segment package with a dead chain, that's 6 failed call attempts, each potentially walking the full chain. Not a correctness issue; a cost/latency note. The spend ceiling (BATCH_LIMIT_USD=30, proof_batch.py:356) bounds it. Nobody flagged the cost.

**N4 (P2, uncertain — depends on providers.py) — `attribute`'s success path trusts `r.backend` and `r.replayed` without a contract.** speakers.py:283: `backend=r.backend, replayed=bool(getattr(r, "replayed", False))`. `backend` is accessed as a plain attribute (would AttributeError if the reply object lacks it — but that's inside the try? No: line 283 is *outside* the try/except, after it). Wait, re-read: the `try` covers lines 277-278 only (`r = router.call(...)` and `rec = check(...)`). Line 283's `r.backend` is outside. If `router.call` returns successfully but the reply object lacks `.backend`, AttributeError propagates out of `attribute` → out of `attribute_package` → kills the seal. But the test's `Reply` class (test_speakers.py:673-675) always sets it, and any real reply from `Router.call` surely has it. Uncertain, P2, "verify providers.py's reply contract includes `backend`". Note the asymmetry: `replayed` uses `getattr(..., False)` defensively but `backend` does not — inconsistent defensiveness in the same line, which suggests `backend` is contractually guaranteed. Probably fine.

**N5 (P2) — `context()` silently truncates at the record's edges, and `say(i, j)` for an empty range.** speakers.py:213-220: if `k0 == 0`, `a = 0`, and `say(0, -1)` → `i <= j` is `0 <= -1` → False → returns `""`. Good. If the record has 1 sentence and `k0=k1=0`: `b = min(0, 0+2) = 0`, `say(1, 0)` → `1 <= 0` False → `""`. Good. Verified: no IndexError path. But: `min(len(sents) - 1, k1 + after)` — if `k1` is the last sentence, `b = len(sents)-1`, and `say(k1+1, b)` = `say(len, len-1)` → `i <= j` False → `""`. Correct. No defect; noting I checked.

**N6 (P2) — the `log` line in `attribute_package` indexes `sp['basis']` for named speakers only via the conditional, but `sp.get('why')` for unknown — consistent.** proof: speakers.py:294-296. No defect. (Listed only because I verified it.)

**N7 (P1, uncertain) — `seal()`'s `body_of` uses `s.get("transcript_sha256")` but `to_pin`'s pin segment also carries it; however `speaker_problems` runs on `pk["segments"]` (the PACKAGE's segments), while the seal runs on the PIN's segments.** Are they the same dicts? In `proof_batch.seal()` (proof_batch.py:407-421): `pk` is loaded, `attribute_package` mutates `pk["segments"]` in place, then `write_pin(pk, ...)` — and `to_pin` (package_pin.py:90-103) builds NEW segment dicts (`segs = [...]` at line 97-103) copying `s.get("speaker")`. So the pin's segments are fresh dicts, but `speaker` is the same object reference. `seal()` then reads `s["speaker"]` from the pin's segment. Since `to_pin` copies it by reference, and `seal` serializes it, the sealed speaker is exactly what `speaker_problems` validated. Verified consistent. But: `to_pin` copies `s.get("speaker")` — if a package segment's speaker were mutated AFTER `to_pin` but before `seal`... in `write_pin` (not in diff) they're presumably sequential. Uncertain, depends on `write_pin`'s internals. Flagging as "verify": **the seal must be computed from the same speaker dicts that `speaker_problems` validated**; the diff's flow makes this true, but nothing enforces it.

Actually, let me reconsider N7's severity. `to_pin` itself: does it call `seal`? Looking at the diff, `to_pin` (lines 90-105) builds `segs` and `edl_vo` and then... the diff ends at line 105 with `edl_vo = {...}`. The seal call is presumably in the unchanged part of `to_pin` (the diff only shows the changed hunk, @@ -126,7 +157,7 @@ and @@ -135,6 +166,7 @@). The unchanged tail of `to_pin` presumably computes `package_sha256 = seal(segs, ...)` and returns the pin. Since `segs`'s `speaker` values are the same objects `speaker_problems` just validated, and nothing mutates them between, this holds. Downgrade N7 to P2-uncertain.

**N8 (P2) — test_speakers.py:836-859's "every earlier pin" test depends on the worktree's proof directory.** It globs `tests/package/proof/**/MOMENTS_PIN*.json` — if a fresh clone (or CI) lacks those fixtures, `n` = 0 and `assertGreaterEqual(n, 6)` fails. That's fail-closed (the test fails, not silently passes), so it's a P2 note, not a defect. But it means the test is environment-dependent: it passes only where the proof artifacts exist. The consensus (Claude's synthesis) says the integrator's `check_pin_only` recomputes from the worktree, so the artifacts are expected to be there. Acceptable.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---||---|
| speakers.check() | 8/10 | 8.5/10 | Fence handling and exception breadth (my two "verify" items) are proven in-diff by tests; the enforcement is stronger than I credited. |
| speakers.attribute/attribute_package | 7.5/10 | 8/10 | Retry proven; residual: string-prefix retry trigger (N1-adjacent), cost of deterministic-failure retries (N3), `r.backend` outside the try (N4). |
| package_pin.speaker_problems | 8/10 | 8.5/10 | K1 implemented exactly as the consensus wanted; residual: measured-flag invariant not enforced (N1). |
| seal / SEALED_LATER | 9/10 | 9/10 | Mechanism verified correct in both directions (old pins recompute, dropped field caught); key-presence-vs-value subtlety noted, intended. |
| proof_batch build/seal | 8/10 | 8/10 | GROK's concurrency concern is benign; delivered/avoid/exclude flow verified against L-p; no new defects. |
| Tests | 8.5/10 | 8.5/10 | Each test names its defect and would fail on it (checked the 9 must-fail shapes, the seed-7/8 sequence, the seal round-trip, the n≥6 glob). Environment-dependence of the n≥6 test noted (N8). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (Everything I'd have called P1 in Cycle 1 is either fixed in this diff with a proving test, or downgrades to P2 on inspection.)

**P2 MEDIUM:**
1. **N1** — package_pin.py:71-82: `speaker_problems` never cross-checks `measured` against the record's shape (a named record with `measured: False` seals). Invariant holds by construction today (speakers.py:282-283); the pin should enforce it. Add: `elif sp["name"] != "unknown" and not sp["measured"]` → problem.
2. **N2** — speakers.py:226-228: `_json` strips a leading fence but not a trailing-only fence; a reply ending in ```` ``` ```` without a leading one fails to parse → unknown (fail-closed, retried once). Strip both sides.
3. **N3** — speakers.py:291-292: the retry fires on deterministic failures too (dead chain → 2× calls per segment, all failing). Consider retrying only transient-exception classes, or accept the cost (bounded by BATCH_LIMIT_USD).
4. **N4 (uncertain, needs providers.py)** — speakers.py:283: `r.backend` is read outside the try; if the reply contract lacks it, one AttributeError kills the seal. `replayed` uses `getattr` defensively; `backend` doesn't. Verify the reply contract guarantees `backend`.
5. **N7 (uncertain, needs write_pin)** — the seal must be computed from the same speaker dicts `speaker_problems` validated; the diff's flow makes it true, nothing enforces it.
6. **N8** — test_speakers.py:836-859: the n≥6 assertion is environment-dependent (needs proof/ artifacts present); fails loudly, so acceptable, but note it in the test's docstring.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Enforce the `measured`-vs-shape invariant in `speaker_problems` (N1): it's the one place where the pin — the enforcement point the law L-j cares about — trusts a record's self-claim instead of checking it, and it's a two-line fix.

## 7. PRODUCTION READY?

**Yes with conditions:**
1. Add the `measured`-vs-shape check to `speaker_problems` (N1) — or state in the module docstring that the invariant is `attribute()`'s, by construction, and add a test pinning it.
2. Confirm (one-line answer, no code) that `Router.call`'s reply contract guarantees `.backend` (N4) — if not, use `getattr(r, "backend", None)`.
3. Confirm (one-line answer) that `write_pin` computes the seal from the same speaker objects `to_pin` validated (N7) — the diff's flow implies it; make it explicit.

Everything else (N2, N3, N8) is polish; ship without them if needed.

SHIP: yes with conditions