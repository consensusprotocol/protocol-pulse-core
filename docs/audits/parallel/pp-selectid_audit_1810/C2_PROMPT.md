# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1810
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
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

Wait — checking the call: `package_pin.window_problems(res["package"]["segments"])` with no `now` → the function defaults `now = now or datetime.now(timezone.utc)`. That **is** the render clock at that moment. ✓. However, the *build's* render clock is `ctx.now` (fixed at build start), while the pin stage uses wall-clock now. If a build runs long, a moment that was 11.9 h at `ctx.now` can be 12.1 h at pin time → the pin is refused

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 42 s finish=stop usage in 13464 / out 685 usd~0.084 (upper-bound price)

**P0: pipeline/package.py:83 (same_speech)**  
REPOST_ALIGN_MIN is read (sum of long matching blocks >= REPOST_ALIGN_MIN * short) but no definition, assignment, or import of it appears anywhere in the diff (only SAME_SPEECH_MIN_WORDS=8 and SAME_SPEECH_RUN=3 are added). Concrete scenario: any call to usable() on a delivered span from another video raises NameError before same_speech can enforce ruling 76(b). Tests that invoke PK.same_speech would also fail under a clean interpreter.

**P1: pipeline/package.py:110 and candidates.py:46 (expire + usable interaction)**  
A candidate whose *last* clip is >12 h (or has unknown publish time) is expired/closed, but the diff does not show that CA.due(), CA.registered(), or any later seed() path is guaranteed to ignore a re-seeded record that was previously closed as "expired". Concrete scenario: proof_ledger re-runs on a CANDIDATES.json that later gets a fresh seed(reg, record_with_old_clip, ...) before the expire() call; the diff leaves open whether the closed state survives or the moment re-enters a lineup. (Test only shows one fresh registry after expiry.)

**P2: tests/package/test_medley.py:338 and pipeline/package.py:82**  
same_speech accepts any two strings whose canonical tokens are identical even if <8 words, but rejects any pair <8 words that differ. Concrete scenario: a 7-word delivered hook that is re-posted verbatim in another video is *not* blocked by ruling 76(b) (only the overlap rule can catch it, and that rule is video_id-specific). The 80 % / run-length heuristic is therefore unreachable for short clips; the diff gives no evidence this matches the owner's intent for "the same speech".

**P2: pipeline/package_pin.py:149 and proof_ledger.py:230**  
window_problems() and the pin-stage call both default to datetime.now(timezone.utc) at the exact instant the check runs. This satisfies "render clock at that moment" for the shown path, but the diff does not show what happens if the pin write is deferred (e.g. queued for later render); the re-check would then use a later clock. (Uncertain from diff alone whether any such deferral path exists.)

**P2: pipeline/candidates.py:38 (_at)**  
expire() calls _at(published[mid]) inside a try/except that treats any failure as "no known publish time". _at itself is not modified or shown in the diff; behavior for malformed ISO strings or missing keys is therefore unchanged from prior code.

All other required checks (no >12 h moment reaches a pin, delivered same-speech blocked for other videos, --hours >12 refused before any write, seal() byte signature untouched, only the two new elif branches added to usable(), ruling-76 counts logged, tests cover the new branches and the mutated refusal paths) pass on the visible diff. The 15-suite "OK" claim cannot be independently verified from the diff alone.

**SHIP: no** (P0 NameError blocks any execution of ruling 76(b); must add/fix REPOST_ALIGN_MIN constant and confirm due()/seed() cannot revive an "expired" candidate).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 42 s finish=stop usage in 14903 / out 2380 usd~0.080 (upper-bound price)

I have reviewed the diff for `pp-selectid-1810` against RULING 76 and the Governing Laws.

### P0 Findings (Blockers)

