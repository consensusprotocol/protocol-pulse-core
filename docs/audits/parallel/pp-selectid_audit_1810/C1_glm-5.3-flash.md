# glm-5.3-flash (z-ai/glm-5.3-flash) 415 s finish=stop usage in 13482 / out 10082 usd~0.192 (upper-bound price)

# Audit: pp-selectid-1810 (RULING 76 — 12 h window, expiry, render-clock re-check)

## P0 findings

None found. Every path I can trace enforces the 12 h window.

## P1 findings

**P1-1 — `package.usable()` (package.py, diff lines 110–115): same-speech check runs before the opt-out / duration / expiry checks, and its `why` message can mask the ruling-76(a) reason; more importantly, the same-speech branch is evaluated before `expired(m, ctx.now)`**

Order of `elif` arms in `usable()`:

1. delivered-id / overlap → 2. **same-speech (new)** → 3. opt-out → 4. duration → 5. time-sensitive (L-v 3) → 6. **expired (new)** → 7. speaker-change → 8. usable.

Concrete scenario: a moment that is both over 12 h old **and** the same speech as a delivered clip in another video reports `why = "ruling 76 (b): the same speech as a delivered clip …"`, not "ruling 76 (a)". Both exclude, so the moment still cannot enter a line-up — the ruling's *effect* holds on every path. But the STATE/record's `why` attribution is order-dependent, and the ruling-76(d) count `inside_12h` is computed independently in the driver (`sum(not PK.expired(m, now) for m in moments)`), so the counts and the `why` reasons can disagree about *why* a moment is out. This is a reporting-accuracy issue, not a leak; P1 because the ruling requires the stage that dies to be *reported*.

**P1-2 — `same_speech` (package.py, diff lines 67–83): difflib `get_matching_blocks()` can over-count when the shorter text's words appear in multiple long common runs, and the 80 % threshold uses `REPOST_ALIGN_MIN * short` where `short = min(len(ta), len(tb))` — but the matching blocks are computed against the *other* (longer) text, so a delivered clip whose text is much longer than the candidate's can satisfy 80 % of the shorter while the candidate's extra words are never checked**

Scenario: delivered clip text = 40 words; candidate = 10 words, 8 of which appear in order in the delivered text (e. g. the delivered clip is the same story, longer cut). 8/10 = 80 % → merged as "same speech" even though the candidate's remaining 2 words differ. That is arguably correct (a re-post cut differently), but the converse miss: a candidate that is a *different* 10-word sentence whose 8 words happen to be common connectives in order ("and the market is going to be in the next few years") can pass 80 % while being a different speech. The ruling's own guard is the run-length ≥ 3, which mitigates but does not eliminate this. Concrete miss case: two genuinely different sentences sharing a long common phrase (e. g. "Bitcoin launched in January of 2009" + different continuation) — 7-word run = 70 % of a 10-word shorter text, below 80 %, correctly not merged; but a 9-word shared phrase in a 10-word shorter text merges even if the 10th word differs. Whether that is "wrong" depends on the ruling's intent; the ruling says "the same speech re-posted", and a 9/10-word overlap is the same speech. **Verdict: no concrete wrong-merge/miss provable from the diff; flag as P1-uncertain, not a defect.** The test at diff line 341–342 (`scattered`) covers the scattered-words case.

**P1-3 — `proof_ledger.py` (diff lines 202–210): the publish-time harvest reads `inputs.json` only from `e["source"]` — a candidate whose clips were found by a *different* record than the one that seeded it, or whose `inputs.json` lists moments not in `e["lineup"]`, silently gets no publish time → expired**

The harvest filters `if m.get("moment_id") in e["lineup"]`, so moments not in the lineup are dropped — correct. But if `inputs.json` is unreadable, the `except … pass` swallows it and **every** moment of that candidate gets no publish time → the whole candidate expires ("never assumed fresh" — ruling-compliant, fail-closed). Concrete scenario: a transient read error (OSError) at 18:10 closes for good a candidate whose clips are 2 h old. Fail-closed, so ruling-compliant, but the candidate is *permanently* lost to a transient I/O error, and `expire()` runs before any candidate is tried — the candidate cannot recover because expiry is for good. P1: permanent loss on a transient error, by design but worth noting; the ruling says "expired for good", so this is compliant, just lossy.

**P1-4 — `proof_ledger.py` (diff lines 229–230): the pin-stage re-check joins `window_problems` to ruling 68's `pin_problems` — but the re-check uses `now=None` → `datetime.now(timewindow.utc)` inside `window_problems`**

