# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2322
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## PROMPT_GROK_QWEN — CYCLE 1 OUTPUT
# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2322
# Branch: pp-selectid
# Generated: 2026-11-13 23:22 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation at a place a listener hears as the break between the two
  words (DEC-10, 2026-11-11: no minimum pause; the 01:50 order's 80 ms is recalibrated to the approved v2f
  reference, whose edges measure 0-10 ms; pipeline/sentence_law.py states every constant with its
  measurement). An unpunctuated transcript stretch has NO boundary
  (fail closed). Punctuation is added at transcription time only from a second, prompted ASR decode of
  the same audio, onto aligned verbatim words; the words never change (pipeline/punctuation.py). No
  language model decides a boundary (the per-gap adjudicator called 19/19 gaps sentence ends; removed).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the heard gap between the chosen sentence and its neighbour
  (the previous word's offset .. the next word's onset, at speech - 6 dB); it may never add or drop a word.
  A short gap is cut at the envelope minimum between the two words, never rejected for its length (DEC-10 d);
  its fade sits inside the gap (L-b: 2 video frames = 83 ms when it fits, down to 10 ms).
- NEIGHBOUR (DEC-10 c-ii): NO audible part of the neighbouring word: every frame the cut keeps on the
  neighbour's side of that minimum stays below the valley threshold (local speech - 12 dB) after the fade.
  A window is rejected for its edges only if this, the 85 % edge-word rule or sentence-completeness fails.
- ONSET/TAIL: edge words keep >= 85 % of their duration in the render (a floor for timestamp noise, never
  permission to trim: L-b below). The START OF PLAYBACK keeps the D1
  rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine
  sub-speech audio before the first onset or a declared room-tone lead-in pad; codec zero/padding is not
  room tone. Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms).
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12 / G15 measure the brand-red rings the renderer
  draws and G15 checks each disc is the credited channel's registered avatar (DEC-11).
- L-a SIGN-OFF NAMES ALL (PBX, 2026-11-11): the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical.
  Check: run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f.
- L-b EDGE WORDS WHOLE (PBX, 2026-11-11): a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay.
  Check: sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges.
- L-c DISSENT IS RIGHT UNTIL DISPROVED (PBX, 2026-11-11): a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against th

## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 83 s finish=stop usage in 49463 / out 4873 usd~0.221 (upper-bound price)

# Audit: pp-selectid-2322 (spotlight pin kind)

## Seal backward compatibility

**Verified OK.** `seal()` (package_pin.py:165-192) adds `body["vo"]["closing"]` only when the key exists in `edl_vo`, and `shape`/`first_comment` only when `shape == "spotlight"`. A medley's `edl_vo` (built at package_pin.py:278-279) never carries `"closing"`, and `to_pin` passes `shape=None` for non-spotlights, so old medley bodies are byte-identical. `pin_seal()` (195-203) mirrors `to_pin`'s call exactly, and test_spotlight.py:1623-1635 recomputes every existing MOMENTS_PIN. One subtlety: `pin_seal` passes `shape="spotlight" if shape == "spotlight" else None` — a pin whose `mp["shape"]` is some *other* new string (e.g. "max_v3") would seal with `shape=None`, matching the old behaviour; consistent with the docstring, but only "medley"/absent/None/spotlight shapes are proven by the test. Not a defect, noting the assumption.

<medium> **package_pin.py:186-187 — the closing enters the seal keyed on `"closing" in edl_vo`, not on shape.** A *medley* whose `edl_vo` happens to carry a `closing` key (e.g. a future medley variant, or a hand-edited pin) silently changes its seal. Today no medley path writes the key (verified: to_pin:281-283 adds it only when `spot`), so this is latent, not breaking. Concrete: if the integrator's renderer ever echoes `closing: null` back into a medley's `edl_vo` and the readiness check re-seals, the digest changes and the pin fails readiness. Fail-closed, but a surprise.

## Closing line cannot ship without its rows

**Verified OK, with one gap.** In `package_for` (spotlight.py:1252-1276): the closing ships only when `val.ok and cf.ok and cf.measured and cc.ok and cc.measured`; otherwise `pk1 = None` and the package falls back to `pk0` (no closing). `inventory()` (951-962) adds the three CLOSING_GATES rows only when `closing is not None`, and `required_gates` (package_pin.py:150) demands them exactly when `_closing(pk) is not None`. `to_pin` → `gate_problems` + `spotlight_problems` + `line_problems` cross-check the shipped line against the gated one. Test test_spotlight.py:1891-1906 covers value-no, out-of-contract, fidelity-fail, context-fail, style-fail — all leave no line.

<medium> **spotlight.py:1289-1305 — the final `cheap()` runs on the *chosen* package, but the closing's free-gate pass was measured on `pk1` assembled *before* `LP.apply` and before the speaker/credits fields.** `LP.apply(pk, pre)` (1308) can adopt a spoken text, changing segment `approved_text`/`text` after the fidelity/context verdicts were measured. For the *closing* line this is the same adoption the medley does, and `precheck`'s adopted text is the render's own contract (ruling 72/84), so likely intended — but the closing_fidelity/context verdicts were computed on the pre-adoption bytes. If `LP.apply` adopts a different spoken closing, the sealed `closing_fidelity` row's evidence no longer matches the shipped bytes. I cannot verify from the diff whether `LP.apply` touches `vo["closing"]`; if it can, this is a real (if narrow) evidence-vs-bytes gap under L-j. Flag for the integrator's adoption semantics.

<medium> **spotlight.py:960-962 — `closing_context` row's `measured` comes from `cc.get("measured")`, but the ship condition (1269) also requires `cc.ok`; the row's PASS is `_row(cc.get("ok") is True, ...)` — consistent. However `closing_fidelity`'s row (957-959) uses `cf.get("ok") is True` with `measured=bool(cf.get("measured"))`; if `cf` were `{"ok": True, "measured": False}` the row would be PASS with `measured: False` — but the ship condition (1269) requires `cf.measured`, so it could not ship. Consistent. No defect.

## Rows computed from measurement

**Verified: no hard-coded PASS.** Every row's `ok` derives from a measured record; `_row` (895-897) yields "NOT RUN" when `measured` is false, and `gate_problems` demands exactly "PASS", so NOT RUN fails the pin. Specifics:

- `stands_alone` (921-925): `sv is not None and score >= 4` — no verdict → NOT RUN → refused. ✔
- `hook_own` (916-919): `own is not None`. ✔
- `step_a_two_families` (927-931): requires exactly 2 and no failures; `measured=len(a_two)==2`. ✔
- `precheck` (946-950): `measured=pre is not None and not pre.error`; a precheck with `ok: True` but *empty/absent* `segments`... note `build()` (1154-1158) treats `pre.error or not pre.segments` as a stop, but `package_for`'s inventory would still record `precheck` PASS from `pre.get("ok")` if a caller passed such a `pre` directly. In the actual flow `build` gates this, so unreachable. ✔ (borderline)
- `never_delivered` / `one_per_channel_day` (940-945): `measured=isinstance(facts[...], bool)` — a non-bool fact → NOT RUN. ✔ But see the next finding.

<high> **spotlight.py:1160-1163 — `facts["never_delivered"]` is computed via `P.usable([m], ...)` *after* the moment already passed the pool, but `facts["one_per_

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 115 s finish=stop usage in 48469 / out 1109 usd~0.270 (upper-bound price)

**Findings**

No <critical>, <high>, or <medium> findings. All items listed in the query hold based solely on the diff:

- Old pins recompute identically (tests/package/test_spotlight.py:1616-1628 asserts PP.pin_seal(pin) == mp["package_sha256"] and PP.seal(...) without shape/first_comment for every MOMENTS_PIN*.json; pipeline/package_pin.py:186-191 adds "closing"/"shape"/"first_comment" to body only if "closing" in edl_vo or shape == "spotlight"; integrator call at test:1642-1645 passes **kwargs only for spotlight).
- No path ships a closing line without all three CLOSING_GATES exactly PASS (spotlight.py:1266 requires val.get("ok") and cf.get("ok") and cc.get("ok") and measured before pk1 is kept; inventory:951 adds the rows only if closing_rec; required_gates:150 adds CLOSING_GATES only if _closing(pk) is not None; final gate_problems:1310 after LP.apply refuses any non-PASS or v_all violation; test:1873-1875 confirms all PASS when kept, test:1894-1897 confirms no CLOSING_GATES and no line when any fails).
- Every required row is from measurement (no hard-coded PASS; e.g. stands_alone:921 measured=sv is not None and uses its score/text_sha256; spotlight_source:932 measured=layout.measured is True; visual:912 measured=v.get("measured") is True; one_per_channel_day:943 measured=isinstance(facts["one_per_channel_day"], bool); precheck:947 measured=pre is not None and not error; window_12h/never_delivered use explicit facts; _row:896 status="NOT RUN" if not measured; P.inventory call:906 supplies fid/dup/rt_ok/cx/truth/exc/visual/hook/stand_alone/style; test:1873 confirms gate_problems empty only when all measured PASS).
- Snap never pads, never crosses marker, never exceeds 35 s, and snapped span is re-judged (spotlight.py:465-479 while-loop adds only whole sentences, rejects on marker inside (453), on >SPOT_S[1] (451), or cannot add (478); SNAP_TO_S=13.7 used only as floor; returns new M.record with new moment_id, eligibility, rank_score, topics, risk (486-490); pool:521-530 runs usable/snap then usable again on v; build:1010-1176 runs prescreen/truth/hook_onset/visual/second_screen/alone/source_test/exclusion/lock/package_for on it; TestSnap:1700-1733 verifies with concrete S5/S20/S33 inputs).
- Ruling 92 test cannot pass solo recap/reaction and fails closed when unmeasured (source_test:573 if not layout.measured: False+"not measured"; 576 if lay not in LAYOUT_OK: False with explicit why; 579 if conversation+measured turns and tpm<1.0: False; layout_for:631 if no measured sheet: measured=False; episode_turns:557 if no units: unmarked=True (unknown, not solo); build:1127 passes only if ok; test:1740-1758 with unmarked/recap/reaction/solo tpm=0.48 inputs confirms FAIL and "ruling 92" stop).
- Every verdict off writers' vendor/family (L-s), value included (package_for:1223 wv_/wf_ from replies; 1224 selects a_off with vendor/family not in those sets for a_lab/fidelity/context; value_verdict:780 avoid_vendor=writers_v/avoid_family=writers_f on coherence_verdict role; 780-784 rejects out-of-contract; test:1787-1797 confirms avoid and no line if not clear-yes).
- Per-channel-per-day rule, including unreadable record (pool:508 if spotlit is None: why="...record cannot be read" for all, return [] (no spotlight); 513 taken={r["channel_id"] for r in spotlit if day_et==day}; et_day:392 uses America/New_York; load_spotlit:406-410 returns None on any read/JSON/key/type error; record_spotlit:416 raises if None; build:1008 early-returns if no pool; test:1837-1839 with spotlit=None confirms block).
- Medley behaviour unchanged (package.py:30 seg_max=SEG_MAX_S default (20 s medley rule), spotlight calls with 35 explicitly (505); scorer_pass:73 have=set of (id,text_sha) before adding extra, comment:74 "medley's own candidates and the spotlight's never replace each other"; build:104 passes extra=scorer_extra but only for spotlight pool (ruling 90); package_pin.py:149 if shape=="spotlight" else old REQUIRED_GATES+MEDLEY_GATES; seal:190 if shape=="spotlight" only; required_gates:150, screen_problems:214, to_pin:281, line_problems:227 only for spotlight; proof_ledger.py:1352 sp_pool sent but medley path identical).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 227 s finish=stop usage in 55232 / out 5650 usd~0.250 (upper-bound price)

# Audit: pp-selectid-2322 (Spotlight Pin Kind)

## <critical>

**1. `spotlight.py:1160` — `never_delivered` gate is hard-coded to `True` (Law L-m violation)**
In `build()`, the `facts` dict passed to `package_for()` → `inventory()` contains:
```python
facts = {"now": ctx.now, "day": et_day(ctx.now), "never_delivered": True, ...}
```
This value is **never computed**. It is a literal `True`. The `inventory()` function then stamps:
```python
rows["never_delivered"] = _row(facts["never_delivered"] is True, ...)
```
which always produces `"status": "PASS"`.

**Concrete scenario:** A moment whose span overlaps a previously delivered clip (e.g., the same 20-second segment was already shipped in a medley pin 6 hours ago). `pool()` calls `P.usable()` which *does* check `delivered` spans and would exclude it. However, if the moment passes `pool()` (e.g., the delivered span was from a *different* video, or the overlap check has a boundary edge case), the `never_delivered` gate in the sealed inventory will still read `PASS` because it is hard-coded. The gate provides **zero protection** at the pin stage. The integrator's readiness check (which recomputes `seal()` but does not re-run `pool()`) will accept the pin.

The same pattern applies to `one_per_channel_day` (line 1161–1162), which *is* computed from `spotlit`, but `never_delivered` is not. The comment says `# pool(): usable() with delivered` but the value is not derived from that check's result.

**Fix:** The `facts["never_delivered"]` must be set to the actual result of the `usable()` check for this specific moment, or the gate must be removed from `SPOTLIGHT_GATES` if it is redundant with `pool()`. As written, it is a dead gate that always passes.

---

## <high>

**2. `spotlight.py:1249–1264` — Closing-line verdicts submitted to `ThreadPoolExecutor` before the executor is entered**

```python
with ThreadPoolExecutor(max_workers=6) as ex:
    f_fid = ex.submit(VF.check, ...)          # line 1250
    if closing0 is not None:
        pk1 = assemble(...)
        v1 = cheap(...)
        if v1:
            cl_why, pk1 = ..., None
        else:
            f_val = ex.submit(value_verdict, ...)   # line 1259
            f_cf  = ex.submit(VF.check, ...)        # line 1260
            f_cc  = ex.submit(CI.check_contexts, ...) # line 1262
            val, cf, cc = f_val.result(), f_cf.result(), f_cc.result()  # line 1264
```

