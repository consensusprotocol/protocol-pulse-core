# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0426
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 272 s finish=stop usage in 13063 / out 5371 usd~0.120 (upper-bound price)

# Audit: pp-selectid-0426 — Ruling 34 (miner's BTC screen at the pin stage)

Scope note: I can only see the 346-line diff. I have not seen the full bodies of `stand_alone.topical`, `stand_alone.check_edl`'s opener/`_words`/`BITCOIN` definitions, `package_pin.gate_problems`/`required_gates`, `moments_package` (render side), or the test helpers (`pm`, `spk`, `ctx`). Statements below are conditioned on those being as the diff's context implies; where they matter I flag it.

## P0

None found.

## P1

**P1-1 — `package.py:59` (`stand_alone_check`): the pin stage judges the line-up with the module-level `E.BTC_SCREEN`, but seals whatever the package carries — they are the same only by construction, not by check.**
`stand_alone_check` calls `SA.check_edl(..., screen=E.BTC_SCREEN)`; `assemble_medley` seals `pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}`. Both read the same constant, so today they agree. But nothing in the diff ties the *judged* screen to the *sealed* screen: if `pk["btc_screen"]` were ever set (or mutated) independently of the constant used in `stand_alone_check`, a pin could be sealed whose `moments_package.btc_screen.pattern` differs from the pattern the line-up actually passed. `screen_problems` (package_pin.py:143–161) validates only *shape* (non-empty, ≤500 chars, compiles with re.I, has a source) — it deliberately accepts any compiling pattern, which is the render's acceptance, so it cannot catch a divergence. Scenario: a future pin built by a path that copies a stored/older `btc_screen` into the package (or a test fixture) — the pin seals, the render applies a different (e.g. stricter) pattern, and the render refuses a line-up the pin stage passed. This is exactly the class of drift the sealing exists to prevent. Mitigation is one assertion in `to_pin`/`assemble_medley` (`pk["btc_screen"]["pattern"] == E.BTC_SCREEN.pattern` when the stage's own constant is what judged) or a test that round-trips a mutated pattern. Not provably a bug from the diff — the only writer of `pk["btc_screen"]` shown is `assemble_medley` — hence P1, not P0. (The mirror test at tests/eligibility/test_eligibility.py:259–271 pins the constant to the miner's file, which helps, but it tests the constant, not the package↔judgement coupling.)

**P1-2 — `stand_alone.py:244` (`medley_names_bitcoin`): the "names Bitcoin in the speaker's own words" test uses `BITCOIN` (the module's existing regex), not the sealed screen, and the diff does not show `BITCOIN`'s definition.**
The ruling says the medley must name Bitcoin "in the speaker's own words (bitcoin / btc)". The diff's context in eligibility.py:8 shows the *old* literal regex was `\b(bitcoins?|btcs?)\b` (T11/G2, `names_bitcoin`), and `stand_alone.py`'s `topical` default subject is `("bitcoin", "btc")`, so `BITCOIN` in stand_alone is presumably equivalent — but I cannot verify from the diff that `BITCOIN` (a) exists in `stand_alone.py` at all, (b) matches exactly `bitcoin(s)?|btc(s)?` with word boundaries, and (c) is case-insensitive. If `BITCOIN` were, say, broader (matching "Bitcoin" inside "Bitcoiners" without a boundary) or narrower (missing "BTC"), the pin stage's medley rule would diverge from the render's — the render's merged 55315124 `check_edl` is claimed byte-identical, so both sides would compute the same *wrong* thing consistently, which is actually fine for pin↔render agreement but would silently differ from the ruling's words. Also note the asymmetry: the *topic* screen accepts "saylor"/"halving"/"sats" etc. as "about Bitcoin", while the *medley* rule demands the literal word — that is what the ruling says, and the test at test_medley.py:302–306 correctly shows a screen-passing, name-failing medley (`"Sats are the unit."` → `ok == False`). Good. But the test never exercises the case where the *hook* is the naming segment (the ruling explicitly allows "the hook or one clip"); `medley_names_bitcoin`'s `zip(segs, rows)` includes the hook row, so it should work, yet it is untested in the diff. P1 for the unverified `BITCOIN` definition + the untested hook-names case.

**P1-3 — `package.py:85` (`no_role` / `no_topic`): the "most favourable place" argument is sound only if the previous segment is guaranteed to name Bitcoin, which the diff does not establish for the *filter* stage.**
`no_topic(m)` evaluates `SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)` — i.e. it asks: could this moment survive as a clip placed *right after a segment whose text is the literal string "Bitcoin"*? That is indeed the most favourable predecessor, because `topical()`'s completion rule (per the diff's context, stand_alone.py:198–199) keys on the previous segment's text. Two consequences:
(a) If the moment passes that, it is guaranteed a place *topic-wise* in any line-up where the previous segment names Bitcoin — but not in a 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 13025 / out 137 usd~0.069 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none** (all changes byte-for-byte match the Ruling 34 contract and the render-side merge at 55315124; screen_problems exactly reproduces render acceptance; seal includes btc_screen only when supplied so old pins recompute; topical_screen + medley_names_bitcoin logic is identical to stand_alone.py on main; eligibility hook path and story-path-without-screen are untouched; miner regex test confirms verbatim source@8e6afb61; no_topic drops only moments that topical_screen would reject even in best-case position; all tests exercise the exact failure modes described).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 93 s finish=stop usage in 14325 / out 3311 usd~0.093 (upper-bound price)

# Audit: pp-selectid-0426 (Ruling 34 — BTC Screen)

## P0 Findings (Blockers)

**1. `pipeline/stand_alone.py`: `topical_screen` fails closed for Clips when `screen` is `None`**
*   **Scenario:** The `check_edl` function (line 219) accepts `screen=None` to preserve the "story path" (old behavior). However, the internal logic at line 234-235 is:
    ```python
    t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
        topical(kind, s.get("text"), prev, subject)
    ```
    While this *looks* correct, look at `topical_screen` (line 203). If `screen` is passed as `None` (which shouldn't happen due to the ternary, but let's look at the `no_topic` function in `package.py`), it calls `SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)`.
    
    Wait, the critical issue is in **`pipeline/eligibility.py`** and **`pipeline/package.py`** interaction with the **Story Path**.
    
    Actually, looking closer at `stand_alone.py` line 234:
    ```python
    t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
        topical(kind, s.get("text"), prev, subject)
    ```
    This is safe.
    
    **However**, there is a **P0 Logic Error in `pipeline/stand_alone.py` `check_edl` regarding the `medley_names_bitcoin` check.**
    
    Line 243-249:
    ```python
    if screen is not None:                                   # ruling 34: the MEDLEY names Bitcoin, once at least
        named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]
        out["medley_names_bitcoin"] = {"pass": bool(named), "segments": named, ...}
        out["ok"] = out["ok"] and bool(named)
    ```
    The variable `BITCOIN` is used here. Where is it defined?
    In `pipeline/eligibility.py` (line 8), `BITCOIN_TERMS` is defined.
    In `pipeline/stand_alone.py`, is `BITCOIN` imported or defined?
    The diff for `stand_alone.py` does **not** show an import of `BITCOIN` or `BITCOIN_TERMS`.
    The diff for `eligibility.py` defines `BITCOIN_TERMS`.
    If `stand_alone.py` does not import `BITCOIN` (or `BITCOIN_TERMS` and alias it), this code will raise a `NameError` at runtime whenever `screen is not None`.
    
    *Verification:* The diff for `stand_alone.py` (lines 194-250) shows changes to `topical` and `check_edl`. It does **not** show any `import` statements being added or modified at the top of the file. The existing code in `stand_alone.py` (not shown in diff, but implied by context) likely imports `re` and other things. If `BITCOIN` is not a global in `stand_alone.py`, this is a crash.
    
    *Assumption:* If `BITCOIN` is not defined in `stand_alone.py`, this is a **P0 Crash**.
    *Counter-Assumption:* Perhaps `BITCOIN` is defined in `stand_alone.py` in the base code? The diff doesn't show it. The `eligibility.py` diff defines `BITCOIN_TERMS`. It is highly likely `stand_alone.py` needs to import it or define it. Given the "Smallest diff" law, if the import is missing, it's a bug.
    
    Let's look at `pipeline/eligibility.py` line 8: `BITCOIN_TERMS = re.compile(...)`.
    In `stand_alone.py`, the code uses `BITCOIN.search(...)`.
    If `stand_alone.py` does not have `BITCOIN` defined, it crashes.
    
    **Finding P0-1:** `pipeline/stand_alone.py` line 244 uses `BITCOIN` which is not defined in the diff and likely not imported. This will cause a `NameError` for all Moments Medleys (where `screen` is not None).

**2. `pipeline/eligibility.py`: `BTC_SCREEN` Regex Syntax Error / Inconsistency**
    Line 13-14:
    ```python
    BTC_SCREEN = re.compile(r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
                            r"cold storage|microstrategy|mstr|ibit|saylor)\b", re.I)
    ```
    The test `test_the_screen_is_the_miners_verbatim` (line 259) attempts to parse the source file `pp-ingest pipeline/ingest/mine.py@8e6afb61` using a regex:
    ```python
    m = _re.search(r'BTC_SCREEN = re.compile\(r"(.*?)"\s*\n\s*r"(.*?)", re.I\)', r.stdout)
    ```
    This test regex expects the source code to be formatted as:
    `BTC_SCREEN = re.compile(r"..." \n r"...", re.I)`
    
    However, the code in `eligibility.py` is:
    `BTC_SCREEN = re.compile(r"..." \n r"...", re.I)`
    
    The test asserts `E.BTC_SCREEN.pattern == m.group(1) + m.group(2)`.
    If the source file `mine.py` has the regex on a single line, or formatted differently, the test fails.
    More importantly, the test relies on `git show` from a specific worktree `/home/ultron/worktrees/pp-ingest`. If this path doesn't exist in the CI/CD environment or the audit environment, the test is skipped (`skipTest`). This is acceptable for local dev, but the **P0** is the potential `NameError` in `stand_alone.py`.

**3. `pipeline/package.py`: `no_topic` Logic Flaw**
    Line 73:
    ```python
   

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0426 (ruling 34's pin side: the miner's screen sealed and applied, the medley names Bitcoin): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers stand_alone.py (the sync), eligibility.py, package.py, package_pin.py and the two test
files. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: no P0, "yes with conditions";
- qwen: "SHIP: NO" on three P0s, each refuted below with evidence.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The sealed screen equals the judged one only by construction (glm P1-1 and condition 2; qwen's P0-4 on the same seal path, found consistent) | IMPLEMENTED: screen_problems refuses a medley whose sealed btc_screen.pattern is not the pattern its "stand_alone" gate row recorded. check_edl's out["screen"] is copied into the row by inventory. Tested: a row with no judged screen refuses, and a compiling but different pattern refuses. |
| K2 | stand_alone.BITCOIN, the medley rule's regex, is not shown in the diff (qwen P0-1 and P1-1, glm P1-2) | REFUTED with the file. stand_alone.py:27 is `BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)`, in the base file and byte-identical to the render's (main 55315124, cmp). The medley-rule tests run that code path and pass, which a NameError would not. IMPLEMENTED: glm's hook-only case ("named by hook"). |
| K3 | no_topic's literal "Bitcoin" predecessor may not be the most favourable place (qwen P0-3, glm P1-3 and condition 4) | VERIFIED as maximal. topical()'s completion rule (stand_alone.py:80-97) is `prev_text and _mentions(prev_text, subject) and first in BACKREF and FIGURE.search(text)`. It reads the previous text ONLY through _mentions(prev_text, {bitcoin, btc}). Every predecessor that mentions Bitcoin gives the same result, so "Bitcoin" is maximal, and a moment it fails can take no place. glm confirms the drop direction is safe. |
| K4 | Does stand_alone_check serve the story path (glm P1-4, condition 1)? | VERIFIED by grep. It is called only by package.py's medley build (lineup_for's need_stand_alone and the two inventory call sites) and by tests. The story path never calls it, and the render's story path passes no screen (unchanged). |

## Refuted

- **qwen P0-2 (the mirror test's parsing):** not a defect. The test ran, it was not skipped, and it passed: it parsed mine.py at 8e6afb61 and matched the pattern exactly. Its skip covers only an environment without pp-ingest's history.

## Verification

- test_medley 57 OK; test_eligibility 30 OK; all 11 suites OK.
- Old pins still recompute (check_pin_only, with the integrator's 7-argument call, on d2657bbe, 1b4a63d0 and 41f29b1f: READY, per the integrator at 04:20 ET).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0426/C2_STEP.diff (364 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index 24a1e721..f2e898ba 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -56,6 +56,12 @@ MIN_STATEMENT_TOKENS = 5                    # T14 story_semantics.py:372 (quote_
   6 |  HOOK_LEAD_S = sentence_law.HEAD_LEAD_MIN_S  # T12 sentence_law.py:57 (D1; G17a's hook lead; GPT-cut F12)
   7 |  CLIP_SCORER_MIN = stand_alone.CLIP_MIN_SCORE  # T8 stand_alone.py:30
   8 |  BITCOIN_TERMS = re.compile(r"\b(bitcoins?|btcs?)\b", re.I)          # T11 / G2 editorial_select.py:59
   9 | +# RULING 34 (orchestrator 03:12 ET Nov 13; the render's side merged at 55315124): the miner's about-Bitcoin screen,
  10 | +# verbatim, is the per-segment topic test of a moments package. It is sealed into every moments pin (package_pin:
  11 | +# moments_package.btc_screen), and the render's stand_alone.check_edl applies exactly the sealed pattern.
  12 | +BTC_SCREEN_SOURCE = "pp-ingest pipeline/ingest/mine.py@8e6afb61"
  13 | +BTC_SCREEN = re.compile(r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
  14 | +                        r"cold storage|microstrategy|mstr|ibit|saylor)\b", re.I)
  15 |  V2F_VIDEO_IDS = frozenset({"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"})   # S3 editorial_select.py:60
  16 |  CONTINUATION_OPENERS = frozenset(stand_alone.CONJUNCTIONS)          # T8 = editorial_select.py:127
  17 |  INTERJECTIONS = frozenset({"oh", "ah", "wow", "yeah", "yes", "right", "okay", "mhm", "hmm", "huh", "wait", "sure",
  18 | @@ -451,9 +457,11 @@ def _span(span, ctx, role):
  19 |      else:
  20 |          facts["duration_s"] = None
  21 |          R("duration", "no word timestamps: the duration is not measured")
  22 | -    # T11 subject
  23 | -    if not names_bitcoin(text):
  24 | -        R("no_bitcoin", "does not name Bitcoin (Bitcoin-only editorial line; stand_alone.topical at selection)")
  25 | +    # T11 subject. Ruling 34: the literal regex is retired. The HOOK must pass the miner's about-Bitcoin screen itself;
  26 | +    # a clip is judged per line-up (stand_alone.check_edl with the screen: the screen, or it completes the previous
  27 | +    # claim), and the medley must name Bitcoin once (check_edl's medley_names_bitcoin).
  28 | +    if role == "hook" and not BTC_SCREEN.search(text):
  29 | +        R("no_bitcoin", "the hook does not pass the miner's about-Bitcoin screen (ruling 34)")
  30 |      # T12 the hook's lead-in
  31 |      if role == "hook":
  32 |          if w0 == 0:
  33 | diff --git a/pipeline/package.py b/pipeline/package.py
  34 | index cbf43239..089cc44b 100644
  35 | --- a/pipeline/package.py
  36 | +++ b/pipeline/package.py
  37 | @@ -338,6 +338,7 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
  38 |            "bridges_after_clip": ([k] if mid else []) + ([n_clips] if t is not None else [])}
  39 |      pk = _package(segs, ctx, fields, vo_kind, vo, lines)
  40 |      pk["shape"] = "medley"
  41 | +    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}   # ruling 34: sealed (to_pin)
  42 |      pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
  43 |                                             "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
  44 |                                             "text": b["text"], "why": b.get("why"),
  45 | @@ -561,12 +562,15 @@ def stand_alone_check(segs):
  46 |      a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
  47 |      check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
  48 |      scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
  49 | -    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1)."""
  50 | +    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1).
  51 | +    RULING 34 (the render's side merged at 55315124): the topic test is the miner's about-Bitcoin screen that every
  52 | +    moments pin seals (eligibility.BTC_SCREEN, moments_package.btc_screen), and the MEDLEY must name Bitcoin in at
  53 | +    least one segment (out["medley_names_bitcoin"], part of out["ok"]): check_edl(..., screen=...), as the render."""
  54 |      import stand_alone as SA
  55 |      edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  56 |             "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  57 |                       for i, m in enumerate(segs[1:], 1)]}
  58 | -    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  59 | +    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  60 |  
  61 |  
  62 |  def ad_read_out(ms, sources):
  63 | @@ -588,6 +592,16 @@ def ad_read_out(ms, sources):
  64 |      return out
  65 |  
  66 |  
  67 | +def no_topic(m):
  68 | +    """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  69 | +    fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  70 | +    names Bitcoin (stand_alone.topical_screen as a clip: its most favourable place). build() leaves it out before any
  71 | +    vendor call."""
  72 | +    import stand_alone as SA
  73 | +    ok, why = SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)
  74 | +    return None if ok else f"the render's STAND_ALONE topic rule with the pin's screen (ruling 34): {why}"
  75 | +
  76 | +
  77 |  def no_role_on_screen(m):
  78 |      """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  79 |      opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  80 | @@ -1041,7 +1055,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  81 |      usd0 = _spent(spend)
  82 |      ms, why = usable(moments, ctx, delivered, optout)
  83 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  84 | -    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  85 | +    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m) or no_topic(m)] if r}
  86 |      ms = [m for m in ms if m["moment_id"] not in no_role]
  87 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  88 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  89 | @@ -1054,9 +1068,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  90 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  91 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  92 |             "package": None}
  93 | -    log(f"  {n_usable} usable, {len(no_role)} of them left out (they open on a conjunction or reply fragment, which "
  94 | -        f"the render's STAND_ALONE fails with no clip scorer), {len(ad_read)} on an ad-read marker (the exclusion "
  95 | -        f"screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  96 | +    log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
  97 | +        f"would have to affirm, or no place under the topic rule with the pin's screen), {len(ad_read)} on an ad-read "
  98 | +        f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  99 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 100 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 101 |          return out
 102 | @@ -1513,6 +1527,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 103 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 104 |                                      "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 105 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 106 | -                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []])}
 107 | +                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 108 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 109 |             if stand is not None else {}),
 110 |      }
 111 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 112 | index 6c15c3b0..101b0e28 100644
 113 | --- a/pipeline/package_pin.py
 114 | +++ b/pipeline/package_pin.py
 115 | @@ -69,14 +69,16 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 116 |                  "speaker")                                 # the 00:05 ET Nov 13 order, item 3
 117 |  
 118 |  
 119 | -def seal(segments, edl_vo, signoff, title, caption, gates):
 120 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 121 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 122 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 123 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
 124 |      A SEALED_LATER field enters the body only when the segment carries its key. Every pin sealed before that field
 125 |      existed then recomputes to its own package_sha256: the integrator's check recomputes seals with this module, and
 126 |      all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
 127 | -    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest."""
 128 | +    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest.
 129 | +    btc_screen (ruling 34: the miner's about-Bitcoin screen the render applies, {"pattern", "source"}) enters the body
 130 | +    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems)."""
 131 |      def body_of(s):
 132 |          b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 133 |               "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
 134 | @@ -86,9 +88,35 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 135 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
 136 |                                                               for b in edl_vo.get("bridges") or []]},
 137 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 138 | +    if btc_screen is not None:
 139 | +        body["btc_screen"] = btc_screen
 140 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 141 |  
 142 |  
 143 | +def screen_problems(pk):
 144 | +    """[why] for a moments medley that does not carry the screen its line-up was judged with (ruling 34). The render
 145 | +    reads moments_package.btc_screen and, without it, applies the stricter every-segment rule, so a pin judged with
 146 | +    the screen but sealed without it could be refused at render. A carried screen is {"pattern": a non-empty str of at
 147 | +    most 500 characters that compiles with re.I, "source": a non-empty str}: the render's own acceptance
 148 | +    (run_fresh.moments_screen)."""
 149 | +    if pk.get("shape") != "medley":
 150 | +        return []
 151 | +    sc = pk.get("btc_screen")
 152 | +    if not isinstance(sc, dict) or set(sc) != {"pattern", "source"}:
 153 | +        return ["btc_screen: a medley must carry {pattern, source} (ruling 34)"]
 154 | +    pat, src = sc.get("pattern"), sc.get("source")
 155 | +    if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 or not isinstance(src, str) or not src.strip():
 156 | +        return ["btc_screen: the pattern must be a non-empty str of at most 500 characters, with a source"]
 157 | +    try:
 158 | +        re.compile(pat, re.I)
 159 | +    except re.error as e:
 160 | +        return [f"btc_screen: the pattern does not compile ({e})"]
 161 | +    judged = ((pk.get("gates") or {}).get("stand_alone") or {}).get("screen")
 162 | +    if judged != pat:                  # the sealed screen IS the one the line-up passed with (audit 0426 C1, glm P1-1)
 163 | +        return [f"btc_screen: the sealed pattern is not the one the stand_alone row judged with ({judged!r})"]
 164 | +    return []
 165 | +
 166 | +
 167 |  def speaker_problems(segments):
 168 |      """[why] for segments whose speaker record (speakers.attribute) is missing or malformed: the orchestrator's 00:05 ET
 169 |      Nov 13 order (item 3) has every pin carry, per segment, the speaker's name (or "unknown", never a guess) with its
 170 | @@ -161,7 +189,8 @@ def line_problems(pk):
 171 |  def to_pin(pk, run_name):
 172 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 173 |                                                                       for x in line_problems(pk)] + \
 174 | -        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or [])
 175 | +        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 176 | +        screen_problems(pk)
 177 |      if problems:
 178 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 179 |      segs = []
 180 | @@ -174,7 +203,7 @@ def to_pin(pk, run_name):
 181 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 182 |      edl_vo = {"intro": pk["vo"]["intro"],
 183 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 184 | -    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"])
 185 | +    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"))
 186 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
 187 |              "label": "bitcoin", "headline": pk["title"],
 188 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
 189 | @@ -195,6 +224,7 @@ def to_pin(pk, run_name):
 190 |                                  "supply_exception": pk.get("supply_exception"),
 191 |                                  "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
 192 |                                  "gates": pk["gates"],
 193 | +                                **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 194 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 195 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
 196 |                                             "models": pk.get("models")},
 197 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 198 | index 168a1cc3..fadf036c 100644
 199 | --- a/pipeline/stand_alone.py
 200 | +++ b/pipeline/stand_alone.py
 201 | @@ -96,9 +96,28 @@ def topical(kind, text, prev_text=None, subject=("bitcoin", "btc")):
 202 |                     f"previous segment's claim (it opens on {first!r}): context, not a clip")
 203 |  
 204 |  
 205 | -def check_edl(edl, rate=None, subject=("bitcoin", "btc")):
 206 | +def topical_screen(kind, text, prev_text, screen):
 207 | +    """Ruling 34 (orchestrator 2026-11-13 '03:42'), moments packages only: a segment is about Bitcoin when the miner's
 208 | +    about-Bitcoin screen (BTC_SCREEN, carried on the pin) matches its own words, or (a clip only) it completes the
 209 | +    previous segment's claim exactly as topical() allows. The medley-level rule (one segment names Bitcoin) is
 210 | +    check_edl's."""
 211 | +    m = screen.search(text or "")
 212 | +    if m:
 213 | +        return True, f"about Bitcoin by the miner's screen ({m.group(0)!r})"
 214 | +    if kind == "hook":
 215 | +        return False, "the hook does not pass the miner's about-Bitcoin screen"
 216 | +    ok, why = topical(kind, text, prev_text, ("bitcoin", "btc"))
 217 | +    if ok:
 218 | +        return ok, why
 219 | +    return False, f"does not pass the miner's about-Bitcoin screen and does not complete the previous claim"
 220 | +
 221 | +
 222 | +def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 223 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 224 | -    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed."""
 225 | +    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed.
 226 | +    screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 227 | +    and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 228 | +    speaker's own words. screen None: every segment names the subject, as before (the story path)."""
 229 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 230 |      need = [(label, s) for label, kind, s in segs if kind == "clip" and _words(s.get("text"))[:1]
 231 |              and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)]
 232 | @@ -114,10 +133,19 @@ def check_edl(edl, rate=None, subject=("bitcoin", "btc")):
 233 |          sc = scores.get(label)
 234 |          score, fault = (sc[0], sc[2]) if sc else (None, None)
 235 |          o_ok, o_why = opener(kind, s.get("text"), score, fault)
 236 | -        t_ok, t_why = topical(kind, s.get("text"), prev, subject)
 237 | +        t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
 238 | +            topical(kind, s.get("text"), prev, subject)
 239 |          rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
 240 |                       "opener": {"pass": o_ok, "why": o_why}, "topic": {"pass": t_ok, "why": t_why},
 241 |                       **({"scorer": {"score": sc[0], "reason": sc[1], "fault": sc[2]}} if sc else {}),
 242 |                       "pass": o_ok and t_ok})
 243 |          prev = s.get("text")
 244 | -    return {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
 245 | +    out = {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
 246 | +    if screen is not None:                                   # ruling 34: the MEDLEY names Bitcoin, once at least
 247 | +        named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]
 248 | +        out["medley_names_bitcoin"] = {"pass": bool(named), "segments": named,
 249 | +                                       "why": f"named by {', '.join(named)}" if named else
 250 | +                                       "no segment names Bitcoin in the speaker's own words (ruling 34)"}
 251 | +        out["screen"] = screen.pattern
 252 | +        out["ok"] = out["ok"] and bool(named)
 253 | +    return out
 254 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 255 | index 46c20050..afffc2c0 100644
 256 | --- a/tests/eligibility/test_eligibility.py
 257 | +++ b/tests/eligibility/test_eligibility.py
 258 | @@ -252,6 +252,20 @@ class TestSpan(unittest.TestCase):
 259 |          self.assertNotIn("opener", r.names(), r.why())
 260 |          self.assertTrue(any("'and so'" in t for t in r.facts["targets_missed"]), r.facts)
 261 |  
 262 | +    def test_the_screen_is_the_miners_verbatim(self):                  # ruling 34: sealed as its source names it
 263 | +        import subprocess
 264 | +        path, commit = E.BTC_SCREEN_SOURCE.split()[-1].split("@")     # 'pipeline/ingest/mine.py', '8e6afb61'
 265 | +        r = subprocess.run(["git", "--no-optional-locks", "-C", "/home/ultron/worktrees/pp-ingest", "show",
 266 | +                            f"{commit}:{path}"], capture_output=True, text=True)
 267 | +        if r.returncode != 0:
 268 | +            self.skipTest("pp-ingest's history is not readable here")
 269 | +        import re as _re
 270 | +        m = _re.search(r'BTC_SCREEN = re.compile\(r"(.*?)"\s*\n\s*r"(.*?)", re.I\)', r.stdout)
 271 | +        self.assertIsNotNone(m)
 272 | +        self.assertEqual(E.BTC_SCREEN.pattern, m.group(1) + m.group(2))
 273 | +        self.assertEqual(E.BTC_SCREEN_SOURCE, "pp-ingest pipeline/ingest/mine.py@8e6afb61")
 274 | +        self.assertTrue(E.BTC_SCREEN.flags & _re.I)
 275 | +
 276 |      def test_duration_count_subject_lead(self):
 277 |          short = self.hook(["Bitcoin fell five percent overnight on the open."])
 278 |          self.assertNotIn("duration", short.names())                                              # law L-o: a target
 279 | @@ -267,6 +281,10 @@ class TestSpan(unittest.TestCase):
 280 |          alt = self.hook(["Solana rallied twenty percent this week after the exchange listing news broke on "
 281 |                           "Monday morning, leading every large cap token higher into the weekend close."])
 282 |          self.assertIn("no_bitcoin", alt.names())                                                 # an altcoin sentence
 283 | +        sats = self.hook(["Michael Saylor just bought another twenty thousand coins for the treasury this week."])
 284 | +        self.assertNotIn("no_bitcoin", sats.names())              # ruling 34: the miner's screen ('saylor'), the hook
 285 | +        src = source(["Gold has been the premier monetary asset for most of human history, people say."])
 286 | +        self.assertNotIn("no_bitcoin", E.eligible(E.Span(src, 0, 0), ctx("clip")).names())   # a clip: per line-up
 287 |          tight = source(["Prices were calm overnight in Asia.", HOOK_TXT], pause=0.0)    # 40 ms between words only
 288 |          sp = E.Span(tight, 1, 1)
 289 |          self.assertIn("hook_lead", E.eligible(sp, ctx("hook", story=statements(sp))).names())   # 40 ms gap (G17a)
 290 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 291 | index 30f6c0dc..971d971a 100644
 292 | --- a/tests/package/test_medley.py
 293 | +++ b/tests/package/test_medley.py
 294 | @@ -332,6 +332,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 295 |  
 296 |      def gates(self, pk, **over):
 297 |          g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
 298 | +        g["stand_alone"] = dict(g["stand_alone"], screen=E.BTC_SCREEN.pattern)      # the screen it judged with
 299 |          g.update(over)
 300 |          return g
 301 |  
 302 | @@ -725,6 +726,61 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 303 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 304 |  
 305 |  
 306 | +class TestRuling34Screen(unittest.TestCase):
 307 | +    """Ruling 34 (render side merged at 55315124): the topic test is the miner's about-Bitcoin screen the pin seals;
 308 | +    the hook must pass it itself, a clip may complete the previous claim, and the MEDLEY must name Bitcoin once."""
 309 | +
 310 | +    def check(self, *texts):
 311 | +        return PK.stand_alone_check([{"text": t} for t in texts])
 312 | +
 313 | +    def test_the_screen_is_the_topic_and_the_medley_must_name_bitcoin(self):
 314 | +        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying.", "Sats are the unit.")
 315 | +        self.assertEqual([x["topic"]["pass"] for x in r["rows"]], [True, True, True])      # the screen, each one
 316 | +        self.assertFalse(r["medley_names_bitcoin"]["pass"])                                  # but no "Bitcoin"
 317 | +        self.assertFalse(r["ok"])
 318 | +        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying Bitcoin.",
 319 | +                       "That was 25 % of the float.")                                       # completes the claim
 320 | +        self.assertTrue(r["ok"], r["rows"])
 321 | +        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["clip_01"])
 322 | +        self.assertEqual(r["screen"], E.BTC_SCREEN.pattern)
 323 | +        r = self.check("Bitcoin is the hardest money.", "Saylor keeps buying.", "Sats are the unit.")
 324 | +        self.assertTrue(r["ok"], r["rows"])                                                  # the hook alone names it
 325 | +        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["hook"])
 326 | +        r = self.check("Gold is the oldest money.", "Bitcoin is the newest.", "Bitcoin wins.")
 327 | +        self.assertFalse(r["ok"])                                                            # the hook must pass
 328 | +        self.assertIn("the hook does not pass the miner's about-Bitcoin screen", r["rows"][0]["topic"]["why"])
 329 | +
 330 | +    def test_a_moment_with_no_place_under_the_topic_rule_is_left_out(self):
 331 | +        self.assertIn("ruling 34", PK.no_topic({"text": "Gold is the oldest money."}))
 332 | +        for t in ("Saylor keeps buying.", "That was 25 % of the float.", "Bitcoin is money."):
 333 | +            self.assertIsNone(PK.no_topic({"text": t}), t)
 334 | +
 335 | +    def test_every_medley_seals_the_screen_and_the_recompute_needs_it(self):
 336 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0))}
 337 | +        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 338 | +                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
 339 | +                  "caption": {"text": "three clips", "cites": []}}
 340 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 341 | +        self.assertEqual(pk["btc_screen"], {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE})
 342 | +        pk["gates"] = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1}
 343 | +                       for k in package_pin.required_gates(pk)}
 344 | +        with self.assertRaises(package_pin.PinRefused):                 # no judged screen on the stand_alone row
 345 | +            package_pin.to_pin(spk(pk), "test")
 346 | +        pk["gates"]["stand_alone"]["screen"] = PK.stand_alone_check(pk["segments"])["screen"]   # what it judged
 347 | +        pin = package_pin.to_pin(spk(pk), "test")
 348 | +        mp = pin["moments_package"]
 349 | +        self.assertEqual(mp["btc_screen"], pk["btc_screen"])
 350 | +        args = (pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"])
 351 | +        self.assertEqual(package_pin.seal(*args, mp.get("btc_screen")), mp["package_sha256"])   # check_pin_only's
 352 | +        self.assertNotEqual(package_pin.seal(*args), mp["package_sha256"])                      # 7-argument call
 353 | +        for bad in (None, {"pattern": "", "source": "s"}, {"pattern": "(", "source": "s"},
 354 | +                    {"pattern": "x" * 501, "source": "s"}, {"pattern": "bitcoin"},
 355 | +                    {"pattern": "bitcoin", "source": "s"}):         # compiles, but not the pattern it was judged with
 356 | +            p = dict(spk(pk), btc_screen=bad)
 357 | +            with self.assertRaises(package_pin.PinRefused):
 358 | +                package_pin.to_pin(p, "test")
 359 | +
 360 | +
 361 |  class TestAdReadBeforeTheAngle(unittest.TestCase):
 362 |      """The exclusion screen's deterministic part (moments.ad_read_marker) runs before step A, so no angle is built
 363 |      around a moment the package stage would refuse. The 03:39 build lost its line-up's hook to it after the write."""
 364 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
"pins"; another session (the integrator) renders them with the main pipeline. The pin stage must never seal a line-up
the render's own checks would refuse.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 34 (03:12 ET Nov 13): "no_bitcoin: the literal regex is retired for clips. The miner's
about-Bitcoin screen is the per-clip test. The MEDLEY must name Bitcoin: at least one clip or the hook says it in the
speaker's own words." The integrator merged the render side (main 55315124) with this contract:
- The pin seals moments_package.btc_screen = {"pattern": <regex str of at most 500 characters, compiled with re.I by
  the render>, "source": <file@commit>} inside the sealed package (so it is in moments_package_sha256).
- The render's stand_alone.check_edl(edl, screen=<compiled pattern>) checks each segment's TOPIC with the screen: the
  screen matches the segment's words, or (a clip only) the segment completes the previous claim (topical()'s old
  rule). The HOOK must match the screen itself.
- The MEDLEY must name Bitcoin: the hook or one clip says bitcoin / btc in its own words (out["medley_names_bitcoin"],
  part of out["ok"]).
- If btc_screen is absent or malformed, the render applies the old strict rule (every segment names Bitcoin).
- The integrator's recompute (check_pin_only) now calls seal(..., mp.get("btc_screen")) as a 7th argument.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. The relaxation here is the orchestrator's own
  ruling and the render's merged code; check that the pin stage does exactly that and no more.

The change:
1. pipeline/stand_alone.py: synced BYTE-IDENTICAL to main's at 55315124 (the render's own topical_screen() and
   check_edl(screen=...)). Passing no screen keeps the old behaviour.
2. pipeline/eligibility.py:
   - BTC_SCREEN: the miner's screen verbatim (pp-ingest pipeline/ingest/mine.py@8e6afb61, 131 characters), compiled
     with re.I, plus BTC_SCREEN_SOURCE;
   - T11: the HOOK role needs BTC_SCREEN, not the literal regex; the CLIP role has no per-moment topic flag (a clip
     may complete the previous claim, decided per line-up).
3. pipeline/package.py:
   - stand_alone_check passes screen=E.BTC_SCREEN, so the line-up filter and the sealed "stand_alone" row require the
     screen topic AND medley_names_bitcoin (out["ok"]);
   - no_topic(m): a moment that fails topical_screen as a clip right after a segment naming Bitcoin (its most
     favourable place) can take no place, and build() leaves it out with the opener rule before any vendor call;
   - assemble_medley sets pk["btc_screen"] = {pattern, source};
   - the inventory row records medley_names_bitcoin and the screen.
4. pipeline/package_pin.py:
   - seal(..., btc_screen=None): the screen enters the sealed body only when given, so every earlier pin recomputes;
   - to_pin seals pk["btc_screen"] and writes moments_package.btc_screen;
   - screen_problems refuses a MEDLEY without a valid {pattern, source}: a non-empty str of at most 500 characters
     that compiles with re.I, and a source. That is the render's own acceptance.
5. Tests:
   - the screen as topic, and the medley rule;
   - the hook must pass the screen; a clip may complete the previous claim;
   - no_topic;
   - every medley seals the screen, and the 7-argument recompute equals while the 6-argument one does not;
   - a missing or malformed screen refuses the pin;
   - the eligibility hook rule;
   - a mirror test of the pattern against the miner's file at the sealed commit.

Check in particular:
- that the pin stage's check is the render's, with the same compiled screen, the same medley rule and the same
  hook-must-match rule, and cannot PASS a line-up the render would refuse;
- that the sealed screen is exactly the one the line-up was judged with;
- that old pins still recompute;
- that no_topic drops ONLY moments that can take no place under the render's rule;
- that the story path (no screen) is unchanged.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
