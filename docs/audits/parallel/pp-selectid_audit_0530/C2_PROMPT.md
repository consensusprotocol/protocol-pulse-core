# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0530
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 692 s finish=length usage in 15632 / out 24000 usd~0.407 (upper-bound price)

# Audit — pp-selectid, ruling 33 part 2 (trim one leading word)

Scope: I verified only what the diff shows. Where the diff references helpers I cannot see (`no_role_on_screen`, `no_topic`, `E.spoken`, `canon.canon_tokens`, `self_repair`, `Rig`, `spk`, `ctx`, `pm`, `source`, `labels`, `src_of`, `CLIP_MIN_SCORE`, `CONJUNCTIONS`, `REPLY_FRAGMENTS`, `_words`, `opener`, `topical_screen`), I note the dependency and mark uncertainty rather than guess.

---

## P0 findings

**P0-1. `trim_variant` (package.py:39–68, diff lines 39–68): the variant's `end` is never recomputed, and `duration_s` is derived from `m["end"]` — but the render's contract says "start/end bound the KEPT words", and the variant's `words` now begin at `w0+1`.**

Scenario: the variant carries `words=[w0+1, w1]` and `start = nxt["start"]`, but keeps the parent's `end` (via `dict(m, ...)` — `end` is not overridden). If the parent's `end` was derived from token `w1`'s end, this is consistent; but if the parent's `end` was ever padded or rounded differently from the token record (e.g. the miner's `end` includes trailing decay, or `m["end"]` ≠ `toks[w1]["end"]`), the variant's `end`/`duration_s` silently disagree with the kept-word span. The diff's own test (test_medley.py:371) only asserts `duration_s ≈ end − v["start"]` — it never asserts `v["end"] == toks[w1]["end"]`. The render's contract binds start/end to the kept words; nothing in the diff proves the inherited `end` does. **Verify `m["end"]` is exactly `toks[w1]["end"]` upstream, or recompute it.** (Uncertain: `m`'s provenance is not in the diff.)

**P0-2. `trim_variant` (package.py:54): `word, nxt = toks[w0].get("word") or "", toks[w0 + 1]` — if `w0 + 1 == w1` (a one-word moment) or `w0+1 > w1`, the variant's kept span is empty or inverted, and `E.spoken(toks[w0+1:w1+1])` yields `""`.**

Scenario: a moment whose entire text is one word — say "But." — with `words=[w0, w0]`. Then `w1 == w0`, the guard `if w1 <= w0: return None` catches it. Good. But if `w1 == w0 + 1` (two-word moment, e.g. "But Bitcoin."), the variant's kept text is one word, `duration_s` is that word's duration, and the variant proceeds. That is presumably intended. However, the guard `w1 <= w0` is checked **after** `toks[w0+1]` is already evaluated — no, it's on the next line, so `toks[w0+1]` is evaluated first and can raise `IndexError` if `w0+1 >= len(toks)`. That IS caught by the `except (IndexError, ...)` — so it returns None. OK, fail-closed. Downgrade: this is actually safe. **Withdrawn as P0; noted as correct-by-exception.**

**P0-3. `build()` (package.py:88–89): the trim variants are appended AFTER the no-role filter but BEFORE the ad-read screen and step A — but the variant's `moment_id` is `"<id>~trim"`, and `truth_for`'s cache is keyed by `m["moment_id"]`.**

Scenario: if the same build is re-run (retry, or the 113-moment rebuild of item 42), the cache key `t~trim` collides with nothing — fine. But `truth_for` (package.py:74–82) catches all exceptions and stores `{"ok": False, "error": ...}` — fail-closed, good. However: **the variant inherits the parent's `channel_id`, `channel_name`, `published_at`, `transcript_sha256` via `dict(m, ...)` — but the diff does not show whether `no_role_on_screen`/`no_topic`/step A/ad-read/angle-building key anything else off `moment_id`** (e.g. `delivered`, `optout`, `a_by`, `fails`, `coh_ok`, `coh`, `exc`, `dup`, `rt_ok` — all keyed by `moment_id` in `build()`'s signature and the `inventory()` call). The variant's id `t~trim` will not be found in `a_by`, `fails`, `exc`, `optout`, `delivered`, `dup`, `rt_ok` — those maps were built for the parent ids. If any of those maps gates the variant's progress (e.g. `cleared = {m: m for m in ms if m["moment_id"] in a_by and not fails.get(...)}` at package.py:94), **a variant whose parent was cleared will not be found in `a_by` under its `~trim` id and will be silently dropped from `cleared` — the variant never reaches a package.** The diff's test at test_medley.py:421–434 monkeypatches `trim_variant` and passes `no_hook={"b~trim"}` to the `Rig`, which suggests the rig knows about `~trim` ids — but the rig is not in the diff, so I cannot verify that `a_by`/`fails`/`exc`/`optout`/`delivered`/`dup`/`rt_ok` are keyed to include `~trim` ids. **This is the highest-risk item: if those maps are keyed by parent id only, the feature silently does nothing (or, worse, the parent is dropped by no_role and the variant is dropped by the id-keyed maps, so a ruling-33 moment ships as nothing).** Must-verify: how `a_by`, `fails`, `exc`, `optout`, `delivered`, `dup`, `only if` — the angle/step-A machinery — resolve `~trim` ids.

Wait — re-reading: `ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())` — the variants are appended at the END of `ms`. Then `ad_read = ad_read_out(ms, sources)` runs on the combined list, then `ms

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 49 s finish=stop usage in 15568 / out 803 usd~0.098 (upper-bound price)

**P0: pipeline/stand_alone.py:201-205 (trimmed_opener) + tests/package/test_medley.py:386 (test_the_scorer_verdict_is_pending...)**  
When rate=None (exactly as called from package.stand_alone_check:29 and used at pin stage), score=None reaches trimmed_opener for any trimmed segment. It returns (False, "...no clip-scorer verdict... (fail closed, ruling 33 part 2)"). The test nevertheless asserts r["ok"] is True and scorer_pending=["clip_01"]. These cannot both be true from the diffed code; the gate cannot be both fail-closed and ok=True. Violates L-j / L-m / LAW 20 on missing measurement and never changing what a check accepts.

**P1: pipeline/package.py:106-108 (trim_cut) + 88 (trims added before step A) + transcript_truth.py:262-280 (edges trimmed handling)**  
(a) is enforced at pin: trimmed moments failing hook_onset are removed from cleared and recorded in prescreen["trim_cut"]; such a moment is out at any place. (c) is enforced at pin: trim_variant:66 returns None if no_role_on_screen(v) or no_topic(v) on the trimmed text, so no variant reaches usable moments. (b) remains pending (scorer_pending list). Untrimmed paths, old pins (SEALED_LATER), and non-trimmed IN logic are byte-identical to prior code; tests/package/test_angles.py:308-327 and test_medley.py:375-380 verify this.

**P1: pipeline/package_pin.py:142-161 (trim_problems), 172 (called), 180 (to_pin copy), 132 (SEALED_LATER), package.py:19+64+98 (fields in rows / out["trimmed"])**  
Pin fields match the render contract exactly when present (both keys or neither; canonical token in TRIM_WORDS; 0 <= untrimmed_start < start; approved_text/start/end bound kept words). Malformed pins are refused (PinRefused). When absent the pin is unchanged. Seal hash changes only when the trim fields are present. scorer_pending is carried in the stand_alone gate row (package.py:30, package_pin.py:118) and is visible; nothing in the diff pretends the scorer affirmed it.

**P2: pipeline/package.py:57-67 (trim_variant), 89 (added to ms before ad-read / step A), transcript_truth.py:289 (verify_segment passes trimmed)**  
trim_variant only emits a variant for the exact one leading TRIM_WORDS token, adjusts text/start/words/duration_s/untrimmed_start, and rejects if the trimmed text itself would fail no_role/no_topic. edges() with trimmed=None is unchanged; with trimmed it requires the recogniser heard exactly that word immediately before the kept span and moves the IN sentence boundary before the trimmed word (or fails IN). All covered by the added tests; no other call sites altered.

"pending at the render" is not a defensible reading of item-42 from the diff. The order says "USE RULING 33 PART 2 NOW (merged on main 11e361cc)" and "Rebuild with trimmed_leading as soon as your side is audited". The diff implements the pin-side fields and the fail-closed scorer path, yet the test expects overall ok=True while the orchestrator comment and trimmed_opener both acknowledge the render will see a refused scorer. This collides with L-j (missing data rejects), L-m (nothing measured is never a pass), and the governing rule that the pin must never seal what the render would refuse except where the orchestrator explicitly carved out an exception. The diff does not contain such a carve-out that reconciles the test and the fail-closed logic.

**SHIP: no**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 55 s finish=stop usage in 17132 / out 3711 usd~0.107 (upper-bound price)

I’ll audit the diff strictly against the stated laws, the orchestrator’s Ruling 33 / item 42, and the render contract. I’ll focus on whether (a) and (c) are truly enforced at the pin stage, whether the scorer’s pending status is honestly represented, whether the pin fields match the render contract, and whether untrimmed/legacy behavior is preserved.

## P0 Findings

**P0-1: `pipeline/package.py:106-109` — Acoustic onset rule (a) is applied to the *original* cut, not the *trimmed* cut.**
*   **Scenario:** A moment `m` starts at `t=1.0s` with the word "But". The trimmed variant `v` starts at `t=1.2s` (the next word). The code computes `hook_onset` for `m` (the original moment) in the `cleared` dict. Then it checks `if m.get("trimmed_leading") ...` on the *original* moment `m` (which does *not* have `trimmed_leading` set; only the variant `v` does).
    *   Wait, let's look closer at `build()`.
    *   `ms` is filtered to remove `no_role` moments.
    *   `trims` are created from `no_role` moments.
    *   `ms` becomes `[originals] + [trims]`.
    *   `ad_read` is computed on `ms`.
    *   `cleared` is computed on `ms` (which includes trims).
    *   `hook_onset` is measured for `cleared` moments.
    *   The check at line 106: `trim_cut = {mid: ... for mid, m in cleared.items() if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}`.
    *   Here `m` is the *trimmed variant* (because it has `trimmed_leading`).
    *   Does `hook_onset` measure the *trimmed* cut?
    *   `hook_onset` is likely a function that checks the audio before `m["start"]`.
    *   For the trimmed variant `v`, `v["start"]` is the start of the *kept* words (e.g., "Bitcoin...").
    *   The acoustic onset rule (Ruling 33a) requires "genuine sub-speech audio before the first onset".
    *   If `hook_onset` checks the silence before `v["start"]`, it is checking the gap between "But" and "Bitcoin".
    *   However, the law says: "The START OF PLAYBACK keeps the D1 rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine sub-speech audio before the first onset".
    *   For a *clip* (not a hook), the law says: "Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms)."
    *   BUT, Ruling 33(a) specifically says: "the acoustic onset rule is met on the **trimmed cut**".
    *   The "trimmed cut" is the point where "But" ends and "Bitcoin" begins.
    *   If `hook_onset` is designed for hooks (checking file head or lead-in), does it apply to clips?
    *   The code applies `hook_onset` to *all* cleared moments, including clips.
    *   If `hook_onset` fails for a clip because there isn't 80ms of silence before "Bitcoin" (because "But" was just spoken), the clip is rejected.
    *   Is this correct? Ruling 33(a) says "acoustic onset rule is met on the trimmed cut". This implies the cut point (start of "Bitcoin") must have the required quiet.
    *   The code *does* reject if `hook_onset` fails. So (a) is enforced.
    *   **However**, there is a subtle issue. `hook_onset` is typically a "hook" check. Does it behave correctly for a mid-video clip?
    *   The comment says: "G17a at the pin stage: genuine quiet before the first onset".
    *   If the "first onset" is "Bitcoin", and "But" ended 50ms ago, is that "genuine quiet"?
    *   The law says "Inside the video there is no lead / tail minimum".
    *   If `hook_onset` enforces an 80ms lead-in for *clips*, it might be too strict or incorrect for non-hook segments.
    *   But Ruling 33(a) explicitly invokes the "acoustic onset rule" for the trimmed cut.
    *   Let's check if `hook_onset` is the right function. The code uses `m["hook_onset"]`.
    *   If `hook_onset` is only valid for hooks, applying it to clips might be a logic error.
    *   **Correction:** The code applies `hook_onset` to *all* cleared moments. If `hook_onset` is a generic "is there quiet before this start time" check, it's fine. If it's specifically "is this a valid hook start (file head or 80ms lead)", it might be misapplied to clips.
    *   Given the ambiguity, I will flag this as a potential P1/P2, but let's look for harder failures.

**P0-2: `pipeline/package.py:30` — `stand_alone_check` does not pass `rate` to `SA.check_edl` for trimmed segments, but claims to record `scorer_pending`.**
*   **Scenario:** `stand_alone_check` calls `SA.check_edl(edl, rate=None, ...)`.
*   In `stand_alone.py`, `check_edl` with `rate=None` will fail closed for any segment that needs the scorer (conjunctions or trimmed words).
*   The code in `package.py` line 30: `r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs) if m.get("trimmed_leading")]`.
*   This records *which* segments are pending.
*   But `r` (the result of `check_edl`) will have `ok: False` for those segments because `rate=None` causes `trimmed_opener` to return `

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0530 (ruling 33 part 2 at the pin stage, item 42): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** Verdicts:
- grok: "SHIP: no", on one P0 that rests on a misreading (K1) and a policy objection (K5);
- qwen: two P0s, one a misreading (K2), the other the same design question from the opposite side (it argues the
  pin should be sealed with the verdict pending, which is what the code does);