The `ex.submit()` calls on lines 1259–1262 are **inside** the `with` block, so this is actually correct. However, the `f_fid` future (line 1250) is resolved on line 1273, *after* the `with` block exits (line 1273 is outside the `with`). Wait — re-reading: line 1273 `fid = f_fid.result()` is **outside** the `with` block (the `with` ends at line 1264's indentation level). Actually, looking at the indentation more carefully:

```python
    with ThreadPoolExecutor(max_workers=6) as ex:
        f_fid = ex.submit(VF.check, ...)
        if closing0 is not None:
            ...
            val, cf, cc = f_val.result(), f_cf.result(), f_cc.result()
            ...
        fid = f_fid.result()    # line 1273 — INSIDE the with block
```

Line 1273 is at the same indentation as `f_fid = ex.submit(...)`, so it **is** inside the `with` block. This is correct. **Retracting this finding.**

**2 (revised). `spotlight.py:1249–1273` — `f_fid` (VO fidelity on base lines) is submitted before the closing-line branch, but its result is consumed after the closing-line futures. If the closing-line branch raises an unhandled exception, `f_fid` is never resolved and the executor's `__exit__` will call `shutdown(wait=True)`, which is fine. No bug here. Retracted.**

**2 (actual). `spotlight.py:1223–1225` — `a_off` selection can return `None` on the second write, causing a hard failure that is not a gate failure**

```python
wv_, wf_ = {x.vendor for x in replies}, {x.family for x in replies}
a_off = next((a for a in a_two for b in [router.backends.get(a.get("backend"))]
              if b is not None and b.vendor not in wv_ and b.family not in wf_), None)
if a_off is None:
    return None, (f"no step-A verdict off the writers {sorted(wv_)} / {sorted(wf_)} (L-x): ...")
```

On the **first** write (`w == 0`), `replies` has one entry. On the **second** write (`w == 1`), `replies` has two entries. If both writers happen to be from the same vendor or family as both step-A backends, `a_off` is `None` and the function returns `None`. This is correct fail-closed behavior. **No bug.** Retracted.

**2 (actual high). `spotlight.py:1160` — `facts["never_delivered"]` is hard-coded `True` (see critical #1). Additionally, `facts["one_per_channel_day"]` is computed but the computation at line 1161–1162 re-derives the `taken` set from `spotlit` rather than reusing the check already done in `pool()`. If `spotlit` is mutated between `pool()` and this point (it is not, in the current code, b

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 2322, cycle 1: consensus (the spotlight, rulings 90-92; the decoder c705b20ed800)

Reviewers: grok-4.20-0309-reasoning (SHIP yes, no finding), qwen3.8-27b (one critical, mediums; its reply then
repeats one paragraph about twenty times), glm-5.3-flash (first try failed on the network: IncompleteRead; retried on
the current diff, see C1_glm-5.3-flash.md when present). grok and qwen reviewed C1_STEP_grok_qwen.diff.

## Implemented

1. qwen <critical> 1: `never_delivered` was a literal True in build()'s facts, so the row could only PASS. It rested
   on pool()'s usable() call made at the build's start, but the row itself measured nothing (law L-m). FIXED:
   build() now measures it again right before the package: `P.usable([m], ctx, delivered, optout,
   seg_max=SPOT_S[1])` must keep the moment (no delivered span overlapped, not the same speech, inside 12 h). A
   moment usable() drops is a FAIL row and the pin is refused.

## Changed since cycle 1 by the builder (in the fixed diff)

2. The ALONE scorer's wait counts its polls (wait_s // SCORER_POLL_S) instead of reading the clock. Production waits
   the same; a test with a stubbed sleep no longer spins for 60 s.
3. The writer is told the speaker is VERIFIED only when BOTH step-A verdicts verify it. The gates read the verdict off
   the writer, which is unknown until the writer answers.
4. The driver reads SPOTLIGHTS.json again right before it writes a spotlight pin, and refuses the pin when the channel
   already has a spotlight that ET day or the record cannot be read. This closes a race between two builds.
5. snap(): a moment whose own span holds a speaker marker is reported as such, not as "not measured".

## Refuted, with evidence

- qwen <medium> 3 (LP.apply runs after the gates, so an adopted spoken text was not the text the verdicts judged):
  - This is the medley's own order (package.build's no_voice path and the voiced path both apply the lock after
    gate_problems), so it is not new.
  - LP.apply refuses a package whose lines quote an adopted segment's changed words (ruling 67).
  - The adopt class is fillers and one function word (ruling 84).
  - For a spotlight, the segment seals the ALONE scorer's verdict on the rated text. If an adoption changes the text,
    package_pin.scorer_problems refuses the pin ("carries a clip-scorer verdict that does not affirm exactly its
    text"), so it fails closed.
- qwen <medium> 4 (thread safety of VF.check / CI.check_contexts in parallel): package.paid_gates runs the same two
  calls in parallel on one pool for every medley package.
- qwen <medium> 5 (the build can wait up to 10 minutes for the ALONE scorer): this is by design, bounded
  (SCORER_WAIT_S), and only when a moment that passed every other stage has no rating yet.
- qwen <high> 2 (several versions): qwen retracted each one in its own text ("Retracted", "No bug").

## glm-5.3-flash (retried on the current diff: SHIP yes with conditions)

Implemented:
6. glm <medium> package_pin.p

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2322/C2_STEP.diff (2041 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | index 2da920e..e7095b4 100644
   3 | --- a/pipeline/lock_precheck.py
   4 | +++ b/pipeline/lock_precheck.py
   5 | @@ -42,10 +42,12 @@ import attest as AT
   6 |  
   7 |  RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
   8 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
   9 | -DECODER = "962353613cb0"                      # side): the render's own cut placement joins the pre-check (a passing
  10 | +DECODER = "c705b20ed800"                      # side): the render's own cut placement joins the pre-check (a passing
  11 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  12 | -#   84 changes the render's adjudicate_lock (pinned.py), so the decoder_sha changed again: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  13 | -#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7)
  14 | +#   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  15 | +#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  16 | +#   spotlight branches in pinned.py, merged fd5c9cc4 at 23:16 ET Nov 13; RULES unchanged; every medley span's decode,
  17 | +#   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  18 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  19 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  20 |                          "lock_requests")      # this worktree's; the service only reads it
  21 | diff --git a/pipeline/package.py b/pipeline/package.py
  22 | index 68384f1..8972b95 100644
  23 | --- a/pipeline/package.py
  24 | +++ b/pipeline/package.py
  25 | @@ -156,12 +156,13 @@ def expired(m, now):
  26 |      return age is None or age > package_pin.WINDOW_H
  27 |  
  28 |  
  29 | -def usable(moments, ctx, delivered=(), optout=frozenset()):
  30 | +def usable(moments, ctx, delivered=(), optout=frozenset(), seg_max=SEG_MAX_S):
  31 |      """delivered: moment ids, or {"video_id", "start", "end"[, "text", "pin"]} of every DELIVERED clip. A moment that
  32 |      overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated),
  33 |      and (RULING 76 b) neither is the same speech (same_speech) anywhere: re-posted by another channel, or said again
  34 |      at another time of the same video (audit 1810 C3: "never reuse any of it"). RULING 76 (a): a moment whose source
  35 | -    is over 12 h old on the render clock (ctx.now) is expired."""
  36 | +    is over 12 h old on the render clock (ctx.now) is expired. seg_max: the longest clip (L-u's 20 s per source video
  37 | +    for a medley; RULING 90's 35 s for a spotlight, the orchestrator's 22:58 note)."""
  38 |      ids = {d for d in delivered if isinstance(d, str)}
  39 |      spans = [d for d in delivered if isinstance(d, dict)]
  40 |      out, why = [], {}
  41 | @@ -187,8 +188,8 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
  42 |                           ", said again at another time of the same video"))
  43 |          elif m["channel_id"] in optout:
  44 |              why[mid] = "channel opted out"
  45 | -        elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
  46 | -            why[mid] = f"{m.get('duration_s')} s: over the {SEG_MAX_S} s per source video (L-u) or unmeasured"
  47 | +        elif m.get("duration_s") is None or m["duration_s"] > seg_max:
  48 | +            why[mid] = f"{m.get('duration_s')} s: over the {seg_max} s per source video (L-u) or unmeasured"
  49 |          elif time_sensitive(m) and (E.age_hours(m["published_at"], ctx.now) is None or
  50 |                                      E.age_hours(m["published_at"], ctx.now) > TIME_SENSITIVE_H):
  51 |              why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
  52 | @@ -1152,12 +1153,14 @@ def write_candidates(path, ms, ctx, build_name):
  53 |      return True
  54 |  
  55 |  
  56 | -def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
  57 | +def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, extra=()):
  58 |      """RULING 56, once per build, before any verdict is attached. (1) The integrator's verdicts (scorer_verdicts, fail
  59 |      closed). (2) The next pass's candidates (write_candidates): every moment the render's STAND_ALONE leaves out as an
  60 |      opener the clip scorer would have to affirm (no_role_on_screen fires, the topic rule does not: no verdict could
  61 |      give a moment that fails the topic rule a place), and the trimmed variant of every moment left out (ruling 33 part
  62 | -    2), each with its text exactly as it would be locked. -> {"index": {pid: verdict}, "record": {...}}."""
  63 | +    2), each with its text exactly as it would be locked. extra (RULING 90): the spotlight pool's moments
  64 | +    (spotlight.pool), whose stand-alone rating the spotlight needs; they join the same request, so the medley's own
  65 | +    candidates and the spotlight's never replace each other. -> {"index": {pid: verdict}, "record": {...}}."""
  66 |      index, rec = scorer_verdicts(verdicts_path, render_scorer_sha()) if verdicts_path else \
  67 |          ({}, {"read": False, "why": "no verdicts file given"})
  68 |      if candidates_path:
  69 | @@ -1165,6 +1168,12 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
  70 |                  ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
  71 |          ask = [m for m, o, t in left if o and not t] + \
  72 |              [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
  73 | +        have = {(m["moment_id"], text_sha(m["text"])) for m in ask}
  74 | +        for m in extra or ():                            # ruling 90: once each (same id and text)
  75 | +            k = (m["moment_id"], text_sha(m["text"]))
  76 | +            if k not in have:
  77 | +                have.add(k)
  78 | +                ask.append({x: y for x, y in m.items() if x != "scorer_verdict"})
  79 |          rec = dict(rec, candidates=len(ask), candidates_written=write_candidates(candidates_path, ask, ctx, build_name))
  80 |      return {"index": index, "record": rec}
  81 |  
  82 | @@ -2168,7 +2177,7 @@ def candidate_lineup(router, candidate, cleared, now):
  83 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  84 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  85 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  86 | -          visual_cache=None, registered=None, lock_check=None):
  87 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
  88 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  89 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  90 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  91 | @@ -2208,6 +2217,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  92 |        - a package keeps the approved texts, or seals an adopted spoken text with its "attested" record
  93 |          (lock_precheck.apply, checked again at the pin stage).
  94 |      The no-voice line-up is asked too. lock_check None: no pre-check (the tests' rigs); the driver always passes it.
  95 | +    scorer_extra (RULING 90): the spotlight pool's moments, sent to the clip scorer with this build's own candidates.
  96 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
  97 |      t0 = time.time()
  98 |      usd0 = _spent(spend)
  99 | @@ -2237,7 +2247,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 100 |      ms, why = usable(moments, ctx, delivered, optout)
 101 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 102 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 103 | -    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name)   # ruling 56
 104 | +    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name,   # ruling 56
 105 | +                         extra=scorer_extra)                                                       # ruling 90
 106 |      ms = [with_verdict(m, scorer["index"]) for m in ms]
 107 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
 108 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
 109 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 110 | index 34b2e86..445a53b 100644
 111 | --- a/pipeline/package_pin.py
 112 | +++ b/pipeline/package_pin.py
 113 | @@ -33,10 +33,45 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 114 |                  "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 115 |  
 116 |  
 117 | +# RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
 118 | +# Its contract, agreed with the integrator (22:44 ET): moments_package.shape "spotlight", ONE segment (role "hook"),
 119 | +# edl_vo {"intro": null, "bridges": [], "closing": <one line, <= 12 words> or null}, signoff_expected naming that one
 120 | +# channel, first_comment the WHOLE first comment (printed verbatim, nothing appended), and these gate rows, each exactly
 121 | +# PASS and not replayed. No medley row applies (no join, no clips-alone verdict, no coherence of several clips, no L-y
 122 | +# shape); the R4 of a spotlight is its 28-50 s runtime (the render's edl_rules R4 / G5), the "runtime" row.
 123 | +SPOTLIGHT_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime",
 124 | +                   "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable",
 125 | +                   "house_style", "hook_onset", "stand_alone",          # it opens cold: the hook's own pin-stage rows
 126 | +                   "spotlight_source",                                   # ruling 92: conversation, not reaction
 127 | +                   "hook_own", "stands_alone",                           # ruling 90: >= 4 as an opener, >= 4 alone
 128 | +                   "step_a_two_families", "visual", "window_12h", "never_delivered", "one_per_channel_day",
 129 | +                   "precheck")                                           # rulings 68 / 72 / 73 / 84: pass or adopt
 130 | +CLOSING_GATES = ("closing_value", "closing_fidelity", "closing_context")   # ruling 91: a non-null closing only with all
 131 | +SPOT_RUNTIME_S = (28.0, 50.0)            # ruling 90: the moment, the closing line, sign-off, credits card and outro
 132 | +SPOT_CLOSING_MAX_WORDS = 12              # ruling 90 / 91: at most ONE closing line of 12 words or fewer
 133 | +CREDITS_LINE = "Credits \U0001F9E1"      # ruling 90: PBX's first-comment format, 'Credits' and the orange heart
 134 | +
 135 | +
 136 | +def _closing(pk):
 137 | +    """The spotlight's closing line in a package (pk["vo"]) or in a pin's moments_package (edl_vo), else None."""
 138 | +    vo = (pk or {}).get("vo") if isinstance((pk or {}).get("vo"), dict) else (pk or {}).get("edl_vo")
 139 | +    return (vo or {}).get("closing")
 140 | +
 141 | +
 142 |  def required_gates(pk):
 143 |      """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 144 | -    clips-alone verdict and the L-y shape."""
 145 | -    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 146 | +    clips-alone verdict and the L-y shape. A spotlight (ruling 90): SPOTLIGHT_GATES, plus CLOSING_GATES whenever its
 147 | +    closing line is not null (ruling 91). pk: a package, or a pin's moments_package."""
 148 | +    shape = (pk or {}).get("shape")
 149 | +    if shape == "spotlight":
 150 | +        return SPOTLIGHT_GATES + (CLOSING_GATES if _closing(pk) is not None else ())
 151 | +    return REQUIRED_GATES + (MEDLEY_GATES if shape == "medley" else ())
 152 | +
 153 | +
 154 | +def first_comment_text(lines, tags):
 155 | +    """RULING 90: the first comment in PBX's format, the WHOLE comment: the casual line(s), a blank line, 'Credits' and
 156 | +    the orange heart, a blank line, the credits (verified X handles, or the untagged names). Code, never the model."""
 157 | +    return f"{lines}\n\n{CREDITS_LINE}\n\n{' '.join(tags)}"
 158 |  
 159 |  
 160 |  class PinRefused(Exception):
 161 | @@ -112,7 +147,7 @@ def window_problems(segments, now=None):
 162 |      return out
 163 |  
 164 |  
 165 | -def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 166 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None):
 167 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 168 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 169 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
 170 | @@ -121,7 +156,10 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 171 |      all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
 172 |      because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest.
 173 |      btc_screen (ruling 34: the miner's about-Bitcoin screen the render applies, {"pattern", "source"}) enters the body
 174 | -    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems)."""
 175 | +    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems).
 176 | +    RULING 90, the spotlight: for shape "spotlight" only, the body gains edl_vo's "closing" (null included), the
 177 | +    shape and first_comment. A medley's body never holds them, so every pin sealed before the spotlight recomputes
 178 | +    (pin_seal)."""
 179 |      def body_of(s):
 180 |          b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 181 |               "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
 182 | @@ -133,9 +171,23 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 183 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 184 |      if btc_screen is not None:
 185 |          body["btc_screen"] = btc_screen
 186 | +    if shape == "spotlight":                               # ruling 90: the closing line, the kind and the comment,
 187 | +        body["vo"]["closing"] = edl_vo.get("closing")      # sealed; keyed on the kind alone, so no medley's body
 188 | +        body["shape"], body["first_comment"] = shape, first_comment   # can change (audit 2322 C1, glm)
 189 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 190 |  
 191 |  
 192 | +def pin_seal(pin):
 193 | +    """The package_sha256 a pin's own bytes recompute to, exactly as to_pin sealed it, for every kind (a medley, the
 194 | +    PBX MAX v3 shape, a spotlight): the readiness check's one call. Raises KeyError / TypeError on a pin without the
 195 | +    sealed fields."""
 196 | +    mp = pin["moments_package"]
 197 | +    shape = mp.get("shape")
 198 | +    return seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"],
 199 | +                mp.get("btc_screen"), shape="spotlight" if shape == "spotlight" else None,
 200 | +                first_comment=mp.get("first_comment") if shape == "spotlight" else None)
 201 | +
 202 | +
 203 |  def affirmed_verdict(s):
 204 |      """RULING 56 under RULING 60: True when the segment carries the render's own clip scorer's AFFIRMATION of exactly its
 205 |      text (approved_text in a pin, text in a package): scorer_verdict with affirmed true, kind "moments" and no event
 206 | @@ -210,11 +262,11 @@ def screen_problems(pk):
 207 |      the screen but sealed without it could be refused at render. A carried screen is {"pattern": a non-empty str of at
 208 |      most 500 characters that compiles with re.I, "source": a non-empty str}: the render's own acceptance
 209 |      (run_fresh.moments_screen)."""
 210 | -    if pk.get("shape") != "medley":
 211 | +    if pk.get("shape") not in ("medley", "spotlight"):    # ruling 90: a spotlight is judged with the screen too
 212 |          return []
 213 |      sc = pk.get("btc_screen")
 214 |      if not isinstance(sc, dict) or set(sc) != {"pattern", "source"}:
 215 | -        return ["btc_screen: a medley must carry {pattern, source} (ruling 34)"]
 216 | +        return [f"btc_screen: a {pk.get('shape')} must carry {{pattern, source}} (ruling 34)"]
 217 |      pat, src = sc.get("pattern"), sc.get("source")
 218 |      if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 or not isinstance(src, str) or not src.strip():
 219 |          return ["btc_screen: the pattern must be a non-empty str of at most 500 characters, with a source"]
 220 | @@ -294,6 +346,42 @@ def line_problems(pk):
 221 |      for k in ("title", "caption"):
 222 |          if by.get(k) != pk.get(k):
 223 |              out.append(k)
 224 | +    if pk.get("shape") == "spotlight":                    # ruling 90: the closing line and the first comment too
 225 | +        if by.get("closing") != vo.get("closing"):
 226 | +            out.append("closing")
 227 | +        cr = pk.get("comment_credits") or {}
 228 | +        com = by.get("comment")
 229 | +        if not isinstance(com, str) or not com.strip() or not isinstance(cr.get("tags"), list) or \
 230 | +                not all(isinstance(t, str) and t.strip() for t in cr["tags"]) or \
 231 | +                pk.get("first_comment") != first_comment_text(com, cr["tags"]):
 232 | +            out.append("first_comment")
 233 | +    return out
 234 | +
 235 | +
 236 | +def spotlight_problems(pk):
 237 | +    """[why] for a spotlight that breaks the agreed contract (ruling 90): exactly ONE segment; no intro and no bridge;
 238 | +    a closing line of at most SPOT_CLOSING_MAX_WORDS words, or null; a sign-off that names the segment's channel; a
 239 | +    non-empty first comment; the runtime estimate inside SPOT_RUNTIME_S. Any other shape: none."""
 240 | +    if pk.get("shape") != "spotlight":
 241 | +        return []
 242 | +    out = []
 243 | +    segs = pk.get("segments") or []
 244 | +    vo = pk.get("vo") or {}
 245 | +    if len(segs) != 1:
 246 | +        out.append(f"a spotlight has exactly one segment (got {len(segs)})")
 247 | +    if vo.get("intro") is not None or vo.get("bridges") or vo.get("bridges_after_clip"):
 248 | +        out.append("a spotlight has no intro and no bridge (ruling 90)")
 249 | +    c = vo.get("closing")
 250 | +    if c is not None and (not isinstance(c, str) or not c.strip() or len(c.split()) > SPOT_CLOSING_MAX_WORDS):
 251 | +        out.append(f"the closing line must be null or 1-{SPOT_CLOSING_MAX_WORDS} words (ruling 90): {c!r}")
 252 | +    ch = segs[0].get("channel") if len(segs) == 1 else None
 253 | +    if not isinstance(ch, str) or not ch.strip() or ch not in str(vo.get("signoff") or ""):
 254 | +        out.append(f"the sign-off must name the spotlight's one channel {ch!r} (ruling 90)")
 255 | +    if not isinstance(pk.get("first_comment"), str) or not pk["first_comment"].strip():
 256 | +        out.append("a spotlight carries its first comment (ruling 90)")
 257 | +    rt = pk.get("runtime_s_estimate")
 258 | +    if not isinstance(rt, (int, float)) or isinstance(rt, bool) or not SPOT_RUNTIME_S[0] <= rt <= SPOT_RUNTIME_S[1]:
 259 | +        out.append(f"runtime estimate {rt!r} outside {SPOT_RUNTIME_S[0]:g}-{SPOT_RUNTIME_S[1]:g} s (ruling 90)")
 260 |      return out
 261 |  
 262 |  
 263 | @@ -301,7 +389,8 @@ def to_pin(pk, run_name):
 264 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 265 |                                                                       for x in line_problems(pk)] + \
 266 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 267 | -        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or [])
 268 | +        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
 269 | +        spotlight_problems(pk)
 270 |      if problems:
 271 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 272 |      segs = []
 273 | @@ -317,7 +406,11 @@ def to_pin(pk, run_name):
 274 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 275 |      edl_vo = {"intro": pk["vo"]["intro"],
 276 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 277 | -    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"))
 278 | +    spot = pk.get("shape") == "spotlight"                 # ruling 90: the agreed contract
 279 | +    if spot:
 280 | +        edl_vo["closing"] = pk["vo"].get("closing")
 281 | +    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"),
 282 | +               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None)
 283 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
 284 |              "label": "bitcoin", "headline": pk["title"],
 285 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
 286 | @@ -332,12 +425,18 @@ def to_pin(pk, run_name):
 287 |                                  "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
 288 |                                                 if pk["vo"]["intro"] else {}),
 289 |                                              **{s: "takeaway" if s == "takeaway" else "connection"
 290 | -                                               for s in bridge_slots(pk)}},
 291 | +                                               for s in bridge_slots(pk)},
 292 | +                                            **({"closing": "closing"} if spot and edl_vo["closing"] is not None
 293 | +                                               else {})},
 294 |                                  "shape": pk.get("shape"),
 295 |                                  "bridge": pk.get("bridge"),
 296 |                                  "supply_exception": pk.get("supply_exception"),
 297 |                                  "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
 298 |                                  "caption_fallback": bool(pk.get("caption_fallback")),   # ruling 65 (b): a placeholder
 299 | +                                **({"first_comment": pk["first_comment"],              # ruling 90: sealed, printed
 300 | +                                    "first_comment_credits": pk.get("comment_credits"),  # verbatim; who is tagged
 301 | +                                    "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 302 | +                                   if spot else {}),
 303 |                                  "gates": pk["gates"],
 304 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 305 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 306 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 307 | new file mode 100644
 308 | index 0000000..e443d86
 309 | --- /dev/null
 310 | +++ b/pipeline/spotlight.py
 311 | @@ -0,0 +1,1005 @@
 312 | +#!/usr/bin/env python3
 313 | +"""pipeline/spotlight.py: RULINGS 90, 91 and 92 (the orchestrator's 22:40 and 22:52 orders, Nov 13; ruling 90 is LAW
 314 | +since 22:52): the SPOTLIGHT, a second pin kind. The medley stays the flagship and is always tried first: "a spotlight
 315 | +is built only when the window's search ends with no medley, or for a moment no medley used".
 316 | +
 317 | +RULING 90, its words: "ONE moment, one speaker, one channel: 12 to 35 s of clip. No hook/clip split, no bridge, no
 318 | +join. Then at most ONE closing line in the PBX MAX voice, 12 words or fewer, class D commentary that characterises what
 319 | +was SAID (the two refused patterns stay refused) ... Then the sign-off and the credits card with that one channel, then
 320 | +the outro. Total 28 to 50 s. ... it must rate >= 4 on the hook's own job (it opens cold) AND >= 4 as a clip standing
 321 | +alone (the ALONE scorer + step A, both vendors as routed); the visual check clean; inside 12 h at the render clock;
 322 | +never a delivered span; at most one spotlight per channel per day. If the strong moment is under 12 s, snap it OUTWARD
 323 | +to the speaker's whole thought (ruling 32's snap; the added words judged as usual), not padded. EVERY integrity law is
 324 | +unchanged: L-s, L-v, the pre-check (17 / 72 / 73 / 84), the cut rules, G16-G20, the credits."
 325 | +RULING 91: "Default for a spotlight: NO PBX line ... A line is written only as a candidate and is kept only if a
 326 | +separate VALUE verdict (off the writer's family) answers all of: it says something the clip does not already say; it
 327 | +does not restate, summarise or cheer the clip; a viewer would miss it if it were cut; it is 12 words or fewer; plus
 328 | +the usual fidelity and context gates. One write, one verdict; anything short of a clear yes means no line."
 329 | +RULING 92: "A spotlight moment must come from a conversation or original reporting ... NOT from a solo host-to-camera
 330 | +news recap or reaction segment, on any channel. Measured, not listed by name: the turn markers across the episode (one
 331 | +speaker throughout = solo), plus the visual check's layout (one face to camera with headline graphics or b-roll =
 332 | +recap)."
 333 | +The pin contract, agreed with the integrator at 22:44 ET: package_pin's shape "spotlight" (SPOTLIGHT_GATES,
 334 | +CLOSING_GATES, spotlight_problems, first_comment_text, the sealed closing / shape / first comment).
 335 | +
 336 | +- pool(): free, before any verdict. package.usable with ruling 90's 35 s ceiling (the orchestrator's 22:58 note: L-u's
 337 | +  20 s per source video is a medley rule), one spotlight per channel per ET day (the SPOTLIGHTS record), the snap of a
 338 | +  short moment (snap()), the render's hook opener rule and its topic rule. The driver sends the pool to the clip scorer
 339 | +  with the medley's own candidates at the build's start (package.build's scorer_extra), so the ALONE rating is asked
 340 | +  before the spotlight needs it.
 341 | +- build(): the medley's own verdicts, each cached or recorded across builds (step A, the second recognition pass and
 342 | +  CUTTABLE, G17a, the hook rating, the visual sheet, the second step-A family), then the ALONE scorer, ruling 92's
 343 | +  source test, the exclusion verdict and the render's lock pre-check, best moment first; then ONE write (title,
 344 | +  caption, the first comment and a candidate closing line), the gates, the closing line's value verdict, and the
 345 | +  package. Nothing measured is never a pass (law L-m); any failure of the closing line leaves no line (ruling 91).
 346 | +"""
 347 | +import base64
 348 | +import hashlib
 349 | +import json
 350 | +import os
 351 | +import re
 352 | +import threading
 353 | +import time
 354 | +from concurrent.futures import ThreadPoolExecutor
 355 | +
 356 | +import context_integrity as CI
 357 | +import eligibility as E
 358 | +import house_style as HS
 359 | +import package as P
 360 | +import package_pin as PP
 361 | +import vo_fidelity as VF
 362 | +
 363 | +SPOT_S = (12.0, 35.0)                  # ruling 90: 12 to 35 s of clip
 364 | +RUNTIME_S = PP.SPOT_RUNTIME_S          # ruling 90: total 28 to 50 s (the render's edl_rules R4 / G5)
 365 | +SNAP_TO_S = round(max(SPOT_S[0], RUNTIME_S[0] - P.FINAL_TAIL_S), 2)
 366 | +#   13.7 s: the factory's tail (sign-off, credits card, outro, edges) is 14.3 s, so with no closing line (ruling 91's
 367 | +#   default) a shorter clip cannot reach 28 s. A moment shorter than this is snapped; it is never padded.
 368 | +HOOK_MIN = 4                           # ruling 90: >= 4 on the hook's own job (package.hook_own: scroll / alone)
 369 | +ALONE_MIN = 4.0                        # ruling 90: >= 4 standing alone, by the ALONE scorer (its scale is 1-5)
 370 | +CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
 371 | +COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
 372 | +COMMENT_MAX_WORDS = 30
 373 | +MARKER_TOL_S = 1.0                     # = ledger_build.MARKER_EDGE_S: a caption marker this close to an edge is not in
 374 | +LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
 375 | +LAYOUT_OK = ("conversation", "first_hand")
 376 | +CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 377 | +FINALISTS = 3                          # moments taken to exclusion, the pre-check and the write, best first
 378 | +WRITES = 2                             # the title, caption and comment: one more write when a gate refuses them
 379 | +SCORER_WAIT_S = 600.0                  # a moment that passes everything but has no ALONE rating yet waits this long for
 380 | +SCORER_POLL_S = 30.0                   # the integrator's scorer pass (its request went out at the build's start)
 381 | +HANDLES = "/home/ultron/protocol_pulse/pipeline/channels.json"   # the integrator's registry: x_handle is verified,
 382 | +HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")                 # an empty one is none (22:44 ET)
 383 | +VALUE_KEYS = ("adds", "no_restate", "missed", "short")
 384 | +CLOSING_SAID = P.TAKEAWAY_SAID.replace("The takeaway may", "The closing line may").replace("the clips SAID",
 385 | +                                                                                            "the clip SAID")
 386 | +
 387 | +
 388 | +def et_day(now):
 389 | +    """The ET calendar day of the render clock (all times ET): the 'day' of one spotlight per channel per day."""
 390 | +    from zoneinfo import ZoneInfo
 391 | +    return now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
 392 | +
 393 | +
 394 | +def load_spotlit(path):
 395 | +    """The spotlights already sealed: [{"channel_id", "channel", "day_et", "story_id", "package_sha256", "at"}]. No
 396 | +    file: none yet. -> the list, or None when the file cannot be read (then one per channel per day is not measured,
 397 | +    and no spotlight is built: law L-m)."""
 398 | +    if not os.path.exists(path):
 399 | +        return []
 400 | +    try:
 401 | +        with open(path) as f:
 402 | +            rows = json.load(f)["spotlights"]
 403 | +    except (OSError, ValueError, KeyError, TypeError):
 404 | +        return None
 405 | +    ok = isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("channel_id"), str) and
 406 | +                                        r["channel_id"] and isinstance(r.get("day_et"), str) for r in rows)
 407 | +    return rows if ok else None
 408 | +
 409 | +
 410 | +def record_spotlit(path, row):
 411 | +    """Append one sealed spotlight to the record, atomically. Raises ValueError when the record cannot be read."""
 412 | +    rows = load_spotlit(path)
 413 | +    if rows is None:
 414 | +        raise ValueError(f"{path} cannot be read: the spotlight is not recorded")
 415 | +    with open(path + ".tmp", "w") as f:
 416 | +        json.dump({"spotlights": rows + [row]}, f, indent=1)
 417 | +    os.replace(path + ".tmp", path)
 418 | +
 419 | +
 420 | +def snap(m, sources, ctx, captions_for=None):
 421 | +    """RULING 90 with ruling 32's snap: a moment shorter than SNAP_TO_S is snapped OUTWARD to the speaker's whole
 422 | +    thought: whole sentences of the SAME word record, the next ones first (the speaker going on), then the ones before
 423 | +    it, until it lasts SNAP_TO_S, never past SPOT_S[1] and never across a caption speaker-change marker (ruling 69's
 424 | +    markers; MARKER_TOL_S from an edge does not count, as ruling 32 reads them). Never padded. Captions with no marker
 425 | +    show no change; L-v 2 then measures one speaker on the audio, as for any snapped moment. The snapped span is a NEW
 426 | +    moment (its own id; the miner's eligibility and price-prediction risk judged again on it) and every gate of the
 427 | +    build judges it as usual. -> (moment, None) or (None, why)."""
 428 | +    import ledger_build as LB
 429 | +    import moments as M
 430 | +    import speakers as SP
 431 | +    try:
 432 | +        src = P.src_of(m, sources)
 433 | +        k0, k1 = m["sentences"]
 434 | +        n = len(src.sentences)
 435 | +        units, _ = (captions_for or SP.captions)(m["video_id"])
 436 | +    except Exception as e:                             # noqa: BLE001  no record to snap in: never a guess
 437 | +        return None, f"no word record or caption record to snap in ({type(e).__name__}: {str(e)[:120]})"
 438 | +    marks = [u[0] for u in units or () if u[2]]
 439 | +
 440 | +    def t(i, key):
 441 | +        x = src.tokens[i].get(key)
 442 | +        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
 443 | +
 444 | +    def measure(a, b):
 445 | +        t0, t1 = t(src.sentences[a][0], "start"), t(src.sentences[b][1], "end")
 446 | +        if t0 is None or t1 is None:
 447 | +            return None, "a word time is missing"
 448 | +        if t1 - t0 > SPOT_S[1]:
 449 | +            return None, f"it would run {t1 - t0:.2f} s, over {SPOT_S[1]:g} s"
 450 | +        inside = [x for x in marks if t0 + MARKER_TOL_S < x < t1 - MARKER_TOL_S]
 451 | +        if inside:
 452 | +            return None, f"a caption speaker-change marker at {inside[0]:.2f} s"
 453 | +        return t1 - t0, None
 454 | +
 455 | +    a, b = k0, k1
 456 | +    dur, why = measure(a, b)
 457 | +    if dur is None:
 458 | +        return None, f"the moment itself: {why}"
 459 | +    if dur >= SNAP_TO_S:
 460 | +        return m, None                                 # long enough: no snap, the moment as it is
 461 | +    blocked = []
 462 | +    while dur < SNAP_TO_S:
 463 | +        step = None
 464 | +        for na, nb, side in ((a, b + 1, "the next sentence"), (a - 1, b, "the sentence before")):
 465 | +            if na < 0 or nb >= n:
 466 | +                blocked.append(f"{side}: the word record ends")
 467 | +                continue
 468 | +            d, w = measure(na, nb)
 469 | +            if d is None:
 470 | +                blocked.append(f"{side}: {w}")
 471 | +                continue
 472 | +            step = (na, nb, d)
 473 | +            break
 474 | +        if step is None:
 475 | +            return None, f"{dur:.2f} s and no whole sentence can be added ({'; '.join(blocked[-2:])})"
 476 | +        a, b, dur = step
 477 | +    sp = E.Span(src, a, b)
 478 | +    w_old0, w_old1 = src.sentences[k0][0], src.sentences[k1][1]
 479 | +    info = {"snapped_words": [w_old0 - sp.w0, sp.w1 - w_old1]}
 480 | +    record = {"from": m["moment_id"], "sentences": [a, b], "was": [k0, k1], "seconds": [m.get("duration_s"), None],
 481 | +              "added": {"before": E.spoken(src.tokens[sp.w0:w_old0]), "after": E.spoken(src.tokens[w_old1 + 1:sp.w1 + 1])},
 482 | +              "rule": f"ruling 90 with ruling 32's snap: whole sentences outward to {SNAP_TO_S:g} s, no speaker marker"}
 483 | +    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
 484 | +                        "risk": LB.snap_risk(sp.text, info, m.get("risk")), "topics": list(m.get("topics") or []),
 485 | +                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
 486 | +                   dict(m.get("mined") or {}, spotlight_snap_from=m["moment_id"]))
 487 | +    rec["rank_score"] = M.rank_score(rec)
 488 | +    if m.get("source_key"):
 489 | +        rec["source_key"] = m["source_key"]
 490 | +    record["seconds"][1] = rec["duration_s"]
 491 | +    rec["spotlight_snap"] = record
 492 | +    return rec, None
 493 | +
 494 | +
 495 | +def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), captions_for=None):
 496 | +    """Stage 1, FREE (no vendor call) -> (the moments that may be a spotlight, {moment id: why not}): package.usable
 497 | +    with ruling 90's 35 s ceiling (inside 12 h on the render clock, never a delivered span or the same speech, no hard
 498 | +    exclusion, no speaker change inside, L-v 3), one per re-posted speech (ruling 53), one spotlight per channel per ET
 499 | +    day (spotlit; None: not measured, so none), a moment under SNAP_TO_S snapped (snap(), then usable() again on the
 500 | +    snapped span), the render's STAND_ALONE hook opener rule (it opens cold) and its topic rule."""
 501 | +    import stand_alone as SA
 502 | +    ms, why = P.usable(moments, ctx, delivered, optout, seg_max=SPOT_S[1])
 503 | +    ms, reposted = P.reposted_once(ms, sources)
 504 | +    why.update({k: f"ruling 53: {v}" for k, v in reposted.items()})
 505 | +    if spotlit is None:
 506 | +        why.update({m["moment_id"]: "ruling 90: one spotlight per channel per day is not measured (the spotlights "
 507 | +                                    "record cannot be read)" for m in ms})
 508 | +        return [], why
 509 | +    day = et_day(ctx.now)
 510 | +    taken = {r["channel_id"] for r in spotlit if r.get("day_et") == day}
 511 | +    out, seen = [], set()
 512 | +    for m in ms:
 513 | +        mid = m["moment_id"]
 514 | +        if m["channel_id"] in taken:
 515 | +            why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
 516 | +            continue
 517 | +        v = m
 518 | +        if float(m["duration_s"]) < SNAP_TO_S:
 519 | +            v, w = snap(m, sources, ctx, captions_for)
 520 | +            if v is None:
 521 | +                why[mid] = f"ruling 90: {m['duration_s']} s is under {SNAP_TO_S:g} s and the snap fails: {w}"
 522 | +                continue
 523 | +            ok, w2 = P.usable([v], ctx, delivered, optout, seg_max=SPOT_S[1])
 524 | +            if not ok:
 525 | +                why[mid] = f"ruling 90: snapped to {v['moment_id']} ({v['duration_s']} s), which is out: " \
 526 | +                           f"{w2.get(v['moment_id'])}"
 527 | +                continue
 528 | +        if v["moment_id"] in seen:
 529 | +            why[mid] = f"the same span as {v['moment_id']}, already in the pool"
 530 | +            continue
 531 | +        ok, w = SA.opener("hook", v.get("text") or "")
 532 | +        if not ok:
 533 | +            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"
 534 | +            continue
 535 | +        top = P.no_topic(v)
 536 | +        if top:
 537 | +            why[mid] = top
 538 | +            continue
 539 | +        seen.add(v["moment_id"])
 540 | +        out.append(v)
 541 | +    return out, why
 542 | +
 543 | +
 544 | +def episode_turns(video_id, captions_for=None):
 545 | +    """RULING 92's caption half: the speaker-change markers across the EPISODE (speakers.captions, ruling 69's reader).
 546 | +    -> {"measured", "turns", "minutes", "turns_per_min", "file", "sha256"}; no marked record: {"measured": False,
 547 | +    "unmarked": True} (no marker at all is unknown, not solo: pp-ingest's contract)."""
 548 | +    import speakers as SP
 549 | +    try:
 550 | +        units, rec = (captions_for or SP.captions)(video_id)
 551 | +    except Exception as e:                             # noqa: BLE001
 552 | +        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:120]}"}
 553 | +    if not units:
 554 | +        return {"measured": False, "unmarked": True,
 555 | +                "why": "no caption record with speaker-change markers: unmarked or missing (unknown, not solo)"}
 556 | +    turns = sum(1 for u in units if u[2])
 557 | +    minutes = (units[-1][0] - units[0][0]) / 60.0
 558 | +    return {"measured": True, "turns": turns, "minutes": round(minutes, 1),
 559 | +            "turns_per_min": round(turns / minutes, 2) if minutes > 0 else None,
 560 | +            "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 561 | +
 562 | +
 563 | +def source_test(turns, layout):
 564 | +    """RULING 92 -> (ok, why). A PASS needs a MEASURED layout of a conversation or a first-hand statement
 565 | +    (LAYOUT_OK). A recap, a reaction, or a layout the judge cannot place ('other') fails on any channel; a layout that
 566 | +    is not measured is never a pass (law L-m). The caption markers across the episode can only make it stricter: a
 567 | +    layout read as a conversation from an episode whose captions are marked but carry fewer than CONVERSATION_TPM
 568 | +    turns a minute is not measured as a conversation (Nov 13: Simply Bitcoin's solo recap L6H7538ogGs 0.48 turns a
 569 | +    minute; the pool's interviews and panels 1.18-2.53). Unmarked captions are unknown, not solo: the layout decides."""
 570 | +    if not (layout or {}).get("measured"):
 571 | +        return False, f"the layout is not measured: {(layout or {}).get('why')}"
 572 | +    lay = layout["layout"]
 573 | +    if lay not in LAYOUT_OK:
 574 | +        return False, f"the layout is '{lay}' ({layout.get('why')}): not a conversation or a first-hand statement"
 575 | +    tpm = (turns or {}).get("turns_per_min")
 576 | +    if lay == "conversation" and (turns or {}).get("measured") and (tpm is None or tpm < CONVERSATION_TPM):
 577 | +        return False, (f"the frames read as a conversation but the episode's captions carry {tpm} speaker turns a "
 578 | +                       f"minute (under {CONVERSATION_TPM:g})")
 579 | +    return True, f"layout '{lay}'" + (f"; {turns['turns']} caption turns in {turns['minutes']} min ({tpm} a minute)"
 580 | +                                      if (turns or {}).get("measured") else "; captions unmarked")
 581 | +
 582 | +
 583 | +LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 584 | +bottom. The clip's words, as spoken: "{text}"
 585 | +From the frames only, classify the SOURCE's format:
 586 | +- "conversation": two or more people talking with each other: an interview, a podcast, a panel (in one room, or on a
 587 | +  split screen or a video call);
 588 | +- "first_hand": one person making their own statement to an audience: a keynote, a speech, a guest answering on a news
 589 | +  network;
 590 | +- "recap": one host speaking to the camera with headline graphics, a news set or b-roll: a news recap;
 591 | +- "reaction": a host showing or reacting to another video, a post or a chart inside the host's own frame;
 592 | +- "other": none of these, or you cannot tell.
 593 | +Return ONLY this JSON object: {{"layout": "conversation" | "first_hand" | "recap" | "reaction" | "other",
 594 | +"people_on_screen": <the most people visible in one frame, a number>, "why": "<one sentence>"}}"""
 595 | +LAYOUT_VERSION = hashlib.sha256(LAYOUT_PROMPT.encode()).hexdigest()[:12]
 596 | +LAYOUT_LOCK = threading.Lock()
 597 | +
 598 | +
 599 | +def parse_layout(text):
 600 | +    """The layout verdict in contract, or ValueError."""
 601 | +    v = json.loads(text.strip())
 602 | +    if not isinstance(v, dict) or set(v) != {"layout", "people_on_screen", "why"}:
 603 | +        raise ValueError("keys must be exactly layout, people_on_screen, why")
 604 | +    if v["layout"] not in LAYOUTS or type(v["people_on_screen"]) is not int or v["people_on_screen"] < 0 or \
 605 | +            not isinstance(v["why"], str) or not v["why"].strip():
 606 | +        raise ValueError("layout out of contract")
 607 | +    return {"layout": v["layout"], "people_on_screen": v["people_on_screen"], "why": v["why"].strip()[:300]}
 608 | +
 609 | +
 610 | +def _load_json(path):
 611 | +    try:
 612 | +        with open(path) as f:
 613 | +            d = json.load(f)
 614 | +        return d if isinstance(d, dict) else {}
 615 | +    except (OSError, ValueError):
 616 | +        return {}
 617 | +
 618 | +
 619 | +def layout_for(router, m, vrec, cache_path=None, seed=7):
 620 | +    """RULING 92's visual half: the source's layout, judged on the clip's own contact sheet (the visual check's, ruling
 621 | +    70: the same bytes it judged) with LAYOUT_PROMPT, by the visual_check role (one call, cached by the moment, the
 622 | +    sheet's sha256 and the prompt's version). -> {"measured", "layout", "people_on_screen", "why", "backend",
 623 | +    "replayed"} or {"measured": False, "why"}: never a pass unmeasured."""
 624 | +    import providers as Pr
 625 | +    from story_semantics import quote_data
 626 | +    sheet = (vrec or {}).get("sheet") or {}
 627 | +    path, sha = sheet.get("path"), sheet.get("sha256")
 628 | +    if not (vrec or {}).get("measured") or not path or not sha:
 629 | +        return {"measured": False, "why": "no judged contact sheet (the visual check is not measured)"}
 630 | +    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}"
 631 | +    hit = _load_json(cache_path).get(k) if cache_path else None
 632 | +    if isinstance(hit, dict) and hit.get("measured") is True:
 633 | +        return dict(hit, cached=True)
 634 | +    try:
 635 | +        with open(path, "rb") as f:
 636 | +            raw = f.read()
 637 | +    except OSError as e:
 638 | +        return {"measured": False, "why": f"the sheet cannot be read ({type(e).__name__})"}
 639 | +    if hashlib.sha256(raw).hexdigest() != sha:
 640 | +        return {"measured": False, "why": "the sheet on disk is not the one the visual check judged"}
 641 | +    prompt = {"text": LAYOUT_PROMPT.format(n=len(sheet.get("times") or []),
 642 | +                                           text=quote_data(m.get("text") or "", 700).replace('"', "'")),
 643 | +              "images": [base64.b64encode(raw).decode()]}
 644 | +    r = None
 645 | +    try:
 646 | +        r = router.call("visual_check", prompt, 600, seed)
 647 | +        v = parse_layout(r.text)
 648 | +    except Exception as e:                             # noqa: BLE001  no verdict: never a pass (law L-m)
 649 | +        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
 650 | +            router.reject(r)
 651 | +        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 652 | +    rec = dict(v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
 653 | +               version=LAYOUT_VERSION, sheet_sha256=sha)
 654 | +    if cache_path and not rec["replayed"]:
 655 | +        with LAYOUT_LOCK:
 656 | +            c = _load_json(cache_path)
 657 | +            c[k] = rec
 658 | +            with open(cache_path + ".tmp", "w") as f:
 659 | +                json.dump(c, f, indent=1)
 660 | +            os.replace(cache_path + ".tmp", cache_path)
 661 | +    return rec
 662 | +
 663 | +
 664 | +def alone_score(m):
 665 | +    """The ALONE scorer's rating of the moment's CURRENT text (package.verdict_of: the integrator's verdicts of the
 666 | +    render's own scorer, rulings 56 / 60), or None when it has none yet."""
 667 | +    v = P.verdict_of(m)
 668 | +    return float(v["score"]) if v is not None else None
 669 | +
 670 | +
 671 | +def _published_ts(m):
 672 | +    """The moment's publish time as a UTC timestamp; an unreadable one sorts as the oldest."""
 673 | +    from datetime import datetime, timezone
 674 | +    z = P.utc_z(m.get("published_at"))
 675 | +    return datetime.strptime(z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if z else float("-inf")
 676 | +
 677 | +
 678 | +def rank_key(m):
 679 | +    """Best first: the hook's own-job rating, the ALONE rating, the hook's parts, the miner's score, the newest
 680 | +    source, then the id (a total order)."""
 681 | +    hr = m.get("hook_rating") or {}
 682 | +    return (-((P.hook_own(m) or {}).get("rating") or 0), -(alone_score(m) or 0.0),
 683 | +            -sum(hr.get(k) or 0 for k in P.HOOK_PARTS), -float(m.get("rank_score") or 0.0), -_published_ts(m),
 684 | +            m["moment_id"])
 685 | +
 686 | +
 687 | +WRITE_SPOT = """You are PBX MAX, the host of a short Bitcoin video that SPOTLIGHTS one clip of another channel's own
 688 | +words. The clip plays alone, in full; then a sign-off credits the channel (written by code).
 689 | +
 690 | +{note}
 691 | +{clip}
 692 | +
 693 | +Write:
 694 | +- "title": ONE title of at most 8 words (and at most 70 characters) that says what the clip is about.
 695 | +- "caption": ONE caption (at most 220 characters).
 696 | +- "comment": the first comment under the video, as PBX writes them: one or two short casual lines about THIS clip in
 697 | +  plain words; not preachy; no emoji, no hashtags, no handles, no links and no credits (code adds the credits).
 698 | +- "closing": a CANDIDATE closing line the host speaks right after the clip, at most {cmax} words, as your OWN
 699 | +  commentary. It is kept ONLY if it says something the clip does not already say: it never restates, summarises or
 700 | +  cheers the clip, and a viewer would miss it if it were cut. When you have nothing to add, give null: the clip then
 701 | +  goes straight to the sign-off, which is the default. {said}
 702 | +Every line gives "cites": the clip's id when it relies on the clip (none for your own commentary).
 703 | +RULES (a line that breaks one is rejected):
 704 | +- NEVER restate the clip's claim, and never repeat its words: the clip says it, in its own words.
 705 | +- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
 706 | +  or company; never what the speaker thinks; no prediction of what will happen; no advice or instruction to the viewer
 707 | +  (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
 708 | +- Say what the speaker says or thinks ONLY when the clip is marked VERIFIED, by that name, with the clip's own hedge:
 709 | +  "thinks" for "I think", "feels" for "I feel like", "says" only for a flat statement. Otherwise credit the SHOW only
 710 | +  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
 711 | +- No price level; no advice to buy, sell or use leverage; no quotes except the clip's exact words; no "destroys",
 712 | +  "slams", "exposes", "admits", "confirms", "caught".
 713 | +- A line that names a show, a person or Bitcoin's price cites the clip.
 714 | +{style}
 715 | +{extra}Return ONLY this JSON object: {{"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}},
 716 | +"comment": {{"text": "...", "cites": []}}, "closing": {{"text": "...", "cites": []}} or null}}"""
 717 | +
 718 | +VALUE_PROMPT = """You judge ONE line a host would speak right after a clip in a short video. The clip plays first,
 719 | +alone and in full; then the host's line; then a sign-off credits the channel.
 720 | +{note}
 721 | +CLIP (on {show}): "{clip}"
 722 | +LINE: "{line}"
 723 | +Answer each question "yes" or "no". Anything you cannot answer with a clear yes is "no".
 724 | +- "adds": does the line say something the clip does not already say?
 725 | +- "no_restate": does the line avoid restating, summarising or cheering the clip?
 726 | +- "missed": would a viewer miss the line if it were cut?
 727 | +- "short": is the line 12 words or fewer?
 728 | +Return ONLY this JSON object: {{"adds": "yes" | "no", "no_restate": "yes" | "no", "missed": "yes" | "no", "short":
 729 | +"yes" | "no", "why": "<one sentence>"}}"""
 730 | +
 731 | +
 732 | +def parse_write(text, mid, closing_allowed=True):
 733 | +    """One write in contract -> {"title", "caption", "comment", "closing"} (closing None or a line), or ValueError."""
 734 | +    obj = json.loads(text.strip())
 735 | +    keys = {"title", "caption", "comment", "closing"}
 736 | +    if not isinstance(obj, dict) or set(obj) != keys:
 737 | +        raise ValueError(f"keys must be exactly {sorted(keys)}")
 738 | +    out = {}
 739 | +    for slot in ("title", "caption", "comment", "closing"):
 740 | +        ln = obj[slot]
 741 | +        if slot == "closing" and (ln is None or not closing_allowed):
 742 | +            out[slot] = None
 743 | +            continue
 744 | +        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 745 | +                not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 746 | +                any(not isinstance(c, str) or c != mid for c in ln["cites"]):
 747 | +            raise ValueError(f"{slot}: needs text and cites from the clip's id")
 748 | +        out[slot] = {"text": ln["text"].strip(), "cites": list(dict.fromkeys(ln["cites"]))}
 749 | +    if len(out["title"]["text"]) > 70 or len(out["caption"]["text"]) > 220:
 750 | +        raise ValueError("title <= 70 characters, caption <= 220")
 751 | +    return out
 752 | +
 753 | +
 754 | +def parse_value(text):
 755 | +    """Ruling 91's value verdict in contract -> {"adds", "no_restate", "missed", "short", "why"}, or ValueError."""
 756 | +    v = json.loads(text.strip())
 757 | +    if not isinstance(v, dict) or set(v) != set(VALUE_KEYS) | {"why"}:
 758 | +        raise ValueError(f"keys must be exactly {sorted(set(VALUE_KEYS) | {'why'})}")
 759 | +    if any(v[k] not in ("yes", "no") for k in VALUE_KEYS) or not isinstance(v["why"], str):
 760 | +        raise ValueError("each answer is 'yes' or 'no', with a reason")
 761 | +    return {**{k: v[k] for k in VALUE_KEYS}, "why": v["why"].strip()[:300]}
 762 | +
 763 | +
 764 | +def value_verdict(router, m, line, show, writers_v, writers_f, seed=7):
 765 | +    """RULING 91: ONE value verdict on the candidate closing line, off the writer's vendor and family (the
 766 | +    coherence_verdict role). ok only when all four answers are "yes" AND the line counts at most CLOSING_MAX_WORDS
 767 | +    words in code; an unavailable or out-of-contract answer is no verdict, so no line (never re-asked: "one write, one
 768 | +    verdict")."""
 769 | +    import providers as Pr
 770 | +    from select_by_id import UNTRUSTED
 771 | +    from story_semantics import quote_data
 772 | +    prompt = VALUE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), show=quote_data(show, 80),
 773 | +                                 clip=quote_data(m["text"], 1200).replace('"', "'"),
 774 | +                                 line=quote_data(line, 200).replace('"', "'"))
 775 | +    r = None
 776 | +    try:
 777 | +        r = router.call("coherence_verdict", prompt, 400, seed, avoid_vendor=writers_v, avoid_family=writers_f)
 778 | +        v = parse_value(r.text)
 779 | +    except Exception as e:                             # noqa: BLE001  no verdict: no line (ruling 91)
 780 | +        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
 781 | +            router.reject(r)
 782 | +        return {"measured": False, "ok": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 783 | +    words = len(line.split())
 784 | +    return dict(v, measured=True, ok=all(v[k] == "yes" for k in VALUE_KEYS) and words <= CLOSING_MAX_WORDS,
 785 | +                words=words, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 786 | +
 787 | +
 788 | +def style_lint(lines):
 789 | +    """PBX's house style on a spotlight's lines: the title and caption rules (house_style.lint); the closing line by
 790 | +    the takeaway's rules and at most CLOSING_MAX_WORDS words; the comment by the rules every surface keeps (no hashtag,
 791 | +    dash, emoji, hedge or AI phrasing), at most COMMENT_MAX_LINES lines and COMMENT_MAX_WORDS words, and no handle, link
 792 | +    or credit (code adds the credits)."""
 793 | +    out = []
 794 | +    for ln in lines:
 795 | +        slot, text = ln["slot"], ln.get("text") or ""
 796 | +        if slot in ("title", "caption"):
 797 | +            out += HS.lint(slot, text)
 798 | +        elif slot == "closing":
 799 | +            out += [dict(v, slot="closing") for v in HS.lint("takeaway", text)]
 800 | +            if len(text.split()) > CLOSING_MAX_WORDS:
 801 | +                out.append({"slot": "closing", "rule": "STYLE",
 802 | +                            "detail": f"closing-words: {len(text.split())} words (at most {CLOSING_MAX_WORDS})"})
 803 | +        elif slot == "comment":
 804 | +            out += [dict(v, slot="comment") for v in HS.lint("bridge", text)]   # the every-surface rules only
 805 | +            n_lines = len([x for x in text.split("\n") if x.strip()])
 806 | +            if n_lines > COMMENT_MAX_LINES:
 807 | +                out.append({"slot": "comment", "rule": "STYLE",
 808 | +                            "detail": f"comment-lines: {n_lines} lines (at most {COMMENT_MAX_LINES})"})
 809 | +            if HS.words(text) > COMMENT_MAX_WORDS:
 810 | +                out.append({"slot": "comment", "rule": "STYLE",
 811 | +                            "detail": f"comment-words: {HS.words(text)} words (at most {COMMENT_MAX_WORDS})"})
 812 | +            if re.search(r"@|https?://|www\.|\bcredits?\b", text, re.I):
 813 | +                out.append({"slot": "comment", "rule": "STYLE",
 814 | +                            "detail": "comment-credits: no handle, link or credit (code adds them)"})
 815 | +    return out
 816 | +
 817 | +
 818 | +def credits(channel, speaker, table_path=HANDLES):
 819 | +    """RULING 90: the first comment's credits: the channel's X handle and the attested speaker's, ONLY from the
 820 | +    verified table (the integrator's registry: x_handle, an empty one is none). The speaker has a handle only when the
 821 | +    attested name is itself a registry channel (no speaker-level table exists: the integrator, 22:44 ET); a name
 822 | +    without a verified handle stays UNTAGGED, and the record says so. -> {"tags", "channel", "speaker"}."""
 823 | +    try:
 824 | +        with open(table_path) as f:
 825 | +            reg = json.load(f)
 826 | +        rows = reg if isinstance(reg, list) else []
 827 | +    except (OSError, ValueError):
 828 | +        rows = []
 829 | +    def handle_of(name):
 830 | +        for r in rows:
 831 | +            names = [r.get("display_name")] + list(r.get("aliases") or [])
 832 | +            if isinstance(r, dict) and name in [x for x in names if isinstance(x, str)]:
 833 | +                h = r.get("x_handle")
 834 | +                return (h, None) if isinstance(h, str) and HANDLE_RE.match(h) else \
 835 | +                    (None, "the registry has no verified X handle for it")
 836 | +        return None, "not in the verified table" if rows else "the verified table cannot be read"
 837 | +    h, why = handle_of(channel)
 838 | +    out = {"channel": {"name": channel, "handle": h, "untagged_why": why}, "speaker": None}
 839 | +    tags = [h or channel]
 840 | +    sp = speaker if isinstance(speaker, dict) and speaker.get("measured") is True and \
 841 | +        isinstance(speaker.get("name"), str) and speaker["name"] not in ("", "unknown") else None
 842 | +    if sp is not None and sp["name"] != channel:
 843 | +        hs, why_s = handle_of(sp["name"])
 844 | +        out["speaker"] = {"name": sp["name"], "handle": hs, "untagged_why": why_s}
 845 | +        if (hs or sp["name"]) not in tags:
 846 | +            tags.append(hs or sp["name"])
 847 | +    elif sp is None:
 848 | +        out["speaker"] = {"name": None, "handle": None,
 849 | +                          "untagged_why": "no attested speaker (the speaker record names none): the channel only"}
 850 | +    out["tags"] = tags
 851 | +    return out
 852 | +
 853 | +
 854 | +def assemble(m, ctx, fields, closing):
 855 | +    """The spotlight package (ruling 90): ONE segment (label "hook"), no intro and no bridge, the closing line or none,
 856 | +    the sign-off with its one channel (package.signoff), the title, caption and comment as gated lines, the medley's
 857 | +    about-Bitcoin screen (ruling 34: the render judges with it), and the factory's runtime estimate with the closing
 858 | +    line counted."""
 859 | +    lines = ([dict(closing, slot="closing")] if closing else []) + \
 860 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption"),
 861 | +         dict(fields["comment"], slot="comment")]
 862 | +    vo = {"intro": None, "bridges": [], "bridges_after_clip": [], "closing": closing["text"] if closing else None}
 863 | +    pk = P._package([m], ctx, {"title": fields["title"], "caption": fields["caption"], "type": "moments",
 864 | +                               "angle": "", "style": "spotlight"}, "spotlight (ruling 90)", vo, lines)
 865 | +    pk["shape"] = "spotlight"
 866 | +    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}
 867 | +    pk["runtime_s_estimate"] = P.runtime([m], [vo["closing"]])
 868 | +    pk["runtime_note"] = (f"the moment {m['duration_s']:.2f} s (word timing)" +
 869 | +                          (f" + the closing line ({len(vo['closing'].split())} words at {P.R4_WPS} w/s + "
 870 | +                           f"{P.R4_PREROLL_S} s pre-roll)" if vo["closing"] else ", no closing line") +
 871 | +                          f" + tail {P.FINAL_TAIL_S} s (sign-off, credits card, outro, edges): the factory's estimate")
 872 | +    return pk
 873 | +
 874 | +
 875 | +def cheap(pk, a_by, levels, now):
 876 | +    """The free gates of a spotlight's lines -> (violations, det, dup, rt_ok, style): VO fidelity's deterministic rules,
 877 | +    DUPLICATE, the 28-50 s runtime, the house style and the recency facts the pin carries."""
 878 | +    segs_v = P.fidelity_segments(pk, a_by)
 879 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 880 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 881 | +    det = VF.check_deterministic(segs_v, lines, man, levels)
 882 | +    dup = P.duplicates(pk)
 883 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 884 | +    style = style_lint(pk["lines"])
 885 | +    v = det["violations"] + dup + style + \
 886 | +        ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail": f"{pk['runtime_s_estimate']} s outside "
 887 | +                                                                     f"{RUNTIME_S[0]:g}-{RUNTIME_S[1]:g} s"}]) + \
 888 | +        [{"slot": "-", "rule": "RECENCY", "detail": w} for w in PP.recency_problems(pk["segments"])]
 889 | +    return v, det, dup, rt_ok, style
 890 | +
 891 | +
 892 | +def _row(ok, by, replayed=False, measured=True, **extra):
 893 | +    return dict({"status": "NOT RUN" if not measured else ("PASS" if ok else "FAIL"), "by": by,
 894 | +                 "replayed": replayed if isinstance(replayed, bool) else None, "n": 1}, **extra)
 895 | +
 896 | +
 897 | +def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre, src_rec, facts, closing=None):
 898 | +    """The sealed gate inventory of a spotlight (package_pin.SPOTLIGHT_GATES, + CLOSING_GATES with a closing line):
 899 | +    package.inventory's rows that apply to one clip (its "r4" and "coherence" rows judge several clips and a medley's
 900 | +    VO: they are left out), then ruling 90-92's own rows. facts: {"never_delivered", "one_per_channel_day",
 901 | +    "window"} as the build measured them. closing: {"value", "fidelity", "context"} when a closing line ships."""
 902 | +    mid = m["moment_id"]
 903 | +    rows = P.inventory(fid, dup, rt_ok, (True, "n/a"), cx, {"hook": a_off}, {mid: exc}, {mid: truth}, False,
 904 | +                       {"measured": False}, style=style, hook=m.get("hook_onset"), stand=P.stand_alone_check([m]),
 905 | +                       visual=[m.get("visual")])
 906 | +    rows.pop("r4", None)
 907 | +    rows.pop("coherence", None)
 908 | +    v = m.get("visual") or {}
 909 | +    rows["visual"] = _row(v.get("measured") is True and not v.get("flags"), v.get("backend"), v.get("replayed"),
 910 | +                          measured=v.get("measured") is True, flags=list(v.get("flags") or []),
 911 | +                          by_rule="ruling 90: the visual check clean (no flag; ruling 70's sheet)")
 912 | +    own, hr = P.hook_own(m), m.get("hook_rating") or {}
 913 | +    rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 914 | +                            bool(hr.get("replayed", False)), measured=own is not None,
 915 | +                            rating=(own or {}).get("rating"), scroll=hr.get("scroll"), alone=hr.get("alone"),
 916 | +                            why=hr.get("why"), min=HOOK_MIN, rule="ruling 90: >= 4 on the hook's own job (ruling 61)")
 917 | +    sv = P.verdict_of(m)
 918 | +    rows["stands_alone"] = _row(sv is not None and float(sv["score"]) >= ALONE_MIN,
 919 | +                                f"the ALONE scorer ({(sv or {}).get('model')}, the render's stand_alone scorer as the "
 920 | +                                f"integrator's pin-stage service gave it, rulings 56 / 60)", False,
 921 | +                                measured=sv is not None, score=(sv or {}).get("score"), reason=(sv or {}).get("reason"),
 922 | +                                text_sha256=(sv or {}).get("text_sha256"), min=ALONE_MIN)
 923 | +    fams = [a.get("backend") for a in a_two or []]
 924 | +    rows["step_a_two_families"] = _row(len(a_two or []) == 2 and not any(CI.a_failures(a) for a in a_two),
 925 | +                                       fams, None if any(not isinstance(a.get("replayed"), bool) for a in a_two or [])
 926 | +                                       else any(a.get("replayed") for a in a_two or []),
 927 | +                                       measured=len(a_two or []) == 2,
 928 | +                                       rule="ruling 90: step A from both families as routed (package.second_screen)")
 929 | +    rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 930 | +                                    bool((src_rec.get("layout") or {}).get("replayed", False)),
 931 | +                                    measured=(src_rec.get("layout") or {}).get("measured") is True,
 932 | +                                    why=src_rec.get("why"), turns=src_rec.get("turns"), layout=src_rec.get("layout"),
 933 | +                                    rule="ruling 92: conversation, not reaction (caption turns + the layout)")
 934 | +    rows["window_12h"] = _row(not PP.window_problems(pk["segments"], facts["now"]),
 935 | +                              "code (package_pin.window_problems, ruling 76: <= 12 h on the render clock)",
 936 | +                              why=PP.window_problems(pk["segments"], facts["now"]))
 937 | +    rows["never_delivered"] = _row(facts["never_delivered"] is True,
 938 | +                                   "code (package.usable: no delivered span overlapped, not the same speech, ruling 76 b)",
 939 | +                                   measured=isinstance(facts["never_delivered"], bool))
 940 | +    rows["one_per_channel_day"] = _row(facts["one_per_channel_day"] is True,
 941 | +                                       f"code (the spotlights record: no spotlight from this channel on {facts['day']} ET)",
 942 | +                                       measured=isinstance(facts["one_per_channel_day"], bool))
 943 | +    rows["precheck"] = _row(bool((pre or {}).get("ok")), "lock_precheck (the render's own lock: rulings 17 / 68 / 72 / "
 944 | +                                                         "73 / 84)", False, measured=pre is not None and
 945 | +                            not (pre or {}).get("error"),
 946 | +                            verdicts=[s.get("verdict") for s in (pre or {}).get("segments") or []
 947 | +                                      if isinstance(s, dict)])
 948 | +    if closing is not None:
 949 | +        val, cf, cc = closing["value"], closing["fidelity"], closing["context"]
 950 | +        rows["closing_value"] = _row(val.get("ok") is True, val.get("backend"), bool(val.get("replayed", False)),
 951 | +                                     measured=val.get("measured") is True,
 952 | +                                     answers={k: val.get(k) for k in VALUE_KEYS}, why=val.get("why"),
 953 | +                                     words=val.get("words"), rule="ruling 91: all four a clear yes")
 954 | +        rows["closing_fidelity"] = _row(cf.get("ok") is True, cf.get("backend"), bool(cf.get("replayed", False)),
 955 | +                                        measured=bool(cf.get("measured")),
 956 | +                                        violations=[f"{x['slot']}: {x['rule']}" for x in cf.get("violations") or []])
 957 | +        rows["closing_context"] = _row(cc.get("ok") is True, cc.get("backends"), cc.get("replayed"),
 958 | +                                       measured=bool(cc.get("measured")),
 959 | +                                       violations=[x.get("rule") for x in cc.get("violations") or []])
 960 | +    return rows
 961 | +
 962 | +
 963 | +STAGES = ("step A", "the second recognition pass and CUTTABLE", "opens cold (G17a, the hook rules)",
 964 | +          "the hook's own job >= 4", "the visual check clean", "step A from the second family", "the ALONE scorer >= 4",
 965 | +          "ruling 92's source test", "exclusion, the pre-check and the package")
 966 | +
 967 | +
 968 | +def near(rec, k=3):
 969 | +    """The k moments that got furthest (ruling 92's 'three nearest and their ratings'): by the last stage passed, then
 970 | +    the hook's own-job rating, then the ALONE rating."""
 971 | +    rows = sorted(rec.items(), key=lambda kv: (-kv[1].get("stage", 0), -(kv[1].get("hook_own") or 0),
 972 | +                                               -(kv[1].get("alone") or 0), kv[0]))
 973 | +    return [dict(v, moment_id=mid, passed=list(STAGES[:v.get("stage", 0)])) for mid, v in rows[:k]]
 974 | +
 975 | +
 976 | +def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, work_dir=None, store=None,
 977 | +          step_a_cache=None, hook_cache=None, scorer_verdicts_path=None, visual_cache=None, layout_cache=None,
 978 | +          lock_check=None, spotlit=(), handles_path=HANDLES, wait_s=SCORER_WAIT_S, sleep=time.sleep,
 979 | +          captions_for=None, finalists=FINALISTS, attribute=None):
 980 | +    """RULINGS 90-92: the best spotlight in the pool, or none -> {"package", "pool", "moments" (each moment's furthest
 981 | +    stage and why it stopped), "finalists", "near", "why_none", ...}. The stages run cheapest first, each on what the
 982 | +    one before passed; every verdict is the medley's own and cached or recorded across builds: step A
 983 | +    (package.prescreen), L-v 2 and CUTTABLE (truth_for), G17a (hook_onset_for), the render's hook rules and the hook's
 984 | +    own-job rating (package._can_open, hook_ratings: >= HOOK_MIN), the visual check clean (visual_pin: measured, no
 985 | +    flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 986 | +    (a moment with no rating yet waits up to wait_s for the integrator's pass, polling the verdicts file), ruling 92's
 987 | +    source test; then, best first (rank_key), up to `finalists` moments: the exclusion verdict, the render's lock
 988 | +    pre-check (lock_check; no verdict stops the search, as in a medley build) and package_for(). lock_check None: no
 989 | +    pin (fail closed). spotlit: load_spotlit()'s list (None: not measured, no spotlight). attribute: the speaker
 990 | +    attribution (default speakers.attribute_package)."""
 991 | +    import lock_precheck as LP
 992 | +    import visual_pin as VP
 993 | +    t0 = time.time()
 994 | +    out = {"shape": "spotlight", "package": None, "moments": {}, "finalists": [], "near": [], "why_none": None}
 995 | +    if not work_dir:
 996 | +        out["why_none"] = "no work_dir: L-v 2's second pass cannot run (fail closed)"
 997 | +        return out
 998 | +    ms, why = pool(moments, sources, ctx, delivered, optout, spotlit, captions_for)
 999 | +    out["pool"] = {"may": len(ms), "out": why,
1000 | +                   "snapped": {m["moment_id"]: m["spotlight_snap"] for m in ms if m.get("spotlight_snap")}}
1001 | +    log(f"  SPOTLIGHT (rulings 90-92): {len(ms)} moment(s) may be one ({len(out['pool']['snapped'])} snapped outward "
1002 | +        f"to {SNAP_TO_S:g} s), {len(why)} out before any verdict")
1003 | +    if not ms:
1004 | +        out["why_none"] = "no moment in the 12 h pool may be a spotlight before any verdict (stage 1)"
1005 | +        return out
1006 | +    rec = out["moments"]
1007 | +    for m in ms:
1008 | +        rec[m["moment_id"]] = {"channel": P._name(m, ctx), "video_id": m["video_id"], "seconds": m["duration_s"],
1009 | +                               "text": (m.get("text") or "")[:200], "stage": 0}
1010 | +
1011 | +    def stop(mid, why_):
1012 | +        rec[mid]["out"] = why_
1013 | +
1014 | +    def passed(mids, k):
1015 | +        for mid in mids:
1016 | +            rec[mid]["stage"] = max(rec[mid]["stage"], k)
1017 | +    idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha()) if scorer_verdicts_path else \
1018 | +        ({}, {"read": False, "why": "no verdicts file given"})
1019 | +    out["scorer"] = srec
1020 | +    ms = [P.with_verdict(m, idx) for m in ms]
1021 | +    wv, wf = P._writers(router)
1022 | +    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache)
1023 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
1024 | +    for m in ms:
1025 | +        if m["moment_id"] not in cleared:
1026 | +            stop(m["moment_id"], "step A: " + ("; ".join(fails.get(m["moment_id"]) or []) or "no verdict (law L-m)"))
1027 | +    passed(cleared, 1)
1028 | +    tru, hk = {}, {}
1029 | +    with ThreadPoolExecutor(max_workers=8) as ex:
1030 | +        futs = {mid: ex.submit(P.truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
1031 | +        got = {mid: f.result() for mid, f in futs.items()}
1032 | +    tru.update(got)
1033 | +    cut = {}
1034 | +    for mid, m in cleared.items():
1035 | +        t = tru.get(mid) or {}
1036 | +        if t.get("ok") and (t.get("edges") or {}).get("cuttable") is True:
1037 | +            cut[mid] = m
1038 | +        else:
1039 | +            stop(mid, "L-v 2 / CUTTABLE: " + ("NOT MEASURED: " + str(t["error"]) if t.get("error") else
1040 | +                                              "the second pass disagrees" if not t.get("ok") else
1041 | +                                              "not cuttable at an edge"))
1042 | +    passed(cut, 2)
1043 | +    openers = {}
1044 | +    for mid, m in cut.items():
1045 | +        m["hook_onset"] = P.hook_onset_for(m, sources, work_dir, hk)
1046 | +        m.pop("hook_rating", None)                       # a rating is this build's own (its cache's)
1047 | +        m.pop("visual_hook_block", None)
1048 | +        if P._can_open(m):
1049 | +            openers[mid] = m
1050 | +        else:
1051 | +            stop(mid, f"it cannot open cold: hook eligibility, G17a ({(m['hook_onset'] or {}).get('why')}) or the "
1052 | +                      f"render's hook rule")
1053 | +    passed(openers, 3)
1054 | +    rated, herr = P.hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
1055 | +        ({}, None)
1056 | +    strong = {}
1057 | +    for mid, m in openers.items():
1058 | +        m["hook_rating"] = rated.get(mid) or {"rating": None, "why": f"not rated: {herr}"}
1059 | +        own = P.hook_own(m)
1060 | +        rec[mid]["hook_own"] = (own or {}).get("rating")
1061 | +        if own is not None and own["rating"] >= HOOK_MIN:
1062 | +            strong[mid] = m
1063 | +        else:
1064 | +            stop(mid, f"the hook's own job rates {(own or {}).get('rating')} (needs {HOOK_MIN}): "
1065 | +                      f"{m['hook_rating'].get('why')}")
1066 | +    passed(strong, 4)
1067 | +    vcache = VP.load_cache(visual_cache) if visual_cache else {}
1068 | +    if strong:
1069 | +        with ThreadPoolExecutor(max_workers=4) as ex:
1070 | +            vis = list(ex.map(lambda m_: VP.visual_for(router, m_, work_dir, vcache), list(strong.values())))
1071 | +        for m, v in zip(list(strong.values()), vis):
1072 | +            m["visual"] = v
1073 | +        if visual_cache:
1074 | +            VP.save_cache(visual_cache, vcache)
1075 | +    clean = {}
1076 | +    for mid, m in strong.items():
1077 | +        v = m.get("visual") or {}
1078 | +        if v.get("measured") is True and not v.get("flags") and not VP.hook_block(v):
1079 | +            clean[mid] = m
1080 | +        else:
1081 | +            stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
1082 | +                                              f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
1083 | +    passed(clean, 5)
1084 | +    two, off_fail = P.second_screen(router, clean, a_by, sources, ctx, log=log, cache=step_a_cache) if clean else \
1085 | +        ({}, {})
1086 | +    both = {}
1087 | +    for mid, m in clean.items():
1088 | +        if mid in two:
1089 | +            both[mid] = m
1090 | +        else:
1091 | +            stop(mid, "step A from the second family: " + "; ".join(off_fail.get(mid) or ["no verdict (law L-m)"]))
1092 | +    passed(both, 6)
1093 | +    waited = 0.0
1094 | +    if both and scorer_verdicts_path and wait_s > 0 and \
1095 | +            not any((alone_score(m) or 0.0) >= ALONE_MIN for m in both.values()) and \
1096 | +            any(alone_score(m) is None for m in both.values()):
1097 | +        log(f"  SPOTLIGHT: {sum(alone_score(m) is None for m in both.values())} moment(s) wait for the ALONE scorer "
1098 | +            f"(the integrator's pass; up to {wait_s:.0f} s)")
1099 | +        t_w = time.time()
1100 | +        for _ in range(max(1, int(wait_s // SCORER_POLL_S))):      # a bounded number of polls
1101 | +            sleep(SCORER_POLL_S)
1102 | +            idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha())
1103 | +            both = {mid: P.with_verdict(m, idx) for mid, m in both.items()}
1104 | +            if all(alone_score(m) is not None for m in both.values()):
1105 | +                break
1106 | +        waited = time.time() - t_w
1107 | +        out["scorer"] = srec
1108 | +    out["scorer_waited_s"] = round(waited, 1)
1109 | +    fine = {}
1110 | +    for mid, m in both.items():
1111 | +        sc = alone_score(m)
1112 | +        rec[mid]["alone"] = sc
1113 | +        if sc is not None and sc >= ALONE_MIN:
1114 | +            fine[mid] = m
1115 | +        else:
1116 | +            stop(mid, f"the ALONE scorer: {sc if sc is not None else 'no rating yet'} (needs {ALONE_MIN:g})" +
1117 | +                 (f": {(P.verdict_of(m) or {}).get('reason')}" if sc is not None else
1118 | +                  " (asked with the build's scorer candidates)"))
1119 | +    passed(fine, 7)
1120 | +    ok_src = []
1121 | +    for mid, m in fine.items():
1122 | +        turns = episode_turns(m["video_id"], captions_for)
1123 | +        lay = layout_for(router, m, m.get("visual"), layout_cache)
1124 | +        ok, w = source_test(turns, lay)
1125 | +        m["spotlight_source"] = {"ok": ok, "why": w, "turns": turns, "layout": lay}
1126 | +        rec[mid]["source"] = w
1127 | +        if ok:
1128 | +            ok_src.append(m)
1129 | +        else:
1130 | +            stop(mid, f"ruling 92: {w}")
1131 | +    passed([m["moment_id"] for m in ok_src], 8)
1132 | +    ranked = sorted(ok_src, key=rank_key)
1133 | +    out["finalists"] = [m["moment_id"] for m in ranked]
1134 | +    log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
1135 | +        f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
1136 | +        f"{ALONE_MIN:g}, {len(ranked)} from a conversation ({time.time() - t0:.0f} s)")
1137 | +    exc_cache = {}
1138 | +    for m in ranked[:finalists]:
1139 | +        mid = m["moment_id"]
1140 | +        exc = P.exclusion_for(router, m, sources, exc_cache)
1141 | +        if exc.get("verdict") != "keep":
1142 | +            stop(mid, f"the exclusion verdict: {exc.get('verdict')} ({exc.get('why')})")
1143 | +            continue
1144 | +        if lock_check is None:
1145 | +            stop(mid, "no lock pre-check was given: never a pin (fail closed)")
1146 | +            continue
1147 | +        try:
1148 | +            pre = lock_check([m])
1149 | +        except Exception as e:                           # noqa: BLE001  no verdict, never a pass
1150 | +            pre = LP.failed(e)
1151 | +        if not pre.get("ok"):
1152 | +            stop(mid, f"rulings 68 / 72: the render's lock: {pre.get('error') or 'the clip holds'}"[:400])
1153 | +            if pre.get("error") or not pre.get("segments"):
1154 | +                out["lock_stop"] = rec[mid]["out"]       # no verdict: the search stops (as a medley build)
1155 | +                break
1156 | +            continue
1157 | +        facts = {"now": ctx.now, "day": et_day(ctx.now),                 # measured again right before the package:
1158 | +                 "never_delivered": bool(P.usable([m], ctx, delivered, optout, seg_max=SPOT_S[1])[0]),   # no
1159 | +                 "one_per_channel_day": spotlit is not None and m["channel_id"] not in    # delivered span or speech
1160 | +                 {r["channel_id"] for r in spotlit or () if r.get("day_et") == et_day(ctx.now)}}
1161 | +        pk, why_p = package_for(router, m, ctx, sources, two[mid], tru[mid], exc, pre, facts, log=log,
1162 | +                                handles_path=handles_path, attribute=attribute)
1163 | +        if pk is not None:
1164 | +            pk["seconds"] = round(time.time() - t0, 1)
1165 | +            out["package"] = pk
1166 | +            rec[mid]["out"] = "PACKAGE"
1167 | +            break
1168 | +        stop(mid, why_p)
1169 | +    if out["package"] is None:
1170 | +        out["near"] = near(rec)
1171 | +        out["why_none"] = out.get("lock_stop") or ("no moment passes rulings 90-92 now" if not ranked else
1172 | +                                                   f"no finalist gave a package: " +
1173 | +                                                   "; ".join(f"{mid}: {rec[mid].get('out')}"
1174 | +                                                             for mid in out["finalists"][:finalists]))[:600]
1175 | +    return out
1176 | +
1177 | +
1178 | +def package_for(router, m, ctx, sources, a_two, truth, exc, pre, facts, log=print, handles_path=HANDLES,
1179 | +                attribute=None):
1180 | +    """The writes, the gates and the package for ONE moment -> (package, None) or (None, why).
1181 | +    - ONE write (angle_write): title, caption, comment and a candidate closing line. A title, caption or comment that
1182 | +      fails a free gate gets ONE more write of those lines (P._redo); the closing line is never written again
1183 | +      (ruling 91: one write, one verdict).
1184 | +    - Every verdict comes off every writer's vendor and family (law L-s); step A's verdict off them must exist (L-x).
1185 | +    - The lines without the closing: VO fidelity's verdict (vo_fidelity_verdict) and, when no closing ships, context
1186 | +      integrity (context_b / context_c).
1187 | +    - The closing line ships only when ALL hold: it passes the free gates with the package (house style, <= 12 words,
1188 | +      DUPLICATE, the runtime still 28-50 s), ruling 91's value verdict is a clear yes on all four, its own fidelity
1189 | +      verdict passes, and context integrity passes with it spoken after the clip. Otherwise no line (the default).
1190 | +    - Then the speaker record (sealed), the credits and the first comment (code), the lock's adopted text (LP.apply),
1191 | +      and the inventory, every required row exactly PASS (package_pin.gate_problems)."""
1192 | +    import lock_precheck as LP
1193 | +    import providers as Pr
1194 | +    import speakers as SP
1195 | +    from select_by_id import UNTRUSTED
1196 | +    mid = m["moment_id"]
1197 | +    show = P._name(m, ctx)
1198 | +    levels = P.current_levels(sources.values(), ctx)
1199 | +    both_verify = dict(a_two[0], speaker_verified=all((a or {}).get("speaker_verified") for a in a_two))
1200 | +    clip = P._lineup_block([m], ctx, {mid: both_verify}).replace("HOOK id=", "CLIP id=", 1)   # a name only when
1201 | +    #   BOTH step-A verdicts verify the speaker: the gates read the one off the writer, unknown until it answers
1202 | +    replies, notes, fields, closing0, extra = [], [], None, None, ""
1203 | +    for w in range(WRITES):
1204 | +        r = None
1205 | +        prompt = WRITE_SPOT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), clip=clip,
1206 | +                                   cmax=CLOSING_MAX_WORDS, said=CLOSING_SAID, style=HS.PROMPT_RULES,
1207 | +                                   extra=(extra + "\n") if extra else "")
1208 | +        try:
1209 | +            r = router.call("angle_write", prompt, 1500, 7 + w, deadline_s=P.WRITER_DEADLINE_S)
1210 | +            got = parse_write(r.text, mid, closing_allowed=(w == 0))
1211 | +        except (Pr.ProviderError, Pr.SpendLimit) as e:
1212 | +            return None, f"no writer answered ({type(e).__name__}: {str(e)[:200]})"
1213 | +        except (ValueError, TypeError, KeyError) as e:
1214 | +            if r is not None:
1215 | +                router.reject(r)
1216 | +            notes.append({"write": w + 1, "error": f"{type(e).__name__}: {str(e)[:200]}"})
1217 | +            extra = f"Your previous reply was REJECTED as out of contract ({str(e)[:200]}). Return the JSON exactly."
1218 | +            continue
1219 | +        replies.append(r)
1220 | +        if w == 0:
1221 | +            closing0 = got["closing"]
1222 | +        fields = {k: got[k] for k in ("title", "caption", "comment")}
1223 | +        wv_, wf_ = {x.vendor for x in replies}, {x.family for x in replies}
1224 | +        a_off = next((a for a in a_two for b in [router.backends.get(a.get("backend"))]
1225 | +                      if b is not None and b.vendor not in wv_ and b.family not in wf_), None)
1226 | +        if a_off is None:
1227 | +            return None, (f"no step-A verdict off the writers {sorted(wv_)} / {sorted(wf_)} (L-x): "
1228 | +                          f"{[a.get('backend') for a in a_two]}")
1229 | +        pk0 = assemble(m, ctx, fields, None)
1230 | +        v0 = cheap(pk0, {mid: a_off}, levels, ctx.now)[0]
1231 | +        notes.append({"write": w + 1, "backend": r.backend, "fields": fields, "closing": closing0 if w == 0 else None,
1232 | +                      "cheap": v0})
1233 | +        if not v0:
1234 | +            break
1235 | +        fields, extra = None, P._redo(v0)
1236 | +    if fields is None:
1237 | +        return None, "the title, caption or comment failed the free gates in both writes: " + \
1238 | +            "; ".join(f"{v['slot']}: {v['rule']}" for v in (notes[-1].get("cheap") or []))[:400] if notes else \
1239 | +            "no write in contract"
1240 | +    writers_v, writers_f = {x.vendor for x in replies}, {x.family for x in replies}
1241 | +    a_lab = {"hook": a_off}
1242 | +    segs_v = P.fidelity_segments(pk0, {mid: a_off})
1243 | +    man = {"channels": [show], "date": ctx.now.strftime("%Y-%m-%d")}
1244 | +    line = lambda pk_, slots: [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk_["lines"]
1245 | +                               if x["slot"] in slots]
1246 | +    spoken_after = lambda pk_: dict(pk_, vo=dict(pk_["vo"], intro=pk_["vo"]["closing"], bridges=[],
1247 | +                                                 bridges_after_clip=[]))   # CI reads the line after the clip there
1248 | +    closing_rec, cl_why, pk1 = None, "no candidate (the writer gave none)", None
1249 | +    with ThreadPoolExecutor(max_workers=6) as ex:
1250 | +        f_fid = ex.submit(VF.check, router, segs_v, line(pk0, ("title", "caption", "comment")), writers_v, 7, man,
1251 | +                          levels, writers_f)
1252 | +        if closing0 is not None:
1253 | +            pk1 = assemble(m, ctx, fields, closing0)
1254 | +            v1 = cheap(pk1, {mid: a_off}, levels, ctx.now)[0]
1255 | +            if v1:
1256 | +                cl_why, pk1 = "the free gates: " + "; ".join(f"{v['slot']}: {v['rule']}: {v['detail']}"
1257 | +                                                             for v in v1)[:300], None
1258 | +            else:
1259 | +                f_val = ex.submit(value_verdict, router, m, closing0["text"], show, writers_v, writers_f)
1260 | +                f_cf = ex.submit(VF.check, router, segs_v, line(pk1, ("closing",)), writers_v, 7, man, levels,
1261 | +                                 writers_f)
1262 | +                f_cc = ex.submit(CI.check_contexts, router, spoken_after(pk1),
1263 | +                                 CI.contexts_from_sources(pk1, sources, ctx.now), writers_v, 7, a_lab, writers_f, True)
1264 | +                val, cf, cc = f_val.result(), f_cf.result(), f_cc.result()
1265 | +                closing_rec = {"value": val, "fidelity": cf, "context": cc}
1266 | +                if not (val.get("ok") and cf.get("ok") and cf.get("measured") and cc.get("ok") and cc.get("measured")):
1267 | +                    cl_why = ("ruling 91's value verdict: " + str(val.get("why")) if not val.get("ok") else
1268 | +                              "its fidelity verdict: " + "; ".join(f"{x['rule']}" for x in cf.get("violations") or [])
1269 | +                              if not (cf.get("ok") and cf.get("measured")) else
1270 | +                              "context integrity with it: " + "; ".join(str(x.get("rule"))
1271 | +                                                                         for x in cc.get("violations") or []))[:300]
1272 | +                    pk1 = None
1273 | +        fid = f_fid.result()
1274 | +    if not (fid.get("ok") and fid.get("measured")):
1275 | +        return None, "VO fidelity's verdict on the title, caption or comment: " + \
1276 | +            "; ".join(f"{x['slot']}: {x['rule']}" for x in fid.get("violations") or [])[:300]
1277 | +    if pk1 is not None:
1278 | +        pk, cx = pk1, closing_rec["context"]
1279 | +    else:
1280 | +        pk = pk0
1281 | +        cx = CI.check_contexts(router, pk0, CI.contexts_from_sources(pk0, sources, ctx.now), writers_v, 7, a_lab,
1282 | +                               writers_f, True)
1283 | +        closing_rec = None
1284 | +        if not (cx.get("ok") and cx.get("measured")):
1285 | +            return None, "context integrity: " + "; ".join(str(x.get("rule")) for x in cx.get("violations") or [])[:300]
1286 | +    v_all, det, dup, rt_ok, style = cheap(pk, {mid: a_off}, levels, ctx.now)
1287 | +    (attribute or SP.attribute_package)(router, pk, sources, log=log)      # the speaker record, sealed (item 3)
1288 | +    cr = credits(show, pk["segments"][0].get("speaker"), handles_path)
1289 | +    pk["comment_credits"] = cr
1290 | +    pk["first_comment"] = PP.first_comment_text(fields["comment"]["text"], cr["tags"])
1291 | +    src_rec = m.get("spotlight_source") or {"ok": False, "why": "not measured"}
1292 | +    pk["spotlight"] = {"moment_id": mid, "snap": m.get("spotlight_snap"), "hook_own": P.hook_own(m),
1293 | +                       "alone": alone_score(m), "source": {k: src_rec.get(k) for k in ("ok", "why")},
1294 | +                       "closing": {"candidate": (closing0 or {}).get("text"), "kept": pk1 is not None,
1295 | +                                   "why_not": None if pk1 is not None else cl_why},
1296 | +                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes]}
1297 | +    pk["models"] = {"writer": [x.backend for x in replies], "fidelity_verdict": fid.get("backend"),
1298 | +                    "context": cx.get("backends"), "value": ((closing_rec or {}).get("value") or {}).get("backend"),
1299 | +                    "layout": (src_rec.get("layout") or {}).get("backend")}
1300 | +    pk["checks"] = {"fidelity": fid, "context": cx, "closing": closing_rec}
1301 | +    pk["gates"] = inventory(pk, m, dict(fid, deterministic=det), dup, rt_ok, style, cx, a_off, a_two, exc, truth,
1302 | +                            pre, src_rec, facts, closing=closing_rec if pk1 is not None else None)
1303 | +    #   (the deterministic row covers every line that ships, the closing line included: cheap() on the final package)
1304 | +    try:
1305 | +        pk = LP.apply(pk, pre)
1306 | +    except Exception as e:                               # noqa: BLE001  never a crash, never a pin
1307 | +        return None, f"rulings 68 / 72: {e}"[:400]
1308 | +    problems = PP.gate_problems(pk["gates"], PP.required_gates(pk)) + \
1309 | +        [f"{x}: the gated line differs from the one shipped" for x in PP.line_problems(pk)] + \
1310 | +        PP.spotlight_problems(pk) + [f"{v['slot']}: {v['rule']}" for v in v_all]
1311 | +    if problems:
1312 | +        return None, f"a required gate is not exactly PASS: {problems}"[:600]
1313 | +    log(f"  SPOTLIGHT PACKAGE: {mid} ({show}, {m['duration_s']} s" +
1314 | +        (f", snapped from {m['spotlight_snap']['from']}" if m.get("spotlight_snap") else "") +
1315 | +        f"), closing line: {pk['vo']['closing']!r}, runtime {pk['runtime_s_estimate']} s")
1316 | +    return pk, None
1317 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
1318 | index 1982ff9..1a1371b 100644
1319 | --- a/tests/package/proof_ledger.py
1320 | +++ b/tests/package/proof_ledger.py
1321 | @@ -29,6 +29,12 @@ clips-alone verdict in that earlier build's record (its tried[N]; default the fi
1322 |  stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
1323 |  recordings and only what is missing is paid for; never re-lined, swapped or a new angle.
1324 |  
1325 | +RULING 90 (22:40 ET Nov 13; LAW since 22:52, with 91 and 92), THE SPOTLIGHT: after the medley search, every build
1326 | +tries one spotlight (pipeline/spotlight.py): built when the search ends with no medley, or for a moment no medley used
1327 | +(a sealed medley's clips are out of it). Its free pool goes to the clip scorer with the medley's own candidates at the
1328 | +build's start (package.build's scorer_extra). A sealed spotlight is SPOTLIGHT_PIN.json in the build's directory and a
1329 | +row of tests/package/proof/SPOTLIGHTS.json (one per channel per ET day).
1330 | +
1331 |  Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
1332 |                                               [--from-candidate BUILD_DIR[:N]]
1333 |    tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
1334 | @@ -58,9 +64,11 @@ import proof_ly as PL  # noqa: E402
1335 |  import proof_saved_runs as PS  # noqa: E402
1336 |  import providers as P  # noqa: E402
1337 |  import speakers as SP  # noqa: E402
1338 | +import spotlight as SPOT  # noqa: E402
1339 |  import lock_precheck as LP  # noqa: E402
1340 |  
1341 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
1342 | +SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
1343 |  
1344 |  
1345 |  def delivered_pins(paths):
1346 | @@ -187,7 +195,9 @@ def main(argv=None):
1347 |          f"starts at ${PL.LY_STOP_USD:.2f})")
1348 |      own, used = PL.meter(router), PL.reply_meter(router)
1349 |      t0 = time.time()
1350 | -    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say,
1351 | +    spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
1352 | +    sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
1353 | +    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
1354 |                work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
1355 |                spend=lambda: (own["est"], own["best"]),
1356 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
1357 | @@ -235,6 +245,18 @@ def main(argv=None):
1358 |              res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
1359 |                         why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
1360 |          res["candidate_tries"] = tries
1361 | +    # RULING 90: the spotlight after the medley search (the medley is always tried first): built when the search
1362 | +    # ends with no medley, or for a moment no medley used (a sealed medley's clips are out of it)
1363 | +    sp_delivered = delivered + ([{"video_id": sg["video_id"], "start": float(sg["start"]), "end": float(sg["end"]),
1364 | +                                  "pin": "this build's medley", "text": sg["text"]}
1365 | +                                 for sg in res["package"]["segments"]] if res.get("package") else [])
1366 | +    sp = SPOT.build(router, moments, sources, ctx, delivered=sp_delivered, optout=kw["optout"], log=say,
1367 | +                    work_dir=a.work_dir, store=kw["store"], step_a_cache=kw["step_a_cache"], hook_cache=kw["hook_cache"],
1368 | +                    scorer_verdicts_path=PK.SCORER_VERDICTS, visual_cache=kw["visual_cache"],
1369 | +                    layout_cache=os.path.join(HERE, "proof", "LAYOUT_CACHE.json"), lock_check=kw["lock_check"],
1370 | +                    spotlit=spotlit)
1371 | +    res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
1372 | +                                                "scorer_waited_s", "lock_stop", "scorer")}
1373 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
1374 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
1375 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
1376 | @@ -263,6 +285,37 @@ def main(argv=None):
1377 |              say(f"PIN REFUSED: {e}")
1378 |      else:
1379 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
1380 | +    if sp.get("package"):                                # RULING 90: the spotlight pin, its own file
1381 | +        try:
1382 | +            lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
1383 | +            again = SPOT.load_spotlit(SPOTLIGHTS)        # one per channel per day, read again at the pin
1384 | +            if again is None or any(r["channel_id"] == sp["package"]["segments"][0]["channel_id"] and
1385 | +                                    r.get("day_et") == SPOT.et_day(now) for r in again):
1386 | +                lock.append("ruling 90: this channel already has a spotlight today, or the record cannot be read")
1387 | +            if lock:
1388 | +                raise package_pin.PinRefused("; ".join(lock))
1389 | +            path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
1390 | +                                              name="SPOTLIGHT_PIN.json")
1391 | +            res["spotlight_pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1392 | +                                    "package_sha256": pin["moments_package"]["package_sha256"]}
1393 | +            import shutil                                # ruling 70: the segment's sheet beside the pin
1394 | +            sh = (pin["segments"][0].get("visual") or {}).get("sheet") or {}
1395 | +            if sh.get("name") and os.path.exists(os.path.join(a.work_dir, "visual", sh["name"])):
1396 | +                shutil.copyfile(os.path.join(a.work_dir, "visual", sh["name"]), os.path.join(out_dir, sh["name"]))
1397 | +            sg = sp["package"]["segments"][0]
1398 | +            SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
1399 | +                                             "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
1400 | +                                             "package_sha256": pin["moments_package"]["package_sha256"],
1401 | +                                             "at": now.isoformat(timespec="seconds"), "build": name})
1402 | +            say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
1403 | +                f"{sp['package']['vo']['closing']!r})")
1404 | +        except (package_pin.PinRefused, ValueError, OSError) as e:
1405 | +            res["spotlight_pin_refused"] = f"{type(e).__name__}: {e}"
1406 | +            say(f"SPOTLIGHT PIN REFUSED: {e}")
1407 | +    else:
1408 | +        say(f"no spotlight ({sp.get('why_none')})" + "".join(
1409 | +            f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
1410 | +            f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
1411 |      hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries;
1412 |      #   `moments` is the adapter's pool from LB.build_inputs, BEFORE usable() filters it (audit 1810 C3)
1413 |      res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
1414 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
1415 | index fcbcaa6..299098c 100644
1416 | --- a/tests/package/test_lock_precheck.py
1417 | +++ b/tests/package/test_lock_precheck.py
1418 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
1419 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
1420 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
1421 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
1422 | -                         "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")             # ruling 84's decoder
1423 | +                         "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")             # ruling 90's decoder
1424 |  
1425 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
1426 |          segs = LP.segments_of([HOOK, CLIP])
1427 | @@ -180,7 +180,7 @@ class TestCheck(Dirs):
1428 |              self.put(s, entry(s))
1429 |          rep, sleeps = self.run_check([HOOK, CLIP])
1430 |          self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
1431 | -        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")
1432 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")
1433 |  
1434 |      def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
1435 |          segs = LP.segments_of([HOOK, CLIP])
1436 | @@ -203,16 +203,16 @@ class TestCheck(Dirs):
1437 |          self.assertEqual(sleeps, [10.0, 10.0, 10.0])
1438 |  
1439 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
1440 | -        """Audit 1845 C2 (glm): ruling 73 changed the decoder, and ruling 84 changed it again; a file named for an
1441 | -        older decoder (25cd6f15e6c9, 8a101f222598) is never opened, even with a matching, newer entry under the current
1442 | -        rules."""
1443 | +        """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
1444 | +        integrator's spotlight branches) again; a file named for an older decoder (25cd6f15e6c9, 8a101f222598,
1445 | +        962353613cb0) is never opened, even with a matching, newer entry under the current rules."""
1446 |          s = LP.segments_of([HOOK])[0]
1447 | -        for dec in ("25cd6f15e6c9", "8a101f222598"):
1448 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0"):
1449 |              old = LP.result_file(s, self.res, decoder=dec)
1450 |              with open(old, "w") as f:
1451 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
1452 |              self.assertTrue(old.endswith(f".{dec}.json"))
1453 | -        self.assertIsNone(LP.answer(s, self.res))                                         # only 962353613cb0's file
1454 | +        self.assertIsNone(LP.answer(s, self.res))                                         # only c705b20ed800's file
1455 |  
1456 |      def test_ruling_73_holds_a_span_the_render_cannot_cut(self):
1457 |          segs = LP.segments_of([HOOK, CLIP])
1458 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
1459 | new file mode 100644
1460 | index 0000000..41ad179
1461 | --- /dev/null
1462 | +++ b/tests/package/test_spotlight.py
1463 | @@ -0,0 +1,577 @@
1464 | +#!/usr/bin/env python3
1465 | +"""RULINGS 90-92 (orchestrator 22:40 / 22:52 ET Nov 13): the SPOTLIGHT pin kind, offline.
1466 | +
1467 | +- The pin contract agreed with the integrator (22:44 ET): shape "spotlight", one hook segment, edl_vo with "closing",
1468 | +  the whole first comment, the gate rows; the seal covers the closing line, the kind and the comment, and every pin
1469 | +  sealed before it recomputes (pin_seal, and the integrator's exact call).
1470 | +- The snap (ruling 32's, outward to the speaker's whole thought), ruling 92's source test, the writer's and the
1471 | +  value verdict's contracts, PBX's comment format and the verified handles, the pool's free rules.
1472 | +- package_for: the closing line ships only with every gate; any failure leaves no line (ruling 91).
1473 | +- build(): the stages in order, the ALONE scorer's wait, the nearest moments when none qualifies.
1474 | +"""
1475 | +import copy
1476 | +import glob
1477 | +import json
1478 | +import os
1479 | +import shutil
1480 | +import sys
1481 | +import tempfile
1482 | +import unittest
1483 | +from datetime import timedelta
1484 | +from unittest import mock
1485 | +
1486 | +HERE = os.path.dirname(os.path.abspath(__file__))
1487 | +REPO = os.path.dirname(os.path.dirname(HERE))
1488 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1489 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1490 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1491 | +sys.path.insert(0, HERE)
1492 | +import eligibility as E  # noqa: E402
1493 | +import moments as M  # noqa: E402
1494 | +import package as PK  # noqa: E402
1495 | +import package_pin as PP  # noqa: E402
1496 | +import providers as P  # noqa: E402
1497 | +import spotlight as SPOT  # noqa: E402
1498 | +import visual_pin as VP  # noqa: E402
1499 | +from test_eligibility import NOW, REG, source  # noqa: E402
1500 | +from test_gates import Canned, a_item  # noqa: E402
1501 | +from test_medley import sv  # noqa: E402
1502 | +from test_moments import pm  # noqa: E402
1503 | +
1504 | +TEXT = ("Bitcoin is the one money nobody can print more of, and that is exactly why people keep holding it through "
1505 | +        "every single cycle we have seen so far, from the very first one to the one we are in right now today.")
1506 | +GOOD = {"title": {"text": "The money nobody can print", "cites": []},
1507 | +        "caption": {"text": "a clear case for a fixed supply.", "cites": []},
1508 | +        "comment": {"text": "This one stuck with me.\nWorth the full listen.", "cites": []},
1509 | +        "closing": {"text": "Scarcity only matters when nobody can quietly change it.", "cites": []}}
1510 | +
1511 | +
1512 | +class B:
1513 | +    def __init__(self, vendor, family):
1514 | +        self.vendor, self.family = vendor, family
1515 | +
1516 | +
1517 | +class Router(Canned):
1518 | +    """Canned answers by role, with the back-ends the step-A verdicts name."""
1519 | +    backends = {"fake:xai": B("xai", "grok"), "fake:heimdall": B("heimdall", "deepseek")}
1520 | +
1521 | +    def __init__(self, **answers):
1522 | +        super().__init__(**answers)
1523 | +        self.down = set()
1524 | +
1525 | +
1526 | +def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
1527 | +    m = pm(mid, channel, dur)
1528 | +    m.update(text=text, channel_name=channel, published_at=(NOW - timedelta(hours=2)).isoformat(),
1529 | +             hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
1530 | +             hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
1531 | +                          "backend": "fake:xai", "replayed": False},
1532 | +             visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
1533 | +                     "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
1534 | +                                      "finding": "none"}, "on_screen_text": [],
1535 | +                     "lower_third": {"name": None, "text": None}},
1536 | +             scorer_verdict=sv(text, 4.0),
1537 | +             spotlight_source={"ok": True, "why": "layout 'conversation'", "turns": {"measured": False},
1538 | +                               "layout": {"measured": True, "layout": "conversation", "backend": "fake:vis",
1539 | +                                          "replayed": False}})
1540 | +    m.update(kw)
1541 | +    return m
1542 | +
1543 | +
1544 | +def two():
1545 | +    return [dict(a_item("hook"), backend="fake:xai", replayed=False),
1546 | +            dict(a_item("hook"), backend="fake:heimdall", replayed=False)]
1547 | +
1548 | +
1549 | +def pre_of(m):
1550 | +    return {"ok": True, "request_id": "r1", "segments": [{"video_id": m["video_id"], "start": round(m["start"], 3),
1551 | +                                                          "end": round(m["end"], 3), "approved_text": m["text"],
1552 | +                                                          "role": "hook", "verdict": "pass", "outcome": "pass"}]}
1553 | +
1554 | +
1555 | +FID_OK = {"ok": True, "measured": True, "verdict": {"ok": True, "violations": []}, "violations": [],
1556 | +          "backend": "fake:verdict", "replayed": False, "deterministic": {"ok": True, "violations": []}}
1557 | +CX_OK = {"ok": True, "measured": True, "violations": [], "backends": {"B": "fake:b", "C": "fake:c"}, "replayed": False}
1558 | +VALUE_YES = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "it names what is at stake"}
1559 | +
1560 | +
1561 | +def unknown_speaker(router, pk, sources, log=print):
1562 | +    for s in pk["segments"]:
1563 | +        s["speaker"] = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test", "people": [],
1564 | +                        "measured": True}
1565 | +    return pk
1566 | +
1567 | +
1568 | +def package(m=None, value=VALUE_YES, write=GOOD, cx=CX_OK, cx_base=CX_OK, fid=FID_OK, cfid=FID_OK, writes=None):
1569 | +    """package_for on one moment with canned verdicts -> (pk, why, router, the context checks asked)."""
1570 | +    m = m or moment()
1571 | +    ctx = E.Context(NOW, REG)
1572 | +    router = Router(angle_write=writes or [write], coherence_verdict=[value])
1573 | +    asked = []
1574 | +
1575 | +    def ci(router_, pk, contexts, *a, **k):
1576 | +        asked.append(pk["vo"].get("intro"))
1577 | +        return copy.deepcopy(cx if pk["vo"].get("intro") else cx_base)
1578 | +    fids = []
1579 | +
1580 | +    def vf(router_, segs, lines, *a, **k):
1581 | +        fids.append([x["slot"] for x in lines])
1582 | +        return copy.deepcopy(cfid if [x["slot"] for x in lines] == ["closing"] else fid)
1583 | +    facts = {"now": NOW, "day": SPOT.et_day(NOW), "never_delivered": True, "one_per_channel_day": True}
1584 | +    with mock.patch.object(SPOT.VF, "check", vf), mock.patch.object(SPOT.CI, "check_contexts", ci), \
1585 | +            mock.patch.object(SPOT.CI, "contexts_from_sources", lambda pk, s, n: {}), \
1586 | +            mock.patch.object(SPOT.P, "current_levels", lambda *a, **k: []):
1587 | +        pk, why = SPOT.package_for(router, m, ctx, {}, two(), {"ok": True, "model": "fake:stt", "replayed": False,
1588 | +                                                               "edges": {"cuttable": True}},
1589 | +                                   {"verdict": "keep", "backend": "fake:excl", "replayed": False, "measured": True},
1590 | +                                   pre_of(m), facts, log=lambda *a: None, handles_path=HANDLES, attribute=unknown_speaker)
1591 | +    return pk, why, router, asked, fids
1592 | +
1593 | +
1594 | +TMP = tempfile.mkdtemp(prefix="test_spotlight_")
1595 | +HANDLES = os.path.join(TMP, "channels.json")              # a verified table of the integrator's shape (x_handle)
1596 | +
1597 | +
1598 | +def setUpModule():
1599 | +    with open(HANDLES, "w") as f:
1600 | +        json.dump([{"display_name": "DataDash", "x_handle": "@Nicholas_Merten", "aliases": []},
1601 | +                   {"display_name": "Natalie Brunell", "x_handle": "@natbrunell", "aliases": ["Natalie"]},
1602 | +                   {"display_name": "Simply Bitcoin", "x_handle": "", "aliases": []}], f)
1603 | +
1604 | +
1605 | +def tearDownModule():
1606 | +    shutil.rmtree(TMP, ignore_errors=True)
1607 | +
1608 | +
1609 | +class TestPinContract(unittest.TestCase):
1610 | +    def test_required_rows_with_and_without_a_closing_line(self):
1611 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": None}}), PP.SPOTLIGHT_GATES)
1612 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": "A line."}}),
1613 | +                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)
1614 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "edl_vo": {"closing": "A line."}}),   # a pin's
1615 | +                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)                                   # moments_package
1616 | +        self.assertEqual(PP.required_gates({"shape": "medley"}), PP.REQUIRED_GATES + PP.MEDLEY_GATES)
1617 | +        for g in ("spotlight_source", "hook_own", "stands_alone", "step_a_two_families", "visual", "window_12h",
1618 | +                  "never_delivered", "one_per_channel_day", "precheck"):          # the keys agreed at 22:44 ET
1619 | +            self.assertIn(g, PP.SPOTLIGHT_GATES)
1620 | +        self.assertEqual(PP.CLOSING_GATES, ("closing_value", "closing_fidelity", "closing_context"))
1621 | +
1622 | +    def test_every_pin_sealed_before_recomputes(self):
1623 | +        pins = [p for p in glob.glob(os.path.join(HERE, "proof", "*", "*.json"))
1624 | +                if os.path.basename(p).startswith("MOMENTS_PIN")]
1625 | +        self.assertGreater(len(pins), 5)
1626 | +        for p in pins:
1627 | +            with open(p) as f:
1628 | +                pin = json.load(f)
1629 | +            mp = pin.get("moments_package")
1630 | +            if not mp or "package_sha256" not in mp:
1631 | +                continue
1632 | +            self.assertEqual(PP.pin_seal(pin), mp["package_sha256"], p)
1633 | +            self.assertEqual(PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],   # the
1634 | +                                     mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"], p)
1635 | +
1636 | +    def test_a_spotlight_pin_seals_its_closing_kind_and_comment(self):
1637 | +        pk, why, *_ = package()
1638 | +        self.assertIsNone(why)
1639 | +        pin = PP.to_pin(pk, "t")
1640 | +        mp = pin["moments_package"]
1641 | +        self.assertEqual(mp["shape"], "spotlight")
1642 | +        self.assertEqual(len(pin["segments"]), 1)
1643 | +        self.assertEqual(pin["segments"][0]["role"], "hook")
1644 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [], "closing": GOOD["closing"]["text"]})
1645 | +        self.assertEqual(mp["vo_jobs"], {"closing": "closing"})
1646 | +        self.assertEqual(mp["first_comment"], pk["first_comment"])
1647 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
1648 | +        integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
1649 | +                             mp["gates"], mp.get("btc_screen"),
1650 | +                             **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
1651 | +                                if mp.get("shape") == "spotlight" else {}))       # their exact call (23:1x ET)
1652 | +        self.assertEqual(integrator, mp["package_sha256"])
1653 | +        medley = {"segments": [], "edl_vo": {"intro": None, "bridges": [], "closing": None}, "signoff": "S"}
1654 | +        self.assertEqual(PP.seal([], medley["edl_vo"], "S", "t", "c", {}),          # a medley's body never holds the
1655 | +                         PP.seal([], {"intro": None, "bridges": []}, "S", "t", "c", {}))   # closing (C1, glm)
1656 | +        for change in (lambda p: p["moments_package"]["edl_vo"].update(closing="Another line."),
1657 | +                       lambda p: p["moments_package"].update(first_comment="x"),
1658 | +                       lambda p: p["moments_package"].update(shape="medley")):
1659 | +            p2 = copy.deepcopy(pin)
1660 | +            change(p2)
1661 | +            self.assertNotEqual(PP.pin_seal(p2), mp["package_sha256"])
1662 | +
1663 | +    def test_the_contract_refuses_anything_else(self):
1664 | +        pk, why, *_ = package()
1665 | +        self.assertIsNone(why)
1666 | +        cases = {
1667 | +            "two segments": lambda p: p["segments"].append(dict(p["segments"][0], label="clip_01")),
1668 | +            "an intro": lambda p: p["vo"].update(intro="Here is the thing."),
1669 | +            "a bridge": lambda p: p["vo"].update(bridges=["Next."], bridges_after_clip=[1]),
1670 | +            "a long closing": lambda p: (p["vo"].update(closing=" ".join(["word"] * 13)),
1671 | +                                         next(x for x in p["lines"] if x["slot"] == "closing").update(
1672 | +                                             text=" ".join(["word"] * 13))),
1673 | +            "a comment that is not the gated one": lambda p: p.update(first_comment=p["first_comment"] + " extra"),
1674 | +            "a runtime under 28 s": lambda p: p.update(runtime_s_estimate=27.9),
1675 | +            "no source row": lambda p: p["gates"].pop("spotlight_source"),
1676 | +            "a closing without its rows": lambda p: p["gates"].pop("closing_value"),
1677 | +            "a replayed row": lambda p: p["gates"]["hook_own"].update(replayed=True),
1678 | +            "no first comment": lambda p: p.pop("first_comment"),
1679 | +        }
1680 | +        for name, change in cases.items():
1681 | +            p2 = copy.deepcopy(pk)
1682 | +            change(p2)
1683 | +            with self.assertRaises(PP.PinRefused, msg=name):
1684 | +                PP.to_pin(p2, "t")
1685 | +
1686 | +    def test_the_comment_format(self):
1687 | +        self.assertEqual(PP.first_comment_text("Line one.\nLine two.", ["@a", "Some Name"]),
1688 | +                         "Line one.\nLine two.\n\nCredits \U0001F9E1\n\n@a Some Name")
1689 | +
1690 | +
1691 | +def snap_rig(sentences, k, marks=()):
1692 | +    src = source(sentences, channel="DataDash", age_h=2.0, vid="vidS")
1693 | +    ctx = E.Context(NOW, REG)
1694 | +    sp = E.Span(src, k, k)
1695 | +    m = M.record(sp, {"scores": dict(pm("x", "A", 1.0)["scores"]), "names_person": False, "risk": [],
1696 | +                      "topics": ["price_action"], "reason": "r"}, ctx, M.judge(sp, ctx), {"by": "fake"})
1697 | +    m["rank_score"] = 1.0
1698 | +    caps = lambda vid: ([(t, "w", True) for t in marks] or None, {"file": "f", "sha256": "s"} if marks else None)
1699 | +    return m, {"vidS": src}, ctx, caps
1700 | +
1701 | +
1702 | +S5 = "Bitcoin keeps moving and people keep watching it closely today."      # 10 words: 3.3 s with its pause
1703 | +S20 = " ".join(["Bitcoin"] + ["word"] * 63) + "."                              # 64 words: about 19.5 s
1704 | +S33 = " ".join(["Bitcoin"] + ["word"] * 109) + "."                             # 110 words: about 33 s
1705 | +
1706 | +
1707 | +class TestSnap(unittest.TestCase):
1708 | +    def test_the_next_sentences_first_whole_and_never_padded(self):
1709 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 2)
1710 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1711 | +        self.assertIsNone(why)
1712 | +        self.assertEqual(v["spotlight_snap"]["was"], [2, 2])
1713 | +        self.assertEqual(v["spotlight_snap"]["sentences"][0], 2)                # nothing before was needed
1714 | +        self.assertGreaterEqual(v["duration_s"], SPOT.SNAP_TO_S)
1715 | +        self.assertLess(v["duration_s"] - 3.3, SPOT.SNAP_TO_S)                 # one sentence fewer is too short
1716 | +        self.assertNotEqual(v["moment_id"], m["moment_id"])                    # a NEW moment, judged as usual
1717 | +        self.assertEqual(v["spotlight_snap"]["from"], m["moment_id"])
1718 | +        self.assertIn("eligibility", v)
1719 | +
1720 | +    def test_a_speaker_marker_after_turns_it_to_the_sentences_before(self):
1721 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4)
1722 | +        t_next = srcs["vidS"].tokens[srcs["vidS"].sentences[5][0]]["start"]
1723 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4, marks=(t_next + 1.5,))
1724 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1725 | +        self.assertIsNone(why)
1726 | +        self.assertEqual(v["spotlight_snap"]["sentences"][1], 4)                # never across the marker
1727 | +        self.assertLess(v["spotlight_snap"]["sentences"][0], 4)
1728 | +
1729 | +    def test_no_snap_past_35_s_or_past_the_record(self):
1730 | +        m, srcs, ctx, caps = snap_rig([S20, S5, S20], 1)
1731 | +        v, why = SPOT.snap(m, srcs, ctx, caps)                                 # 3.3 + 19.5 = 22.8 s: fine
1732 | +        self.assertIsNone(why)
1733 | +        m, srcs, ctx, caps = snap_rig([S5], 0)
1734 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1735 | +        self.assertIsNone(v)
1736 | +        self.assertIn("the word record ends", why)
1737 | +        m, srcs, ctx, caps = snap_rig([S33, S5, S33], 1)                     # either side runs past 35 s
1738 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1739 | +        self.assertIsNone(v)
1740 | +        self.assertIn("over 35 s", why)
1741 | +        m, srcs, ctx, caps = snap_rig([S5, S20, S5], 1)                       # long enough already: unchanged
1742 | +        self.assertIs(SPOT.snap(m, srcs, ctx, caps)[0], m)
1743 | +
1744 | +
1745 | +class TestSourceTest(unittest.TestCase):
1746 | +    def lay(self, kind):
1747 | +        return {"measured": True, "layout": kind, "why": "w", "backend": "b", "replayed": False}
1748 | +
1749 | +    def test_conversation_or_first_hand_pass_and_recap_reaction_other_fail(self):
1750 | +        unmarked = {"measured": False, "unmarked": True}
1751 | +        for kind, want in (("conversation", True), ("first_hand", True), ("recap", False), ("reaction", False),
1752 | +                           ("other", False)):
1753 | +            self.assertEqual(SPOT.source_test(unmarked, self.lay(kind))[0], want, kind)
1754 | +
1755 | +    def test_an_unmeasured_layout_is_never_a_pass(self):
1756 | +        ok, why = SPOT.source_test({"measured": True, "turns": 30, "minutes": 10, "turns_per_min": 3.0},
1757 | +                                   {"measured": False, "why": "no sheet"})
1758 | +        self.assertFalse(ok)
1759 | +        self.assertIn("not measured", why)
1760 | +
1761 | +    def test_the_markers_only_make_it_stricter(self):
1762 | +        solo = {"measured": True, "turns": 8, "minutes": 16.5, "turns_per_min": 0.48}     # Nov 13: L6H7538ogGs
1763 | +        talk = {"measured": True, "turns": 20, "minutes": 16.8, "turns_per_min": 1.19}    # Nov 13: 3kV3nWC5SAY
1764 | +        self.assertFalse(SPOT.source_test(solo, self.lay("conversation"))[0])
1765 | +        self.assertTrue(SPOT.source_test(talk, self.lay("conversation"))[0])
1766 | +        self.assertTrue(SPOT.source_test(solo, self.lay("first_hand"))[0])       # a keynote is one voice
1767 | +        self.assertFalse(SPOT.source_test(talk, self.lay("recap"))[0])
1768 | +
1769 | +
1770 | +class TestContracts(unittest.TestCase):
1771 | +    def test_layout(self):
1772 | +        self.assertEqual(SPOT.parse_layout('{"layout": "conversation", "people_on_screen": 2, "why": "two people"}')
1773 | +                         ["layout"], "conversation")
1774 | +        for bad in ('{"layout": "panel", "people_on_screen": 2, "why": "w"}',
1775 | +                    '{"layout": "recap", "people_on_screen": "1", "why": "w"}',
1776 | +                    '{"layout": "recap", "people_on_screen": 1}', "not json"):
1777 | +            with self.assertRaises(ValueError):
1778 | +                SPOT.parse_layout(bad)
1779 | +
1780 | +    def test_write(self):
1781 | +        got = SPOT.parse_write(json.dumps(dict(GOOD, title={"text": "T", "cites": ["m1"]})), "m1")
1782 | +        self.assertEqual(got["title"]["cites"], ["m1"])
1783 | +        self.assertIsNone(SPOT.parse_write(json.dumps(GOOD), "m1", closing_allowed=False)["closing"])
1784 | +        self.assertIsNone(SPOT.parse_write(json.dumps(dict(GOOD, closing=None)), "m1")["closing"])
1785 | +        for bad in (dict(GOOD, title={"text": "T", "cites": ["other"]}), {k: GOOD[k] for k in ("title", "caption")},
1786 | +                    dict(GOOD, comment={"text": " ", "cites": []}), dict(GOOD, caption={"text": "x" * 221, "cites": []})):
1787 | +            with self.assertRaises(ValueError):
1788 | +                SPOT.parse_write(json.dumps(bad), "m1")
1789 | +
1790 | +    def test_value_verdict_needs_four_clear_yeses_and_twelve_words(self):
1791 | +        m = moment()
1792 | +        r = Router(coherence_verdict=[VALUE_YES])
1793 | +        v = SPOT.value_verdict(r, m, "Scarcity only matters when nobody can quietly change it.", "DataDash",
1794 | +                               {"heimdall"}, {"deepseek"})
1795 | +        self.assertTrue(v["ok"])
1796 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))   # off the writer
1797 | +        for ans in (dict(VALUE_YES, missed="no"), dict(VALUE_YES, adds="no")):
1798 | +            self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[ans]), m, "A line.", "D", set(), set())["ok"])
1799 | +        self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[VALUE_YES]), m, " ".join(["w"] * 13), "D",
1800 | +                                            set(), set())["ok"])                 # code counts the words too
1801 | +        r = Router(coherence_verdict=['{"adds": "maybe"}'])
1802 | +        v = SPOT.value_verdict(r, m, "A line.", "D", set(), set())
1803 | +        self.assertFalse(v["ok"])
1804 | +        self.assertFalse(v["measured"])
1805 | +        self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1806 | +        self.assertFalse(SPOT.value_verdict(Router(), m, "A line.", "D", set(), set())["ok"])   # no answer: no line
1807 | +
1808 | +    def test_style_of_the_comment_and_the_closing(self):
1809 | +        lint = lambda slot, text: [v["detail"].split(":")[0] for v in SPOT.style_lint([{"slot": slot, "text": text}])]
1810 | +        self.assertEqual(lint("comment", "This one stuck with me.\nWorth the full listen."), [])
1811 | +        self.assertIn("comment-lines", lint("comment", "One.\nTwo.\nThree."))
1812 | +        self.assertIn("comment-words", lint("comment", " ".join(["word"] * 31)))
1813 | +        self.assertIn("comment-credits", lint("comment", "Go follow @someone"))
1814 | +        self.assertIn("comment-credits", lint("comment", "Credits to them."))
1815 | +        self.assertIn("emoji", lint("comment", "So good \U0001F525"))
1816 | +        self.assertIn("closing-words", lint("closing", " ".join(["word"] * 13)))
1817 | +
1818 | +
1819 | +class TestCredits(unittest.TestCase):
1820 | +    def test_verified_handles_only_and_untagged_names_said_so(self):
1821 | +        cr = SPOT.credits("DataDash", {"name": "unknown", "measured": True}, HANDLES)
1822 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
1823 | +        self.assertIn("no attested speaker", cr["speaker"]["untagged_why"])
1824 | +        cr = SPOT.credits("Simply Bitcoin", {"name": "Natalie", "measured": True}, HANDLES)   # an alias
1825 | +        self.assertEqual(cr["tags"], ["Simply Bitcoin", "@natbrunell"])
1826 | +        self.assertIn("no verified X handle", cr["channel"]["untagged_why"])
1827 | +        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": True}, HANDLES)
1828 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten", "Jane Guest"])
1829 | +        self.assertEqual(cr["speaker"]["untagged_why"], "not in the verified table")
1830 | +        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": False}, HANDLES)     # never a guess
1831 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
1832 | +        self.assertEqual(SPOT.credits("DataDash", None, "/nonexistent.json")["tags"], ["DataDash"])
1833 | +
1834 | +
1835 | +class TestPool(unittest.TestCase):
1836 | +    def test_one_per_channel_per_day_and_the_record_must_read(self):
1837 | +        ctx = E.Context(NOW, REG)
1838 | +        a, b = moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset"))
1839 | +        caps = lambda vid: (None, None)                                     # (two texts: one speech is one moment)
1840 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": SPOT.et_day(NOW)}],
1841 | +                             captions_for=caps)
1842 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])
1843 | +        self.assertIn("already has a spotlight", why["a"])
1844 | +        got, _ = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": "2026-11-01"}], captions_for=caps)
1845 | +        self.assertEqual(len(got), 2)                                       # another day
1846 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=None, captions_for=caps)
1847 | +        self.assertEqual(got, [])
1848 | +        self.assertIn("not measured", why["a"])
1849 | +
1850 | +    def test_35_s_ceiling_and_the_cold_open(self):
1851 | +        ctx = E.Context(NOW, REG)
1852 | +        caps = lambda vid: (None, None)
1853 | +        long_ok = moment(mid="l", dur=30.0, channel="A")
1854 | +        too_long = moment(mid="t", dur=36.0, channel="B", text=TEXT.replace("money", "asset"))
1855 | +        conj = moment(mid="c", channel="C", text="And " + TEXT.replace("money", "thing"))
1856 | +        got, why = SPOT.pool([long_ok, too_long, conj], {}, ctx, spotlit=[], captions_for=caps)
1857 | +        self.assertEqual([m["moment_id"] for m in got], ["l"])               # 30 s: a medley's 20 s does not bind
1858 | +        self.assertIn("35.0 s", why["t"])
1859 | +        self.assertIn("cannot open cold", why["c"])
1860 | +
1861 | +    def test_the_record(self):
1862 | +        p = os.path.join(TMP, "SPOTLIGHTS.json")
1863 | +        try:
1864 | +            self.assertEqual(SPOT.load_spotlit(p), [])
1865 | +            SPOT.record_spotlit(p, {"channel_id": "A", "day_et": "2026-11-13"})
1866 | +            self.assertEqual(SPOT.load_spotlit(p), [{"channel_id": "A", "day_et": "2026-11-13"}])
1867 | +            with open(p, "w") as f:
1868 | +                f.write("{")
1869 | +            self.assertIsNone(SPOT.load_spotlit(p))
1870 | +            with self.assertRaises(ValueError):
1871 | +                SPOT.record_spotlit(p, {"channel_id": "B", "day_et": "2026-11-13"})
1872 | +        finally:
1873 | +            if os.path.exists(p):
1874 | +                os.remove(p)
1875 | +
1876 | +
1877 | +class TestPackageFor(unittest.TestCase):
1878 | +    def test_the_closing_line_ships_only_with_every_gate(self):
1879 | +        pk, why, router, asked, fids = package()
1880 | +        self.assertIsNone(why)
1881 | +        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])
1882 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
1883 | +        for g in PP.CLOSING_GATES:
1884 | +            self.assertEqual(pk["gates"][g]["status"], "PASS")
1885 | +        self.assertEqual(asked, [GOOD["closing"]["text"]])                  # context judged WITH the line
1886 | +        self.assertEqual(sorted(map(tuple, fids)), [("closing",), ("title", "caption", "comment")])
1887 | +        self.assertNotIn("coherence", pk["gates"])
1888 | +        self.assertNotIn("r4", pk["gates"])
1889 | +        self.assertTrue(pk["first_comment"].startswith(GOOD["comment"]["text"] + "\n\nCredits \U0001F9E1\n\n"))
1890 | +        self.assertTrue(pk["first_comment"].endswith("@Nicholas_Merten"))
1891 | +        self.assertTrue(28.0 <= pk["runtime_s_estimate"] <= 50.0)
1892 | +
1893 | +    def test_any_failure_leaves_no_line(self):
1894 | +        for name, kw in (("the value verdict says no", {"value": dict(VALUE_YES, adds="no")}),
1895 | +                         ("the value verdict is out of contract", {"value": '{"adds": 1}'}),
1896 | +                         ("its fidelity fails", {"cfid": dict(FID_OK, ok=False, violations=[
1897 | +                             {"slot": "closing", "rule": "COMMENTARY", "detail": "d"}])}),
1898 | +                         ("context fails with it", {"cx": dict(CX_OK, ok=False, violations=[
1899 | +                             {"rule": "NOT_ENTAILED"}])}),
1900 | +                         ("it breaks the house style", {"write": dict(GOOD, closing={
1901 | +                             "text": "Ultimately scarcity matters, which makes it rare.", "cites": []})})):
1902 | +            pk, why, router, asked, fids = package(**kw)
1903 | +            self.assertIsNone(why, name)
1904 | +            self.assertIsNone(pk["vo"]["closing"], name)
1905 | +            self.assertFalse(any(g in pk["gates"] for g in PP.CLOSING_GATES), name)
1906 | +            self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [], name)
1907 | +            self.assertEqual(asked[-1], None, name)                         # the package without it is judged
1908 | +            self.assertFalse(pk["spotlight"]["closing"]["kept"], name)
1909 | +
1910 | +    def test_a_null_closing_is_the_default(self):
1911 | +        pk, why, router, asked, fids = package(write=dict(GOOD, closing=None))
1912 | +        self.assertIsNone(why)
1913 | +        self.assertIsNone(pk["vo"]["closing"])
1914 | +        self.assertEqual(router.calls.count(("coherence_verdict", None, None)), 0)
1915 | +        self.assertNotIn("coherence_verdict", [c[0] for c in router.calls])     # no value verdict is asked
1916 | +
1917 | +    def test_one_more_write_of_a_failing_title_never_of_the_closing(self):
1918 | +        bad = dict(GOOD, title={"text": "The one money nobody can print more of today", "cites": []})   # 9 words
1919 | +        second = dict(GOOD, closing={"text": "A different closing line here.", "cites": []})
1920 | +        pk, why, router, *_ = package(writes=[bad, second])
1921 | +        self.assertIsNone(why)
1922 | +        self.assertEqual(pk["title"], GOOD["title"]["text"])
1923 | +        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])      # the first write's: one write
1924 | +        pk, why, *_ = package(writes=[bad, bad])
1925 | +        self.assertIsNone(pk)
1926 | +        self.assertIn("both writes", why)
1927 | +
1928 | +    def test_the_base_lines_must_pass_their_own_verdicts(self):
1929 | +        pk, why, *_ = package(fid=dict(FID_OK, ok=False, violations=[{"slot": "title", "rule": "VERDICT_NO"}]))
1930 | +        self.assertIsNone(pk)
1931 | +        self.assertIn("VO fidelity", why)
1932 | +        pk, why, *_ = package(value=dict(VALUE_YES, adds="no"), cx_base=dict(CX_OK, ok=False, violations=[
1933 | +            {"rule": "STRONGER"}]))
1934 | +        self.assertIsNone(pk)
1935 | +        self.assertIn("context integrity", why)
1936 | +
1937 | +    def test_step_a_off_the_writer_must_exist(self):
1938 | +        m = moment()
1939 | +        r = Router(angle_write=[GOOD])
1940 | +        r.backends = {"fake:xai": B("fake", "grok"), "fake:heimdall": B("fake", "deepseek")}   # both on the writer
1941 | +        pk, why = SPOT.package_for(r, m, E.Context(NOW, REG), {}, two(), {}, {}, pre_of(m), {}, log=lambda *a: None,
1942 | +                                   attribute=unknown_speaker)
1943 | +        self.assertIsNone(pk)
1944 | +        self.assertIn("L-x", why)
1945 | +
1946 | +
1947 | +class TestBuild(unittest.TestCase):
1948 | +    """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
1949 | +
1950 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None):
1951 | +        ctx = E.Context(NOW, REG)
1952 | +        calls = {}
1953 | +
1954 | +        def prescreen(router, ms_, *a, **k):
1955 | +            return {m["moment_id"]: dict(a_item("hook"), backend="fake:xai") for m in ms_}, \
1956 | +                {m["moment_id"]: [] for m in ms_}, set(), set()
1957 | +
1958 | +        def hook_ratings(router, ms_, *a, **k):
1959 | +            return {m["moment_id"]: {"scroll": ratings[m["moment_id"]], "alone": 5, "setup": 3,
1960 | +                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "fake:xai"}
1961 | +                    for m in ms_}, None
1962 | +
1963 | +        def second(router, cleared, a_by, *a, **k):
1964 | +            return {mid: [a_by[mid], dict(a_item("hook"), backend="fake:heimdall")] for mid in cleared}, {}
1965 | +
1966 | +        def package_for(router, m, ctx_, sources_, a_two, truth, exc, pre, facts, **k):
1967 | +            calls.setdefault("package_for", []).append(m["moment_id"])
1968 | +            calls.setdefault("facts", []).append(facts)
1969 | +            return {"segments": [m], "shape": "spotlight"}, None
1970 | +        idx = {m["moment_id"]: sv(m["text"], s) for m, s in zip(ms, alone or [4.0] * len(ms)) if s is not None}
1971 | +        seq = list(poll or [])
1972 | +        verdicts = lambda path, sha: (seq.pop(0) if seq else idx, {"read": True})
1973 | +        stubs = [(SPOT.P, "prescreen", prescreen), (SPOT.P, "hook_ratings", hook_ratings),
1974 | +                 (SPOT.P, "second_screen", second), (SPOT, "package_for", package_for),
1975 | +                 (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
1976 | +                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
1977 | +                 (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
1978 | +                 (VP, "visual_for", lambda r, m, w, c: {"measured": True, "flags": [], "backend": "fake:vis"}),
1979 | +                 (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
1980 | +                 (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
1981 | +                 (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
1982 | +                 (SPOT.P, "_writers", lambda r: (set(), set()))]
1983 | +        patches = [mock.patch.object(o, n, f) for o, n, f in stubs]
1984 | +        for p in patches:
1985 | +            p.start()
1986 | +        try:
1987 | +            out = SPOT.build(Router(), ms, {}, ctx, work_dir="/tmp", scorer_verdicts_path="v.json",
1988 | +                             lock_check=lock or (lambda segs: pre_of(segs[0])), spotlit=[], sleep=lambda s: None,
1989 | +                             captions_for=lambda vid: (None, None), wait_s=60.0)
1990 | +        finally:
1991 | +            for p in patches:
1992 | +                p.stop()
1993 | +        return out, calls
1994 | +
1995 | +    def test_the_best_qualifying_moment_goes_to_the_package(self):
1996 | +        ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
1997 | +              moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
1998 | +        out, calls = self.run_build(ms, {"a": 3, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1999 | +        self.assertEqual(calls["package_for"], ["b"])                      # c opens best but stands alone at 3
2000 | +        self.assertIn("hook's own job rates 3", out["moments"]["a"]["out"])
2001 | +        self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
2002 | +        self.assertIsNotNone(out["package"])
2003 | +
2004 | +    def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
2005 | +        ms = [moment(mid="a", channel="A")]
2006 | +        later = {"a": sv(TEXT, 4.0)}
2007 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[None], poll=[{}, later])
2008 | +        self.assertEqual(calls["package_for"], ["a"])
2009 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[None], layout="recap")
2010 | +        self.assertIsNone(out["package"])
2011 | +        self.assertNotIn("package_for", calls)
2012 | +        self.assertIn("no rating yet", out["moments"]["a"]["out"])
2013 | +        self.assertEqual(out["near"][0]["moment_id"], "a")
2014 | +        self.assertEqual(out["near"][0]["passed"][-1], "step A from the second family")
2015 | +
2016 | +    def test_never_delivered_is_measured_again_at_the_package(self):
2017 | +        ms = [moment(mid="a", channel="A")]
2018 | +        out, calls = self.run_build(ms, {"a": 5})
2019 | +        self.assertIs(calls["facts"][0]["never_delivered"], True)
2020 | +        real, n = SPOT.P.usable, []
2021 | +
2022 | +        def usable(ms_, *a, **k):                       # the pool keeps it; a delivered span appears before the package
2023 | +            n.append(1)
2024 | +            return real(ms_, *a, **k) if len(n) == 1 else ([], {ms_[0]["moment_id"]: "delivered"})
2025 | +        with mock.patch.object(SPOT.P, "usable", usable):
2026 | +            out, calls = self.run_build(ms, {"a": 5})
2027 | +        self.assertIs(calls["facts"][0]["never_delivered"], False)
2028 | +
2029 | +    def test_ruling_92_and_a_lock_with_no_verdict_stops(self):
2030 | +        ms = [moment(mid="a", channel="A")]
2031 | +        out, calls = self.run_build(ms, {"a": 5}, layout="reaction")
2032 | +        self.assertIsNone(out["package"])
2033 | +        self.assertIn("ruling 92", out["moments"]["a"]["out"])
2034 | +        out, calls = self.run_build(ms, {"a": 5}, lock=lambda segs: {"ok": False, "segments": [], "error": "timeout"})
2035 | +        self.assertIsNone(out["package"])
2036 | +        self.assertIn("timeout", out["lock_stop"])
2037 | +
2038 | +
2039 | +if __name__ == "__main__":
2040 | +    unittest.main()
2041 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that another
session, the integrator, renders into short Bitcoin videos). The change adds a SECOND PIN KIND, the "spotlight"
(one strong clip, an optional host line, the sign-off). Only state what you can verify from the diff; if uncertain,
say so; do not guess. Be factual and specific: file:line and a concrete input that breaks it.

Background (static):
- The flagship kind is the MEDLEY (a hook clip + 2-4 clips back to back, one takeaway line). A package passes many
  gates; package_pin.to_pin() turns it into a pin only when every REQUIRED gate row in its sealed inventory is exactly
  "PASS" with replayed false (law L-j: fail closed), and seals the gated bytes with seal() (sha256). The integrator's
  readiness check imports THIS worktree's package_pin.py live and recomputes seal() on every pin, so seal() must stay
  backward compatible: every pin sealed before this change must recompute to its own package_sha256.
- Law L-m: nothing measured is never a pass (an unavailable or out-of-contract verdict is no verdict).
- Law L-s: a verdict never comes from the vendor or model family that wrote the line it judges.
- The verdicts the spotlight reuses (step A context integrity, the second recognition pass and CUTTABLE, G17a hook
  onset, the hook rating, the visual check, the second step-A family, exclusion, VO fidelity, context integrity) are
  the medley's own, unchanged, cached across builds.
- The ALONE scorer is the render's stand-alone clip scorer (1-5), run by the integrator's service on candidates this
  builder writes at the start of each build (package.scorer_pass); verdicts are read from a file and apply only to the
  exact text they rated (text_sha256).
- The render's lock pre-check (lock_precheck) re-decodes each clip on the integrator's side and passes, adopts a
  spoken text, or holds the clip. Its results are keyed by the integrator's decoder sha, which moved tonight to
  c705b20ed800 (their spotlight branches changed pinned.py; RULES unchanged).

The orders (verbatim excerpts):
- RULING 90 (22:40 ET Nov 13, LAW since 22:52): "a spotlight is built only when the window's search ends with no
  medley, or for a moment no medley used. SHAPE: ONE moment, one speaker, one channel: 12 to 35 s of clip. No hook/clip
  split, no bridge, no join. Then at most ONE closing line in the PBX MAX voice, 12 words or fewer, class D commentary
  that characterises what was SAID (the two refused patterns stay refused) ... Then the sign-off and the credits card
  with that one channel, then the outro. Total 28 to 50 s. ... WHICH MOMENT: it must rate >= 4 on the hook's own job
  (it opens cold) AND >= 4 as a clip standing alone (the ALONE scorer + step A, both vendors as routed); the visual
  check clean; inside 12 h at the render clock; never a delivered span; at most one spotlight per channel per day. If
  the strong moment is under 12 s, snap it OUTWARD to the speaker's whole thought (ruling 32's snap; the added words
  judged as usual), not padded. EVERY integrity law is unchanged ... YOUR SIDE: the spotlight package (kind
  'spotlight' sealed in the pin; gates: the moment's two ratings, step A both families, pre-check, the closing line's
  fidelity + context as for a takeaway, title, caption). Title 8 words or fewer; caption in house style; ALSO write
  the first-comment draft ... in PBX's format: one or two short casual lines specific to this clip (not preachy, no
  emoji), a blank line, 'Credits' + the orange heart, a blank line, the X handles of the channel and the attested
  speaker (handles only from a verified table: if a handle is not in the table, leave the name untagged and say so)."
- RULING 91 (22:52): "Default for a spotlight: NO PBX line ... A line is written only as a candidate and is kept only
  if a separate VALUE verdict (off the writer's family) answers all of: it says something the clip does not already
  say; it does not restate, summarise or cheer the clip; a viewer would miss it if it were cut; it is 12 words or
  fewer; plus the usual fidelity and context gates. One write, one verdict; anything short of a clear yes means no
  line."
- RULING 92 (22:52): "A spotlight moment must come from a conversation or original reporting: an episode whose caption
  turn structure shows two or more speakers (interview, podcast, panel), or a first-hand statement (a keynote, an
  interview on a news network). NOT from a solo host-to-camera news recap or reaction segment, on any channel.
  Measured, not listed by name: the turn markers across the episode (one speaker throughout = solo), plus the visual
  check's layout (one face to camera with headline graphics or b-roll = recap)."
- 22:58: "The 20 s per source video is a medley rule; for a spotlight the ceiling is ruling 90's 35 s."
- The pin contract agreed with the integrator (22:44): moments_package.shape "spotlight"; exactly one segment, role
  "hook"; edl_vo {"intro": null, "bridges": [], "closing": <= 12 words or null}; signoff_expected names that one
  channel; first_comment is the WHOLE comment (printed verbatim, nothing appended); gate rows always required:
  spotlight_source, hook_own, stands_alone, step_a_two_families, visual, window_12h, never_delivered,
  one_per_channel_day, precheck; and closing_value, closing_fidelity, closing_context whenever closing is non-null.
  The integrator's seal call: seal(segments, edl_vo, signoff, title, caption, gates, btc_screen, shape=...,
  first_comment=...) for a spotlight only.

The change:
1. package_pin.py: SPOTLIGHT_GATES, CLOSING_GATES, SPOT_RUNTIME_S (28, 50), SPOT_CLOSING_MAX_WORDS 12,
   first_comment_text(); required_gates() for the spotlight (a package's vo or a pin's edl_vo); seal() gains
   shape / first_comment (in the body only for shape "spotlight") and edl_vo["closing"] (only when the key is present);
   pin_seal(pin); line_problems() checks the closing line and that first_comment is built from the gated comment;
   spotlight_problems() (one segment, no intro or bridge, closing <= 12 words, the sign-off names the channel, a
   first comment, runtime 28-50 s); screen_problems() also for a spotlight; to_pin() emits the agreed fields.
2. package.py: usable(seg_max=...) (35 s for a spotlight); scorer_pass(extra=...) and build(scorer_extra=...) send the
   spotlight's pool to the ALONE scorer with the medley's own candidates (deduplicated by id and text).
3. spotlight.py (new):
   - pool(): free stage (usable with 35 s, one per re-posted speech, one spotlight per channel per ET day from a
     record, the snap for a moment under SNAP_TO_S = 13.7 s: 28 s minus the factory's 14.3 s tail, the render's hook
     opener rule and its topic rule);
   - snap(): whole sentences of the same word record, the next ones first, then the ones before, never past 35 s,
     never across a caption speaker marker; a new moment re-judged by the miner's eligibility;
   - episode_turns() + layout_for() (a vision verdict on the clip's own contact sheet, cached) + source_test()
     (ruling 92: PASS only for a measured layout "conversation" or "first_hand"; a marked episode under 1.0 caption
     turns a minute is not a conversation);
   - build(): the stages in order (step A, L-v 2 / CUTTABLE, G17a and the hook rules, the hook's own job >= 4, the
     visual check clean, step A from the second family, the ALONE scorer >= 4 with a bounded wait, ruling 92), then
     best first: exclusion, the lock pre-check, package_for(); the three nearest when none qualifies;
   - package_for(): one write (title, caption, comment, candidate closing); one more write of title/caption/comment
     only when a free gate refuses them (never of the closing); every verdict off the writers; the closing ships only
     with the free gates, ruling 91's value verdict (four clear yeses AND <= 12 words in code), its own fidelity
     verdict and context integrity with it spoken; otherwise no line; then the speaker record, credits() from the
     verified table, the first comment, LP.apply, and the inventory (package.inventory's rows minus "r4" and
     "coherence", plus the spotlight rows).
4. lock_precheck.py: DECODER c705b20ed800.
5. proof_ledger.py: the pool to the scorer at the build's start; the spotlight after the medley search (a sealed
   medley's clips excluded); SPOTLIGHT_PIN.json and the SPOTLIGHTS record.
6. Tests: test_spotlight.py (new), test_lock_precheck.py (the decoder).

Check, against the diff:
- that every pin sealed before the change recomputes unchanged, and that a spotlight's closing line, kind and first
  comment are inside the seal;
- that no path can ship a closing line without all three closing rows PASS, or ship one that failed any gate;
- that every required row is computed from a measurement (none hard-coded to PASS without evidence); name any row that
  could PASS on missing data;
- that the snap never pads, never crosses a speaker marker, never exceeds 35 s, and that the snapped span is judged
  by every gate;
- that ruling 92's test cannot pass a solo recap or a reaction, and fails closed when unmeasured;
- that every verdict is off the writers' vendor and family (L-s), the value verdict included;
- the per-channel-per-day rule, including an unreadable record;
- that the medley's behaviour is unchanged (scorer_extra, usable's default, seal for medley pins).

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario for each), then
"SHIP: yes / no / yes with conditions". Reminder: only what you can verify from the diff; fail closed is the law.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