Wait — checking the call: `package_pin.window_problems(res["package"]["segments"])` with no `now` → the function defaults `now = now or datetime.now(timezone.utc)`. That **is** the render clock at that moment. ✓. However, the *build's* render clock is `ctx.now` (fixed at build start), while the pin stage uses wall-clock now. If a build runs long, a moment that was 11.9 h at `ctx.now` can be 12.1 h at pin time → the pin is refused even though the build's `usable()` passed it. This is ruling (c) working as intended ("re-checked against (a) at the moment they would render"), but the build's own record's `ruling_76.inside_12h` count (computed with `now` = build start) can disagree with the pin-stage verdict. Reporting inconsistency, not a leak. P1 (reporting), not P0.

**P1-5 — `test_medley.py` (diff lines 318–324): the (a) test's `dict(self.at("c", 1), published_at=None)` — `PK.expired` handles `published_at=None` via `E.age_hours(None, now) is None` → expired. But the unreadable-string case `published_at="yesterday"`: `E.age_hours("yesterday", now)` — whether `E.age_hours` parses "ytestrday" is not shown in the diff**

`E.age_hours` is not in the diff. If it returns `None` on an unparseable string, the test passes and the ruling's "unknown = expired" holds. If it *raises*, `usable()` would propagate the exception — M12 fail-closed, but the test would error, not fail. Since "15 suites OK" is claimed, it presumably returns None. **Uncertain: `E.age_hours`'s behavior on a malformed string is not verifiable from the diff.** Flag as P1-uncertain.

## P2 findings

**P2-1 — `package.py` (diff lines 63–64, 83): `SAME_SPEECH_MIN_WORDS = 8` and the 80 % threshold: `REPOST_ALIGN_MIN` is not defined in the diff**

`REPOST_ALIGN_MIN` must already exist in package.py (used by the repost-alignment logic); the diff does not show its value. The ruling text says "at least 80 %", and the test asserts `same_speech(said, said.upper())` is True and the scattered case is False — if `REPOST_ALIGN_MIN` were not 0.8, the scattered test could still pass. **Not verifiable from the diff that REPOST_ALIGN_MIN == 0.8; if it is not, the ruling's 80 % is not what the code does.** P2 (verify).

**P2-2 — `package.py` (diff lines 67–83): `same_speech` imports `difflib` and `canon` inside the function — repeated import cost per moment × delivered span**

~1000 concurrent users / load: this is the pin builder, not a Flask route, so load is not a concern here; but the function is called once per (moment × delivered span with text) — O(M×D) difflib calls, each O(n²) in tokens. With many delivered pins (the ledger grows), the build slows. P2 (performance, not correctness).

O(n²) SequenceMatcher on token lists; with, say, 200 delivered spans × 200 moments = 40 000 difflib calls. P2.

**P2-3 — `proof_ledger.py` (diff lines 192–194): the `--hours` refusal prints to stderr and returns 2 — but the check `if not 0 < a.hours <= package_pin WINDOW_H` runs *after* `a = ap.parse_args(argv)` and *before* the try block, so nothing is written — correct**

Verified: the refusal happens before `delivered_pins` read and before any write. ✓. But note: `--hours 0` and `--0` are refused with the same message; the test covers "12.5", "72", "0", "-1". The test does not cover the *boundary* 12.0 exactly (allowed) — the test at diff line 293 tests "12.0"? No: it tests "12.5", "72", "0", "-1" — the boundary 12.0 (must be accepted) is not tested in this test. However `test_the_pin_stage_re_checks_on_the_render_clock` asserts `package_pin.WINDOW_H == 12.0` and the default path uses it. The boundary acceptance of `--hours 12` is not directly tested. P2 (test-coverage gap: the inclusive boundary 12.0 is never shown accepted).

P2-3 detail: `0 < a.hours <= 12` — 12.0 inclusive. The test covers 12.5 (refused) but not 12.0 (accepted). Minor.

**P2-4 — `candidates.expire()` (diff lines 27–49): `expire()` closes a candidate if **any** clip in its lineup is over 12 h or of unknown age — the ruling says "a clip's source is over 12 h old … → closed for good"**

The ruling quote: "a clip's source is over 12 h at the render clock (expire()) → closed for good". The code expires the *whole candidate* if any one clip is stale. Is that the ruling's intent? The ruling (a) says "A moment is usable only while its source video's published_at is within 12 HOURS" — a moment-level rule. Expiring a whole 3-clip candidate because one clip's source is 12.1 h old is stricter than the moment-level rule. But since `usable()` would exclude the stale moment anyway, the line-up could not form without it — so expiring the whole candidate is consistent. Actually, wait: `expire()` closes the candidate even if the *other* clips are fresh and the line-up could be re-formed from the fresh ones only. The registry's line-up is fixed at seed time (the search "leaves alone" registered line-ups), so a partially-stale line-up cannot be re-formed — expiring it is the only consistent action. ✓. Compliant; noting the reasoning.