- glm: ten numbered "P0"s. glm was cut at 24000 output tokens (finish=length). Each is answered below; four were real
  defects and are fixed.

## Misreadings (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | grok P0: with rate=None, check_edl fails a trimmed segment closed, so r["ok"] cannot be True | stand_alone_check builds its EDL with NO selection_lock (package.py, the edl dict: index, text, channel, duration). trimmed_word(s) is None, so trimmed_opener never runs at the pin stage, and the opener rule judges the TRIMMED text's own first word. glm P0-4 and P0-9 read this correctly: a divergence from the render by design, which is the policy question in K5. |
| K2 | qwen P0-1: the acoustic onset rule (a) is measured on the ORIGINAL cut | hook_onset_for(m, ...) passes m["words"][0] and m["start"], and for a variant those are the trimmed ones: words = [w0 + 1, w1], start = the next word's start (trim_variant). The trimmed cut is what is measured. |
| K3 | glm P0-1: the variant's end is never recomputed | The kept words still END at w1. end is unchanged by construction, and duration_s = end - the new start. That is the contract ("start/end bound the KEPT words"). |
| K4 | glm P0-5 / P0-6: the trimmed word is the recogniser's first word, or i == 0 | P0-5: prev is None, so the existing IN rule applies (the file head, or a >= 700 ms stretch from the window's start). P0-6: the failure record reads `ws[i - 1]["text"] if i > 0 else None`, which is guarded. |