**1. `pipeline/package.py`: `same_speech` logic is unsound and violates L-k (Canonical Form)**
*   **Location:** `pipeline/package.py` (lines 67-83 in diff context, specifically the `same_speech` function).
*   **Issue:** The function uses `difflib.SequenceMatcher` on `canon.canon_tokens` to determine if two texts are the "same speech."
    *   **Violation of L-k:** L-k states that "two strings a listener hears as the same words compare equal... a different number, unit, sign, name, negation or dropped word never does." `difflib` is a fuzzy string matching algorithm. It does not understand semantic or canonical equivalence. For example, if `canon_tokens` produces `["bitcoin", "is", "up"]` and `["bitcoin", "is", "down"]`, `difflib` might find a high match ratio (2/3 words) and potentially flag it as "same speech" depending on the threshold, which is a critical failure (negation change).
    *   **Unsound Threshold:** The logic `sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short` is mathematically fragile. `REPOST_ALIGN_MIN` is not defined in the diff (likely imported or global, but its value is critical). If `REPOST_ALIGN_MIN` is 0.8, and `short` is 8, it requires 6.4 words in runs of 3. This allows for significant divergence.
    *   **Scenario:** A delivered clip says "Bitcoin crashed 5%." A new clip says "Bitcoin crashed 5% and then recovered." `same_speech` might return `True` if the matching blocks are large enough, incorrectly blocking a valid, distinct new statement. Conversely, if the new clip is "Bitcoin fell 5%," `canon` might normalize "crashed" and "fell" differently, but `difflib` operates on the token list. If `canon` doesn't map synonyms (it shouldn't, per L-k), `difflib` will see them as different. However, the risk is false positives where *different* events are deemed "same speech" due to shared boilerplate words (e.g., "The market is..."), leading to valid content being rejected (M12 Fail Closed violation? No, it's a false rejection, which is safe but bad for utility. Wait, L-k says "a different... dropped word never does." If `same_speech` returns True for different words, it violates the spirit of strict canonical comparison).
    *   **Correction:** `same_speech` should likely rely on exact canonical equality or a very strict subset check, not fuzzy matching. Fuzzy matching is explicitly dangerous for "same speech" determination in a legal/compliance context.

**2. `pipeline/package.py`: `expired` check order and `ctx.now` availability**
*   **Location:** `pipeline/package.py` (lines 123-125 in diff context).
*   **Issue:** The check `elif expired(m, ctx.now):` is placed *after* the `time_sensitive` check.
    *   **Scenario:** A moment is `time_sensitive` AND `expired` (>12h). The code reports `time_sensitive` failure (L-v 3) and does *not* report `expired`. This is acceptable per the comment "both exclude," but the `expired` function itself calls `E.age_hours`. If `ctx.now` is not a valid datetime or `m.get("published_at")` is malformed, `expired` might raise an exception or return `False` incorrectly.
    *   **Critical:** The `expired` function in `package.py` (lines 86-91) calls `E.age_hours(m.get("published_at"), now)`. If `m.get("published_at")` is `None`, `E.age_hours` must handle it. The docstring says "or its publish time cannot be read (never assumed fresh)." If `E.age_hours` returns `None` for missing data, `age is None` is `True`, so it returns `True` (expired). This is correct. However, if `E.age_hours` raises an exception on bad data, `usable` will crash. The diff does not show `E.age_hours` implementation. Assuming it is robust, this is a P1. If it is not, it is P0. Given `M12 FAIL CLOSED`, an exception is a fail, which is safe, but a crash in `usable` might prevent the entire build from running, which is a DoS.

**3. `tests/package/proof_ledger.py`: `--hours` validation logic**
*   **Location:** `tests/package/proof_ledger.py` (lines 192-194 in diff context).
*   **Issue:** `if not 0 < a.hours <= package_pin.WINDOW_H:`.
    *   **Scenario:** If `a.hours` is `0`, it refuses. If `a.hours` is `12.0`, it allows. This is correct.
    *   **However:** The default is `package_pin.WINDOW_H` (12.0). The argument is `type=float`. If a user passes `--hours 12.0000001`, it refuses. This is strict.
    *   **P1:** The refusal message says "outside (0, 12]". This is correct.

### P1 Findings (Major)

**4. `pipeline/candidates.py`: `expire` function does not update `lineup` or `history` correctly for "for good"**
*   **Location:** `pipeline/candidates.py` (lines 27-49 in diff context).
*   **Issue:** `expire` calls `outcome(e, "expired", ...)`. `outcome` sets `state` to `"closed"` and `until` to `None`. This pre

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1810 (ruling 76: the 12 h window on the render clock, the registry expiry, the render-clock re-check, delivered speech re-posted): cycle 1 consensus

- **grok:** "SHIP: no", on one P0 and one P1. Both are refuted below with the code; the P1's durability is now pinned
  by a test.
- **qwen:** "SHIP: No", on two P0s. Both are refuted below.
- **glm:** "SHIP: yes with conditions", no P0. Its conditions are met below.

## Consensus, implemented

**C1-a (grok P1, glm P1-1): can a later seed revive an expired candidate? ("never offered again")**
- The code already holds. `seed()` adds a line-up only when its key is not in the registry
  (`if k not in reg["candidates"]`). It applies "package" only to an entry that is not closed. It seeds each record
  once.
- Durability is now PINNED: test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good seeds a later record
  that passes, and even packages, the expired line-up. It stays closed / expired and is never due.

**C1-b (grok P0, qwen P2-8, glm P1-2 / P2-1, all three): REPOST_ALIGN_MIN is not in the diff.**
- It is ruling 53's module constant, `REPOST_ALIGN_MIN = 0.80` (pipeline/package.py:877), resolved when
  same_speech() is called.
- TestRuling76Window calls same_speech and passes, so there is no NameError.
- The docstring now names it ("ruling 53's 0.80").

## Implemented (single reviewer, verified)

- **glm P2-1:** the bound `--hours 12` (and 6) is accepted. The run goes on past the check, and the test's refusal
  guard stops it at the proof dir.
- **glm P2-5:** same_speech's docstring said equal texts are the same speech, yet one-word texts never are. It now
  says "two texts of at least two words".
- **glm P1-5 / P2-7, and aligned:** eligibility._parse_time (behind usable's `expired`) reads a time WITHOUT a zone as
  no measurement, so expired. window_problems read it as UTC.
  - Now both refuse it (refuse more, never accept more).
  - A pin's source_published_at is utc_z()'s, which is already None for a zoneless time, so no pin changes.
  - E.age_hours never raises on a malformed time (`_parse_time` returns None).

## Refuted (evidence)

- **qwen P0-1** (same_speech is fuzzy, against L-k): L-k governs whether a LOCK's text equals the spoken words.
  same_speech decides only what is EXCLUDED as delivered speech. Its errors:
  - a wrong match loses one moment (fail closed);
  - a missed match would reuse delivered speech, the harm ruling 76 (b) forbids.
  Strict equality would miss every re-post cut differently. The guards (>= 8 words, runs of >= 3 words, 80 % of the
  shorter) keep shared common words from matching (the scattered-words test). qwen's examples are 3-word texts,
  which only an EQUAL text matches.
- **qwen P0-2** (the pin check should use the build's ctx.now): ruling 76 (c) says "re-checked against (a) at the
  moment they would render". The pin stage's real clock is that moment, and it is LATER than the build's start, so
  it only tightens. glm, answer 5: 

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1810/C2_STEP.diff (409 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index ea38cca..a45a456 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -18,6 +18,8 @@ record's tried entry and package.load_candidate rebuilds it. A try's outcome cla
   6 |    "line":    its clips passed but a line failed again            -> resting 6 h, then ONE try with fresh writes;
   7 |                                                                      a line failing that try too -> closed
   8 |    "budget":  a budget stopped it before an outcome               -> as it was
   9 | +  "expired": RULING 76 (18:08 Nov 13): a clip's source is over 12 h old on the render clock (expire()) -> closed for
  10 | +             good: "out of the candidates registry, never offered again"
  11 |  Pure functions; the driver (tests/package/proof_ledger.py) reads and writes the file."""
  12 |  from datetime import datetime, timedelta, timezone
  13 |  
  14 | @@ -45,7 +47,7 @@ def outcome(entry, cls, at, build, why=""):
  15 |      entry["history"].append({"build": build, "at": at, "class": cls, "fresh": bool(entry.get("trying_fresh")),
  16 |                               "why": str(why or "")[:300]})
  17 |      entry.pop("trying_fresh", None)
  18 | -    if cls in ("package", "clip"):
  19 | +    if cls in ("package", "clip", "expired"):
  20 |          entry["state"], entry["until"] = "closed", None
  21 |      elif cls == "line":
  22 |          if entry.get("fresh_used"):
  23 | @@ -88,6 +90,31 @@ def seed(reg, record, source):
  24 |      return added
  25 |  
  26 |  
  27 | +def expire(reg, published, now, window_h):
  28 | +    """RULING 76 (a): close for good (class "expired") every candidate not yet closed with a clip whose source was
  29 | +    published more than window_h before the render clock `now`, or whose publish time is not known (never assumed
  30 | +    fresh). published: {moment id: published_at}. -> [the keys expired now]."""
  31 | +    out = []
  32 | +    for k, e in reg["candidates"].items():
  33 | +        if e["state"] == "closed":
  34 | +            continue
  35 | +        old = []
  36 | +        for mid in e.get("lineup") or []:
  37 | +            try:
  38 | +                t = _at(published[mid])
  39 | +            except (KeyError, TypeError, ValueError):
  40 | +                old.append(f"{mid}: no known publish time")
  41 | +                continue
  42 | +            age = (now - t).total_seconds() / 3600.0
  43 | +            if age > window_h:
  44 | +                old.append(f"{mid}: {age:.1f} h")
  45 | +        if old:
  46 | +            outcome(e, "expired", now.isoformat(), "ruling 76", f"over {window_h:g} h on the render clock: " +
  47 | +                    "; ".join(old))
  48 | +            out.append(k)
  49 | +    return out
  50 | +
  51 | +
  52 |  def registered(reg):
  53 |      """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
  54 |      search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
  55 | diff --git a/pipeline/package.py b/pipeline/package.py
  56 | index ad6dd60..d9982e7 100644
  57 | --- a/pipeline/package.py
  58 | +++ b/pipeline/package.py
  59 | @@ -121,9 +121,44 @@ VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than i
  60 |                              "never relate one speaker to another"}
  61 |  
  62 |  
  63 | +SAME_SPEECH_MIN_WORDS = 8         # ruling 76 (b): below this, only an equal text is the same speech
  64 | +SAME_SPEECH_RUN = 3               # only runs of at least this many words in order count: never scattered common words
  65 | +
  66 | +
  67 | +def same_speech(a, b):
  68 | +    """RULING 76 (b): two texts of at least two words are the same speech when they are equal after normalisation
  69 | +    (canon.canon_tokens), or, with the shorter at least SAME_SPEECH_MIN_WORDS long, when at least REPOST_ALIGN_MIN
  70 | +    (ruling 53's 0.80) of the shorter one's words lie in runs of SAME_SPEECH_RUN or more words that the other says in
  71 | +    the same order (difflib's matching blocks): a re-post cut a little differently is still the same speech; a few
  72 | +    common words in common never are. It decides only what is EXCLUDED: a wrong match loses one moment (fail closed),
  73 | +    a missed one would reuse delivered speech."""
  74 | +    import difflib
  75 | +    import canon
  76 | +    ta, tb = canon.canon_tokens(a or ""), canon.canon_tokens(b or "")
  77 | +    short = min(len(ta), len(tb))
  78 | +    if short < 2:
  79 | +        return False
  80 | +    if ta == tb:
  81 | +        return True
  82 | +    if short < SAME_SPEECH_MIN_WORDS:
  83 | +        return False
  84 | +    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
  85 | +    return sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short
  86 | +
  87 | +
  88 | +def expired(m, now):
  89 | +    """RULING 76 (a): the moment's source is more than package_pin.WINDOW_H old on the render clock, or its publish time
  90 | +    cannot be read (never assumed fresh). No exception for a moment that is not time-sensitive."""
  91 | +    import package_pin
  92 | +    age = E.age_hours(m.get("published_at"), now)
  93 | +    return age is None or age > package_pin.WINDOW_H
  94 | +
  95 | +
  96 |  def usable(moments, ctx, delivered=(), optout=frozenset()):
  97 | -    """delivered: moment ids, or {"video_id", "start", "end"} of moments delivered in the previous 24 h; a moment that
  98 | -    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated)."""
  99 | +    """delivered: moment ids, or {"video_id", "start", "end"[, "text", "pin"]} of every DELIVERED clip. A moment that
 100 | +    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated),
 101 | +    and (RULING 76 b) neither is the same speech (same_speech) in any other video, re-posted by another channel or the
 102 | +    same one. RULING 76 (a): a moment whose source is over 12 h old on the render clock (ctx.now) is expired."""
 103 |      ids = {d for d in delivered if isinstance(d, str)}
 104 |      spans = [d for d in delivered if isinstance(d, dict)]
 105 |      out, why = [], {}
 106 | @@ -137,7 +172,13 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
 107 |          elif m.get("excluded"):
 108 |              why[mid] = f"hard exclusion (L-u): {m['excluded']}"
 109 |          elif mid in ids or overlap:
 110 | -            why[mid] = "delivered in the previous 24 h (or overlaps a delivered moment)"
 111 | +            why[mid] = "delivered (or overlaps a delivered moment)"
 112 | +        elif any(d.get("text") and d.get("video_id") != m["video_id"] and same_speech(d["text"], m.get("text"))
 113 | +                 for d in spans):
 114 | +            d = next(d for d in spans if d.get("text") and d.get("video_id") != m["video_id"] and
 115 | +                     same_speech(d["text"], m.get("text")))
 116 | +            why[mid] = (f"ruling 76 (b): the same speech as a delivered clip ({d.get('pin')}: {d.get('video_id')} "
 117 | +                        f"{d.get('start')}-{d.get('end')}), re-posted in another video")
 118 |          elif m["channel_id"] in optout:
 119 |              why[mid] = "channel opted out"
 120 |          elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
 121 | @@ -145,6 +186,9 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
 122 |          elif time_sensitive(m) and (E.age_hours(m["published_at"], ctx.now) is None or
 123 |                                      E.age_hours(m["published_at"], ctx.now) > TIME_SENSITIVE_H):
 124 |              why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
 125 | +        elif expired(m, ctx.now):
 126 | +            why[mid] = (f"ruling 76 (a): published {m.get('published_at')}, over 12 h before the render clock "
 127 | +                        f"{ctx.now.isoformat(timespec='seconds')}: expired")
 128 |          elif (m.get("speaker") or {}).get("turn_change_inside") is True:
 129 |              why[mid] = "a speaker change inside (L-v 1)"
 130 |          else:
 131 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 132 | index a846a1c..2a97444 100644
 133 | --- a/pipeline/package_pin.py
 134 | +++ b/pipeline/package_pin.py
 135 | @@ -82,6 +82,34 @@ TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE
 136 |  SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
 137 |  
 138 |  
 139 | +WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
 140 | +                         # RENDER clock; past it, expired for good (it superseded ruling 57's 72 h window)
 141 | +
 142 | +
 143 | +def window_problems(segments, now=None):
 144 | +    """RULING 76 (a) and (c): every segment's source was published within WINDOW_H of the render clock `now` (default:
 145 | +    this moment, so the check is made again whenever a pin would go to render). An unknown or unreadable publish time
 146 | +    is a problem (never assumed fresh), and so is a time without a zone: as eligibility._parse_time reads it, no
 147 | +    measurement (audit 1810 C1). -> [why]."""
 148 | +    now = now or datetime.now(timezone.utc)
 149 | +    out = []
 150 | +    for s in segments or []:
 151 | +        p = s.get("source_published_at") or s.get("published_at")
 152 | +        try:
 153 | +            t = datetime.fromisoformat(str(p).replace("Z", "+00:00"))
 154 | +        except (TypeError, ValueError):
 155 | +            out.append(f"ruling 76: {s.get('video_id')}: no readable publish time ({p!r})")
 156 | +            continue
 157 | +        if t.tzinfo is None:
 158 | +            out.append(f"ruling 76: {s.get('video_id')}: a publish time without a zone ({p!r}) is no measurement")
 159 | +            continue
 160 | +        age = (now - t).total_seconds() / 3600.0
 161 | +        if age > WINDOW_H:
 162 | +            out.append(f"ruling 76: {s.get('video_id')} was published {p}, {age:.1f} h before the render clock (over "
 163 | +                       f"{WINDOW_H:g} h): expired")
 164 | +    return out
 165 | +
 166 | +
 167 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 168 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 169 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 170 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 171 | index 38e802b..2b6ad64 100644
 172 | --- a/tests/package/proof_ledger.py
 173 | +++ b/tests/package/proof_ledger.py
 174 | @@ -81,7 +81,7 @@ def delivered_pins(paths):
 175 |              if not isinstance(segs, list) or not segs:
 176 |                  raise ValueError("no clip")
 177 |              spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
 178 | -                       "pin": pin["story_id"]} for s in segs]
 179 | +                       "pin": pin["story_id"], "text": s.get("approved_text")} for s in segs]   # ruling 76 (b)
 180 |              pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
 181 |                           "approved_at": at.isoformat(), "clips": len(segs)})
 182 |          except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:       # which pin (glm C3 P2-3)
 183 | @@ -96,7 +96,8 @@ def main(argv=None):
 184 |                      help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
 185 |                           "newest one's approved_at")
 186 |      ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 187 | -    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 188 | +    ap.add_argument("--hours", type=float, default=package_pin.WINDOW_H,
 189 | +                    help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
 190 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 191 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 192 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 193 | @@ -104,6 +105,9 @@ def main(argv=None):
 194 |                           "record (its tried[N]; default the first that passed), as it was judged")
 195 |      a = ap.parse_args(argv)
 196 |      now = datetime.now(timezone.utc)
 197 | +    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
 198 | +        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
 199 | +        return 2
 200 |      try:                                                 # read before anything is written (glm C2 N-4)
 201 |          delivered, last, pins = delivered_pins(a.delivered)
 202 |          since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 203 | @@ -126,6 +130,16 @@ def main(argv=None):
 204 |              with open(p) as f:
 205 |                  CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
 206 |          CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
 207 | +        pub = {}                                         # RULING 76 (a): the open candidates' clips' publish times,
 208 | +        for e in reg["candidates"].values():             # from the records that found them (unknown: expired)
 209 | +            if e["state"] != "closed":
 210 | +                try:
 211 | +                    with open(os.path.join(REPO, e["source"], "inputs.json")) as f:
 212 | +                        pub.update({m["moment_id"]: m.get("published_at") for m in json.load(f).get("moments") or []
 213 | +                                    if m.get("moment_id") in e["lineup"]})
 214 | +                except (OSError, ValueError, AttributeError, TypeError):
 215 | +                    pass
 216 | +        gone = CA.expire(reg, pub, now, package_pin.WINDOW_H)
 217 |          CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
 218 |      except (OSError, ValueError, KeyError, TypeError) as e:
 219 |          print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 220 | @@ -146,6 +160,8 @@ def main(argv=None):
 221 |          (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
 222 |      say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 223 |          f"{len(delivered)} clip spans out")
 224 | +    say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
 225 | +        (f": {gone}" if gone else ""))
 226 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 227 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 228 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 229 | @@ -223,7 +239,8 @@ def main(argv=None):
 230 |      if res["package"]:
 231 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 232 |          try:
 233 | -            lock = LP.pin_problems(res["package"])       # ruling 68: sealed only with a passing lock pre-check
 234 | +            lock = LP.pin_problems(res["package"]) + \
 235 | +                package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
 236 |              if lock:
 237 |                  raise package_pin.PinRefused("; ".join(lock))
 238 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 239 | @@ -244,6 +261,13 @@ def main(argv=None):
 240 |              say(f"PIN REFUSED: {e}")
 241 |      else:
 242 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 243 | +    hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries
 244 | +    res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
 245 | +                        "cleared": (res.get("prescreen") or {}).get("cleared"),
 246 | +                        "cuttable": (res.get("prescreen") or {}).get("cuttable"),
 247 | +                        "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
 248 | +    say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
 249 | +        f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
 250 |      try:                                         # the record is written whatever the ledger says (audit 0707 C1)
 251 |          after = round(router.spent(), 4)
 252 |      except Exception as e:                       # noqa: BLE001
 253 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 254 | index 7c06985..b477f88 100644
 255 | --- a/tests/package/test_candidates.py
 256 | +++ b/tests/package/test_candidates.py
 257 | @@ -117,6 +117,30 @@ class TestRegistry(unittest.TestCase):
 258 |              with self.assertRaises(ValueError):
 259 |                  CA.registered(reg)
 260 |  
 261 | +    def test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good(self):
 262 | +        reg = CA.new_registry()
 263 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
 264 | +        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")              # already closed: untouched
 265 | +        pub = {m: (T0 - timedelta(hours=2)).isoformat() for m in "abcdefghi"}
 266 | +        pub["e"] = (T0 - timedelta(hours=12, minutes=1)).isoformat()                    # one clip over 12 h
 267 | +        del pub["c"]                                                                    # one clip of unknown age
 268 | +        self.assertEqual(sorted(CA.expire(reg, pub, T0, 12.0)), ["a+b+c", "d+e+f"])
 269 | +        e = reg["candidates"]["d+e+f"]
 270 | +        self.assertEqual((e["state"], e["history"][-1]["class"]), ("closed", "expired"))
 271 | +        self.assertIn("e: 12.0 h", e["history"][-1]["why"])
 272 | +        self.assertIn("c: no known publish time", reg["candidates"]["a+b+c"]["history"][-1]["why"])
 273 | +        self.assertEqual(reg["candidates"]["g+h+i"]["history"][-1]["class"], "clip")
 274 | +        self.assertEqual(CA.due(reg, T0), [])                                          # never offered again
 275 | +        fresh = CA.new_registry()
 276 | +        CA.seed(fresh, record(T0, [t(["a", "b"])]), "r")
 277 | +        self.assertEqual(CA.expire(fresh, {"a": T0.isoformat(), "b": T0.isoformat()}, T0, 12.0), [])
 278 | +        # audit 1810 C1 (grok P1, glm P1-1): a later record that passes the same line-up again never revives it
 279 | +        CA.seed(reg, record(T0 + timedelta(hours=1), [t(["d", "e", "f"])], package={"segments": [
 280 | +            {"moment_id": m} for m in "def"]}), "r-later")
 281 | +        self.assertEqual((reg["candidates"]["d+e+f"]["state"], reg["candidates"]["d+e+f"]["history"][-1]["class"]),
 282 | +                         ("closed", "expired"))
 283 | +        self.assertEqual([k for k, _, _ in CA.due(reg, T0 + timedelta(hours=1))], [])
 284 | +
 285 |      def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 286 |          reg = CA.new_registry()
 287 |          for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 288 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 289 | index 74817cb..807e186 100644
 290 | --- a/tests/package/test_ledger_build.py
 291 | +++ b/tests/package/test_ledger_build.py
 292 | @@ -762,6 +762,24 @@ class TestDriverRefuses(unittest.TestCase):
 293 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 294 |                           before)
 295 |  
 296 | +    def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
 297 | +        """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
 298 | +        carry the approved text, for the same-speech rule."""
 299 | +        sys.path.insert(0, HERE)
 300 | +        import proof_ledger as PLG
 301 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 302 | +                                                                                 "MOMENTS_PIN_LY.json")]
 303 | +        with mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
 304 | +            for h in ("12.5", "72", "0", "-1"):
 305 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", h]), 2, h)
 306 | +            self.assertIn("REFUSED (ruling 76)", err.getvalue())
 307 | +            for h in ("12", "6"):                       # audit 1810 C1 (glm P2-1): the bound itself is accepted; the run
 308 | +                with self.assertRaises(AssertionError) as cm:   # goes on, and the guard stops it at the proof dir
 309 | +                    PLG.main(["--delivered", *pins, "--hours", h])
 310 | +                self.assertIn("went on to write a proof dir", str(cm.exception))
 311 | +        spans, _, _ = PLG.delivered_pins(pins)
 312 | +        self.assertTrue(all(isinstance(s["text"], str) and s["text"] for s in spans))
 313 | +
 314 |      def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
 315 |          """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
 316 |          pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
 317 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 318 | index b395b01..8c8c160 100644
 319 | --- a/tests/package/test_medley.py
 320 | +++ b/tests/package/test_medley.py
 321 | @@ -2166,6 +2166,55 @@ class TestRuling72Lock(unittest.TestCase):
 322 |          self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 323 |  
 324 |  
 325 | +class TestRuling76Window(unittest.TestCase):
 326 | +    """RULING 76 (18:08 Nov 13): (a) a moment only while its source is <= 12 h old on the RENDER clock, no exception for
 327 | +    one that is not time-sensitive; (b) a delivered span never again, nor the same speech re-posted in another video;
 328 | +    (c) the pin stage re-checks (a) on the render clock."""
 329 | +
 330 | +    def at(self, mid, hours_ago, **kw):
 331 | +        return dict(pm(mid, mid.upper(), 12.0, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 332 | +
 333 | +    def test_a_moment_over_12_h_or_of_unknown_age_is_expired(self):
 334 | +        ok, why = PK.usable([self.at("a", 11.9), self.at("b", 12.1), dict(self.at("c", 1), published_at=None),
 335 | +                             dict(self.at("d", 1), published_at="yesterday")], ctx())
 336 | +        self.assertEqual([m["moment_id"] for m in ok], ["a"])
 337 | +        for mid in "bcd":
 338 | +            self.assertIn("ruling 76 (a)", why[mid])
 339 | +        self.assertIn("L-v 3", PK.usable([self.at("t", 30, risk=("time_sensitive",))], ctx())[1]["t"])   # as before
 340 | +
 341 | +    def test_delivered_speech_is_never_used_again_in_any_other_video(self):
 342 | +        said = "Currencies are often born for political reasons, but fail for economic reasons."
 343 | +        delivered = [{"video_id": "vD", "start": 10.0, "end": 20.0, "pin": "moments-x-1", "text": said}]
 344 | +        copy = dict(self.at("c", 1), text="Currencies are often born for political reasons but fail for economic "
 345 | +                                          "reasons, he said.", video_id="vOther")
 346 | +        other = dict(self.at("o", 1), text="Bitcoin launched in January of 2009 and was never renamed.",
 347 | +                     video_id="vOther2")
 348 | +        same_video_elsewhere = dict(self.at("s", 1), text=said, video_id="vD", start=40.0, end=50.0)
 349 | +        ok, why = PK.usable([copy, other, same_video_elsewhere], ctx(), delivered)
 350 | +        self.assertEqual([m["moment_id"] for m in ok], ["o", "s"])         # (the same video: the span rule, as before)
 351 | +        self.assertIn("ruling 76 (b): the same speech as a delivered clip (moments-x-1: vD 10.0-20.0)", why["c"])
 352 | +        self.assertTrue(PK.same_speech(said, said.upper()))
 353 | +        self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))                 # never on one word
 354 | +        self.assertFalse(PK.same_speech(said, "Currencies fail."))             # short: only an equal text
 355 | +        self.assertTrue(PK.same_speech("Bitcoin fixes this.", "bitcoin fixes this"))
 356 | +        scattered = "Currencies are rarely political, but reasons fail for many economic reasons of their own."
 357 | +        self.assertFalse(PK.same_speech(said, scattered))                      # common words, not runs of three
 358 | +
 359 | +    def test_the_pin_stage_re_checks_on_the_render_clock(self):
 360 | +        now = NOW
 361 | +        fresh = {"video_id": "v1", "source_published_at": (now - timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")}
 362 | +        stale = {"video_id": "v2", "source_published_at": (now - timedelta(hours=12, minutes=1)).isoformat()}
 363 | +        naive = {"video_id": "v3", "source_published_at": (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()}
 364 | +        self.assertEqual(package_pin.window_problems([fresh], now), [])
 365 | +        p = package_pin.window_problems([fresh, stale, {"video_id": "v4", "source_published_at": None}, naive], now)
 366 | +        self.assertEqual(len(p), 3)
 367 | +        self.assertIn("v2 was published", p[0])
 368 | +        self.assertIn("over 12 h): expired", p[0])
 369 | +        self.assertIn("v4: no readable publish time", p[1])
 370 | +        self.assertIn("v3: a publish time without a zone", p[2])               # audit 1810 C1: no measurement
 371 | +        self.assertEqual(package_pin.WINDOW_H, 12.0)
 372 | +
 373 | +
 374 |  class TestRuling65Caption(unittest.TestCase):
 375 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 376 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 377 | @@ -2532,7 +2581,8 @@ class TestProposal1PoolFill(unittest.TestCase):
 378 |  class TestRuling57Fresh(unittest.TestCase):
 379 |      """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
 380 |      with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
 381 | -    TRIED first: inside an angle and across angles."""
 382 | +    TRIED first: inside an angle and across angles. RULING 76 (18:08 Nov 13) superseded the 72 h window: a moment over
 383 | +    12 h old is expired and never offered (the line-up preference itself is unchanged, and moot inside 12 h)."""
 384 |  
 385 |      def at(self, mid, ch, dur, hours_ago, **kw):
 386 |          return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
 387 | @@ -2554,12 +2604,18 @@ class TestRuling57Fresh(unittest.TestCase):
 388 |          self.assertLess(PK.fresh_key(unknown, NOW), PK.fresh_key(ms[:3], NOW))   # ranks below 50-70 h, never newest
 389 |  
 390 |      def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
 391 | -        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 392 | +        """Since ruling 76: the 13-70 h moments are expired, never offered to the angle writer, and the line-up is
 393 | +        built from the 12 h pool."""
 394 | +        ms = [self.at("h", "A", 12.0, 13), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 395 |                self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
 396 | -        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 397 | +        rig = Rig(ms, [["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 398 |          out = rig.run()
 399 | -        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
 400 | +        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])
 401 |          self.assertEqual(out["angles"][0]["hook"], "f")
 402 | +        prompt = next(p for r, p in rig.prompts if r == "angle_write")
 403 | +        for old in ("h", "x", "y"):
 404 | +            self.assertNotIn(f"id={old} ", prompt)                            # never offered
 405 | +            self.assertIn("ruling 76 (a)", out["unusable"][old])
 406 |  
 407 |  
 408 |  class TestRuling41Search(unittest.TestCase):
 409 | 
```

---

You are auditing a change to the medley pin builder on branch pp-selectid (Protocol Pulse: it builds sealed pins of
other channels' clips; an integrator renders them). Only state what you can verify from the diff; if uncertain, say so;
do not guess.

The order being implemented, RULING 76 (orchestrator 18:08 Nov 13), quoting the owner: "do we have a system in place to
stop our coping system from reusing old clips? We need to delete all the contents after like 6 to 12 hours so that we
never reuse any of it". It supersedes ruling 57's 72 h window, effective now for every build and every pin not yet
rendered:
 (a) "A moment is usable only while its source video's published_at is within 12 HOURS of the RENDER clock. Past 12 h
     it is expired for good: out of the pool, out of the candidates registry, never offered again. No exception for
     'not time-sensitive'."
 (b) "A span that has been DELIVERED in any video is never used again (already so: keep it, and extend it to any
     overlapping span of the same video and to the same speech re-posted on another channel)."
 (c) "Open candidates and sealed-but-unrendered pins are re-checked against (a) at the moment they would render."
 (d) STATE line 1 carries: moments inside 12 h, how many cleared, how many cuttable, hooks >= 4.
 "Audit as one change (the window constant, the registry expiry, the render-clock re-check)." If the 12 h pool cannot
 form a video, the stage it dies at is reported, rather than widening the window.

The change:
1. package_pin.WINDOW_H = 12.0 and window_problems(segments, now=None):
   - each segment's source published within 12 h of the render clock (default: this moment);
   - an unknown or unreadable time is a problem; a zoneless time is UTC, the pipeline's own convention.
   seal() is not changed (the integrator imports this file live for its seal recompute).
2. package.usable():
   - a moment whose source is over 12 h old on ctx.now (the build's render clock), or of unknown age, is out:
     "ruling 76 (a)". It sits after the time-sensitive rule, so a stale time-sensitive moment still reports L-v 3;
     both exclude.
   - delivered spans may carry their text. A moment in ANY OTHER video whose text is the same speech as a delivered
     clip (same_speech) is out: "ruling 76 (b)".
   - same_speech: equal canonical tokens; or, with the shorter text at least 8 words, at least 80 % of the shorter
     one's words in runs of >= 3 words that the other says in the same order (difflib matching blocks).
   - The same-video overlap rule is unchanged.
3. candidates.expire(reg, published, now, window_h): every candidate not yet closed with a clip over 12 h, or of
   unknown age, closes for good, class "expired" (outcome() accepts it).
4. The driver (tests/package/proof_ledger.py):
   - --hours defaults to 12, and a value outside (0, 12] refuses the run before anything is written;
   - delivered spans carry the pin's approved_text;
   - in the refusal block, after the registry is seeded and its stored times checked (CA.due), the open candidates'
     clip publish times are read from the records that found them (inputs.json; unknown means expired), and
     CA.expire runs before any candidate is tried;
   - at the pin stage, package_pin.window_problems(segments) on the real clock joins ruling 68's pin_problems
     (refuse);
   - the record carries ruling_76 counts (inside 12 h, cleared, cuttable, hooks >= 4) and logs them.
5. Tests:
   - test_medley TestRuling76Window (3): (a) with an unknown or unreadable time; (b) with a re-post in another video
     and same_speech's limits; (c) window_problems;
   - ruling 57's build test rewritten: the old moments are now expired and never offered;
   - test_candidates: expire;
   - test_ledger_build: --hours over 12 refuses (under the refusal guard); delivered spans carry text.
   Mutation runs: each of usable's (a) and (b), outcome's "expired", and the --hours refusal fails a test.
   15 suites OK.

Check, against the diff:
- that no moment over 12 h (or of unknown age) can enter a line-up, a candidate try or a pin, on any path;
- that no delivered speech can be reused in another video (and what same_speech might wrongly merge or miss);
- that the registry expiry is for good, and cannot be undone by a later seed;
- that the window can never be widened by an argument;
- that the pin-stage re-check uses the render clock at that moment;
- that nothing else a gate accepts changes, and seal() is unchanged.

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
