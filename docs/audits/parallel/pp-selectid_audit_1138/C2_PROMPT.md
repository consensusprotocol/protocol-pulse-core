# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1138
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 363 s finish=stop usage in 29400 / out 11970 usd~0.268 (upper-bound price)

# Audit: pp-selectid-1138 — fail-closed admission path (rulings 56/60)

Scope note: I reviewed only the diff provided. Where the diff references code not shown (e.g. `stand_alone.CLIP_MIN_SCORE`, `SA._words`, `SA.CONJUNCTIONS`, `SA.REPLY_FRAGMENTS`, `no_role_on_screen`'s full body, `placement`, `lineup_for`, `text_sha`, `pm`, `source`, `ctx`, `angle`, `Rig` internals, `check_edl`'s tail, `pinned.validate_schema`), I state what the diff implies and flag uncertainty rather than guess.

---

## P0 findings

None found. Every fail-closed path I could trace holds: the reader returns `({}, read: False)` on missing/unreadable/malformed file, wrong kind, present-and-non-null or absent event, wrong `scorer_sha`, wrong threshold; a verdict is dropped for non-numeric score, error, or `affirmed` disagreeing with `SA.affirmed(..., moments=True)`; `verdict_of`/`with_verdict` bind a verdict to the sha of the moment's current text; the pin's `affirmed_verdict` re-derives everything from the sealed bytes. I could not construct a scenario where a segment is sealed without an affirming verdict on exactly its text.

---

## P1 findings

**P1-1. `package.py:130` (scorer_verdicts) — the `why` chain evaluates `sc.get("event", "absent") is not None` correctly, but the "no verdicts" branch is unreachable dead logic, and the `why`-chain ordering silently changes what a malformed `scorer` reports.**
Concrete scenario: the `why` chain is a single conditional expression evaluated eagerly as a chain of `if/elif` — fine — but note that when `d["scorer"]` itself is not a dict (e.g. a list), `sc.get(...)` raises `AttributeError`, which *is* caught (line 141 catches `AttributeError`) and returns `read: False` with the exception's name. That is fail-closed, so not a correctness bug — but the record's `why` becomes `"AttributeError: ..."` instead of a ruling-56 reason, and the diagnostic fields (`kind`, `event`, `scorer_sha`, `threshold`) are lost. Similarly, if `d["verdicts"]` is a list, `isinstance(vs, dict)` fails → `why = "no verdicts"` → the `if why:` block at line 143-145 then reads `sc.get("kind")` etc. — those still work. However: if `d["scorer"]` is a dict but `d["verdicts"]` key is missing, `KeyError` is caught at 141 — good. The one real gap: when `why` is truthy, the record at line 144-145 includes `sc.get("kind")` etc. — but when the *exception* path fired, those diagnostics are absent. Fail-closed either way; P1 because the sealed/ledgered record loses its diagnostic evidence in exactly the cases (malformed file) where you most want it. M12 is satisfied (reject, never pass); this is an observability gap, not an admission leak.

**P1-2. `package.py:167-170` (verdict_of) vs `package_pin.affirmed_verdict` — the builder's `verdict_of` does NOT check `affirmed`, `kind`, `event`, `threshold`, or `scorer_sha`; it trusts the reader. That is correct only because `scorer_verdicts()` pre-filters — but `verdict_of` is also called on verdicts attached by other code paths (e.g. tests, or any future writer of `m["scorer_verdict"]`), where none of that holds.**
Concrete scenario: `no_role_on_screen` (line 252-254) calls `SA.opener("clip", m["text"], v["score"], v["fault"], moments=True)` on whatever `verdict_of(m)` returns. If a moment carries a verdict dict that came from anywhere other than `scorer_verdicts()` — say a stale process, a hand-edited pin, or a future ruling-57 writer — `verdict_of` checks only `text_sha256` and `isinstance(dict)`. A verdict with `affirmed: false, score: 5.0` would pass `SA.opener` (which reads only score/fault, not the `affirmed` flag) and admit the clip, while the pin's `affirmed_verdict` would later refuse it — a build/pin divergence, caught only at pin time. Within this diff, the only producer is `scorer_verdicts()` (which guarantees `affirmed == rule`), so the invariant holds today; but nothing enforces it. P1: the fail-closed chain relies on an unstated coupling between `verdict_of` (lenient) and `scorer_verdicts` (strict). A one-line comment or a shared predicate would fix it. Note `trim_refused` (line 181-191) reads `s["affirmed"]` directly — a verdict without an `affirmed` key (only possible outside the reader's output) would raise `KeyError` there, not fail closed. Same coupling.

**P1-3. `package.py:289` (`admitted`) — the admitted list is computed from `verdict_of(m) and m["moment_id"] not in no_role`, but `no_role` was computed *after* verdicts were attached, so a moment admitted as a clip by its verdict is excluded from `no_role` — yet `admitted`'s definition silently assumes `no_role` keys are exactly the non-admitted. Fine — but the *log line* (line 310-316) reads `sc['verdicts']`, `sc['affirmed']`, `sc['rated_at']`, `sc['scorer_sha']` when `sc.get("read")` is truthy. When `verdicts_path` is None, `rec = {"read": False, "why": "no verdicts file given"}` — the log's else-branch reads `sc.

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 28817 / out 282 usd~0.151 (upper-bound price)

**P0: None.**  
**P1: None.** (All fail-closed paths for kind, event!=null, scorer_sha mismatch, threshold mismatch, text_sha256 mismatch on current text, missing numeric score, error present, "affirmed" flag disagreeing with re-derived stand_alone.affirmed(moments=True), malformed JSON, unreadable file, or absent file are exercised in scorer_verdicts(), affirmed_verdict(), verdict_of(), with_verdict(), trim_refused(), scorer_problems(), trim_problems(), and the 8 new TestRuling56Scorer cases. No path produces a pass or admission without a matching affirmation from the render's own scorer code.)  
**P2: None verifiable from diff.** (stand_alone.py defaults preserve story path when moments=False; TRIM_SCORER_PENDING and scorer_pending reads are removed or refused; atomic .tmp+os.replace write only on changed (pid,text_sha256) set; admitted openers never become hook (ruling 59 can_open/placement still applies); pin recomputes old pins via SEALED_LATER; no touch to sentence law, credits, L-a–L-l, selection_lock, onset/tail, or release_auth bytes; copied stand_alone.py matches K5; all described evidence numbers (145/9/3/68/153) are consistent with the reader logic.)

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 254 s finish=length usage in 32129 / out 16000 usd~0.336 (upper-bound price)

I’ll audit the diff strictly against the provided code and the governing laws. I will focus on fail-closed behavior, hash/verdict binding, pin-stage consistency with the render, and any path that could admit a segment without a valid, text-bound, moments-kind affirmation.

## P0 Findings

### P0-1: `scorer_verdicts` can accept a verdict whose `affirmed` field is missing, then re-derive it — but the integrator contract says `affirmed` must be present and consistent
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~147–154)

**Scenario:**
The integrator’s verdicts file contains a verdict like:
```json
{"text_sha256": "...", "score": 4.0, "reason": "r", "fault": "none"}
```
(no `affirmed` key).

The code does:
```python
rule = SA.affirmed(v["score"], v.get("fault"), moments=True)
if (v.get("affirmed") is True) != rule:
    disagree.append(pid)
    continue
```
If `v.get("affirmed")` is `None`, then `(None is True)` is `False`. If `rule` is `True` (score >= 3.5), then `False != True` → `True`, so it is added to `disagree` and **skipped**. That is correct fail-closed.

But if `rule` is `False` (score < 3.5), then `(None is True)` is `False`, and `False != False` is `False`, so it is **not** added to `disagree` and **is accepted** with `affirmed: False`. That is also correct.

However, the docstring says: “a verdict without a numeric score, with an error, or whose 'affirmed' disagrees with the render's own moments rule ... is no verdict.” The code does not explicitly reject a missing `affirmed` key; it only rejects when the *derived* rule disagrees with the *stored* `affirmed` being `True`. A missing `affirmed` is treated as `False`, which is consistent with a non-affirming verdict. This is acceptable under fail-closed, but it is a subtle contract point: the integrator’s file is expected to always include `affirmed`. If a future integrator omits it for an affirming verdict (score >= 3.5), the code will correctly reject it (because `None is True` is `False`, and `rule` is `True`, so they disagree). So this is **not** a P0. I retract.

**Revised:** No P0 here. The logic is fail-closed.

---

### P0-2: `affirmed_verdict` in `package_pin.py` does not verify that `scorer_sha` matches the *current* render code
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
A pin is sealed with a `scorer_verdict` that has a valid `scorer_sha` at the time of sealing. Later, the render’s `stand_alone.py` or `story_semantics.py` is updated (e.g., a bug fix or threshold change). The pin is re-validated (e.g., by the integrator’s `check_pin_only` or by `to_pin` being called again on the same package). `affirmed_verdict` checks:
```python
bool(v.get("scorer_sha")) and ...
```
It only checks that `scorer_sha` is a non-empty string, **not** that it matches the current render code. This means a pin sealed under an older scorer code will still pass `affirmed_verdict` after the render code changes.

**Why this is P0:**
- The governing law L-j (RELEASE IS AUTHORISED ON THESE BYTES) requires that gates run on “exactly the bytes that are sent.” The scorer verdict is part of the sealed pin. If the render code changes, the verdict is no longer from the render’s *current* scorer.
- The `scorer_verdicts` reader in `package.py` correctly checks `scorer_sha == code_sha` (where `code_sha` is `render_scorer_sha()` computed from the current files). But `affirmed_verdict` in `package_pin.py` does **not** perform this check. It is a separate, weaker validation.
- The pin is the unit of release. If `affirmed_verdict` is the gate that the integrator’s pin check uses (via `to_pin` → `scorer_problems` → `affirmed_verdict`), then a stale `scorer_sha` will be accepted.

**Concrete failure:**
1. Render code at time T1: `stand_alone.py` + `story_semantics.py` hash to `sha_A`.
2. A pin is sealed with `scorer_verdict.scorer_sha = sha_A`.
3. At time T2, the render code is updated; the new hash is `sha_B`.
4. The integrator re-runs `to_pin` on the same package (e.g., to re-seal after a metadata change). `affirmed_verdict` sees `scorer_sha = sha_A` (non-empty) and returns `True`. The pin is accepted.
5. But the verdict was produced by the *old* scorer code. The render’s *current* scorer might rate the same text differently (e.g., a threshold change from 3.5 to 4.0). The pin is now sealed with a verdict that the current render would not produce.

**Fix:**
`affirmed_verdict` should accept a `code_sha` parameter (or compute it) and verify `v["scorer_sha"] == code_sha`. Alternatively, the pin should store the `scorer_sha` and the integrator’s check should compare it against the current render code. As written, `affirmed_verdict` is insufficient.

**Severity:** P0 — violates L-j (release authorised on these bytes) and the fail-closed principle.

---

### P0-3: `scorer_problems` in `package_pin.py` does not check `scorer_

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1138 (RULING 56 under RULING 60, re-based onto 58 + 59): cycle 1 consensus