## Real defects: FIXED

| # | finding | fix |
|---|---|---|
| F1 | glm P0-2: a variant inherits the original's eligibility, so a trimmed text could fall under the 5-word statement minimum | trim_variant needs at least E.MIN_STATEMENT_TOKENS (5) canonical tokens in the kept words. Tested ("But Bitcoin wins now." gives no variant). |
| F2 | glm P0-8: trim_problems' float(s["start"]) could raise a non-PinRefused exception out of to_pin | Every number is checked first (bools excluded); a missing or non-numeric start is a refusal reason. Tested. |
| F3 | glm P0-10: a trimmed word with no canonical token fell back to the untrimmed IN rule | It fails closed: "the trimmed word has no canonical token". Tested with "" and "...". |
| F4 | glm P0-7: a generator used as a membership list | Replaced by a plain token check (`tok[0] in TRIM_WORDS`). |

## K5: the policy question (open, put to the orchestrator)

- **The design:** item 42 says "use ruling 33 part 2 now". The pin stage cannot run the render's clip scorer (GPU0;
  this session may n

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0530/C2_STEP.diff (467 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 2b2f07f1..959e2702 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -79,6 +79,7 @@ SEARCH_USD_REPORTED = 3.00         # ruling 41: a build may spend $3 (vendor-rep
   6 |  SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE delivered (its own line-up). The estimate
   7 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   8 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   9 | +TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
  10 |  SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
  11 |                                     # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
  12 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  13 | @@ -299,7 +300,9 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  14 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
  15 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  16 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  17 | -                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
  18 | +                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  19 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  20 | +                           if m.get("trimmed_leading") else {})}                      # ruling 33 part 2, sealed
  21 |                         for lb, m in zip(labels(len(segs)), segs)],
  22 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  23 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  24 | @@ -579,7 +582,9 @@ def stand_alone_check(segs):
  25 |      edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  26 |             "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  27 |                       for i, m in enumerate(segs[1:], 1)]}
  28 | -    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  29 | +    r = SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  30 | +    r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs) if m.get("trimmed_leading")]   # ruling 33
  31 | +    return r                           # part 2: the render's clip scorer judges a trimmed segment on GPU0 (item 42)
  32 |  
  33 |  
  34 |  def ad_read_out(ms, sources):
  35 | @@ -601,6 +606,41 @@ def ad_read_out(ms, sources):
  36 |      return out
  37 |  
  38 |  
  39 | +def trim_variant(m, sources):
  40 | +    """RULING 33 PART 2 (the render merged it at 11e361cc; the orchestrator's 04:58 item 42, "use it now"). A moment
  41 | +    whose first word is ONE of TRIM_WORDS, left out by the render's STAND_ALONE opener rule, may be cut one word in.
  42 | +    The variant's text, start and words begin at the next word of its word record (start/end bound the KEPT words),
  43 | +    and it carries trimmed_leading (the word as spoken) and untrimmed_start (the trimmed word's start). It must take a
  44 | +    place under the render's STAND_ALONE as trimmed (no_role_on_screen and no_topic both None on the trimmed text).
  45 | +    Then it is judged like any moment: step A on the trimmed span (ruling 33 c), L-v 2 with the trimmed word heard right
  46 | +    before the clip (transcript_truth.edges), and the acoustic onset rule on the trimmed cut (ruling 33 a, build()).
  47 | +    The clip scorer's verdict (ruling 33 b) is the render's, on GPU0: pending at the render (stand_alone_check). -> the
  48 | +    variant, or None."""
  49 | +    import canon
  50 | +    try:
  51 | +        src = src_of(m, sources)
  52 | +        w0, w1 = m["words"]
  53 | +        toks = src.tokens
  54 | +        word, nxt = toks[w0].get("word") or "", toks[w0 + 1]
  55 | +    except (KeyError, IndexError, TypeError, ValueError):
  56 | +        return None
  57 | +    tok = canon.canon_tokens(word)[:1]
  58 | +    if w1 <= w0 or not tok or tok[0] not in TRIM_WORDS:
  59 | +        return None
  60 | +    if len(canon.canon_tokens(E.spoken(toks[w0 + 1:w1 + 1]))) < E.MIN_STATEMENT_TOKENS:
  61 | +        return None                          # the kept words still make a statement (audit 0530 C1, glm P0-2)
  62 | +    a = nxt.get("start")
  63 | +    if not isinstance(a, (int, float)) or isinstance(a, bool) or not float(m["start"]) <= float(a) < float(m["end"]):
  64 | +        return None
  65 | +    v = dict(m, moment_id=f"{m['moment_id']}~trim", text=E.spoken(toks[w0 + 1:w1 + 1]), start=float(a),
  66 | +             duration_s=round(float(m["end"]) - float(a), 2), words=[w0 + 1, w1],
  67 | +             trimmed_leading=word.strip().strip(".,!?;:\"'()\u201c\u201d\u2014\u2026"),
  68 | +             untrimmed_start=float(m["start"]), trimmed_from=m["moment_id"])
  69 | +    if no_role_on_screen(v) or no_topic(v):
  70 | +        return None
  71 | +    return v
  72 | +
  73 | +
  74 |  def no_topic(m):
  75 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  76 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  77 | @@ -1070,7 +1110,7 @@ def truth_for(router, m, work_dir, cache):
  78 |          import transcript_truth as TT
  79 |          try:
  80 |              cache[m["moment_id"]] = TT.verify_segment(router, m["video_id"], float(m["start"]), float(m["end"]),
  81 | -                                                      m["text"], work_dir)
  82 | +                                                      m["text"], work_dir, trimmed=m.get("trimmed_leading"))
  83 |          except Exception as e:                         # not measured: never a pass (law L-m)
  84 |              cache[m["moment_id"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
  85 |      return cache[m["moment_id"]]
  86 | @@ -1149,7 +1189,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  87 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  88 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  89 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  90 | -    ms = [m for m in ms if m["moment_id"] not in no_role]
  91 | +    trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
  92 | +    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
  93 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  94 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  95 |      wv, wf = _writers(router)
  96 | @@ -1157,7 +1198,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  97 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  98 |      levels = current_levels(sources.values(), ctx)
  99 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 100 | -           "no_role": no_role, "ad_read": ad_read,
 101 | +           "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 102 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 103 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 104 |             "package": None}
 105 | @@ -1191,6 +1232,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 106 |      out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 107 |                                        ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 108 |                                        str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 109 | +    trim_cut = {mid: out["prescreen"]["hook_onset"][mid] for mid, m in cleared.items()     # ruling 33 (a): the
 110 | +                if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}    # acoustic onset rule on the
 111 | +    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}                 # trimmed cut, any place
 112 | +    out["prescreen"]["trim_cut"] = trim_cut
 113 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 114 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
 115 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 116 | @@ -1660,6 +1705,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 117 |                                      "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 118 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 119 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 120 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 121 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 122 | +                                scorer_pending=stand.get("scorer_pending") or [])}
 123 |             if stand is not None else {}),
 124 |      }
 125 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 126 | index 101b0e28..c8a76d37 100644
 127 | --- a/pipeline/package_pin.py
 128 | +++ b/pipeline/package_pin.py
 129 | @@ -66,7 +66,10 @@ def recency_problems(segments):
 130 |  
 131 |  
 132 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
 133 | -                "speaker")                                 # the 00:05 ET Nov 13 order, item 3
 134 | +                "speaker",                                 # the 00:05 ET Nov 13 order, item 3
 135 | +                "trimmed_leading", "untrimmed_start")      # ruling 33 part 2 (render merged 11e361cc): only when a word
 136 | +                                                           # is trimmed, so every other pin seals as before
 137 | +TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
 138 |  
 139 |  
 140 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 141 | @@ -93,6 +96,29 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 142 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 143 |  
 144 |  
 145 | +def trim_problems(segments):
 146 | +    """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
 147 | +    refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
 148 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start."""
 149 | +    import canon
 150 | +    out = []
 151 | +    for i, s in enumerate(segments):
 152 | +        has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
 153 | +        if not has_w and not has_s:
 154 | +            continue
 155 | +        if has_w != has_s:
 156 | +            out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 157 | +            continue
 158 | +        w, u, st = s["trimmed_leading"], s["untrimmed_start"], s.get("start")
 159 | +        tok = canon.canon_tokens(w)[:1] if isinstance(w, str) else []
 160 | +        if not tok or tok[0] not in TRIM_WORDS:
 161 | +            out.append(f"segment {i}: trimmed_leading {w!r} is not one of {'/'.join(TRIM_WORDS)}")
 162 | +        num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
 163 | +        if not num(u) or not num(st) or not 0 <= float(u) < float(st):   # never raises (audit 0530 C1, glm P0-8)
 164 | +            out.append(f"segment {i}: untrimmed_start {u!r} must be a number with 0 <= it < start {st!r}")
 165 | +    return out
 166 | +
 167 | +
 168 |  def screen_problems(pk):
 169 |      """[why] for a moments medley that does not carry the screen its line-up was judged with (ruling 34). The render
 170 |      reads moments_package.btc_screen and, without it, applies the stricter every-segment rule, so a pin judged with
 171 | @@ -190,7 +216,7 @@ def to_pin(pk, run_name):
 172 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 173 |                                                                       for x in line_problems(pk)] + \
 174 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 175 | -        screen_problems(pk)
 176 | +        screen_problems(pk) + trim_problems(pk.get("segments") or [])
 177 |      if problems:
 178 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 179 |      segs = []
 180 | @@ -200,6 +226,7 @@ def to_pin(pk, run_name):
 181 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 182 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 183 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 184 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start") if k in s},   # ruling 33 part 2
 185 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 186 |      edl_vo = {"intro": pk["vo"]["intro"],
 187 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 188 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 189 | index fadf036c..76bb890e 100644
 190 | --- a/pipeline/stand_alone.py
 191 | +++ b/pipeline/stand_alone.py
 192 | @@ -112,15 +112,32 @@ def topical_screen(kind, text, prev_text, screen):
 193 |      return False, f"does not pass the miner's about-Bitcoin screen and does not complete the previous claim"
 194 |  
 195 |  
 196 | +def trimmed_word(seg):
 197 | +    """The leading word a segment's lock trims (ruling 33 part 2: selection_lock.trimmed_leading), else None."""
 198 | +    t = (seg.get("selection_lock") or {}).get("trimmed_leading")
 199 | +    return str(t.get("word") or "?") if isinstance(t, dict) else None
 200 | +
 201 | +
 202 | +def trimmed_opener(word, score, fault):
 203 | +    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a segment locked with ONE leading word trimmed passes only
 204 | +    when the clip scorer affirms the TRIMMED text stands alone at the unchanged threshold, whatever its first word."""
 205 | +    if score is None:
 206 | +        return False, f"{word!r} trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)"
 207 | +    if score >= CLIP_MIN_SCORE and fault != "starts_mid_thought":
 208 | +        return True, f"{word!r} trimmed; the clip scorer affirms the trimmed text stands alone ({score}, fault {fault})"
 209 | +    return False, f"{word!r} trimmed; the clip scorer does not affirm the trimmed text stands alone ({score}, fault {fault})"
 210 | +
 211 | +
 212 |  def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 213 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 214 | -    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed.
 215 | +    clips opening on a conjunction / reply fragment (the clip scorer) and for every segment whose lock trims a leading
 216 | +    word (ruling 33 part 2, the hook included); without it they fail closed.
 217 |      screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 218 |      and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 219 |      speaker's own words. screen None: every segment names the subject, as before (the story path)."""
 220 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 221 | -    need = [(label, s) for label, kind, s in segs if kind == "clip" and _words(s.get("text"))[:1]
 222 | -            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)]
 223 | +    need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
 224 | +            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))]
 225 |      scores, rate_error = {}, None
 226 |      if need and rate is not None:
 227 |          try:
 228 | @@ -133,6 +150,8 @@ def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 229 |          sc = scores.get(label)
 230 |          score, fault = (sc[0], sc[2]) if sc else (None, None)
 231 |          o_ok, o_why = opener(kind, s.get("text"), score, fault)
 232 | +        if o_ok and trimmed_word(s):                                   # ruling 33 part 2
 233 | +            o_ok, o_why = trimmed_opener(trimmed_word(s), score, fault)
 234 |          t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
 235 |              topical(kind, s.get("text"), prev, subject)
 236 |          rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
 237 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
 238 | index 47f8b401..02f12079 100644
 239 | --- a/pipeline/transcript_truth.py
 240 | +++ b/pipeline/transcript_truth.py
 241 | @@ -157,7 +157,7 @@ def _canon_to(ws, i):
 242 |      return c[-1] if c else None
 243 |  
 244 |  
 245 | -def edges(second, wav_start, start, end, text):
 246 | +def edges(second, wav_start, start, end, text, trimmed=None):
 247 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
 248 |      the segment's edges, from its word timing on the SOURCE audio. The clip's first / last word is found by its first
 249 |      four letters OR by the L-v 2 canonicaliser on a short run of the recogniser's words (ruling 39: 'sixty-eight
 250 | @@ -166,7 +166,9 @@ def edges(second, wav_start, start, end, text):
 251 |      clip's opening word (a measured pause), or the window reaches the FILE HEAD and holds no word before the clip (the
 252 |      clip opens on the file's first spoken word). OUT: the recogniser's word at the clip's last word (within 0.8 s) ends
 253 |      in terminal punctuation, and the recogniser heard a next word (it did not stop at the window's edge). Store or
 254 | -    caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
 255 | +    caption punctuation is never evidence. trimmed (ruling 33 part 2: ONE leading word trimmed at the cut): the word
 256 | +    the recogniser hears right before the clip's first kept word must be that word, and the IN rule reads before IT,
 257 | +    where the sentence opens. -> {"cuttable", "in", "out"}."""
 258 |      # the recogniser's words in its own (time) order: all 99 recorded transcriptions are time-ordered (audit 0338 C1)
 259 |      ws = [w for w in second.get("words") or [] if w.get("start") is not None]
 260 |      toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
 261 | @@ -187,7 +189,11 @@ def edges(second, wav_start, start, end, text):
 262 |      if ci:                                      # the occurrence NEAREST the clip's start, never an earlier one of the
 263 |          i = min(ci, key=lambda k: abs(float(ws[k]["start"]) - t_in))    # same word (audit 0338: grok C2, glm C1 P2-2)
 264 |          j, repair = i - 1, None
 265 | -        if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
 266 | +        tw = canon.canon_tokens(trimmed or "")[:1]
 267 | +        heard = (canon.canon_tokens(ws[j]["text"])[:1] if j >= 0 else []) if tw else None
 268 | +        if tw and heard == tw:                  # ruling 33 part 2: the trimmed word opens the sentence
 269 | +            j -= 1
 270 | +        elif not tw and self_repair(ws, j, first):     # ruling 8: the speaker's false start opens the sentence
 271 |              repair, j = ws[j]["text"], j - 1
 272 |          prev = ws[j]["text"] if j >= 0 else None
 273 |          t_open = float(ws[j + 1]["start"])      # the clip's opening word (its self-repair, when there is one)
 274 | @@ -209,6 +215,16 @@ def edges(second, wav_start, start, end, text):
 275 |          if repair:
 276 |              out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 277 |                               "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 278 | +        if trimmed is not None and not tw:      # a trim with no canonical word is no trim at all: fail closed
 279 | +            out["in"] = {"ok": False, "word": ws[i]["text"], "trimmed": trimmed,
 280 | +                         "why": f"the trimmed word {trimmed!r} has no canonical token (ruling 33 part 2; audit 0530 C1)"}
 281 | +        elif tw and heard != tw:                # the trimmed word is not what the recogniser heard: no IN
 282 | +            out["in"] = {"ok": False, "word": ws[i]["text"], "before": ws[i - 1]["text"] if i > 0 else None,
 283 | +                         "trimmed": trimmed, "why": f"the recogniser does not hear the trimmed word {trimmed!r} right "
 284 | +                                                    f"before the clip (ruling 33 part 2)"}
 285 | +        elif tw:
 286 | +            out["in"].update(trimmed=trimmed, why=out["in"]["why"] + f" (before the trimmed word {trimmed!r}, which "
 287 | +                                                                      f"opens the sentence: ruling 33 part 2)")
 288 |      else:
 289 |          out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
 290 |      if co:                                      # the occurrence nearest the clip's end (audit 0338, as at the IN)
 291 | @@ -224,7 +240,7 @@ def edges(second, wav_start, start, end, text):
 292 |      return dict(out, cuttable=out["in"]["ok"] and out["out"]["ok"])
 293 |  
 294 |  
 295 | -def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None):
 296 | +def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None, trimmed=None):
 297 |      """Both checks for one selected segment -> a record (the second pass's text kept as evidence). ok only when the
 298 |      critical tokens agree in both directions AND exactly one speaker was measured inside."""
 299 |      if wav is None:
 300 | @@ -243,5 +259,5 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 301 |              "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 302 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 303 |              "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S), start, end,
 304 | -                           text),
 305 | +                           text, trimmed),
 306 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 307 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 308 | index ba246650..fe02d895 100644
 309 | --- a/tests/package/test_angles.py
 310 | +++ b/tests/package/test_angles.py
 311 | @@ -399,6 +399,31 @@ class TestEdgesRulings38And39(unittest.TestCase):
 312 |          self.assertTrue(e["in"]["ok"], e["in"])
 313 |          self.assertEqual((e["in"]["self_repair"], e["in"]["pause_ms"]), ("Bit-", 800))
 314 |  
 315 | +    def test_a_trimmed_leading_word_must_be_heard_and_the_in_rule_reads_before_it(self):    # ruling 33 part 2
 316 | +        e = self.edges([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "But", "start": 1.10, "end": 1.30}],
 317 | +                       1.40)                                                     # 'But' heard right before the clip
 318 | +        self.assertFalse(e["in"]["ok"])                       # without the trim: 'But' runs on into the clip
 319 | +        ws, end = self.ws([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "But", "start": 1.10, "end": 1.30}],
 320 | +                          1.40)
 321 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 322 | +        self.assertTrue(e["in"]["ok"], e["in"])
 323 | +        self.assertEqual((e["in"]["before"], e["in"]["trimmed"]), ("path.", "But"))
 324 | +        self.assertIn("before the trimmed word 'But'", e["in"]["why"])
 325 | +        ws, end = self.ws([{"text": "and", "start": 0.20, "end": 0.50}, {"text": "But", "start": 1.30, "end": 1.38}],
 326 | +                          1.40)
 327 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 328 | +        self.assertTrue(e["in"]["ok"], e["in"])                                  # 800 ms before 'But': a pause
 329 | +        self.assertEqual(e["in"]["pause_ms"], 800)
 330 | +        ws, end = self.ws([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "And", "start": 1.10, "end": 1.30}],
 331 | +                          1.40)
 332 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 333 | +        self.assertFalse(e["in"]["ok"])                                          # another word was heard
 334 | +        self.assertIn("does not hear the trimmed word 'But'", e["in"]["why"])
 335 | +        for bad in ("", "..."):                                                  # no canonical word: fail closed
 336 | +            e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed=bad)
 337 | +            self.assertFalse(e["in"]["ok"], bad)
 338 | +            self.assertIn("has no canonical token", e["in"]["why"])
 339 | +
 340 |      def test_the_window_reaches_4_s_before_the_clip_and_stops_at_the_file_head(self):
 341 |          import tempfile
 342 |          self.assertEqual((TT.PAD_BEFORE_S, TT.PAD_S, TT.PAUSE_MIN_S), (4.0, 1.5, 0.7))
 343 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 344 | index d00f10db..d83437e8 100644
 345 | --- a/tests/package/test_medley.py
 346 | +++ b/tests/package/test_medley.py
 347 | @@ -25,7 +25,7 @@ import eligibility as E  # noqa: E402
 348 |  import package as PK  # noqa: E402
 349 |  import package_pin  # noqa: E402
 350 |  from config import BRIDGE_WORD_CAP  # noqa: E402
 351 | -from test_eligibility import NOW, REG  # noqa: E402
 352 | +from test_eligibility import NOW, REG, source  # noqa: E402
 353 |  from test_gates import Canned  # noqa: E402
 354 |  from test_moments import pm  # noqa: E402
 355 |  import house_style as HS  # noqa: E402
 356 | @@ -734,6 +734,97 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 357 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 358 |  
 359 |  
 360 | +class TestRuling33TrimAtThePinStage(unittest.TestCase):
 361 | +    """Ruling 33 part 2 (render merged 11e361cc), used per the 04:58 order's item 42: a moment opening on ONE of
 362 | +    but/and/so/well/now/yeah, left out by the render's STAND_ALONE opener rule, may be cut one word in. The variant is
 363 | +    judged like any moment (step A, L-v 2 with the trimmed word heard, the acoustic onset rule at the trimmed cut); the
 364 | +    clip scorer's verdict is pending at the render; the pin seals trimmed_leading and untrimmed_start."""
 365 | +
 366 | +    def moment(self, sentence, mid="t"):
 367 | +        src = source([sentence], vid="vT")
 368 | +        a, b = src.sentences[0]
 369 | +        m = dict(pm(mid, "T", 0.0, vid="vT"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
 370 | +                 start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
 371 | +        m["duration_s"] = round(m["end"] - m["start"], 2)
 372 | +        return m, {"vT": src}
 373 | +
 374 | +    def test_one_leading_word_is_trimmed_and_the_variant_carries_it(self):
 375 | +        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 376 | +        self.assertIn("clip opens on 'but'", PK.no_role_on_screen(m))
 377 | +        v = PK.trim_variant(m, srcs)
 378 | +        self.assertEqual((v["moment_id"], v["trimmed_leading"], v["untrimmed_start"]), ("t~trim", "But", m["start"]))
 379 | +        self.assertTrue(v["text"].startswith("Bitcoin has rarely"))
 380 | +        self.assertEqual(v["words"], [m["words"][0] + 1, m["words"][1]])
 381 | +        self.assertGreater(v["start"], m["start"])
 382 | +        self.assertAlmostEqual(v["duration_s"], round(m["end"] - v["start"], 2))
 383 | +        self.assertIsNone(PK.no_role_on_screen(v))
 384 | +
 385 | +    def test_only_one_word_and_only_the_ruled_words(self):
 386 | +        for sentence in ("But then Bitcoin had six negative weeks back to back in its whole history.",    # 'then'
 387 | +                         "Because Bitcoin had six negative weeks back to back in its whole history.",      # not ruled
 388 | +                         "Bitcoin had six negative weeks back to back in its whole history."):             # no opener
 389 | +            m, srcs = self.moment(sentence)
 390 | +            self.assertIsNone(PK.trim_variant(m, srcs), sentence)
 391 | +        self.assertEqual(PK.TRIM_WORDS, package_pin.TRIM_WORDS)
 392 | +        m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
 393 | +        self.assertIsNone(PK.trim_variant(m, srcs))
 394 | +
 395 | +    def test_the_scorer_verdict_is_pending_at_the_render_and_sealed_in_the_row(self):
 396 | +        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 397 | +        v = PK.trim_variant(m, srcs)
 398 | +        r = PK.stand_alone_check([{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}])
 399 | +        self.assertTrue(r["ok"], r["rows"])
 400 | +        self.assertEqual(r["scorer_pending"], ["clip_01"])
 401 | +
 402 | +    def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 403 | +        segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 404 | +                dict(pm("x", "B", 14.0), text="Bitcoin keeps every promise it ever made to me.",
 405 | +                     trimmed_leading="But", untrimmed_start=0.0, start=0.3),
 406 | +                dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
 407 | +        by = {m["moment_id"]: m for m in segs}
 408 | +        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 409 | +                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
 410 | +                  "caption": {"text": "three clips", "cites": []}}
 411 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 412 | +        self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
 413 | +        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 414 | +        pin = package_pin.to_pin(spk(pk), "test")
 415 | +        s1 = pin["segments"][1]
 416 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 417 | +        self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 418 | +        mp = pin["moments_package"]
 419 | +        args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 420 | +        self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 421 | +        other = [dict(x) for x in pin["segments"]]
 422 | +        other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 423 | +        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 424 | +        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0}):
 425 | +            p = spk(pk)
 426 | +            p["segments"][1] = dict(p["segments"][1], **bad)
 427 | +            with self.assertRaises(package_pin.PinRefused):
 428 | +                package_pin.to_pin(p, "test")
 429 | +        self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
 430 | +        p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
 431 | +        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 432 | +        with self.assertRaises(package_pin.PinRefused):                          # both keys or neither
 433 | +            package_pin.to_pin(p, "test")
 434 | +
 435 | +    def test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out(self):
 436 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 437 | +              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
 438 | +        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
 439 | +        saved = PK.trim_variant
 440 | +        try:
 441 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 442 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 443 | +            out = rig.run()
 444 | +        finally:
 445 | +            PK.trim_variant = saved
 446 | +        self.assertEqual(out["trimmed"], {"b": "b~trim"})
 447 | +        self.assertIn("b~trim", out["prescreen"]["trim_cut"])                     # ruling 33 (a): out, any place
 448 | +        self.assertIsNotNone(out["package"])
 449 | +
 450 | +
 451 |  class TestRuling41Search(unittest.TestCase):
 452 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 453 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 454 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 455 | index 71f803a6..876be014 100644
 456 | --- a/tests/package/test_speakers.py
 457 | +++ b/tests/package/test_speakers.py
 458 | @@ -226,6 +226,8 @@ class TestPinCarriesTheSpeaker(unittest.TestCase):
 459 |          pin = package_pin.to_pin(self.pk(unknown), "r")
 460 |          mp = pin["moments_package"]
 461 |          for k in package_pin.SEALED_LATER:
 462 | +            if not any(k in sg for sg in pin["segments"]):      # a conditional field (the trim, ruling 33 part 2): its
 463 | +                continue                                          # sealing is tested where a segment carries it
 464 |              segs = [{x: v for x, v in sg.items() if x != k} for sg in pin["segments"]]
 465 |              self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"],
 466 |                                                   mp["caption"], mp["gates"]), mp["package_sha256"], k)
 467 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins; the integrator renders them. The pin stage must never seal what the render would