**P2-4 (continued):** the candidate's line-up is fixed; a partially-stale line-up cannot be re-formed, so whole-candidate expiry is the only consistent action. Compliant.

**P2-5 — `test_medley.py` (diff lines 374–389): the rewritten ruling-57 test changes the fixture data, not just expectations**

The rewritten test changes `self.at("h", "A", 12.0, 50)` → `self.at("h", "A", 12.0, 13)` and the rig's angles from `[["h","x","y"],["f","g","k"]]` to `[["f","g"," assertionk"]]` (typo in my reading; it's `[["f","g","k"]]`), and drops the assertion `rig.medley_calls[0] == ["f","g","k"]`... no, it keeps it. It adds prompt-content assertions (`id=h ` not in prompt). The old test's *second* angle preference assertion is gone: the old test verified that the fresh angle is judged *first* (the preference order); the new test has only ONE angle in the rig, so the "judged first" property (fresh line-up preferred across angles) is no longer tested. The ruling-57 preference logic itself is unchanged by this diff, but its test coverage is weakened: the cross-angle preference is no longer exercised. P2 (coverage regression in the ruling-57 preference test).

**P2-5 detail:** old test: two angles `[["h","x","anglek"], ["f","g","k"]]`... (reading the diff: `[["h", "x", "y"], ["f", "g", ["f", "g", "k"]]` — the new test has one angle `[["f","g","k"]]`, so the cross-angle preference (the *point* of ruling 57's test) is no longer two angles, so the "juded first" property is no longer exercised. The ruling-57 preference logic is unchanged by this diff, so no production risk; but the test's purpose (cross-angle preference) is weakened. P2.

**P2-6 — `proof_ledger.py` (diff lines 202–210): the publish-time harvest's `pub.update(...)` — if two records' `inputs.json` list the same moment_id with different publish times, last-write-wins, silently**

Two records (different source dirs) could both list moment "x" with different `published_at` values; `pub.update` last-write-wins, iteration order of `reg["candidates"].values()` (insertion order of the JSON dict) decides. If the two disagree, the expiry decision can depend on dict order. Concrete scenario: record A says moment x published 5 h ago, record B says 13 h ago; if B is last, the candidate containing x expires. Fail-closed direction? Not necessarily — if A (5 h, fresh) is last, a 13 h-old moment survives. That would violate (a) if the *true* publish time is 13 h. But the moment-level `usable()` check at build time uses the moment's own `published_at` from the adapter, so the pin-stage `window_problems` re-check (which reads `source_published_at` from the *segment*, not from inputs.json) catches it. Defense in depth: the pin-stage re-check uses the segment's own field, so a wrong harvest value cannot leak into a pin. ✓. P2 (harvest-order dependence, mitigated by the pin-stage re-check).

P2-6 mitigation verified: `window_problems` reads `s.get("source_published_at") or s.get("published_at")` from the segment itself — independent of the harvest. So a wrong harvest value cannot reach a pin. ✓.

**P2-7 — `package_pin.window_problems` (diff lines 141–159): `str(p).replace("Z", "+00:00")` — a time like "2026-11-13T18:00:00.5Z" fractional-seconds+Z handled; but a lowercase "z" or "UTC" suffix is not handled**

`fromisoformat` in 3.12 handles "Z" natively (3.11+), so the `.replace("Z", "+00:0")` is belt-and-braces; lowercase "z" would fail → "no readable publish time" → problem → refuse. Fail-closed. ✓. P2 (informational).

Python 3.12's `fromisoformat` handles "Z" natively; the replace is harmless. Lowercase "z"/"UTC" → unreadable → refused, fail-closed. ✓.

**P2-7 note: the naive-time rule "a zoneless time is UTC" is implemented as `t.replace(tzinfo=timezone.utc)` — correct for the pipeline's convention, and the test covers it (`naive` case, diff line 348–34).**

**P2-8 — `proof_led ruling_76 counts (diff lines 238–244): `hooks_4` uses `isinstance(hp.get("passing"), list) else None` — a non-list `passing` yields None, which is not a count**

The ruling (d) requires STATE line 1 to carry "hooks >= 4" as a count. `None` is not a count; it's an honest "unknown". Fail-closed-ish (M12-adjacent). The ruling says the STATE line "carries" the four counts; None is a defensible representation of "not computable". P2 (informational; the ruling does not say what to do when the hook pool is not a list).

**P2-8: `hooks_4` = None when the hook pool's "passing" is not a list — honest, but the ruling (d) says STATE line 1 "carries" the counts; whether None satisfies "carries" is a judgment call. Informational.**

P2-9 — `same_speech` short-circuit `if short < 2: return False` — two texts of 1 word each that are equal: `ta == tb` would be True, but the `short < 2` check returns False *before* the equality check? No: order is `short = min(...)`; `if short < 2: return False` — so two equal one-word texts ("Bitcoin" vs "Bitcoin") return False. The test at diff line 338 asserts exactly this: `self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))` — "never on one word". Matches the ruling's intent ("a few common words in common never are"). ✓. But note the docstring says "below this, only an equal text is the same speech" — the docstring says equal texts below 8 words ARE the same speech, but the code returns False for equal 1-word texts. Docstring vs code: for 1-word equal texts, code says False, docstring says... the docstring's "below this, only an equal text is the same speech" — for a 1-word equal text, the code returns False, contradicting the docstring's "only an equal text is the same speech" (which implies equal → True). Minor docstring inaccuracy. P2.

Wait, re-read: `if short < 2: return False` comes BEFORE `if ta == tb: return True`. So equal 1-word texts → False. The docstring: "below this, only an same speech" — the docstring says below SAME_SPEECH_MIN_WORDS, only an equal text is the same speech. For 1-word equal texts, the code returns False, contradicting the docstring. Minor. P2-9: docstring says equal texts below 8 words are the same speech, but equal 1-word texts return False (the `short < 2` guard precedes the equality check). The test (line 338) asserts the code's behavior, so the test and code agree; the docstring is the odd one out. Minor.

Hmm, actually re-read the docstring: "two texts are the same speech when they are equal after normalisation (canon.canon_tokens), or, with the shorter at least SAME_SPEEMIN_WORDS long, when at least REPOST_ALIGN_MIN of the shorter one's difflib..." — the docstring's first clause says "equal after normalisation" → same speech, unconditionally. The code's `short < 2` guard precedes the equality check, so equal 1-word texts → False, contradicting the docstring's first clause. The test agrees with the code. So the docstring is wrong, or the guard is. Minor. P2-9.

Hmm, wait — actually, for 1-word equal texts: `short = 1 < 2` → return False. But the docstring's first clause ("equal after normalisation → same speech") would say True. So docstring vs code disagree for 1-word equal texts. The test asserts the code's behavior (assertFalse for "Bitcoin" vs "Bitcoin"). So the docstring is inaccurate for the 1-word case. Minor. P2-9.

Hmm, but wait — actually, is it? Let me re-read the code:

```python
ta, tb = canon.canon_tokens(a or ""), canon.canon_tokens(b or "")
short = min(len(ta), len(tb))
if short < 2:
    line 76: return False