**Run:**
- grok: no P0 or P1, "SHIP: yes".
- glm: "SHIP: yes, with conditions". Its 8 numbered "P1" items close themselves or are by design (below).
- qwen: four "P0" items with one root cause (refuted below). It stopped at its 16,000-token limit, after retracting
  every P1 it raised ("No P1 here. I retract").

No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0-2..P0-5: package_pin.affirmed_verdict checks only that scorer_sha is present, not that it equals the render's code NOW, so a pin sealed under an older scorer passes after the render changes, against L-j | The pin-stage verdict is a pre-filter, never the release gate for the scorer. The render's validate asks its OWN scorer again at render time, on its current code. The integrator's contract (main pipeline/stand_alone_scorer.py, docstring line 6, read only): "Validate re-checks at render as now. Nothing is loosened." The sha equality IS checked where a verdict enters this build: scorer_verdicts() requires the file's scorer_sha == render_scorer_sha() recomputed at the build's start, or uses nothing. A pin carrying a verdict made under older code can therefore at worst be refused at validate: one pin wasted, never a release authorised on a stale verdict. package_pin is also imported by the integrator's seal check (check_pin_only recomputes seal() only), so it stays free of reads of the render's files. |
| R2 | glm P1-4: scorer_problems tests the first word with SA._words against SA.CONJUNCTIONS / REPLY_FRAGMENTS; a capitalised token ("But") would miss the lower-case lists, so a conjunction opener could seal without a verdict | stand_alone._words lower-cases: it is canon.canon_tokens(text, heads=True), "Lower-case word tokens". Measured on this code: _words("But Bitcoin wins.") -> ['but', 'bitcoin']; _words("Yeah, Bitcoin.") -> ['yeah']. The render's check_edl classifies with the same function and the same lists (stand_alone.py, the render's module copied read only), so the two classifications are one. |