refuse, EXCEPT where the orchestrator has ruled otherwise. One such case is stated below.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why:
- ORCHESTRATOR RULING 33 (03:12 ET Nov 13): "A clip that opens on a discourse conjunction or reply word (but, and,
  so, well, now, yeah) may have that ONE leading word trimmed at the cut when (a) the acoustic onset rule is met on
  the trimmed cut, and (b) the pipeline's STAND_ALONE scorer affirms the trimmed clip at its unchanged threshold, and
  (c) L-s step A is re-judged on the trimmed span. The locked text is the trimmed text. If any of the three fails, the
  clip is out."
- ORDER 04:58, item 42: "USE RULING 33 PART 2 NOW (merged on main 11e361cc) ... Rebuild with trimmed_leading as soon
  as your side is audited; report how many of the 113 come back."
- The render's contract (main c6605895): on a segment, only when a word is trimmed:
  - "trimmed_leading", the ONE word as spoken, whose canonical token is one of but/and/so/well/now/yeah;
  - "untrimmed_start", 0 <= untrimmed_start < start;
  - approved_text is the trimmed text, and start/end bound the kept words.
  The render checks:
  - the trimmed word sits right before the lock in its own transcript, with a sentence end (or the file's first word)
    before it;
  - a quiet run between the trimmed word and the first kept word;
  - the cut opens in quiet;
  - STAND_ALONE: its clip scorer (a local model on GPU0) must affirm EVERY trimmed segment.
- THE STATED ASSUMPTION: this session may not use any GPU, so the scorer cannot run at the pin stage. The render's
  check_edl with rate=None fails a trimmed segment closed. Per item 42 ("use it now"), the scorer's verdict is
  PENDING AT THE RENDER: the pin stage records it, and the render holds a trimmed pin its scorer refuses, at validate,
  before any cut (the integrator: "That costs a run slot, not a bad video"). (a) and (c) ARE judged at the pin stage.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (the trim is the orchestrator's own ruling).

The change:
1. pipeline/stand_alone.py: synced byte-identical to main's c6605895 (the render's trimmed_word / trimmed_opener in
   check_edl).
2. pipeline/transcript_truth.py, edges(..., trimmed=None) and verify_segment(..., trimmed=None):
   - with a trimmed word, the recogniser's word right before the clip's first kept word must be that word (by its
     canonical token), else IN fails;
   - the IN rule (a sentence end, a measured pause >= 700 ms, or the file head) then reads before the trimmed word;
   - without one, the IN rule is unchanged.
3. pipeline/package.py:
   - TRIM_WORDS.
   - trim_variant(m, sources): for a moment whose first word is one of TRIM_WORDS, the variant takes text, start and
     words from the next word of its word record, with duration_s = end - new start, trimmed_leading (the word as
     spoken), untrimmed_start (the original start) and moment_id "<id>~trim". It must pass no_role_on_screen and
     no_topic on the trimmed text, else None.
   - build(): the variants of the moments the opener rule left out join the usable moments (before the ad-read screen
     and step A, which judges the trimmed span: ruling 33 c). out["trimmed"] records them.
   - truth_for passes trimmed=m.get("trimmed_leading").
   - After the hook-onset measure, a trimmed moment that does not pass it (the acoustic onset at its trimmed cut:
     ruling 33 a) is left out at ANY place, recorded in out["prescreen"]["trim_cut"].
   - stand_alone_check records r["scorer_pending"] = the labels of trimmed segments. Its EDL carries no
     selection_lock, so check_edl judges the trimmed text's own opener; the sealed stand_alone row carries
     scorer_pending.
   - _package's segment rows carry trimmed_leading and untrimmed_start when present.
4. pipeline/package_pin.py:
   - SEALED_LATER gains trimmed_leading and untrimmed_start, so they enter the seal only when present and older pins
     recompute;
   - TRIM_WORDS;
   - to_pin copies both keys onto the pin segment;
   - trim_problems refuses a pin unless: both keys or neither; the canonical token is one of TRIM_WORDS;
     0 <= untrimmed_start < start.
5. Tests:
   - the edge rule with and without the trim, another word heard, and the pause before the trimmed word;
   - trim_variant ("But" trimmed; "But then" and "Because" and no opener give None);
   - the pending scorer;
   - the pin sealing the trim, and the malformed refusals;
   - a trimmed moment without a clean cut left out.

Check in particular:
- that (a) and (c) are really judged at the pin stage, and that a trimmed moment that fails either is out;
- that the scorer's pending status is visible in the sealed record and nothing pretends it was affirmed;
- that the pin's fields match the render's contract exactly;
- that untrimmed segments, old pins and the rest of the IN rule are unchanged;
- whether "pending at the render" is a defensible reading of the item-42 order. Say so if you think it is not.

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