if ta == tb:
    return True
```

Yes: equal 1-word texts → False. Docstring clause 1 says equal → True. Test line 338: `self.assertFalse(PP.same_speech("Bitcoin", "Bitcoin"))` — "never on one word". So the test agrees with the code, the docstring's clause 1 is inaccurate for the 1-word case. Minor. P2-9.

Hmm, but the test comment says "never on one word" — so the intent is documented in the test. The docstring's clause 1 just doesn't carry the `short < 2` caveat. Minor. P2-9.

**P2-10 — `proof_ledger.py` (diff lines 238–243): `res["ruling_76"]["inside_12h"] = sum(not PK.expired(m, now) for over ALL moments, not just usable ones — the count is over the full moment list**

`moments` here — where does it come from? The diff shows `sum(not PK.expired(m, now) how many moments in the pool before/after filtering. If `moments` is the full adapter list (before usable() filtering), the count "moments inside 12 h" is over the raw pool, which is what the ruling (d) asks ("moments inside 12 h" — of the pool, presumably). If `moments` is the usable list, the count is post-filter. Not verifiable from the diff which list `moments` is. **Uncertain.** P2-10: the ruling-76(d) count's population (raw pool vs usable) is not verifiable from the diff.

**P which list `moments` is — not verifiable from the diff.** P2-10.

## Answers to the specific questions

**1. No moment over 12 h / unknown age enters a line-up, candidate try or pin, on any path?**

- Line-up/try: `usable()` excludes (a) moments; the angle writer's prompt only includes usable moments (verified by the rewritten ruling-57 test's prompt assertions, diff lines 386–389: `id=h ` not in prompt, `ruling 76 (a)` in unusable). ✓
- Candidate try: `CA.expire` runs before any candidate is tried (diff lines 211, 212 — `gone = CA.expire(...)` then `CA.registered(reg)`; the try happens later in main). ✓ (The diff shows expire runs in the refusal block, before the build; the try happens after.)
- Pin: `window_problems` joins the ruling-68 refusal (diff lines 229–232). ✓
- Unknown age: `expired()` returns True when `age is None` (package.py line 91); `window_problems` treats unreadable as a problem (line 152); `expire()` treats unknown as old (line 39–41). ✓ Fail-closed on all three.

Unknown-age handling: `expired()` → `age is None` → True (expired); `window_problems` → unreadable → problem; `expire()` → "no known publish time" → expired. All fail-closed. ✓

**2. No delivered speech reused in another video?**

The same-speech rule fires only when `d.get("text")` and `d.get("video_id") != m["video_id"]` and `same_speech(...)`. Same-video reuse is caught by the unchanged overlap rule (test line 333–335: `same_video_elsewhere` with start=40–50, no overlap with 10–20, is KEPT — the same video, non-overlapping, different span, same text, is allowed). Wait — the ruling (b) says "extend it to any overlapping span of the same video and to the same speech re-posted on another channel". The test keeps a same-video, non-overlapping, same-text moment — is that ruling-compliant? The ruling says "A span that has been DELIVERED in any video is never used again... extend it to any overlapping span of the same video and to the same speech re-posted on another channel". So same-video non-overlapping same-text: the ruling's (b) extension covers "overlapping span of the same video" and "same speech re-posted on another channel" — a same-video non-overlapping same-text span is neither, so keeping it is compliant. ✓. And the test's comment "(the same video: the span rule, as before)" confirms intent. ✓

Same-video: overlap rule unchanged (non-overlapping same-text in the same video is allowed — ruling-compliant, since (b) extends only to overlapping same-video spans and cross-video same-speech). Cross-video: same_speech with ≥8-word shorter, ≥80 % in ≥3-word runs. Miss/merge risks: see P1-2 (no provable defect; the scattered-words case is tested).

**3. Registry expiry for good, not undone by a later seed?**

`outcome(..., "expired")` → `state="closed", until=None` (diff line 19–20: `if cls in ("package", "clip", "expired")`). `CA.due` returns [] for closed. A later `CA.seed` — does seed overwrite a closed entry? Not shown in the diff. **Uncertain: whether `seed()` re-seeds a closed candidate.** The test at diff lines 270–272 seeds a *fresh* registry, not the same one — so "cannot be undone by a later seed" is not directly tested. The docstring at diff lines 5–10 says the driver "reads and writes the file" and the record's tried entry... the header comment says "record's tried entry and package.load_candidate rebuilds it" — the registry is rebuilt from records; if a later build's record re-seeds the same line-up, does the closed/expired state survive? Not verifiable from the diff. P1-6? Let me downgrade: the question asks specifically "cannot be undone by a later seed" — the diff does not show `seed()`'s behavior on an existing closed entry, and the test only seeds a fresh registry. **This is the strongest uncertainty in the audit.**

Hmm, but the header comment of candidates.py (diff lines 5–11) says the registry is keyed by line-up ("g+h+i" keys) and the driver reads/writes the file; the test's fresh-registry case shows expire returns [] on a fresh registry. Whether a later seed of the same line-up resets state to "open" — not shown. If it did, the expiry would be undone. The question demands verification; I cannot verify it. Flag as P1.

**3 (continued).** The strongest uncertainty: `CA.seed`'s behavior on an already-closed (expired) entry is not shown in the diff, and the test only exercises a fresh registry. If seed resets state, expiry is undone by the next build's record. The header comment (diff lines 5–7) says the record's tried entry is what `package.load_candidate` rebuilds — suggesting the registry is derived from records, so a later record could re-seed. Not verifiable. P1.

**4. Window never widened by an argument?**

`--hours` outside (0, 12] → return 2 before any write (diff lines 192–194, verified before the try). `window_problems` takes no window argument — it reads the constant. `expire()` takes `window_h` as a parameter, but the only call passes `package_pin.WINDOW_H` (diff line 211). `usable()`'s expired check uses `package_pin.WINDOW_H` via `expired()` (diff line 89–91: `import package_pin; ... > package_pin.WINDOW_H` — wait, `expired()` imports package_pin and reads WINDOW_H at call time, so a monkeypatched WINDOW_H would change it — but that's how the module constant works; the ruling's "never widened" is about the CLI argument, which is enforced. ✓. `expire`'s `window_h` parameter defaults to nothing — it's required; the only call site passes the constant. ✓

`expire`'s `window_h` is a required parameter — a future caller could pass 72; but the only call site (diff line 211) passes the constant. The ruling's "never widened" is enforced at the CLI (the only user-facing knob). ✓

**5. Pin-stage re-check uses the render clock at that moment?**

`window_problems(segments)` with `now=None` → `datetime.now(timezone.utc)` at call time — the wall clock at the pin stage, which is "the moment they would render" per ruling (c). ✓. Note the divergence from the build's `ctx.now` (P1-4): a moment 11.9 h at build start can be 12.1 h at pin → refused at pin. Ruling-compliant (fail-closed, (c) as written), but the build's `ruling_76.inside_12h` count uses the build's `now` (diff line 239: `sum(not PK.expired(m, now)` where `now = datetime.now(timezone.utc)` from diff line 191 — actually `now` in the driver is also wall-clock at driver start, not ctx.now). Hmm: diff line 191: `now = datetime.now(timezone.utc)` — the driver's `now` is wall-clock at driver start. So the ruling-76(d) count, the CA.expire, and the pin-stage check all use wall-clock nows taken at slightly different instants (driver start, pin stage). The build's `ctx.now` (used by `usable()`) is a third instant. Three clocks, all "render clock" in spirit; the pin-stage one is the binding one (it refuses). Fail-closed in the right direction: later clocks only *tighten* (a moment fresh at build start can be expired at pin; never the reverse, since the pin check is later in time and the window is fixed). ✓ — actually, is that right? A moment 11.9 h at ctx.now (build) → 12.1 h at pin → refused. A moment 12.1 h at ctx.now → excluded by usable() → never reaches pin. So the binding check is the *later* one, and later clocks only tighten. ✓ Fail-closed.

**6. Nothing else a gate accepts changes; seal() unchanged?**

`seal()` is not in the diff (the change note says "seal() is not changed (the integrator imports this file live for its seal recompute)"). The diff to package_pin.py adds only the constant and `window_problems` above `seal()` — no seal() hunk. ✓. `usable()`'s existing exclusions: the delivered-why message changed from "delivered in the previous 24 h (or overlaps a delivered moment)" to "delivered (or overlaps a delivered moment)" — a message change only; the *condition* `mid in ids or overlap` is unchanged. ✓. The time-sensitive rule's position: the new expired check sits *after* it, so a stale time-sensitive moment still reports L-v 3 (test line 324 asserts "L-v 3" still fires). ✓. `outcome()`'s change: "expired" added to the closed-class tuple — "package"/"clip" behavior unchanged; "line" handling unchanged. ✓. The delivered spans now carry `text` (diff line 174) — additive; the pin's story_id, start, end unchanged. Additive field, no gate reads it for acceptance... unless a downstream consumer of `delivered_pins` output is strict about extra keys — not verifiable from the diff. Minor.

Additive `text` key on delivered spans: if any downstream consumer of `delivered_pins()`'s return is strict about extra keys, it could break — not verifiable from the diff; the only consumer shown is `usable()`'s `spans` (which reads `.get("text")` defensively). Minor.

## Ship recommendation

**SHIP: yes with conditions** — conditions: (i) confirm `CA.seed` does not reset a closed/expired entry's state (the strongest unverified point; if it does, expiry is undone by the next build's record — the ruling's "never offered again" would fail); (ii) confirm `REPOST_ALIGN_MIN == 0.8` (the ruling's 80 %); (iii) confirm `E.age_hours` returns None (not raise) on a malformed published_at.

---

### Summary of findings

- **P0:** none.
- **P1:** (1) why-reason order dependence in `usable()` (reporting); (2) same_speech 80 %-of-shorter asymmetry (no provable defect, uncertain); (3) transient inputs.json read error permanently expires a candidate (fail-closed, compliant, lossy); (4) three wall-clock instants (ctx.now, driver now, pin-stage now) — later clocks only tighten, fail-closed, but counts can disagree with verdicts; (5) `E.age_hours`'s malformed-string behavior unverifiable from the diff; (6) `CA.seed`'s behavior on a closed/expired entry unverifiable from the diff — if it resets state, "never offered again" fails.
- **P2:** REPOST_ALIGN_MIN value not shown; O(M×D) difflib cost; boundary `--hours 12` acceptance untested; whole-candidate expiry (consistent, reasoned); ruling-57 test weakened to one angle (cross-angle preference no longer exercised); pub.update last-write-wins (mitigated by the pin-stage segment-field re-check); "Z"-replace/naive-UTC handling (fail-closed); hooks_4=None when the hook pool is not a list; same_speech docstring vs the 1-word guard; ruling_76.inside_12h population (raw vs usable) unverifiable; additive `text` key on delivered spans.

The core ruling-76 mechanics are sound: the window constant is single-sourced (package_pin.WINDOW_H), the CLI knob is bounded, the pin-stage re-check uses the wall clock at the pin (later clocks only tighten), unknown/unreadable times fail closed on all three paths (usable, expire, window_problems), and seal() is untouched. The strongest residual risk is the seed-vs-expiry interaction, which the diff does not show and the tests do not pin down.</think># Audit: pp-selectid-1810 — RULING 76 (12 h window, expiry, render-clock re-check)

## P0

None. Every enforcement path I can trace from the diff holds.

## P1

**P1-1 — `CA.seed` vs. expiry: "never offered again" is not provably durable (candidates.py; test_candidates.py:270-272).**
`outcome(..., "expired")` sets `state="closed", until=None` (diff :18-20), and `CA.due` returns [] for closed (test :269). But the module header (diff :5-11) says the registry is rebuilt from records ("the record's tried entry and package.load_candidate rebuilds it"), and the diff does not show whether a later `CA.seed` of the same line-up resets a closed/expired entry to open. The test only seeds a *fresh* registry (test :270-272) — the "cannot be undone by a later seed" property is asserted nowhere. Scenario: build N expires candidate "d+e+f"; build N+1's record re-seeds the same line-up; if seed overwrites, the expired candidate is offered again, violating (a). Not verifiable from the diff — this is the strongest residual risk.

**P1-2 — `same_speech` asymmetry: 80 % of the *shorter* text, matched against the *longer* (package.py, diff :67-83).**
`short = min(len(ta), len(tb))`; the threshold is `REPOST_ALIGN_MIN * short`, but the matching blocks come from `SequenceMatcher(None, ta, tb)` — the longer text's extra words are never checked. Scenario: delivered clip = 40 words; candidate = 10 words sharing 8 in order → merged as the same speech even if the candidate's other 2 words differ. Conversely, two genuinely different sentences sharing one 9-word phrase in a 10-word shorter text also merge. Whether these are wrong depends on intent ("a re-post cut a little differently" suggests they are right), and the run≥3 + scattered-words test (diff :341-342) covers the main failure mode. No provable wrong-merge/miss; flagged as the rule's known looseness. Also: `REPOST_ALIGN_MIN`'s value (0.8?) is not in the diff — if it is not 0.8, the ruling's "80 %" is not what the code does. Verify.

**P1-3 — transient `inputs.json` read failure permanently expires a candidate (proof_ledger.py, diff :202-210).**
The harvest's `except (OSError, ValueError, AttributeError, TypeError): pass` gives the candidate no publish times → `expire()` closes it for good ("no known publish time"). Fail-closed, ruling-compliant, but permanent: expiry is for good and the candidate cannot recover. Scenario: one transient I/O error at 18:10 kills a 2 h-old candidate forever. Compliant by the ruling's letter; lossy by nature. Note also `pub.update(...)` is last-write-wins if two records list the same moment_id with different publish times — mitigated, because the binding pin-stage check reads `source_published_at` from the *segment* (diff :148), not from the harvest.

**P1-4 — three "render clocks" (package.py ctx.now; proof_ledger.py :191; package_pin.py :145).**
`usable()` uses the build's `ctx.now`; the driver's ruling-76(d) counts and `CA.expire` use wall-clock at driver start; the pin stage uses wall-clock at pin time. Later clocks only *tighten* (a moment 11.9 h at build start can be 12.1 h at pin → refused; never the reverse), so the binding check is fail-closed in the right direction. But the record's `inside_12h` count (diff :239) can disagree with the pin-stage verdict, and the `why` attribution in `usable()` is order-dependent: a moment both stale and same-speech reports "ruling 76 (b)", not (a) (the same-speech elif precedes the expired elif, diff :110 vs :123). Reporting inconsistency, not a leak — but the ruling requires the dying stage to be *reported*.

**P1-5 — `E.age_hours`'s behavior on a malformed string is not in the diff (test_medley :319, `published_at="yesterday"`).**
If it returns None → expired, ruling holds; if it raises → M12 fail-closed but the test errors rather than fails. "15 suites OK" suggests the former; not verifiable from the diff.

## P2

- **P2-1 — Boundary `--hours 12` never shown accepted** (test_ledger_build :293 tests "12.5","72","0","-1" only). The code `0 < a.hours <= WINDOW_H` (diff :192) admits 12.0; the inclusive boundary is untested.
- **P2-2 — O(M×D) difflib calls** in `usable()`'s same-speech any() (diff :110-113): the `next(...)` re-derivation (diff :112-113) also *recomputes* `same_speech` instead of reusing the any() hit — 2× cost, and O(n²) SequenceMatcher per pair. Build-time only; not a route; load-safe.
- **P2-3 — Whole-candidate expiry** when any one clip is stale (diff :35-47): stricter than the moment-level rule, but consistent, since the line-up is fixed at seed and the search "leaves alone" registered line-ups (diff :52-54) — a partially-stale line-up cannot be re-formed. Compliant.
- **P2-4 — Ruling-57 test weakened** (diff :374-389): the rig now has ONE angle, so the cross-angle "fresh line-up judged first" preference — the point of ruling 57 — is no longer exercised. The preference logic itself is unchanged by this diff; coverage regression only.
- **P2-5 — `same_speech` docstring vs. the 1-word guard** (diff :68 vs :76-77): the docstring's first clause ("equal after normalisation → same speech") implies equal 1-word texts are the same speech; the `short < 2` guard precedes the equality check, so they return False. The test (diff :338) agrees with the *code*; the docstring is the odd one out.
- **P2-6 — `hooks_4` = None when the hook pool's "passing" is not a list** (diff :242): honest "unknown", but whether None satisfies (d)'s "STATE line 1 carries" is a judgment call. Likewise `inside_12h`'s population (all moments vs. usable) depends on which list `moments` is — not verifiable from the diff.
- **P2-7 — `window_problems` time parsing** (diff :150-154): 3.12's `fromisoformat` handles "Z" natively, so the `.replace` is harmless; lowercase "z"/"UTC" → unreadable → problem → refuse. Fail-closed. The naive→UTC rule is implemented and tested (diff :348-349). ✓

## Answers to the specific questions

1. **No stale/unknown-age moment enters a line-up, try, or pin?** Yes, on all traced paths: `usable()` excludes (a) with the prompt-coverage test proving the writer never sees expired ids (diff :386-389); `CA.expire` runs in the refusal block before any try (diff :211); the pin stage joins `window_problems` to ruling 68's refusal (diff :229-232). Unknown age fails closed at all three: `expired()` → `age is None` → True (diff :90-91); `window_problems` → unreadable → problem (diff :151-152); `expire()` → "no known publish time" → expired (diff :39-41). Caveat: P1-1 (seed durability) and P1-5 (`E.age_hours`) are the two points the diff cannot prove.
2. **Delivered speech never reused in another video?** The rule fires only cross-video (`d.get("video_id") != m["video_id"]`, diff :110); same-video non-overlapping same-text is kept, which matches (b)'s letter (it extends only to *overlapping* same-video spans and cross-video same-speech) — the test's comment (diff :335) confirms intent. Merge/miss risk: P1-2; no provable defect.
3. **Expiry for good, not undone by a later seed?** Within the diff, yes (closed + `due`→[]); across builds, **unproven** — P1-1.
4. **Window never widened by an argument?** Yes: the CLI knob is bounded to (0, 12] before any write (diff :192-194, verified to precede the try/read); `window_problems` takes no window; `expire`'s `window_h` is a required parameter whose only call site passes the constant (diff :211); `expired()` reads `package_pin.WINDOW_H` directly. A future caller could pass a larger `window_h` to `expire` — the only theoretical widening, not reachable from the current code.
5. **Pin-stage re-check uses the render clock at that moment?** Yes: `now=None` → `datetime.now(timezone.utc)` at call time (diff :145), which is (c)'s "the moment they would render". Later clocks only tighten (P1-4) — fail-closed.
6. **Nothing else a gate accepts changes; seal() unchanged?** Yes: no `seal()` hunk in the diff; `outcome()`'s change is purely additive to the closed-class tuple; the delivered-`why` message changed wording only, condition `mid in ids or overlap` untouched (diff :107-109); the new expired elif sits *after* the time-sensitive rule, and the test proves L-v 3 still reports (diff :324); the delivered spans' new `text` key is additive (a strict downstream consumer of `delivered_pins` is the only theoretical break — none shown).

## SHIP: yes with conditions

Conditions: (i) confirm/patch that `CA.seed` does not resurrect a closed/expired entry (P1-1 — the ruling's "never offered again" hinges on it); (ii) confirm `REPOST_ALIGN_MIN == 0.8` (P1-2); (iii) confirm `E.age_hours` returns None, never raises, on a malformed `published_at` (P1-5); (iv) add the `--hours 12` boundary-acceptance test (P2-1).