## Recorded (no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: verdict_of checks only the text sha, so it trusts its producer | The only producer is scorer_verdicts(), which keeps a verdict only when "affirmed" equals the render's moments rule (a disagreeing one is dropped). The pin's affirmed_verdict is the strict, independent check at the seal. A hand-made verdict cannot reach a build: build() strips any carried verdict (with_verdict) and attaches only the index's. |
| G2 | glm P1-5: the candidates are computed on copies without verdicts, so an opener admitted this pass is asked about again | By design (reading K3, tested): the set is independent of verdicts, so it stays stable across passes. The integrator reuses a rated text and pays only for new ones. |
| G3 

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1138/C2_STEP.diff (973 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 3e07f37..bd24d36 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -89,11 +89,20 @@ SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE de
   6 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   7 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   8 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
   9 | -TRIM_SCORER_PENDING = True         # ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the
  10 | -                                   # pin stage may not use) must affirm every trimmed segment. RULING 49 (07:02 Nov 13):
  11 | -                                   # YES, a trimmed clip is sealed with that verdict PENDING AT THE RENDER (stage_validate
  12 | -                                   # runs before any render; a refusal there costs no GPU), stated in the sealed row and
  13 | -                                   # per clip in the pin (scorer_pending: true). False: the render's check with no scorer
  14 | +# Ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the pin stage may not use itself) must
  15 | +# affirm every trimmed segment. RULING 49 (07:02 Nov 13) let a trimmed clip be sealed with that verdict pending at the
  16 | +# render, and said "If you can call the same scorer ... do that instead". RULING 56 (09:59): the integrator's pin-stage
  17 | +# service asks that same scorer; "seal only what it affirms". The pending form is retired: a trimmed clip is sealed
  18 | +# only with the scorer's affirmation of its trimmed text, and package_pin refuses scorer_pending. RULING 60 (11:01): for
  19 | +# a moments pin the scorer judges stand-alone only, and the affirmation is the score alone (stand_alone.affirmed with
  20 | +# moments=True), as the render's validate reads it.
  21 | +SCORER_VERDICTS = "/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json"   # ruling 56: the
  22 | +SCORER_KIND = "moments"            # integrator's verdicts (read only); ruling 60: kind "moments", no event
  23 | +RENDER_SCORER_CODE = tuple(f"/home/ultron/protocol_pulse/pipeline/{f}" for f in ("stand_alone.py", "story_semantics.py"))
  24 | +                                   # ^ read only: the render's scorer code; the integrator's scorer_sha is a sha256 over
  25 | +                                   # these two files in this order, so a verdict under other code is not the render's now
  26 | +SCORER_CANDIDATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "audits",
  27 | +                                 "parallel", "pp-selectid_SCORER_CANDIDATES.json")   # ruling 56: what I ask it next
  28 |  TRIMMED_PER_LINEUP_MAX = 1         # ruling 49 (b): at most ONE trimmed clip per line-up until the first trimmed clip has
  29 |                                     # been affirmed at validate once (the integrator says when): one refusal cannot sink a
  30 |                                     # line-up twice. package_pin.TRIMMED_PER_PIN_MAX holds the pin to the same number
  31 | @@ -318,10 +327,10 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  32 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  33 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  34 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  35 | -                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"],
  36 | -                            "scorer_pending": bool(TRIM_SCORER_PENDING)}   # ruling 49 (a): the clip scorer's verdict
  37 | -                           if m.get("trimmed_leading") else {})}   # on the trimmed text is pending at the render
  38 | -                                                                   # (strict: False, which the pin refuses)
  39 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  40 | +                           if m.get("trimmed_leading") else {}),
  41 | +                        **({"scorer_verdict": verdict_of(m)}  # ruling 56: "seal only what it affirms" (the pin
  42 | +                           if (verdict_of(m) or {}).get("affirmed") is True else {})}   # refuses any other)
  43 |                         for lb, m in zip(labels(len(segs)), segs)],
  44 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  45 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  46 | @@ -773,30 +782,32 @@ def check_angles(obj, by_id, k=MAX_ANGLES, hooks=None):
  47 |  def stand_alone_check(segs):
  48 |      """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) on one line-up, at the pin stage
  49 |      (the integrator held pin d2657bbe on it, 03:00 ET Nov 13): the hook, then the clips in play order (clip_01, ...), the
  50 | -    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and NO clip scorer.
  51 | -    The render's scorer is a local model on GPU0, which this stage may not use, so a clip that opens on a conjunction or
  52 | -    a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
  53 | -    check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
  54 | -    scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
  55 | -    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1).
  56 | +    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and as the clip
  57 | +    scorer the verdicts the integrator's pin-stage service gave on each segment's CURRENT text (ruling 56: the render's
  58 | +    own scorer, on GPU0, which this stage may not use itself), read with the render's moments rule (ruling 60:
  59 | +    check_edl(moments=True), the score alone). A clip that opens on a conjunction or a reply fragment, and a trimmed
  60 | +    segment (its lock's marker, as the render sets it), pass only with an affirming verdict and fail closed without one,
  61 | +    as check_edl does. check_edl's verdict reads only each segment's text, the subject and rate (channel and duration
  62 | +    feed only the scorer's passages, which rate answers from the sealed verdicts; the labels come from the order). The
  63 | +    subject is fixed because package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen
  64 | +    P1-1).
  65 |      RULING 34 (the render's side merged at 55315124): the topic test is the miner's about-Bitcoin screen that every
  66 |      moments pin seals (eligibility.BTC_SCREEN, moments_package.btc_screen), and the MEDLEY must name Bitcoin in at
  67 |      least one segment (out["medley_names_bitcoin"], part of out["ok"]): check_edl(..., screen=...), as the render."""
  68 |      import stand_alone as SA
  69 |      def seg(m, extra):
  70 | -        lock = {} if TRIM_SCORER_PENDING or not m.get("trimmed_leading") else \
  71 | +        lock = {} if not m.get("trimmed_leading") else \
  72 |              {"selection_lock": {"trimmed_leading": {"word": m["trimmed_leading"]}}}    # the render's own marker
  73 |          return dict(extra, text=m["text"], channel=m.get("channel_name"), **lock)
  74 | -    edl = {"hook": seg(segs[0], {}),
  75 | +    by_label = dict(zip(labels(len(segs)), segs))
  76 | +
  77 | +    def rate(passages):                      # ruling 56: the render's own clip scorer, as its verdicts on each
  78 | +        return {p["pid"]: (v["score"], v["reason"], v["fault"]) for p in passages     # segment's current text; a
  79 | +                for v in [verdict_of(by_label.get(p["pid"]))] if v}                     # segment without one fails
  80 | +    edl = {"hook": seg(segs[0], {}),                                                    # closed, as check_edl does
  81 |             "clips": [seg(m, {"index": i, "duration": m.get("duration_s")}) for i, m in enumerate(segs[1:], 1)]}
  82 | -    r = SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  83 | -    r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs)
  84 | -                           if m.get("trimmed_leading") and TRIM_SCORER_PENDING]            # ruling 33 (b), item 42
  85 | -    for row in r["rows"]:              # the sealed row STATES the divergence, not only the labels (audit 0530 C2, glm)
  86 | -        if row["segment"] in r["scorer_pending"]:
  87 | -            row["opener"]["why"] += ("; the clip scorer's verdict on the trimmed text is PENDING AT THE RENDER (GPU0; "
  88 | -                                     "ruling 33 part 2)")
  89 | -    return r
  90 | +    return SA.check_edl(edl, rate=rate, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN,
  91 | +                        moments=True)                # ruling 60: a moments pin, as the render's validate reads it
  92 |  
  93 |  
  94 |  def ad_read_out(ms, sources):
  95 | @@ -826,7 +837,8 @@ def trim_variant(m, sources):
  96 |      place under the render's STAND_ALONE as trimmed (no_role_on_screen and no_topic both None on the trimmed text).
  97 |      Then it is judged like any moment: step A on the trimmed span (ruling 33 c), L-v 2 with the trimmed word heard right
  98 |      before the clip (transcript_truth.edges), and the acoustic onset rule on the trimmed cut (ruling 33 a, build()).
  99 | -    The clip scorer's verdict (ruling 33 b) is the render's, on GPU0: pending at the render (stand_alone_check). -> the
 100 | +    The clip scorer's verdict on the trimmed text (ruling 33 b) is the render's own scorer's, given at the pin stage
 101 | +    by the integrator's service (ruling 56): build() keeps the variant only with its affirmation (trim_refused). -> the
 102 |      variant, or None."""
 103 |      import canon
 104 |      try:
 105 | @@ -966,6 +978,132 @@ def reposted_once(ms, sources):
 106 |      return out, dup
 107 |  
 108 |  
 109 | +def render_scorer_sha(paths=RENDER_SCORER_CODE):
 110 | +    """RULING 56: the integrator's scorer_sha recomputed from the render's scorer code as it is NOW (read only): a
 111 | +    sha256 over the files' bytes, in order. None when one cannot be read (then no verdict is used)."""
 112 | +    h = hashlib.sha256()
 113 | +    try:
 114 | +        for p in paths:
 115 | +            with open(p, "rb") as f:
 116 | +                h.update(f.read())
 117 | +    except OSError:
 118 | +        return None
 119 | +    return h.hexdigest()
 120 | +
 121 | +
 122 | +def scorer_verdicts(path, code_sha):
 123 | +    """RULING 56 under RULING 60: the integrator's pin-stage verdicts of the render's own clip scorer (read only). ->
 124 | +    ({pid: verdict}, the record of the read). Fail closed, nothing used: a missing, unreadable or malformed file; a kind
 125 | +    other than "moments"; an event at all (a moments verdict carries "event": null); a scorer_sha other than code_sha
 126 | +    (the render's scorer code now, render_scorer_sha); another threshold than stand_alone.CLIP_MIN_SCORE. A verdict
 127 | +    without a numeric score, with an error, or whose "affirmed" disagrees with the render's own moments rule
 128 | +    (stand_alone.affirmed(score, fault, moments=True): the score alone) is no verdict."""
 129 | +    import stand_alone as SA
 130 | +    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
 131 | +    try:
 132 | +        with open(path) as f:
 133 | +            d = json.load(f)
 134 | +        sc, vs = d["scorer"], d["verdicts"]
 135 | +        why = ("a kind other than 'moments' (ruling 60)" if sc.get("kind") != SCORER_KIND else
 136 | +               "an event (ruling 60: a moments verdict carries none)" if sc.get("event", "absent") is not None else
 137 | +               "the render's scorer code could not be read" if not code_sha else
 138 | +               "a scorer_sha that is not the render's scorer code now" if sc.get("scorer_sha") != code_sha else
 139 | +               "another threshold" if not num(sc.get("threshold")) or sc["threshold"] != SA.CLIP_MIN_SCORE else
 140 | +               "no verdicts" if not isinstance(vs, dict) else None)
 141 | +    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
 142 | +        return {}, {"read": False, "why": f"{type(e).__name__}: {str(e)[:160]}"}
 143 | +    if why:
 144 | +        return {}, {"read": False, "why": why, "kind": sc.get("kind"), "event": sc.get("event"),
 145 | +                    "scorer_sha": sc.get("scorer_sha"), "render_scorer_sha": code_sha, "threshold": sc.get("threshold")}
 146 | +    out, disagree = {}, []
 147 | +    for pid, v in vs.items():
 148 | +        if not (isinstance(v, dict) and isinstance(v.get("text_sha256"), str) and num(v.get("score")) and
 149 | +                not v.get("error")):
 150 | +            continue
 151 | +        rule = SA.affirmed(v["score"], v.get("fault"), moments=True)
 152 | +        if (v.get("affirmed") is True) != rule:
 153 | +            disagree.append(pid)
 154 | +            continue
 155 | +        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"), "affirmed": rule,
 156 | +                         "text_sha256": v["text_sha256"], "prompt_sha256": v.get("prompt_sha256"),
 157 | +                         "model": sc.get("model"), "kind": sc["kind"], "event": None, "rubric": sc.get("rubric"),
 158 | +                         "rule": sc.get("rule"), "scorer_sha": sc["scorer_sha"], "threshold": sc["threshold"],
 159 | +                         "rated_at": d.get("rated_at")}
 160 | +    return out, {"read": True, "rated_at": d.get("rated_at"), "build": d.get("build"),
 161 | +                 "candidates_generated_at": d.get("candidates_generated_at"), "model": sc.get("model"),
 162 | +                 "kind": sc["kind"], "rubric": sc.get("rubric"), "scorer_sha": sc["scorer_sha"],
 163 | +                 "threshold": sc["threshold"], "verdicts": len(out), "affirmed": sum(v["affirmed"] for v in out.values()),
 164 | +                 "disagree_with_the_rule": disagree}
 165 | +
 166 | +
 167 | +def verdict_of(m):
 168 | +    """RULING 56: the clip scorer's verdict attached to a moment when it is for the moment's CURRENT text, else None."""
 169 | +    v = (m or {}).get("scorer_verdict")
 170 | +    return v if isinstance(v, dict) and v.get("text_sha256") == text_sha((m or {}).get("text")) else None
 171 | +
 172 | +
 173 | +def with_verdict(m, index):
 174 | +    """The moment with the scorer's verdict for its id attached when that verdict is for its current text (ruling 56);
 175 | +    any other verdict it carries is dropped (a trimmed variant never inherits its original's)."""
 176 | +    m = {k: x for k, x in m.items() if k != "scorer_verdict"}
 177 | +    v = index.get(m["moment_id"])
 178 | +    return dict(m, scorer_verdict=v) if v and v["text_sha256"] == text_sha(m.get("text")) else m
 179 | +
 180 | +
 181 | +def trim_refused(v):
 182 | +    """RULING 56: why a trimmed variant is left out before any vendor call, else None: no clip-scorer verdict on its
 183 | +    trimmed text, or one that does not affirm it ("seal only what it affirms"; ruling 60: the score alone)."""
 184 | +    s = verdict_of(v)
 185 | +    if s is None:
 186 | +        return (f"{v.get('trimmed_leading')!r} trimmed and no clip-scorer verdict on the trimmed text yet (ruling 56: "
 187 | +                f"sealed only when the scorer affirms it)")
 188 | +    if not s["affirmed"]:
 189 | +        return (f"{v.get('trimmed_leading')!r} trimmed; the clip scorer does not affirm the trimmed text stands alone "
 190 | +                f"({s['score']}, under {s['threshold']})")
 191 | +    return None
 192 | +
 193 | +
 194 | +def write_candidates(path, ms, ctx, build_name):
 195 | +    """RULING 56: the next pass's request in the integrator's contract ({generated_at, build, kind, candidates: [{pid,
 196 | +    video_id, channel, duration, text, text_sha256, trimmed_leading}]}; ruling 60: kind "moments", no event), written
 197 | +    atomically (.tmp, then rename), and only when its set of (pid, text_sha256) differs from the file's: a new
 198 | +    generated_at starts a pass, and rated texts are reused there. -> True when written."""
 199 | +    from datetime import datetime, timezone
 200 | +    cands = [{"pid": m["moment_id"], "video_id": m["video_id"], "channel": _name(m, ctx), "duration": m["duration_s"],
 201 | +              "text": m["text"], "text_sha256": text_sha(m["text"]), "trimmed_leading": m.get("trimmed_leading")}
 202 | +             for m in ms]
 203 | +    try:
 204 | +        with open(path) as f:
 205 | +            old = {(c["pid"], c["text_sha256"]) for c in json.load(f)["candidates"]}
 206 | +    except (OSError, ValueError, KeyError, TypeError):
 207 | +        old = None
 208 | +    if old == {(c["pid"], c["text_sha256"]) for c in cands}:
 209 | +        return False
 210 | +    doc = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "build": build_name,
 211 | +           "kind": SCORER_KIND, "candidates": cands}
 212 | +    with open(path + ".tmp", "w") as f:
 213 | +        json.dump(doc, f, indent=1)
 214 | +    os.replace(path + ".tmp", path)
 215 | +    return True
 216 | +
 217 | +
 218 | +def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
 219 | +    """RULING 56, once per build, before any verdict is attached. (1) The integrator's verdicts (scorer_verdicts, fail
 220 | +    closed). (2) The next pass's candidates (write_candidates): every moment the render's STAND_ALONE leaves out as an
 221 | +    opener the clip scorer would have to affirm (no_role_on_screen fires, the topic rule does not: no verdict could
 222 | +    give a moment that fails the topic rule a place), and the trimmed variant of every moment left out (ruling 33 part
 223 | +    2), each with its text exactly as it would be locked. -> {"index": {pid: verdict}, "record": {...}}."""
 224 | +    index, rec = scorer_verdicts(verdicts_path, render_scorer_sha()) if verdicts_path else \
 225 | +        ({}, {"read": False, "why": "no verdicts file given"})
 226 | +    if candidates_path:
 227 | +        left = [(m, no_role_on_screen(m), no_topic(m)) for m in
 228 | +                ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
 229 | +        ask = [m for m, o, t in left if o and not t] + \
 230 | +            [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
 231 | +        rec = dict(rec, candidates=len(ask), candidates_written=write_candidates(candidates_path, ask, ctx, build_name))
 232 | +    return {"index": index, "record": rec}
 233 | +
 234 | +
 235 |  def no_topic(m):
 236 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
 237 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
 238 | @@ -977,13 +1115,18 @@ def no_topic(m):
 239 |  
 240 |  
 241 |  def no_role_on_screen(m):
 242 | -    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
 243 | -    opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
 244 | -    it), else None. build() leaves such moments out before any vendor call."""
 245 | +    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule (it opens on a conjunction
 246 | +    or a reply fragment: the clip role fails closed without an affirming clip-scorer verdict, the hook role fails on
 247 | +    it), else None. RULING 56: the clip role reads the render's own scorer's verdict on the moment's CURRENT text when
 248 | +    one is attached (verdict_of), by the render's moments rule (ruling 60: the score alone); the hook role never does.
 249 | +    build() leaves such moments out before any vendor call."""
 250 |      import stand_alone as SA
 251 | -    c_ok, c_why = SA.opener("clip", m["text"])          # a moment without text fails fast (audit 0310 C2, qwen)
 252 | +    v = verdict_of(m)
 253 | +    c_ok, c_why = SA.opener("clip", m["text"], v["score"] if v else None, v["fault"] if v else None,
 254 | +                            moments=True)                # a moment without text fails fast (audit 0310 C2, qwen)
 255 |      h_ok, h_why = SA.opener("hook", m["text"])
 256 | -    return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
 257 | +    return None if (c_ok or h_ok) else ("the render's STAND_ALONE " + ("with the clip scorer's verdict" if v else
 258 | +                                        "with no clip scorer at the pin stage") + f": {c_why}; {h_why}")
 259 |  
 260 |  
 261 |  def can_open(m):
 262 | @@ -1599,7 +1742,7 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 263 |  
 264 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 265 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 266 | -          hook_cache=None):
 267 | +          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name=""):
 268 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 269 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 270 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 271 | @@ -1607,6 +1750,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 272 |      work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 273 |      spend: a callable returning the ledger's USD (dollars per package).
 274 |      step_a_cache / hook_cache (rulings 58 / 59): the verdict caches every build shares (None: this build's only).
 275 | +    scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 276 | +    render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 277 |      RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 278 |      own job in one batched call (hook_ratings); only a hook rated >= HOOK_MIN opens; with none, the build stops there
 279 |      ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 280 | @@ -1618,9 +1763,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 281 |      ms, why = usable(moments, ctx, delivered, optout)
 282 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 283 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 284 | +    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name)   # ruling 56
 285 | +    ms = [with_verdict(m, scorer["index"]) for m in ms]
 286 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
 287 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
 288 | -    trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
 289 | +    admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
 290 | +    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms if m["moment_id"] in no_role
 291 | +             for v in [trim_variant(m, sources)] if v}
 292 | +    trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
 293 | +    trims = {k: v for k, v in trims.items() if k not in trim_out}
 294 |      ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
 295 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
 296 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 297 | @@ -1632,6 +1783,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 298 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 299 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 300 |             "reposted": reposted,
 301 | +           "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 302 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 303 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 304 |             "package": None}
 305 | @@ -1640,6 +1792,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 306 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 307 |          f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 308 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 309 | +    sc = out["scorer"]
 310 | +    log(f"  the clip scorer's verdicts (ruling 56, ruling 60): " + (
 311 | +        f"{sc['verdicts']} read, {sc['affirmed']} affirmed (rated {sc['rated_at']}, scorer {str(sc['scorer_sha'])[:12]})"
 312 | +        if sc.get("read") else f"none used ({sc.get('why')})") +
 313 | +        f"; {len(admitted)} opener(s) admitted as clips, {len(trims)} trimmed variant(s) affirmed, {len(trim_out)} left "
 314 | +        f"out without an affirmation" + (f"; candidates {sc['candidates']} ("
 315 | +                                         f"{'written' if sc['candidates_written'] else 'unchanged'})"
 316 | +                                         if "candidates" in sc else ""))
 317 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 318 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 319 |          return out
 320 | @@ -2234,10 +2394,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 321 |                                 lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 322 |             if hook is not None else {}),
 323 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 324 | -                                    "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 325 | +                                    "stage, moments=True: the render's clip scorer's verdicts as the integrator's "
 326 | +                                    "service gave them, stand-alone only, the score alone (rulings 56, 60); without an "
 327 | +                                    "affirming one a conjunction, reply-fragment or trimmed opener fails closed)"),
 328 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 329 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 330 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 331 | -                                scorer_pending=stand.get("scorer_pending") or [])}
 332 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 333 |             if stand is not None else {}),
 334 |      }
 335 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 336 | index dfbb94f..f2e4325 100644
 337 | --- a/pipeline/package_pin.py
 338 | +++ b/pipeline/package_pin.py
 339 | @@ -68,12 +68,15 @@ def recency_problems(segments):
 340 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
 341 |                  "speaker",                                 # the 00:05 ET Nov 13 order, item 3
 342 |                  "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
 343 | -                "scorer_pending")                          # is trimmed, so every other pin seals as before (ruling 49 a)
 344 | +                "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 345 | +                                                           # retired by ruling 56: kept so its pins still recompute)
 346 | +                "scorer_verdict")                          # ruling 56: the clip scorer's affirmation, only when sealed
 347 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 348 |                                                             # separate constant (a test holds them equal): the
 349 |                                                             # integrator's check_pin_only imports this module, which
 350 |                                                             # must never pull package.py into that process
 351 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
 352 | +SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
 353 |  
 354 |  
 355 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 356 | @@ -100,12 +103,45 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 357 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 358 |  
 359 |  
 360 | +def affirmed_verdict(s):
 361 | +    """RULING 56 under RULING 60: True when the segment carries the render's own clip scorer's AFFIRMATION of exactly its
 362 | +    text (approved_text in a pin, text in a package): scorer_verdict with affirmed true, kind "moments" and no event
 363 | +    (the stand-alone judgment), threshold SCORER_MIN and a numeric score at or over it (the score alone,
 364 | +    stand_alone.affirmed(moments=True)), a scorer_sha, and text_sha256 = the sha256 of the text's UTF-8 bytes."""
 365 | +    v = s.get("scorer_verdict")
 366 | +    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
 367 | +    text = s["approved_text"] if "approved_text" in s else s.get("text")
 368 | +    return isinstance(v, dict) and v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and \
 369 | +        v["event"] is None and num(v.get("score")) and v.get("threshold") == SCORER_MIN and v["score"] >= SCORER_MIN \
 370 | +        and bool(v.get("scorer_sha")) and isinstance(text, str) and \
 371 | +        v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
 372 | +
 373 | +
 374 | +def scorer_problems(segments):
 375 | +    """[why] for segments that need the clip scorer and do not carry its affirmation (ruling 56: "seal only what it
 376 | +    affirms"): every clip after the hook whose first word is a conjunction or a reply fragment (the render's
 377 | +    stand_alone.check_edl asks its scorer for exactly these), and any segment carrying a scorer_verdict that is not an
 378 | +    affirmation of exactly its text. A trimmed clip's affirmation is trim_problems'."""
 379 | +    import stand_alone as SA
 380 | +    out = []
 381 | +    for i, s in enumerate(segments):
 382 | +        text = s["approved_text"] if "approved_text" in s else s.get("text")
 383 | +        w = SA._words(text)[:1]
 384 | +        needs = i > 0 and bool(w) and (w[0] in SA.CONJUNCTIONS or w[0] in SA.REPLY_FRAGMENTS)
 385 | +        if needs and not affirmed_verdict(s):
 386 | +            out.append(f"segment {i}: opens on {w[0]!r}: the clip scorer's affirmation of its text must be sealed "
 387 | +                       f"(ruling 56)")
 388 | +        elif "scorer_verdict" in s and not affirmed_verdict(s):
 389 | +            out.append(f"segment {i}: carries a clip-scorer verdict that does not affirm exactly its text (ruling 56)")
 390 | +    return out
 391 | +
 392 | +
 393 |  def trim_problems(segments):
 394 |      """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
 395 |      refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
 396 | -    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49: (a) every trimmed clip says
 397 | -    scorer_pending: true (the clip scorer's verdict is pending at the render) and no other clip carries the key;
 398 | -    (b) at most TRIMMED_PER_PIN_MAX trimmed clips."""
 399 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49 (b): at most TRIMMED_PER_PIN_MAX
 400 | +    trimmed clips. RULING 56 ("seal only what it affirms", retiring 49 a's pending form): every trimmed clip carries
 401 | +    the clip scorer's affirmation of its trimmed text (affirmed_verdict), and no segment carries scorer_pending."""
 402 |      import canon
 403 |      out = []
 404 |      n = sum("trimmed_leading" in s or "untrimmed_start" in s for s in segments)
 405 | @@ -114,13 +150,14 @@ def trim_problems(segments):
 406 |                     f"(ruling 49 b)")
 407 |      for i, s in enumerate(segments):
 408 |          has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
 409 | +        if "scorer_pending" in s:
 410 | +            out.append(f"segment {i}: scorer_pending is no longer sealed (ruling 56: seal only what the scorer "
 411 | +                       f"affirms)")
 412 |          if not has_w and not has_s:
 413 | -            if "scorer_pending" in s:
 414 | -                out.append(f"segment {i}: scorer_pending belongs to a trimmed clip only (ruling 49 a)")
 415 |              continue
 416 | -        if s.get("scorer_pending") is not True:
 417 | -            out.append(f"segment {i}: a trimmed clip must say scorer_pending: true (ruling 49 a: the clip scorer's "
 418 | -                       f"verdict on the trimmed text is pending at the render)")
 419 | +        if not affirmed_verdict(s):
 420 | +            out.append(f"segment {i}: a trimmed clip must carry the clip scorer's affirmation of its trimmed text "
 421 | +                       f"(ruling 56)")
 422 |          if has_w != has_s:
 423 |              out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 424 |              continue
 425 | @@ -231,7 +268,7 @@ def to_pin(pk, run_name):
 426 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 427 |                                                                       for x in line_problems(pk)] + \
 428 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 429 | -        screen_problems(pk) + trim_problems(pk.get("segments") or [])
 430 | +        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or [])
 431 |      if problems:
 432 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 433 |      segs = []
 434 | @@ -241,7 +278,7 @@ def to_pin(pk, run_name):
 435 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 436 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 437 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 438 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_pending") if k in s},
 439 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict") if k in s},
 440 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 441 |      edl_vo = {"intro": pk["vo"]["intro"],
 442 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 443 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 444 | index 76bb890..a8b2f45 100644
 445 | --- a/pipeline/stand_alone.py
 446 | +++ b/pipeline/stand_alone.py
 447 | @@ -37,7 +37,41 @@ def _words(text):
 448 |      return canon.canon_tokens(text, heads=True)
 449 |  
 450 |  
 451 | -def opener(kind, text, score=None, fault=None):
 452 | +def affirmed(score, fault, moments=False):
 453 | +    """The clip scorer's affirmation, the ONE threshold: opener, trimmed_opener and the pin-stage scorer
 454 | +    (stand_alone_scorer.py, order '09:58' item 56) all read it here. The story path: score >= CLIP_MIN_SCORE and no
 455 | +    starts_mid_thought fault. A MOMENTS pin (ruling 60, '11:01': "bar 3.5, no fixed score for an opener word: the
 456 | +    model judges the clip as spoken"): the score alone. Measured 2026-11-13: the model labels an opening "I mean" /
 457 | +    "However" starts_mid_thought while scoring the clip 4 ("understood alone"), and every REFERENT_OUTSIDE clip it
 458 | +    refuses scores <= 3, so the label added only an opener penalty."""
 459 | +    if moments:
 460 | +        return score is not None and score >= CLIP_MIN_SCORE
 461 | +    return score is not None and score >= CLIP_MIN_SCORE and fault != "starts_mid_thought"
 462 | +
 463 | +
 464 | +def clip_scorer(event, llm=None, moments=False):
 465 | +    """The clip scorer stage_validate asks: rate(passages) -> {pid: (score, reason, fault)} on the GPU0 LocalLLM
 466 | +    (gemma3:27b, temperature 0). The story path: story_semantics.rate_passages with {"underlying_event": event}. A
 467 | +    MOMENTS pin (ruling 60): story_semantics.rate_alone, stand-alone only, no event. ONE code path for the render's
 468 | +    validate and the pin-stage scorer (order '09:58' item 56). Without `llm` it starts the model and stops it after
 469 | +    the call (validate's way); with one, the caller owns its life. An unparseable reply raises (never invented)."""
 470 | +    def rate(passages):
 471 | +        import story_semantics as sm
 472 | +        own = llm is None
 473 | +        m = sm.LocalLLM().start() if own else llm
 474 | +        try:
 475 | +            ratings, err = sm.rate_alone(m, passages) if moments else \
 476 | +                sm.rate_passages(m, {"underlying_event": event}, passages)
 477 | +        finally:
 478 | +            if own:
 479 | +                m.stop()
 480 | +        if err:
 481 | +            raise RuntimeError(f"clip scorer reply unparseable: {err}")
 482 | +        return ratings
 483 | +    return rate
 484 | +
 485 | +
 486 | +def opener(kind, text, score=None, fault=None, moments=False):
 487 |      """(ok, reason) for the first word of a hook or a clip."""
 488 |      ws = _words(text)
 489 |      if not ws:
 490 | @@ -51,7 +85,7 @@ def opener(kind, text, score=None, fault=None):
 491 |      if w in CONJUNCTIONS or w in REPLY_FRAGMENTS:
 492 |          if score is None:
 493 |              return False, f"clip opens on {w!r} and no clip-scorer verdict is available (fail closed)"
 494 | -        if score >= CLIP_MIN_SCORE and fault != "starts_mid_thought":
 495 | +        if affirmed(score, fault, moments):
 496 |              return True, f"clip opens on {w!r}; the clip scorer affirms it stands alone ({score}, fault {fault})"
 497 |          return False, f"clip opens on {w!r}; the clip scorer does not affirm it stands alone ({score}, fault {fault})"
 498 |      return True, f"opens on {w!r}"
 499 | @@ -118,23 +152,24 @@ def trimmed_word(seg):
 500 |      return str(t.get("word") or "?") if isinstance(t, dict) else None
 501 |  
 502 |  
 503 | -def trimmed_opener(word, score, fault):
 504 | +def trimmed_opener(word, score, fault, moments=False):
 505 |      """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a segment locked with ONE leading word trimmed passes only
 506 |      when the clip scorer affirms the TRIMMED text stands alone at the unchanged threshold, whatever its first word."""
 507 |      if score is None:
 508 |          return False, f"{word!r} trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)"
 509 | -    if score >= CLIP_MIN_SCORE and fault != "starts_mid_thought":
 510 | +    if affirmed(score, fault, moments):
 511 |          return True, f"{word!r} trimmed; the clip scorer affirms the trimmed text stands alone ({score}, fault {fault})"
 512 |      return False, f"{word!r} trimmed; the clip scorer does not affirm the trimmed text stands alone ({score}, fault {fault})"
 513 |  
 514 |  
 515 | -def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 516 | +def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None, moments=False):
 517 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 518 |      clips opening on a conjunction / reply fragment (the clip scorer) and for every segment whose lock trims a leading
 519 |      word (ruling 33 part 2, the hook included); without it they fail closed.
 520 |      screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 521 |      and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 522 | -    speaker's own words. screen None: every segment names the subject, as before (the story path)."""
 523 | +    speaker's own words. screen None: every segment names the subject, as before (the story path).
 524 | +    moments (ruling 60, a moments pin): the scorer's verdict is read with affirmed(..., moments=True), the score alone."""
 525 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 526 |      need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
 527 |              and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))]
 528 | @@ -149,9 +184,9 @@ def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 529 |      for label, kind, s in segs:
 530 |          sc = scores.get(label)
 531 |          score, fault = (sc[0], sc[2]) if sc else (None, None)
 532 | -        o_ok, o_why = opener(kind, s.get("text"), score, fault)
 533 | +        o_ok, o_why = opener(kind, s.get("text"), score, fault, moments)
 534 |          if o_ok and trimmed_word(s):                                   # ruling 33 part 2
 535 | -            o_ok, o_why = trimmed_opener(trimmed_word(s), score, fault)
 536 | +            o_ok, o_why = trimmed_opener(trimmed_word(s), score, fault, moments)
 537 |          t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
 538 |              topical(kind, s.get("text"), prev, subject)
 539 |          rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
 540 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 541 | index 6aa7ba2..3310302 100644
 542 | --- a/tests/package/proof_ledger.py
 543 | +++ b/tests/package/proof_ledger.py
 544 | @@ -136,7 +136,9 @@ def main(argv=None):
 545 |                     work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 546 |                     spend=lambda: (own["est"], own["best"]),
 547 |                     step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 548 | -                   hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"))          # ruling 59 (a): cached
 549 | +                   hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 550 | +                   scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 551 | +                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 552 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 553 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 554 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 555 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 556 | index b8e5231..4b5f5f7 100644
 557 | --- a/tests/package/test_medley.py
 558 | +++ b/tests/package/test_medley.py
 559 | @@ -70,6 +70,21 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
 560 |  
 561 |  
 562 |  
 563 | +def sv(text, score, fault="none"):
 564 | +    """A clip-scorer verdict on exactly `text` as build() attaches it (package.scorer_verdicts' shape, ruling 56; ruling
 565 | +    60: kind "moments", no event, the affirmation is the score alone)."""
 566 | +    return {"score": score, "reason": "r", "fault": fault, "affirmed": score >= 3.5, "text_sha256": PK.text_sha(text),
 567 | +            "prompt_sha256": "p" * 64, "model": "gemma3:27b", "kind": "moments", "event": None,
 568 | +            "rubric": "ruling 60: stand-alone only", "rule": "stand_alone.affirmed(moments=True): score >= threshold",
 569 | +            "scorer_sha": "s" * 64, "threshold": 3.5, "rated_at": "2026-11-13T15:35:10Z"}
 570 | +
 571 | +
 572 | +def fv(text, score, fault="none"):
 573 | +    """One verdict as the integrator's verdicts file holds it (their contract, ruling 56), on exactly `text`."""
 574 | +    return {"text_sha256": PK.text_sha(text), "score": score, "reason": "r", "fault": fault,
 575 | +            "affirmed": score >= 3.5, "prompt_sha256": "p" * 64}            # ruling 60: the score alone
 576 | +
 577 | +
 578 |  def spk(pk):
 579 |      """speakers.attribute's record on every segment, as the real flow attaches it before the pin is sealed (the
 580 |      00:05 ET Nov 13 order, item 3): an unknown speaker, measured, no person named."""
 581 | @@ -505,12 +520,13 @@ class Rig:
 582 |  
 583 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 584 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 585 | -                 trim_fail=(), hooks=None, hook_err=None):
 586 | +                 trim_fail=(), hooks=None, hook_err=None, verdicts=None):
 587 |          import providers as P
 588 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 589 |          self.takeaways, self.spend = list(takeaways or []), spend
 590 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 591 |          self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
 592 | +        self.verdicts = verdicts                           # ruling 56: {pid: verdict} in the integrator's file shape
 593 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 594 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 595 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 596 | @@ -623,15 +639,28 @@ class Rig:
 597 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 598 |                                                               "replayed": False}),
 599 |          }
 600 | +        kw, path = {}, None
 601 | +        if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 602 | +            import tempfile
 603 | +            fd, path = tempfile.mkstemp(suffix=".json")
 604 | +            with os.fdopen(fd, "w") as f:
 605 | +                json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "test", "scorer": {
 606 | +                    "model": "gemma3:27b", "kind": "moments", "threshold": 3.5, "event": None,
 607 | +                    "scorer_sha": "s" * 64},
 608 | +                    "verdicts": self.verdicts}, f)
 609 | +            kw["scorer_verdicts_path"] = path
 610 | +            stubs["render_scorer_sha"] = lambda *a, **k: "s" * 64       # the render's scorer code, as it is now
 611 |          saved = {k: getattr(PK, k) for k in stubs}
 612 |          try:
 613 |              for k, v in stubs.items():
 614 |                  setattr(PK, k, v)
 615 |              return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
 616 | -                            spend=self.spend)
 617 | +                            spend=self.spend, **kw)
 618 |          finally:
 619 |              for k, v in saved.items():
 620 |                  setattr(PK, k, v)
 621 | +            if path:
 622 | +                os.remove(path)
 623 |  
 624 |  
 625 |  class TestBuildLoop(unittest.TestCase):
 626 | @@ -881,7 +910,8 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 627 |      """Ruling 33 part 2 (render merged 11e361cc), used per the 04:58 order's item 42: a moment opening on ONE of
 628 |      but/and/so/well/now/yeah, left out by the render's STAND_ALONE opener rule, may be cut one word in. The variant is
 629 |      judged like any moment (step A, L-v 2 with the trimmed word heard, the acoustic onset rule at the trimmed cut); the
 630 | -    clip scorer's verdict is pending at the render; the pin seals trimmed_leading and untrimmed_start."""
 631 | +    clip scorer must affirm the trimmed text (ruling 56: the integrator's pin-stage verdicts; ruling 49 a's pending form
 632 | +    is retired); the pin seals trimmed_leading, untrimmed_start and the affirmation."""
 633 |  
 634 |      def moment(self, sentence, mid="t"):
 635 |          src = source([sentence], vid="vT")
 636 | @@ -913,24 +943,27 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 637 |          m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
 638 |          self.assertIsNone(PK.trim_variant(m, srcs))
 639 |  
 640 | -    def test_pending_at_the_render_by_ruling_49_and_strict_on_the_switch(self):
 641 | +    def test_ruling_56_a_trimmed_clip_passes_only_with_the_scorers_affirmation(self):
 642 |          m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 643 |          v = PK.trim_variant(m, srcs)
 644 | -        line = [{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}]
 645 | -        self.assertTrue(PK.TRIM_SCORER_PENDING)                       # ruling 49 (07:02): YES
 646 | -        r = PK.stand_alone_check(line)
 647 | -        self.assertTrue(r["ok"], r["rows"])
 648 | -        self.assertEqual(r["scorer_pending"], ["clip_01"])
 649 | -        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 650 | -        saved = PK.TRIM_SCORER_PENDING
 651 | -        try:                                                          # the strict switch: the render's check with
 652 | -            PK.TRIM_SCORER_PENDING = False                            # no scorer fails closed, never sealed
 653 | -            r = PK.stand_alone_check(line)
 654 | -        finally:
 655 | -            PK.TRIM_SCORER_PENDING = saved
 656 | +        hook, last = {"text": "Bitcoin is the hardest money ever made."}, {"text": "Bitcoin wins."}
 657 | +        self.assertFalse(hasattr(PK, "TRIM_SCORER_PENDING"))          # ruling 49 (a)'s pending form is retired
 658 | +        r = PK.stand_alone_check([hook, v, last])                     # no verdict: fails closed, as at validate
 659 |          self.assertFalse(r["ok"])
 660 |          self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 661 | -        self.assertEqual(r["scorer_pending"], [])
 662 | +        self.assertNotIn("scorer_pending", r)
 663 | +        r = PK.stand_alone_check([hook, dict(v, scorer_verdict=sv(v["text"], 4.0)), last])
 664 | +        self.assertTrue(r["ok"], r["rows"])
 665 | +        self.assertIn("the clip scorer affirms the trimmed text", r["rows"][1]["opener"]["why"])
 666 | +        self.assertEqual(r["rows"][1]["scorer"]["score"], 4.0)        # the verdict used is in the sealed row
 667 | +        for bad in (sv(v["text"], 3.0, "ends_mid_thought"), sv(v["text"], 3.4),
 668 | +                    sv(m["text"], 4.0)):                              # the untrimmed text's verdict is not its own
 669 | +            self.assertFalse(PK.stand_alone_check([hook, dict(v, scorer_verdict=bad), last])["ok"], bad)
 670 | +        self.assertTrue(PK.stand_alone_check([hook, dict(v, scorer_verdict=sv(v["text"], 4.0, "starts_mid_thought")),
 671 | +                                              last])["ok"])           # ruling 60: the score alone, as validate
 672 | +        self.assertIn("no clip-scorer verdict on the trimmed text yet", PK.trim_refused(v))
 673 | +        self.assertIsNone(PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 4.0))))
 674 | +        self.assertIn("does not affirm", PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 3.0, "other"))))
 675 |  
 676 |      def test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin(self):
 677 |          self.assertEqual(PK.TRIMMED_PER_LINEUP_MAX, package_pin.TRIMMED_PER_PIN_MAX)
 678 | @@ -946,10 +979,12 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 679 |                 {"trimmed_leading": "So", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True}]
 680 |          self.assertIn("2 trimmed clips", package_pin.trim_problems(two)[0])
 681 |  
 682 | -    def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 683 | +    def test_the_pin_seals_the_trim_with_its_affirmation_and_refuses_a_malformed_one(self):
 684 | +        import copy
 685 | +        x_text = "Bitcoin keeps every promise it ever made to me."
 686 |          segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 687 | -                dict(pm("x", "B", 14.0), text="Bitcoin keeps every promise it ever made to me.",
 688 | -                     trimmed_leading="But", untrimmed_start=0.0, start=0.3),
 689 | +                dict(pm("x", "B", 14.0), text=x_text, trimmed_leading="But", untrimmed_start=0.0, start=0.3,
 690 | +                     scorer_verdict=sv(x_text, 4.0)),
 691 |                  dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
 692 |          by = {m["moment_id"]: m for m in segs}
 693 |          fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 694 | @@ -958,32 +993,42 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 695 |          pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 696 |          self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
 697 |          pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 698 | -        pin = package_pin.to_pin(spk(pk), "test")
 699 | +        pin = package_pin.to_pin(copy.deepcopy(spk(pk)), "test")
 700 |          s1 = pin["segments"][1]
 701 | -        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"], s1["scorer_pending"]), ("But", 0.0, True))
 702 | -        self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 703 | -        self.assertNotIn("scorer_pending", pin["segments"][0])                    # ruling 49 (a): per trimmed clip
 704 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 705 | +        self.assertTrue(package_pin.affirmed_verdict(s1))                         # ruling 56: sealed, on its text
 706 | +        self.assertNotIn("scorer_pending", s1)
 707 | +        for k in ("trimmed_leading", "scorer_verdict", "scorer_pending"):         # untrimmed segments: unchanged
 708 | +            self.assertNotIn(k, pin["segments"][0])
 709 |          mp = pin["moments_package"]
 710 |          args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 711 |          self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 712 | -        other = [dict(x) for x in pin["segments"]]
 713 | +        other = copy.deepcopy(pin["segments"])
 714 |          other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 715 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 716 | -        other[1]["trimmed_leading"], other[1]["scorer_pending"] = "But", False      # and so is scorer_pending
 717 | +        other = copy.deepcopy(pin["segments"])
 718 | +        other[1]["scorer_verdict"]["score"] = 5.0                                 # and so is the affirmation
 719 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 720 |          for bad in ({"trimmed_leading": "Because"}, {"trimmed_leading": "But so"}, {"trimmed_leading": "and/or"},
 721 |                      {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
 722 | -                    {"scorer_pending": False}):                                       # ruling 49 (a) in plain words
 723 | -            p = spk(pk)
 724 | +                    {"scorer_pending": True},                                     # ruling 56: never sealed
 725 | +                    {"scorer_verdict": sv(x_text, 3.0, "ends_mid_thought")},      # a refusal
 726 | +                    {"scorer_verdict": sv("But " + x_text, 4.0)},                 # another text's verdict
 727 | +                    {"scorer_verdict": dict(sv(x_text, 4.0), kind="story")}):     # not the moments judgment
 728 | +            p = copy.deepcopy(spk(pk))                                            # each case on its own
 729 |              p["segments"][1] = dict(p["segments"][1], **bad)
 730 | -            with self.assertRaises(package_pin.PinRefused):
 731 | +            with self.assertRaises(package_pin.PinRefused, msg=str(bad)):
 732 |                  package_pin.to_pin(p, "test")
 733 | -        p = spk(pk)
 734 | -        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # only on a trimmed clip
 735 | +        p = copy.deepcopy(spk(pk))
 736 | +        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "scorer_verdict"}   # no affirmation
 737 | +        with self.assertRaises(package_pin.PinRefused):
 738 | +            package_pin.to_pin(p, "test")
 739 | +        p = copy.deepcopy(spk(pk))
 740 | +        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # not on any segment
 741 |          with self.assertRaises(package_pin.PinRefused):
 742 |              package_pin.to_pin(p, "test")
 743 |          self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
 744 | -        p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
 745 | +        p = copy.deepcopy(spk(pk))                                        # ^ refused, never raised (glm P0-8)
 746 |          p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 747 |          with self.assertRaises(package_pin.PinRefused):                          # both keys or neither
 748 |              package_pin.to_pin(p, "test")
 749 | @@ -995,9 +1040,10 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 750 |          saved = PK.trim_variant
 751 |          try:
 752 |              PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 753 | -            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"})
 754 | +            ok = {"b~trim": fv("Bitcoin x.", 4.0)}                  # ruling 56: the scorer affirms the trimmed text
 755 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"}, verdicts=ok)
 756 |              out = rig.run()
 757 | -            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 758 | +            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"}, verdicts=ok)
 759 |              out2 = rig2.run()
 760 |          finally:
 761 |              PK.trim_variant = saved
 762 | @@ -1238,6 +1284,210 @@ class TestRuling59HookFirst(unittest.TestCase):
 763 |          self.assertEqual(rig.medley_calls, [])
 764 |  
 765 |  
 766 | +class TestRuling56Scorer(unittest.TestCase):
 767 | +    """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 768 | +    about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
 769 | +    sealed. Their verdicts file is read only and fail closed."""
 770 | +
 771 | +    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."
 772 | +
 773 | +    def file(self, verdicts=None, drop=(), **scorer):
 774 | +        import tempfile
 775 | +        fd, path = tempfile.mkstemp(suffix=".json")
 776 | +        sc = {k: x for k, x in dict({"model": "gemma3:27b", "kind": "moments", "rubric": "ruling 60: stand-alone only",
 777 | +                                     "threshold": 3.5, "event": None, "scorer_sha": "s" * 64}, **scorer).items()
 778 | +              if k not in drop}
 779 | +        with os.fdopen(fd, "w") as f:
 780 | +            json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "b", "candidates_generated_at": "g",
 781 | +                       "scorer": sc, "verdicts": verdicts or {}}, f)
 782 | +        self.addCleanup(os.remove, path)
 783 | +        return path
 784 | +
 785 | +    def test_the_verdicts_file_is_used_only_when_every_check_holds(self):
 786 | +        good = {"a": fv(self.OPENER, 4.0), "b": fv("Bitcoin b.", 3.0, "ends_mid_thought")}
 787 | +        idx, rec = PK.scorer_verdicts(self.file(good), "s" * 64)
 788 | +        self.assertEqual(sorted(idx), ["a", "b"])
 789 | +        self.assertEqual((rec["read"], rec["verdicts"], rec["affirmed"]), (True, 2, 1))
 790 | +        self.assertEqual((idx["a"]["affirmed"], idx["b"]["affirmed"]), (True, False))
 791 | +        self.assertEqual((idx["a"]["kind"], idx["a"]["event"], idx["a"]["scorer_sha"], idx["a"]["threshold"]),
 792 | +                         ("moments", None, "s" * 64, 3.5))
 793 | +        for scorer, code, why in (({"kind": "story"}, "s" * 64, "a kind other than 'moments' (ruling 60)"),
 794 | +                                  ({"event": "Pinned: bitcoin"}, "s" * 64,
 795 | +                                   "an event (ruling 60: a moments verdict carries none)"),
 796 | +                                  ({}, "t" * 64, "a scorer_sha that is not the render's scorer code now"),
 797 | +                                  ({}, None, "the render's scorer code could not be read"),
 798 | +                                  ({"threshold": 3.0}, "s" * 64, "another threshold"),
 799 | +                                  ({"threshold": True}, "s" * 64, "another threshold")):
 800 | +            idx, rec = PK.scorer_verdicts(self.file(good, **scorer), code)
 801 | +            self.assertEqual((idx, rec["read"], rec["why"]), ({}, False, why))
 802 | +        idx, rec = PK.scorer_verdicts(self.file(good, drop=("event",)), "s" * 64)   # "event": null, never absent
 803 | +        self.assertEqual((idx, rec["why"]), ({}, "an event (ruling 60: a moments verdict carries none)"))
 804 | +        idx, rec = PK.scorer_verdicts(self.file({"f": fv("x", 4.0, "starts_mid_thought")}), "s" * 64)
 805 | +        self.assertTrue(idx["f"]["affirmed"])                           # ruling 60: the score alone
 806 | +        idx, rec = PK.scorer_verdicts("/nonexistent/latest.json", "s" * 64)
 807 | +        self.assertEqual((idx, rec["read"]), ({}, False))
 808 | +        bad = self.file()
 809 | +        with open(bad, "w") as f:
 810 | +            f.write("{not json")
 811 | +        self.assertEqual(PK.scorer_verdicts(bad, "s" * 64)[0], {})
 812 | +        odd = {"e": dict(fv("x", 4.0), error="not rated"), "n": dict(fv("x", 4.0), score=None),
 813 | +               "t": dict(fv("x", 4.0), score=True), "d": dict(fv("x", 3.0), affirmed=True),
 814 | +               "s": dict(fv("x", 4.0), text_sha256=None)}
 815 | +        idx, rec = PK.scorer_verdicts(self.file(odd), "s" * 64)
 816 | +        self.assertEqual(idx, {})                                       # none of them is a verdict
 817 | +        self.assertEqual(rec["disagree_with_the_rule"], ["d"])          # "affirmed" against the render's own rule
 818 | +
 819 | +    def test_the_scorer_sha_is_recomputed_from_the_renders_code(self):
 820 | +        import hashlib
 821 | +        import tempfile
 822 | +        self.assertEqual(PK.RENDER_SCORER_CODE, ("/home/ultron/protocol_pulse/pipeline/stand_alone.py",
 823 | +                                                 "/home/ultron/protocol_pulse/pipeline/story_semantics.py"))
 824 | +        with tempfile.TemporaryDirectory() as d:
 825 | +            a, b = os.path.join(d, "a.py"), os.path.join(d, "b.py")
 826 | +            for path, data in ((a, b"one"), (b, b"two")):
 827 | +                with open(path, "wb") as f:
 828 | +                    f.write(data)
 829 | +            self.assertEqual(PK.render_scorer_sha((a, b)), hashlib.sha256(b"onetwo").hexdigest())
 830 | +            self.assertIsNone(PK.render_scorer_sha((a, os.path.join(d, "missing.py"))))
 831 | +
 832 | +    def test_a_verdict_attaches_only_to_its_own_text(self):
 833 | +        m = dict(pm("a", "A", 12.0), text=self.OPENER)
 834 | +        got = PK.with_verdict(m, {"a": sv(self.OPENER, 4.0)})
 835 | +        self.assertIs(PK.verdict_of(got), got["scorer_verdict"])
 836 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"a": sv("Another text.", 4.0)}))
 837 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"b": sv(self.OPENER, 4.0)}))
 838 | +        trimmed = dict(got, moment_id="a~trim", text=self.OPENER[len("And "):])   # carries the key, not the verdict
 839 | +        self.assertIsNone(PK.verdict_of(trimmed))
 840 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(trimmed, {"a": sv(self.OPENER, 4.0)}))
 841 | +
 842 | +    def test_an_affirmed_opener_plays_as_a_clip_never_as_the_hook(self):
 843 | +        m = dict(pm("a", "A", 12.0), text=self.OPENER, hook_onset={"pass": True})
 844 | +        self.assertIn("with no clip scorer", PK.no_role_on_screen(m))
 845 | +        ok = dict(m, scorer_verdict=sv(self.OPENER, 4.0))
 846 | +        self.assertIsNone(PK.no_role_on_screen(ok))
 847 | +        why = PK.no_role_on_screen(dict(m, scorer_verdict=sv(self.OPENER, 3.0, "ends_mid_thought")))
 848 | +        self.assertIn("with the clip scorer's verdict", why)
 849 | +        self.assertIn("does not affirm", why)
 850 | +        self.assertIsNone(PK.no_role_on_screen(dict(m, scorer_verdict=sv(self.OPENER, 4.0, "starts_mid_thought"))))
 851 | +        self.assertTrue(ok["eligibility"]["hook"]["ok"])               # hook-eligible (L-o: a conjunction is a target)
 852 | +        self.assertEqual(PK.placement(ok), " | cannot open (never the hook)")   # but the render's hook rule refuses
 853 | +        self.assertEqual(PK.placement(dict(ok, duration_s=6.0)), " | under 8 s: only the LAST clip")
 854 | +        hook, x = dict(pm("h", "B", 12.0), hook_onset={"pass": True}), dict(pm("x", "C", 13.0), hook_onset={"pass": True})
 855 | +        r = PK.stand_alone_check([hook, ok, x])
 856 | +        self.assertTrue(r["ok"], r["rows"])
 857 | +        self.assertIn("the clip scorer affirms it stands alone", r["rows"][1]["opener"]["why"])
 858 | +        self.assertFalse(PK.stand_alone_check([ok, hook, x])["ok"])    # never the hook
 859 | +        by = {y["moment_id"]: y for y in (ok, hook, x, dict(pm("y", "D", 13.0), hook_onset={"pass": True}))}
 860 | +        segs = PK.lineup_for(angle(["a", "h", "x", "y"], "a"), by, need_onset=True, need_stand_alone=True)
 861 | +        self.assertNotEqual(segs[0]["moment_id"], "a")                  # the proposer's hook gives way ...
 862 | +        self.assertIn("a", [y["moment_id"] for y in segs])             # ... and it plays as a clip
 863 | +
 864 | +    def test_the_build_admits_only_what_the_scorer_affirms(self):
 865 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), dict(pm("b", "E", 13.0), text=self.OPENER)]
 866 | +        rig = Rig(ms, ["h", "b", "x", "y"], [(True, [], None, Rig.LINE)], [None], verdicts={"b": fv(self.OPENER, 4.0)})
 867 | +        out = rig.run()
 868 | +        self.assertNotIn("b", out["no_role"])
 869 | +        self.assertEqual((out["scorer"]["read"], out["scorer"]["admitted"]), (True, ["b"]))
 870 | +        self.assertIn("id=b | E | 13.0 s | cannot open (never the hook) | ",
 871 | +                      next(p for r, p in rig.prompts if r == "angle_write"))
 872 | +        seg = next(s for s in out["package"]["segments"] if s["moment_id"] == "b")      # it plays, as a clip,
 873 | +        self.assertTrue(package_pin.affirmed_verdict(seg))                                # its affirmation sealed
 874 | +        self.assertNotEqual(out["package"]["segments"][0]["moment_id"], "b")
 875 | +        refused = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None],
 876 | +                      verdicts={"b": fv(self.OPENER, 3.0, "ends_mid_thought")}).run()
 877 | +        self.assertIn("with the clip scorer's verdict", refused["no_role"]["b"])
 878 | +        self.assertEqual(refused["scorer"]["admitted"], [])
 879 | +        none = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None]).run()     # no verdicts: as before 56
 880 | +        self.assertIn("with no clip scorer", none["no_role"]["b"])
 881 | +        self.assertEqual(none["scorer"]["why"], "no verdicts file given")
 882 | +
 883 | +    def test_a_trimmed_variant_needs_the_affirmation_before_any_vendor_call(self):
 884 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 885 | +              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
 886 | +        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
 887 | +        saved, outs = PK.trim_variant, {}
 888 | +        try:
 889 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 890 | +            for k, vs in (("none", None), ("refused", {"b~trim": fv("Bitcoin x.", 3.0, "ends_mid_thought")}),
 891 | +                          ("affirmed", {"b~trim": fv("Bitcoin x.", 4.0)})):
 892 | +                rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=vs)
 893 | +                outs[k] = (rig, rig.run())
 894 | +        finally:
 895 | +            PK.trim_variant = saved
 896 | +        for k in ("none", "refused"):
 897 | +            rig, out = outs[k]
 898 | +            self.assertEqual(out["trimmed"], {}, k)
 899 | +            self.assertFalse(any("b~trim" in ids for _, ids in rig.screens), k)     # never sent to step A
 900 | +        self.assertIn("no clip-scorer verdict on the trimmed text yet", outs["none"][1]["scorer"]["trims_out"]["b"])
 901 | +        self.assertIn("does not affirm", outs["refused"][1]["scorer"]["trims_out"]["b"])
 902 | +        rig, out = outs["affirmed"]
 903 | +        self.assertEqual((out["trimmed"], out["scorer"]["trims_affirmed"]), ({"b": "b~trim"}, ["b"]))
 904 | +        self.assertTrue(any("b~trim" in ids for _, ids in rig.screens))
 905 | +
 906 | +    def test_the_candidates_file_asks_about_every_opener_left_out_and_changes_only_with_its_set(self):
 907 | +        import tempfile
 908 | +        but, srcs = TestRuling33TrimAtThePinStage().moment(
 909 | +            "But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 910 | +        opener = dict(pm("o", "B", 12.0), text=self.OPENER)
 911 | +        gold = dict(pm("g", "C", 12.0), text="And gold is the hardest money ever made, which is why it wins.")
 912 | +        plain = pm("p", "D", 12.0)
 913 | +        with tempfile.TemporaryDirectory() as d:
 914 | +            path = os.path.join(d, "candidates.json")
 915 | +
 916 | +            def load():
 917 | +                with open(path) as f:
 918 | +                    return json.load(f)
 919 | +            r = PK.scorer_pass([but, opener, gold, plain], srcs, ctx(), None, path, "ledger_test")
 920 | +            self.assertEqual((r["index"], r["record"]["read"], r["record"]["candidates_written"]), ({}, False, True))
 921 | +            doc = load()
 922 | +            self.assertEqual((doc["build"], doc["kind"]), ("ledger_test", "moments"))   # ruling 60: no event
 923 | +            got = {c["pid"]: c for c in doc["candidates"]}
 924 | +            self.assertEqual(sorted(got), ["o", "t", "t~trim"])           # gold fails the topic rule: never asked
 925 | +            for pid, c in got.items():
 926 | +                self.assertEqual(c["text_sha256"], PK.text_sha(c["text"]), pid)
 927 | +                self.assertEqual(set(c), {"pid", "video_id", "channel", "duration", "text", "text_sha256",
 928 | +                                          "trimmed_leading"})
 929 | +            self.assertEqual((got["t~trim"]["trimmed_leading"], got["o"]["trimmed_leading"]), ("But", None))
 930 | +            self.assertTrue(got["t~trim"]["text"].startswith("Bitcoin has rarely"))
 931 | +            gen = doc["generated_at"]
 932 | +            r = PK.scorer_pass([but, dict(opener, scorer_verdict=sv(self.OPENER, 4.0)), gold, plain], srcs, ctx(),
 933 | +                               None, path, "ledger_test2")                # a verdict attached changes nothing asked
 934 | +            self.assertFalse(r["record"]["candidates_written"])
 935 | +            self.assertEqual(load()["generated_at"], gen)
 936 | +            r = PK.scorer_pass([but, plain], srcs, ctx(), None, path, "ledger_test3")
 937 | +            self.assertTrue(r["record"]["candidates_written"])
 938 | +            self.assertEqual(sorted(c["pid"] for c in load()["candidates"]), ["t", "t~trim"])
 939 | +            self.assertFalse(os.path.exists(path + ".tmp"))
 940 | +        self.assertTrue(PK.SCORER_CANDIDATES.endswith("docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json"))
 941 | +
 942 | +    def test_the_pin_holds_the_affirmation_to_its_text(self):
 943 | +        import stand_alone as SA
 944 | +        self.assertEqual(package_pin.SCORER_MIN, SA.CLIP_MIN_SCORE)
 945 | +        s = {"approved_text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}
 946 | +        self.assertTrue(package_pin.affirmed_verdict(s))
 947 | +        self.assertTrue(package_pin.affirmed_verdict({"text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}))
 948 | +        for bad in (dict(sv(self.OPENER, 4.0), affirmed=False), sv(self.OPENER, 3.0),
 949 | +                    dict(sv(self.OPENER, 4.0), kind="story"), dict(sv(self.OPENER, 4.0), threshold=3.0),
 950 | +                    dict(sv(self.OPENER, 4.0), score="4"), dict(sv(self.OPENER, 4.0), scorer_sha=""),
 951 | +                    dict(sv(self.OPENER, 4.0), event="Pinned: bitcoin"),
 952 | +                    {k: x for k, x in sv(self.OPENER, 4.0).items() if k != "event"},
 953 | +                    sv(self.OPENER + " ", 4.0), None, "affirmed"):
 954 | +            self.assertFalse(package_pin.affirmed_verdict(dict(s, scorer_verdict=bad)), bad)
 955 | +        self.assertTrue(package_pin.affirmed_verdict(dict(s, scorer_verdict=sv(self.OPENER, 4.0, "starts_mid_thought"))))
 956 | +        self.assertTrue(SA.affirmed(4.0, "starts_mid_thought", moments=True))        # the render's own module,
 957 | +        self.assertFalse(SA.affirmed(4.0, "starts_mid_thought"))                     # ruling 60's moments rule;
 958 | +        self.assertFalse(SA.affirmed(3.4, "none", moments=True))                     # the story path unchanged
 959 | +        segs = [{"approved_text": "Bitcoin is money."}, {"approved_text": self.OPENER},
 960 | +                {"approved_text": "Yeah, Bitcoin is money."},
 961 | +                {"approved_text": "Bitcoin x.", "scorer_verdict": sv("Bitcoin y.", 4.0)}]
 962 | +        self.assertEqual([x.split(":")[0] for x in package_pin.scorer_problems(segs)],
 963 | +                         ["segment 1", "segment 2", "segment 3"])
 964 | +        for i, t in ((1, self.OPENER), (2, "Yeah, Bitcoin is money."), (3, "Bitcoin x.")):
 965 | +            segs[i]["scorer_verdict"] = sv(t, 4.0)
 966 | +        self.assertEqual(package_pin.scorer_problems(segs), [])
 967 | +        self.assertEqual(package_pin.scorer_problems([{"approved_text": self.OPENER}]), [])   # a hook: the gate's
 968 | +
 969 | +
 970 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 971 |      """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 972 |      after a write swaps out that clip only, and the line-up carries on."""
 973 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels, sealed in a pin that the integrator renders). Your role: a strict reviewer of a fail-closed admission path.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- The render's STAND_ALONE check (stand_alone.check_edl, run at validate before any render) judges each segment's
  opener:
  - a HOOK that opens on a pronoun, a conjunction or a reply fragment always fails;
  - a CLIP that opens on a conjunction or a reply fragment passes only when the render's clip scorer affirms it;
  - a segment whose lock trims ONE leading word (ruling 33 part 2) passes only when the scorer affirms the trimmed
    text.
  check_edl calls rate(passages) -> {pid: (score, reason, fault)} for exactly those segments; without a rating they
  fail closed.
- The scorer is a local model (gemma3:27b) on GPU0, which this builder may not use. The builder therefore left out
  every moment that opens on a conjunction or reply fragment (no_role_on_screen), and offers a variant with ONE
  leading word trimmed (trim_variant), sealed with the verdict "pending at the render" (ruling 49 a: scorer_pending).
- RULING 56 (09:59): the integrator's pin-stage service asks the render's own scorer about the moments this builder
  leaves out. "Submit them all, untrimmed and trimmed variants; seal only what it affirms."
- RULING 60 (the orchestrator, 11:01; merged by the integrator into the render): for a MOMENTS pin the scorer judges
  STAND-ALONE ONLY.
  - It uses story_semantics.ALONE_PROMPT via stand_alone.clip_scorer(moments=True), with no event and no topic.
    Topicality stays ruling 34's: this builder's screen, and the medley names Bitcoin.
  - The affirmation is the score alone: stand_alone.affirmed(score, fault, moments=True) = score >= 3.5. The fault is
    recorded but does not rule.
  - Validate does the same for every moments pin (check_edl(..., moments=True)).
- The integrator's verdicts file: {rated_at, build, candidates_generated_at, scorer: {model, kind "moments", rubric,
  prompt, threshold 3.5, rule, event null, scorer_sha}, verdicts: {pid: {text_sha256, score, reason, fault, affirmed,
  prompt_sha256} | {text_sha256, error}}}.
  - scorer_sha = sha256 over the render's pipeline/stand_alone.py + story_semantics.py.
  - The integrator's admission rule: "require scorer.kind == moments, scorer.event null, scorer_sha == the render's
    sha now, and affirmed true re-derived as score >= 3.5; an affirmed opener as a clip only, never as the hook."
- RULINGS 58 + 59 are already in HEAD:
  - every candidate is screened at step A;
  - hooks are rated first, and only a hook rated >= 4 opens (can_open);
  - angles are written FOR the passing hooks.
- The integrator's pin check imports pipeline/package_pin.py from this worktree and recomputes seal(). A new
  sealed field enters the body only when a segment carries it (SEALED_LATER).

The change (pipeline/package.py, pipeline/package_pin.py, pipeline/stand_alone.py, tests/package/proof_ledger.py,
tests/package/test_medley.py):

1. pipeline/stand_alone.py becomes the render's own module as it is now, copied read only from the main tree. It adds
   affirmed(), clip_scorer() and a moments flag through opener / trimmed_opener / check_edl. The defaults keep the old
   (story) path.
2. scorer_verdicts(path, code_sha), read only. It uses nothing at all on:
   - a missing, unreadable or malformed file;
   - a kind other than "moments";
   - any event (the key must be present and null);
   - a scorer_sha other than code_sha (render_scorer_sha() recomputes it from the render's two files, read only);
   - a threshold other than stand_alone.CLIP_MIN_SCORE.
   A single verdict is no verdict when it lacks a numeric score, carries an error, or its "affirmed" disagrees with
   stand_alone.affirmed(score, fault, moments=True).
3. with_verdict / verdict_of: a verdict attaches to a moment only when its text_sha256 is the sha256 of the moment's
   CURRENT text. A copied key on a trimmed variant is never its verdict.
4. no_role_on_screen: the CLIP role reads the attached verdict (stand_alone.opener with its score and fault,
   moments=True); the hook role never does. stand_alone_check:
   - check_edl gets a rate() answered from the attached verdicts, with moments=True;
   - a trimmed segment always carries the render's lock marker, so trimmed_opener judges it, as at validate;
   - the scorer_pending list and its row text are removed.
5. build(scorer_verdicts_path, scorer_candidates_path, build_name), via scorer_pass():
   - It reads the verdicts and attaches them before the STAND_ALONE rules. out["scorer"]["admitted"] lists the openers
     that took a clip place; ruling 59's can_open already refuses them as hooks.
   - A trimmed variant without an affirmation is left out BEFORE step A (trim_refused).
   - It writes the next pass's candidates: the moments no_role_on_screen leaves out whose topic rule passes, plus the
     trimmed variant of every moment left out. The file is {generated_at, build, kind "moments", candidates}. The set
     is computed before any verdict attaches. The write is atomic and happens only when the (pid, text_sha256) set
     changed.
6. The rows seal "scorer_verdict" only when it affirms. TRIM_SCORER_PENDING and scorer_pending are removed.
7. package_pin:
   - "scorer_verdict" joins SEALED_LATER; "scorer_pending" stays there so old pins still recompute.
   - SCORER_MIN 3.5 (a test holds it equal to stand_alone.CLIP_MIN_SCORE).
   - affirmed_verdict(s): affirmed true, kind "moments", the event key present and null, threshold == SCORER_MIN, a
     numeric score >= it, a scorer_sha, and text_sha256 == the sha256 of approved_text (pin) or text (package). There
     is no fault test (ruling 60).
   - scorer_problems: any clip after the hook that opens on a conjunction or reply fragment must carry an affirmation;
     any carried verdict must affirm exactly its text.
   - trim_problems: every trimmed clip must carry an affirmation, and scorer_pending is refused on any segment.
   - to_pin runs scorer_problems.
8. The stand_alone inventory row's "by" text names the verdicts and moments=True. Its empty scorer_pending field is
   gone.
9. proof_ledger passes the integrator's latest.json, the candidates file path and the record's name.
10. Tests: 8 new (TestRuling56Scorer). The ruling-49 tests of the pending form are rewritten for the verdict path.
    test_medley 113 OK; every other suite OK, including "every earlier pin still recomputes".

Stated readings (say so if you read the rulings differently):
- K1: "seal only what it affirms" retires ruling 49 (a)'s pending form, and 49 itself said "If you can call the same
  scorer ... do that instead". The integrator also wrote "nothing sealed pending".
- K2: ruling 60's moments rule is applied everywhere this builder reads a verdict: the reader, no_role_on_screen,
  check_edl, the pin. That makes the pin stage the same check validate runs.
- K3: a moment that also fails the topic rule is not submitted, because no verdict can give it a place.
- K4: TRIMMED_PER_LINEUP_MAX stays 1 (ruling 49 b waits for an affirmation AT VALIDATE).
- K5: copying the render's stand_alone.py keeps the pin stage's check the render's own. Its new functions are inert
  here except affirmed() and the moments flag.

Evidence (a read-only dry run of this code on the real verdicts file and the current moments):
- 145 verdicts read, 9 affirmed, 0 that disagree with the rule; the scorer_sha matches the render's code now
  (ae7f410162d3).
- 3 openers admitted as clips; 68 trimmed variants: 2 kept, 66 left out (47 refused, 19 not yet rated).
- The next candidates: 153.

Check in particular:
- every fail-closed path (the kind, the event, the sha, the threshold, a disagreeing "affirmed");
- the sha matching (a trimmed variant never inherits);
- that an admitted opener can never open (ruling 59's can_open, placement);
- the pin's three checks and the seal's backward compatibility;
- the atomic, only-on-change write;
- any remaining reader of scorer_pending or TRIM_SCORER_PENDING;
- that the copied stand_alone.py changes nothing on the story path;
- that no check accepts more than before except through an affirmation, by the render's own scorer, of exactly the
  text that is sealed.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
