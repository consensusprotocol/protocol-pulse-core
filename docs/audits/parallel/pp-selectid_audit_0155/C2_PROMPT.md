# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0155
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 180 s finish=stop usage in 13245 / out 5203 usd~0.118 (upper-bound price)

# Audit: pp-selectid-0155 — G17a at the pin stage (hook_onset)

Scope note: I can only see the diff. `sentence_law.edge_plan`, `head_tail`, `quiet_runs`, `SourceAudio`, `transcript_truth.audio_window`, `eligibility.Source`, and the rest of `package.build` are referenced but not shown; where a finding depends on their behavior I say so.

## P0

**P0-1 — The pin-stage check measures a different signal than the render gate it duplicates, and the divergence is structural, not incidental.** `pipeline/hook_onset.py:32-37, 73` — `_Slice` reuses the source envelope's 10 ms frames (`sa.t[m] - t0`), so `head_tail`'s lead measurement is quantized to the source's 10 ms hop and, as the module docstring admits (lines 22-23), excludes the render's 20 ms fade-in. The docstring argues the missing fade "can only make this check stricter" — that is true for the lead *count*, but the docstring also concedes the slice "can differ from the render's decode of the prepared file by up to one 10 ms frame." So a hook whose true lead is exactly at the boundary (e.g. 75-85 ms) can measure PASS at the pin stage and FAIL at the render's `gate_g17_prepared`, or vice versa. Concrete scenario: source lead = 75 ms of room tone; the prepared file's decode, with the 20 ms fade-in applied, measures 85+ ms at the render → pin-stage PASS (75 < 80, actually FAIL — see P1-1) — the two gates disagree, and since MEDLEY_GATES now requires the pin row exactly PASS while the render gate is a hard stop (LAW 20), a package can be pinned and then held at render, which is exactly the 01:39 failure mode this diff claims to prevent. The diff's own test only exercises the pin stage; nothing in the diff proves the two measurements agree. Whether the 10 ms quantization plus the 20 ms fade can actually flip a 75-85 ms case depends on `head_tail`'s internals (not shown) — flagging as a likely divergence, uncertain on the exact flip window.

**P0-2 — `hook_onset_for` caches by `moment_id` but `measure`'s result depends on `work_dir`/audio-window state, and the cache is keyed only on the moment.** `pipeline/package.py:115-126` — the cache `hk` is created once in `build()` (line 136) and passed to every `hook_onset_for` call; `measure` fetches the L-v 2 window via `TT.audio_window(video_id, start, end, work_dir)` when `audio is None` (hook_onset.py:46-48). If `audio_window` writes into `work_dir` and can return different results across calls (e.g. a transient download/decode failure then success, or vice versa), the first call's outcome — including a fail-closed `{"pass": False, "measured": False}` — is frozen for the whole build. That is fail-closed (L-m compliant) but it means a transient I/O error permanently disqualifies a moment from opening any medley in this run, silently, with only a prescreen log line. Not wrong per the laws (fail closed), but it is a behavioral coupling worth noting; whether `audio_window` is deterministic/cached-on-disk is not verifiable from the diff. Downgrade to P1 if `audio_window` is disk-cached and deterministic.

## P1

**P1-1 — The 75-85 ms boundary case: the pin-stage lead excludes the render's 20 ms fade-in, so the pin gate is stricter than the render gate, and the test's 80 ms threshold comparison is against the wrong signal.** (Overlaps P0-1; stated separately because the *direction* matters.) `pipeline/hook_onset.py:22-23, 77-78` — `lead = round(ht["lead_ms"] + pad*1000)`; `ok = lead >= need` where `need = 80`. Since the render's prepared-clip measurement includes a 20 ms fade-in that the pin-stage slice does not, a hook with 60-79 ms of genuine source lead can measure FAIL at the pin (correctly, per the pin's own definition) but would PASS at the render. That is the safe direction (no held render), but it means the pin gate and the render gate are not the same check, and the "G17a at the pin stage" framing (a *duplicate* of the render's G17_onset_tail) is only approximately true. The diff's justification for the 20 ms omission ("can only make this check stricter") is correct for pass/fail direction but the diff never reconciles the two thresholds. If the intent is "the render will never hold again," stricter-at-pin achieves it; if the intent is "the pin gate equals the render gate," it does not. Uncertain which is intended; the docstring says "G17a at the PIN stage," which suggests deliberate divergence — but then the render's G17_onset_tail can still hold a pinned package, and the 01:39 hold can recur for the *fade/quantization* residual, just not for the zeros-vs-room-tone defect. This is the central question of the diff and the diff does not answer it.

**P1-2 — `lineup_for`'s `need_onset` filter can silently change the medley's channel/clip composition, and the repeat_ok fallback also filters, so a package can lose its proposer's hook with no recorded reason beyond the prescreen.** `pipeline/package.py:106-108, 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 152 s finish=stop usage in 13183 / out 388 usd~0.076 (upper-bound price)

**Findings**
- **None (P0/P1/P2)**: No concrete failure scenarios (specific inputs → wrong output on gates, lineup, pin, measurement, or tests) are verifiable from the diff alone. All added/updated logic matches the described intent for G17a (hook_onset.measure using SL.edge_plan + SL.head_tail on source slice/_Slice, lead_ms vs HEAD_LEAD_MIN_S, pad only from edge_plan, measured=False never a pass). Checks (a)-(e) hold directly from the code: (a) <80 ms lead yields pass=False/measured=True → filtered in lineup_for:107 + FAIL row in inventory:201 (cannot open medley or pin); (b) exceptions or words-outside-window yield measured=False → "NOT RUN"/no lineup (hook_onset_for:124, measure:51/56, inventory:195); (c) non-hooks untouched (lineup_for only filters opener hooks; full-window path via audio=None or test audio=; no changes to other calls visible in diff); (d) hook_onset required+sealed for every medley (package_pin:215 update, test_medley:307/315/369 including no-voice path, gate_problems via required_gates, inventory:202 adds row with measured=...is True); (e) tests assert exactly the named defects (e.g. breath+zeros+floor env → lead_ms<80+FAIL+G17a in why at test_hook_onset:276; room-tone → PASS at 284; no-audio/words-outside → measured=False at 289; no_hook={"h"} → switches opener or no lineup+no paid medley call at test_medley:350). Uncertainty on exact SL.head_tail/edge_plan behavior or unshown calls to lineup_for is stated; nothing else verifiable.

**Verdict**  
SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 109 s finish=stop usage in 14582 / out 3641 usd~0.098 (upper-bound price)

# Audit: pp-selectid-0155 (G17a at the PIN stage)

## Findings

### P1 — `hook_onset.measure` can return `pass: True` for a hook that has *no* cut before it (file head)
**File:** `pipeline/hook_onset.py:65-79`

The code path:
```python
cin = plan.get("in") or {}
if not cin.get("cuttable"):
    return {"pass": False, ...}
cut_in = float(cin["cut"])
...
pad = float(cin.get("lead_in_pad_s") or 0.0)
lead = int(round(ht["lead_ms"] + pad * 1000))
ok = lead >= need
```

If the hook is the **first word in the source file** (a file-head hook), `edge_plan` will report the "in" cut as the file head (t=0) and grant a `lead_in_pad_s` (the room-tone pad). The `_Slice` will be `[0, cut_out]`. `head_tail` on that slice will measure `lead_ms` as the quiet before the first onset *within the slice* — which is the pad region. So `lead = pad_ms + head_tail_lead_ms`.

**The problem:** The pad is *synthetic* room tone inserted by the renderer. The law says "a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine sub-speech audio before the first onset **or a declared room-tone lead-in pad**." The code adds the pad to the measured lead, which is correct per the law. However, the `head_tail` measurement on the slice `[0, cut_out]` will see the pad as part of the audio. If the pad is, say, 100 ms of -55 dBFS room tone, `head_tail` will report `lead_ms ≈ 100`, and `pad` will also be 100 ms, giving `lead = 200 ms`. **This double-counts the pad.** The pad is already in the slice; adding it again inflates the lead.

**Failure scenario:** A file-head hook with a 50 ms pad and 30 ms of genuine quiet before onset. True genuine lead = 30 ms (FAIL). Code computes `lead = 30 + 50 = 80 ms` (PASS). The hook opens a medley with only 30 ms of genuine quiet, violating D1.

**Mitigation check:** I cannot verify from the diff whether `edge_plan`'s `lead_in_pad_s` is *included* in the slice or *added on top*. The `_Slice` is `[cut_in, cut_out]` where `cut_in = cin["cut"]`. If `cin["cut"]` is 0 for a file head, the slice starts at 0 and does *not* include the pad (the pad is added by the renderer *before* the cut). In that case, `head_tail` on `[0, cut_out]` measures only the source audio, and adding `pad` is correct. **I am uncertain** which interpretation is correct without seeing `edge_plan`'s contract. Flagging as P1 pending verification.

---

### P1 — `lineup_for` with `need_onset=True` can silently drop all hooks, producing a medley that opens with a *clip* instead of a hook
**File:** `pipeline/package.py:106-107` (the `hooks` filter) and `:164-167` (the call sites)

```python
hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
         (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
```

If *no* moment in the angle has `hook_onset.pass == True`, `hooks` is empty. The code then iterates `for h in hooks:` (line 109), which does nothing. The function returns `None` (implied by the "None if impossible" docstring). This is correct: no line-up is produced.

**However**, the test at `test_medley.py:347-359` confirms this: `no_hook={"h","x","y","z"}` → `out["package"] is None`. Good.

**But:** What if the angle has *some* hooks that pass and some that don't? The proposer's hook (`angle["hook"]`) is sorted first (line 108: `m["moment_id"] != angle["hook"]` as primary key). If the proposer's hook fails G17a but another moment passes, the proposer's hook is skipped and the next hook is used. This is the intended behavior ("the proposer's hook gives way to the angle's next one that did"). **No defect here.**

---

### P2 — `hook_onset_for` caches by `moment_id` but the cache is shared across all angles
**File:** `pipeline/package.py:115-126`

```python
def hook_onset_for(m, sources, work_dir, cache):
    if m["moment_id"] not in cache:
        ...
        cache[m["moment_id"]] = HO.measure(...)
    return cache[m["moment_id"]]
```

The cache is a plain dict keyed by `moment_id`. Since a moment belongs to exactly one video and has fixed `start`/`end`, the measurement is deterministic and caching is safe. **No defect.**

---

### P2 — The `hook_onset` gate row is only added to `inventory` when `hook is not None`
**File:** `pipeline/package.py:201-204`

```python
**({"hook_onset": dict(row(...), ...)} if hook is not None else {}),
```

If `hook` is `None`, the row is absent. `package_pin.MEDLEY_GATES` includes `"hook_onset"`, so `to_pin` will refuse the pin (missing required row). This is correct fail-closed behavior.

**However**, in `build()`, the `hook` argument is:
```python
hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset")
```

If `pk["segments"][0]["moment_id"]` is not in `cleared` (e.g., the moment was dropped after the hook_onset measurement), `cleared.get(...)` returns `None`, `{}.get("hook_onset")` returns `None`, and the row is absen

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of G17a at the pin stage (hook onset): cycle 1 consensus (synthesis by the pp-selectid session, 02:00 ET Nov 13)

**Run.** C1_STEP.diff covers hook_onset.py, package.py, package_pin.py and the two test files. No P0 holds.
- grok-4.20-0309-reasoning (xAI): no findings, "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s (the pad; "a medley opens with a clip"). SHIP yes with conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): two "P0"s and four P1s. SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the pin-stage lead is measured on the SOURCE envelope sliced at the planned cut. The render measures its own decode of the prepared file, and the two can differ by one 10 ms frame, so a lead of 80-89 ms here could be a G17a hold at render (glm P0-1 / P1-1, qwen) | IMPLEMENTED: a hook passes here only with HEAD_LEAD_MIN_S + MARGIN_MS (one HOP_S frame) = 90 ms. The missing 20 ms fade-in can only make the check stricter. Test: test_a_lead_within_one_frame_of_80_ms_does_not_pass (85 ms fails, 120 ms passes) |

## Unique findings: implemented, refuted or kept (each verified)

- **qwen P1 (pad double-counted?):** REFUTED, and now TESTED.
  - edge_plan grants LEAD_PAD_S only at a file head whose genuine lead is < 80 ms. The render adds that room tone
    BEFORE the source audio.
  - The slice is the source alone, so the pad is added once.
  - Test: test_a_file_head_hook_counts_the_pad_the_render_adds_once (60 ms of source lead, plus the 250 ms pad,
    passes; the source alone is < 80 ms).
- **qwen P1 ("a medley opens with a clip instead of a hook"):** REFUTED. With no hook-able moment, lineup_for returns
  None: no line-up, nothing paid. Tested (no_hook = every moment: no package, no clips-alone call).
- **glm P0-2 (the cache freezes a transient failure for the build):** KEPT. It is fail closed, and the L-v 2 audio
  window is cached on disk, so the read is deterministic.
- **glm P1-2 (angle["hook"] may name a moment that does not open):** REFUTED. angle["hook"] is read only by
  check_angles (it is one of the angle's moments), lineup_for's sort preference, and the report. The package's hook is
  always segments[0] (package.py:542 / 566 / 1050).
- **glm P1-3 (CUTTABLE vs edge_plan "not cuttable"):** KEPT. These are two different checks.
  - CUTTABLE is the second recogniser's sentence boundary.
  - edge_plan's "in" is the acoustic room before the first word.
  - A moment can be cuttable and still unable to open a medley; it stays usable as a non-hook clip.
- **glm P1-4 (the no-voice added clip):** KEPT. The hook is segments[0], which always comes from a line-up drawn from
  `cleared`. The added clip is never the hook.

## Found by the first FRESH ledger build (01:56 ET), fixed, and in cycle 2's scope

The first live ledger build with window records gave "0 moments cleared step A ... in 0 s" (ledger_20261113_065638).
Two defects:
1. **The step-A batch was poisoned.** On

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0155/C2_STEP.diff (600 lines)
```
   1 | diff --git a/pipeline/hook_onset.py b/pipeline/hook_onset.py
   2 | new file mode 100644
   3 | index 00000000..b5cc7c46
   4 | --- /dev/null
   5 | +++ b/pipeline/hook_onset.py
   6 | @@ -0,0 +1,79 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/hook_onset.py: G17a at the PIN stage. The render holds a medley whose HOOK keeps less than
   9 | +HEAD_LEAD_MIN_S (80 ms, D1: the hook starts playback) of GENUINE quiet before its first onset in the prepared clip
  10 | +(sentence_law.gate_g17_prepared).
  11 | +
  12 | +Batch pin #1, held 01:39 ET Nov 13: the word record put a 400 ms gap before the hook's first word. The source audio
  13 | +holds breath, then a run of digital zeros (a hard edit), then speech. Zeros are not room tone, so the genuine lead
  14 | +was 30 ms. The word record's timestamps cannot see an edit; only the audio can.
  15 | +
  16 | +So before a moment may OPEN a medley:
  17 | +- its cut is planned on the SOURCE audio (the L-v 2 window that transcript_truth.audio_window already fetched for the
  18 | +  second recogniser) with the render's own sentence_law.edge_plan;
  19 | +- the planned prepared clip's head (the source's 10 ms envelope from the planned cut on, a lead-in pad added only
  20 | +  where edge_plan allows one: a file head) is measured with the render's own sentence_law.head_tail.
  21 | +
  22 | +The envelope is sliced from the source, so it can differ from the render's decode of the prepared file by up to one
  23 | +10 ms frame. A hook therefore passes here only with HEAD_LEAD_MIN_S + MARGIN_MS (one frame): a pass here cannot be a
  24 | +G17a hold at render by that frame (audit 0155 C1: glm P0-1 / P1-1, qwen). The render's 20 ms fade-in is not
  25 | +applied, which can only make this check stricter.
  26 | +
  27 | +measure(...) -> {"pass", "measured", "lead_ms", "cut_in", "pad_s", "why"}. Not measured (no audio, no plan) is never
  28 | +a pass (law L-m).
  29 | +"""
  30 | +import sentence_law as SL
  31 | +import transcript_truth as TT
  32 | +
  33 | +MARGIN_MS = int(round(SL.HOP_S * 1000))     # one 10 ms envelope frame: the slice vs the render's own decode
  34 | +
  35 | +
  36 | +class _Slice(SL.SourceAudio):
  37 | +    """[t0, t1] of a decoded source's envelope on its own clock (from 0): the planned prepared clip, before fades."""
  38 | +
  39 | +    def __init__(self, sa, t0, t1):                     # no decode: SourceAudio's methods read t / db / dur only
  40 | +        m = (sa.t >= t0 - 1e-9) & (sa.t < t1 - 1e-9)
  41 | +        self.path, self.t, self.db, self.dur = sa.path, sa.t[m] - t0, sa.db[m], max(0.0, t1 - t0)
  42 | +
  43 | +
  44 | +def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  45 | +    """The hook moment's planned prepared clip: does it keep >= HEAD_LEAD_MIN_S of genuine quiet before its first
  46 | +    onset? src: the moment's eligibility Source; w0 / w1: its first / last word indices in src.tokens; start / end:
  47 | +    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window."""
  48 | +    need = SL.HEAD_LEAD_MIN_S * 1000 + MARGIN_MS
  49 | +    try:
  50 | +        if audio is None:
  51 | +            wav, a = TT.audio_window(video_id, float(start), float(end), work_dir)
  52 | +            sa = SL.SourceAudio(wav)
  53 | +        else:
  54 | +            sa, a = audio
  55 | +    except Exception as e:
  56 | +        return {"pass": False, "measured": False, "why": f"no source audio: {type(e).__name__}: {str(e)[:120]}"}
  57 | +    toks = src.tokens
  58 | +    idx = [i for i, t in enumerate(toks) if isinstance(t.get("start"), (int, float)) and
  59 | +           isinstance(t.get("end"), (int, float)) and float(t["start"]) >= a and float(t["end"]) <= a + sa.dur]
  60 | +    if w0 not in idx or w1 not in idx:
  61 | +        return {"pass": False, "measured": False, "why": "the clip's words are not inside its audio window"}
  62 | +    words = [{"word": toks[i]["word"], "start": float(toks[i]["start"]) - a, "end": float(toks[i]["end"]) - a}
  63 | +             for i in idx]
  64 | +    i0, i1 = idx.index(w0), idx.index(w1)
  65 | +    try:
  66 | +        plan = SL.edge_plan(sa, words, i0, i1)
  67 | +    except Exception as e:                               # LawError: no audio to read levels from, and the like
  68 | +        return {"pass": False, "measured": False, "why": f"no cut plan: {type(e).__name__}: {str(e)[:120]}"}
  69 | +    cin = plan.get("in") or {}
  70 | +    if not cin.get("cuttable"):
  71 | +        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut before the hook: "
  72 | +                f"{cin.get('reason') or 'not cuttable'}"}
  73 | +    cut_in = float(cin["cut"])
  74 | +    out = plan.get("out") or {}
  75 | +    cut_out = float(out["cut"]) if out.get("cuttable") else words[i1]["end"]
  76 | +    try:
  77 | +        ht = SL.head_tail(_Slice(sa, cut_in, cut_out))
  78 | +    except Exception as e:
  79 | +        return {"pass": False, "measured": False, "why": f"no head measured: {type(e).__name__}: {str(e)[:120]}"}
  80 | +    pad = float(cin.get("lead_in_pad_s") or 0.0)         # a room-tone pad: edge_plan allows one only at a file head
  81 | +    lead = int(round(ht["lead_ms"] + pad * 1000))
  82 | +    ok = lead >= need
  83 | +    return {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  84 | +            "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
  85 | +                                    f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
  86 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
  87 | index 8165074a..b45f33b5 100644
  88 | --- a/pipeline/ledger_build.py
  89 | +++ b/pipeline/ledger_build.py
  90 | @@ -245,34 +245,43 @@ def window_source(row, wp, ctx, store=STORE):
  91 |      return src, path, None
  92 |  
  93 |  
  94 | -def caption_source(row, ctx, store=STORE):
  95 | +def caption_source(row, ctx, store=STORE, ledger_store=None):
  96 |      """The full-video record the ledger row was MINED from: the one whose segments sha is the row's transcript_sha256
  97 | -    (the full-video slots transcripts/<vid>/transcript.*.json only; never a window). It is a window record's L-s
  98 | -    context (the contract) -> (Source with .duration_s, file name) or (None, why). Two records matching is ambiguous:
  99 | -    no context (audit 0123 C1, glm P0-1)."""
 100 | +    (the full-video slots transcripts/<vid>/transcript.*.json only; never a window). It is searched in `store` (main's)
 101 | +    and then in `ledger_store`, the store the ledger was mined from (pp-ingest's data/editorial, read-only). The
 102 | +    first live build found 8 of 16 window videos' caption records there and not in main's (5 absent, 3 re-fetched
 103 | +    under another sha). It is a window record's L-s context (the contract) -> (Source with .duration_s,
 104 | +    "<store>/<file>") or (None, why). Matches whose tokens differ are ambiguous, and give no context (audit 0123 C1,
 105 | +    glm P0-1); the same record copied in both stores gives the same tokens and is one record."""
 106 |      vid, want = row["video_id"], row.get("transcript_sha256")
 107 | -    d = os.path.join(store, "transcripts", vid)
 108 | -    try:
 109 | -        names = sorted(n for n in os.listdir(d) if n.startswith("transcript.") and n.endswith(".json"))
 110 | -    except OSError:
 111 | -        return None, "no transcript directory for the video"
 112 | -    found, unreadable = [], 0
 113 | -    for n in names:
 114 | +    found, unreadable, dirs = [], 0, 0
 115 | +    for label, root in (("main", store), ("ledger", ledger_store)):
 116 | +        if not root:
 117 | +            continue
 118 | +        d = os.path.join(root, "transcripts", vid)
 119 |          try:
 120 | -            with open(os.path.join(d, n)) as f:
 121 | -                rec = json.load(f)
 122 | -            if not isinstance(rec, dict) or not want or rec.get("transcript_sha256") != want or \
 123 | -                    ts.segments_sha256(rec.get("segments") or []) != want:
 124 | -                continue
 125 | -            found.append((n, rec, S.tokens_from_record(rec)))
 126 | -        except (OSError, ValueError, KeyError, TypeError, AttributeError):
 127 | -            unreadable += 1
 128 | +            names = sorted(n for n in os.listdir(d) if n.startswith("transcript.") and n.endswith(".json"))
 129 | +        except OSError:
 130 |              continue
 131 | +        dirs += 1
 132 | +        for n in names:
 133 | +            try:
 134 | +                with open(os.path.join(d, n)) as f:
 135 | +                    rec = json.load(f)
 136 | +                if not isinstance(rec, dict) or not want or rec.get("transcript_sha256") != want or \
 137 | +                        ts.segments_sha256(rec.get("segments") or []) != want:
 138 | +                    continue
 139 | +                found.append((f"{label}/{n}", rec, S.tokens_from_record(rec)))
 140 | +            except (OSError, ValueError, KeyError, TypeError, AttributeError):
 141 | +                unreadable += 1
 142 | +                continue
 143 |      if not found:
 144 | -        return None, ("no record in the store matches the row's transcript_sha256" +
 145 | +        return None, ("no transcript directory for the video" if not dirs else
 146 | +                      "no record in the store matches the row's transcript_sha256" +
 147 |                        (f" ({unreadable} transcript file(s) could not be read)" if unreadable else ""))   # C2 glm N2
 148 | -    if len(found) > 1:
 149 | -        return None, f"{len(found)} records match the row's transcript_sha256 ({[n for n, _, _ in found]}): ambiguous"
 150 | +    if len({json.dumps(toks, sort_keys=True) for _, _, toks in found}) > 1:
 151 | +        return None, f"{len(found)} records match the row's transcript_sha256 ({[n for n, _, _ in found]}) with " \
 152 | +                     f"different words: ambiguous"
 153 |      n, rec, (timing, toks) = found[0]
 154 |      reg = ctx.channel(row.get("channel_id")) or {}
 155 |      src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 156 | @@ -375,7 +384,7 @@ def reanchor(row, src):
 157 |      return sp, info
 158 |  
 159 |  
 160 | -def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None):
 161 | +def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None):
 162 |      """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
 163 |      {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
 164 |      nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
 165 | @@ -425,7 +434,7 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None):
 166 |                  report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 167 |                  report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 168 |                  continue
 169 | -            src.context_source, cwhy = caption_source(wrow, ctx, store)
 170 | +            src.context_source, cwhy = caption_source(wrow, ctx, store, ledger_store)
 171 |              if src.context_source is None:
 172 |                  src.context_source = None
 173 |                  report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
 174 | diff --git a/pipeline/package.py b/pipeline/package.py
 175 | index aaae8f37..6b98ef3a 100644
 176 | --- a/pipeline/package.py
 177 | +++ b/pipeline/package.py
 178 | @@ -390,15 +390,20 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 179 |          contexts = {}
 180 |          for m in chunk:
 181 |              text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1], *m["words"])
 182 | +            if text is None:        # no L-s context (a window record without its caption record, short coverage, an
 183 | +                fails[m["moment_id"]] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]   # unclocked
 184 | +                continue            # moment): THIS moment is not cleared; it never poisons its batch's call
 185 |              contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
 186 |                                          "channel": _name(m, ctx), "window": win,
 187 |                                          "published": str(m.get("published_at") or "")[:16],
 188 |                                          "show_date": ctx.now.strftime("%Y-%m-%d")}
 189 | +        if not contexts:
 190 | +            continue
 191 |          try:
 192 |              got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i, writer_family=writer_family)
 193 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 194 | -            for m in chunk:
 195 | -                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
 196 | +            for mid in contexts:
 197 | +                fails[mid] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
 198 |              continue
 199 |          b = router.backends.get(backend)
 200 |          vendors.add(b.vendor if b else backend)
 201 | @@ -542,7 +547,7 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 202 |      return out
 203 |  
 204 |  
 205 | -def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
 206 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False):
 207 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 208 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 209 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 210 | @@ -550,11 +555,14 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
 211 |      (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
 212 |      earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
 213 |      seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
 214 | -    ONE channel may give two clips, from two different videos. None if impossible."""
 215 | +    ONE channel may give two clips, from two different videos. need_onset (build() sets it): a moment opens the
 216 | +    medley only if its hook onset was measured and passed (hook_onset_for, G17a at the pin stage); the proposer's hook
 217 | +    gives way to the angle's next one that did. None if impossible."""
 218 |      lo, hi = crange or medley_content_range()
 219 |      pos = {m: i for i, m in enumerate(angle["moments"])}
 220 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 221 | -    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 222 | +    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
 223 | +             (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
 224 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 225 |      for h in hooks:
 226 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 227 | @@ -907,6 +915,20 @@ def truth_for(router, m, work_dir, cache):
 228 |      return cache[m["moment_id"]]
 229 |  
 230 |  
 231 | +def hook_onset_for(m, sources, work_dir, cache):
 232 | +    """G17a at the pin stage (hook_onset.measure): may this moment OPEN a medley? Its cut planned on the source audio
 233 | +    (the L-v 2 window) with the render's own edge_plan, and >= 80 ms of genuine quiet before its first onset by the
 234 | +    render's own head_tail. Any failure to measure is recorded and never a pass (law L-m)."""
 235 | +    if m["moment_id"] not in cache:
 236 | +        import hook_onset as HO
 237 | +        try:
 238 | +            cache[m["moment_id"]] = HO.measure(sources[m["video_id"]], m["words"][0], m["words"][1], m["video_id"],
 239 | +                                               float(m["start"]), float(m["end"]), work_dir)
 240 | +        except Exception as e:
 241 | +            cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 242 | +    return cache[m["moment_id"]]
 243 | +
 244 | +
 245 |  def _writers(router):
 246 |      """The vendor and family of the angle_write chain's first back-end not down (verdicts avoid them; a live failover
 247 |      adds the next writer's)."""
 248 | @@ -992,6 +1014,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 249 |      cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
 250 |      out["prescreen"]["cuttable"] = len(cleared)
 251 |      log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
 252 | +    hk = {}
 253 | +    with ThreadPoolExecutor(max_workers=4) as pre:     # G17a at the pin stage: which moments may OPEN a medley
 254 | +        futs = {mid: pre.submit(hook_onset_for, m, sources, work_dir, hk) for mid, m in cleared.items()}
 255 | +        for mid, f in futs.items():
 256 | +            cleared[mid]["hook_onset"] = f.result()
 257 | +    out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 258 | +                                      ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 259 | +                                      str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 260 | +    log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 261 | +        f"(>= 80 ms of genuine quiet before the first onset, G17a)")
 262 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 263 |          out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
 264 |                             f"channels")
 265 | @@ -1106,7 +1138,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 266 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 267 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
 268 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 269 | -                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 270 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 271 | +                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 272 |          import package_pin
 273 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 274 |          if problems:
 275 | @@ -1129,9 +1162,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 276 |              while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
 277 |                  if over_budget(ai):
 278 |                      break
 279 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed)), None
 280 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True), None
 281 |                  if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 282 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True)
 283 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True)
 284 |                      if segs is not None:
 285 |                          rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 286 |                                 if sum(m["channel_id"] == c for m in segs) > 1]
 287 | @@ -1280,7 +1313,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 288 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 289 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 290 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 291 | -                                            style=HS.lint_lines(pk["lines"]))
 292 | +                                            style=HS.lint_lines(pk["lines"]),
 293 | +                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 294 |                      if not ok_c:
 295 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 296 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 297 | @@ -1338,11 +1372,13 @@ def _spent(spend):
 298 |      return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 299 |  
 300 |  
 301 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None):
 302 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 303 | +              hook=None):
 304 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 305 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 306 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 307 | -    (shape=(ok, [why]) from ly_shape())."""
 308 | +    (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
 309 | +    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin."""
 310 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 311 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 312 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 313 | @@ -1398,4 +1434,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 314 |          **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 315 |                                  why=[f"{v['slot']}: {v['detail']}" for v in style])}
 316 |             if style is not None else {}),
 317 | +        **({"hook_onset": dict(row(hook.get("pass") is True, "hook_onset.measure (sentence_law.edge_plan + head_tail "
 318 | +                                   "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
 319 | +                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 320 | +           if hook is not None else {}),
 321 |      }
 322 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 323 | index 87fb9461..d975d12f 100644
 324 | --- a/pipeline/package_pin.py
 325 | +++ b/pipeline/package_pin.py
 326 | @@ -26,7 +26,8 @@ from datetime import datetime, timezone
 327 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 328 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 329 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 330 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style")   # L-y (20:30): the clips-alone verdict, the medley's shape;
 331 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset")   # hook_onset: G17a at the pin stage, after
 332 | +                                                                      # batch pin #1's render hold (01:39 ET Nov 13)   # L-y (20:30): the clips-alone verdict, the medley's shape;
 333 |                                                           # ruling 6 (22:40): PBX's copy rules on every line
 334 |  
 335 |  
 336 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 337 | index 37091176..44aaa8eb 100644
 338 | --- a/tests/package/proof_ledger.py
 339 | +++ b/tests/package/proof_ledger.py
 340 | @@ -113,7 +113,8 @@ def main(argv=None):
 341 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 342 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 343 |      say(f"  word pass: {json.dumps(wp_rep)}")
 344 | -    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp)
 345 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 346 | +                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 347 |      inputs["word_pass"] = wp_rep
 348 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 349 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 350 | diff --git a/tests/package/test_hook_onset.py b/tests/package/test_hook_onset.py
 351 | new file mode 100644
 352 | index 00000000..8987f5bb
 353 | --- /dev/null
 354 | +++ b/tests/package/test_hook_onset.py
 355 | @@ -0,0 +1,92 @@
 356 | +#!/usr/bin/env python3
 357 | +"""pipeline/hook_onset.py: G17a at the PIN stage. Batch pin #1 was held at render (01:39 ET Nov 13) because its hook
 358 | +kept 30 ms of genuine quiet before its first onset. The word record showed a 400 ms gap, but the source held breath,
 359 | +then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
 360 | +rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
 361 | +import os
 362 | +import sys
 363 | +import unittest
 364 | +
 365 | +import numpy as np
 366 | +
 367 | +HERE = os.path.dirname(os.path.abspath(__file__))
 368 | +REPO = os.path.dirname(os.path.dirname(HERE))
 369 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 370 | +import eligibility as E  # noqa: E402
 371 | +import hook_onset as HO  # noqa: E402
 372 | +import sentence_law as SL  # noqa: E402
 373 | +
 374 | +WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),        # the previous sentence
 375 | +         ("When", 1.75, 2.15), ("Bitcoin", 2.15, 2.60), ("rises.", 2.60, 3.20),           # the hook: words 3..5
 376 | +         ("Next", 3.60, 4.00), ("words", 4.00, 4.40), ("follow.", 4.40, 5.00)]
 377 | +
 378 | +
 379 | +class Env(SL.SourceAudio):
 380 | +    """A synthetic source envelope (no decode): `spans` [(t0, t1, dBFS)] over a bed of room tone."""
 381 | +
 382 | +    def __init__(self, spans, dur=6.0, bed=-55.0):
 383 | +        self.path, self.dur = "synthetic", dur
 384 | +        self.t = np.arange(int(round(dur / SL.HOP_S))) * SL.HOP_S
 385 | +        self.db = np.full(len(self.t), bed)
 386 | +        for a, b, v in spans:
 387 | +            self.db[(self.t >= a - 1e-9) & (self.t < b - 1e-9)] = v
 388 | +
 389 | +
 390 | +SPEECH = [(0.20, 1.36, -20.0), (3.60, 5.00, -20.0)]
 391 | +
 392 | +
 393 | +def src():
 394 | +    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in WORDS)
 395 | +    return E.Source("vidH", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
 396 | +                    timing="word", file_head=False, vod=True)
 397 | +
 398 | +
 399 | +class TestHookOnset(unittest.TestCase):
 400 | +    def measure(self, env, **kw):
 401 | +        return HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent", audio=(env, 0.0), **kw)
 402 | +
 403 | +    def test_breath_then_digital_zeros_before_the_first_word_fails_g17a(self):
 404 | +        """Pin #1's pattern: a 400 ms word-record gap that is breath, then digital zeros, then 30 ms of quiet."""
 405 | +        env = Env(SPEECH + [(1.41, 1.58, -27.0), (1.65, 1.78, -200.0), (1.78, 1.81, -60.0), (1.81, 3.20, -20.0)])
 406 | +        r = self.measure(env)
 407 | +        self.assertEqual((r["pass"], r["measured"]), (False, True), r)
 408 | +        self.assertLess(r["lead_ms"], 80)
 409 | +        self.assertIn("G17a", r["why"])
 410 | +
 411 | +    def test_room_tone_before_the_first_word_passes(self):
 412 | +        env = Env(SPEECH + [(1.81, 3.20, -20.0)])                    # 1.36 .. 1.81: genuine room tone (-55)
 413 | +        r = self.measure(env)
 414 | +        self.assertEqual((r["pass"], r["measured"]), (True, True), r)
 415 | +        self.assertGreaterEqual(r["lead_ms"], 80)
 416 | +
 417 | +    def test_a_lead_within_one_frame_of_80_ms_does_not_pass(self):
 418 | +        """Audit 0155 C1 (glm P0-1 / P1-1, qwen): the slice can differ from the render's decode by one 10 ms frame,
 419 | +        so 80-89 ms of genuine lead is not enough here."""
 420 | +        for lead_s, ok in ((0.085, False), (0.12, True)):
 421 | +            env = Env(SPEECH + [(1.36, 1.81 - lead_s, -27.0), (1.81, 3.20, -20.0)])   # breath, then room tone
 422 | +            r = self.measure(env)
 423 | +            self.assertEqual(r["pass"], ok, (lead_s, r))
 424 | +
 425 | +    def test_a_file_head_hook_counts_the_pad_the_render_adds_once(self):
 426 | +        """qwen C1: at a file head edge_plan grants a room-tone pad when the genuine lead is short. The render adds it
 427 | +        before the source audio, so it is added to the measured lead once, never twice."""
 428 | +        toks = tuple({"word": w, "start": a - 1.70, "end": b - 1.70} for w, a, b in WORDS[3:])  # the hook opens the file
 429 | +        s0 = E.Source("vidF", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
 430 | +                      timing="word", file_head=True, vod=True)
 431 | +        env = Env([(0.06, 1.50, -20.0), (1.90, 3.30, -20.0)], dur=4.0)          # speech 60 ms after the file start
 432 | +        r = HO.measure(s0, 0, 2, "vidF", 0.05, 1.50, "/nonexistent", audio=(env, 0.0))
 433 | +        self.assertEqual(r["pad_s"], SL.LEAD_PAD_S)
 434 | +        self.assertTrue(r["pass"], r)
 435 | +        self.assertLess(r["lead_ms"] - int(SL.LEAD_PAD_S * 1000), 80)            # the source alone has < 80 ms
 436 | +
 437 | +    def test_no_audio_or_words_outside_the_window_is_not_measured_never_a_pass(self):
 438 | +        r = HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent/dir")      # no L-v 2 window, no network
 439 | +        self.assertEqual((r["pass"], r["measured"]), (False, False))
 440 | +        env = Env(SPEECH + [(1.81, 3.20, -20.0)], dur=2.5)                       # the hook runs past the audio
 441 | +        r = self.measure(env)
 442 | +        self.assertEqual((r["pass"], r["measured"]), (False, False))
 443 | +        self.assertIn("not inside its audio window", r["why"])
 444 | +
 445 | +
 446 | +if __name__ == "__main__":
 447 | +    unittest.main()
 448 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 449 | index ebf6bd6d..4417ea1e 100644
 450 | --- a/tests/package/test_ledger_build.py
 451 | +++ b/tests/package/test_ledger_build.py
 452 | @@ -492,13 +492,30 @@ class TestWindowRecords(unittest.TestCase):
 453 |              self.assertTrue(text.startswith("money caption line 585"))        # ... ("money", the last word of line 510)
 454 |              self.assertGreaterEqual(win[1], m["end"] + CI.CONTEXT_AFTER_S)
 455 |  
 456 | -    def test_two_records_matching_the_rows_sha_are_ambiguous_and_give_no_context(self):
 457 | -        with tempfile.TemporaryDirectory() as d:
 458 | +    def test_the_ledgers_own_record_is_found_and_differing_matches_are_ambiguous(self):
 459 | +        """The first FRESH build: 8 of 16 window videos had their caption record only in the ledger's store
 460 | +        (pp-ingest's), not in main's. A copy with the same words is one record; same-sha matches whose words differ
 461 | +        are ambiguous (audit 0123 C1, glm P0-1), so there is no context."""
 462 | +        ctx = E.Context(NOW, REG)
 463 | +        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as led:
 464 |              rel, wp, r, words = window_fixture(d)
 465 |              src = os.path.join(d, "transcripts", "vidW", "transcript.yt_auto.json")
 466 | -            with open(src) as f, open(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"), "w") as g:
 467 | -                g.write(f.read())
 468 | -            cs, why = LB.caption_source(r, E.Context(NOW, REG), d)
 469 | +            os.makedirs(os.path.join(led, "transcripts", "vidW"))
 470 | +            with open(src) as f:
 471 | +                cap = json.load(f)
 472 | +            os.remove(src)                                                   # only in the ledger's store
 473 | +            with open(os.path.join(led, "transcripts", "vidW", "transcript.yt_auto.json"), "w") as f:
 474 | +                json.dump(cap, f)
 475 | +            self.assertIsNone(LB.caption_source(r, ctx, d)[0])                  # main's store alone: none
 476 | +            cs, where = LB.caption_source(r, ctx, d, led)
 477 | +            self.assertEqual((cs.transcript_method, where), ("yt_auto", "ledger/transcript.yt_auto.json"))
 478 | +            with open(src, "w") as f:                                         # the same record in main's store too
 479 | +                json.dump(cap, f)
 480 | +            self.assertEqual(LB.caption_source(r, ctx, d, led)[1], "main/transcript.yt_auto.json")
 481 | +            odd = dict(cap, words=[{"word": "other", "start": 1.0, "end": 1.5}])    # same segments sha, other words
 482 | +            with open(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"), "w") as g:
 483 | +                json.dump(odd, g)
 484 | +            cs, why = LB.caption_source(r, ctx, d, led)
 485 |              self.assertIsNone(cs)
 486 |              self.assertIn("ambiguous", why)
 487 |              os.remove(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"))
 488 | @@ -506,6 +523,35 @@ class TestWindowRecords(unittest.TestCase):
 489 |                  f.write("{not json")                                         # "no record matches" alone
 490 |              self.assertIn("1 transcript file(s) could not be read", LB.caption_source(r, E.Context(NOW, REG), d)[1])
 491 |  
 492 | +    def test_a_moment_without_context_never_poisons_its_step_a_batch(self):
 493 | +        """The first FRESH build: one window moment without a caption record in a step-A batch made the batch's call
 494 | +        fail, and EVERY moment in it was marked unavailable (0 cleared in 0 s). Now that moment alone is not cleared."""
 495 | +        import context_integrity as CI
 496 | +        import package as PK
 497 | +        ctx = E.Context(NOW, REG)
 498 | +        with tempfile.TemporaryDirectory() as d:
 499 | +            rel, wp, r, words = window_fixture(d, caption=False)              # a window without its caption
 500 | +            TestWordSourceAndInputs.store_with(self, d, "vidA", SENTS)        # a full-video record, other channel
 501 | +            ra = dict(row(SENTS[1], mid="A1", vid="vidA"), channel_id="UCother", channel_name="Other")
 502 | +            ms, srcs, rep = LB.build_inputs([r, ra], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 503 | +            self.assertEqual(sorted(m["mined"]["ledger_moment_id"] for m in ms), ["A1", "W1"])
 504 | +            sent = []
 505 | +
 506 | +            def step_a(router, contexts, *a, **k):
 507 | +                sent.append(sorted(contexts))
 508 | +                return {mid: dict(sent=True) for mid in contexts}, "xai:grok"
 509 | +            saved, CI.step_a = CI.step_a, step_a
 510 | +            try:
 511 | +                router = type("R", (), {"backends": {}})()
 512 | +                a_by, fails, v, f = PK.prescreen(router, ms, srcs, ctx, "heimdall", log=lambda s: None)
 513 | +            finally:
 514 | +                CI.step_a = saved
 515 | +            mid_w = next(m["moment_id"] for m in ms if m["mined"]["ledger_moment_id"] == "W1")
 516 | +            mid_a = next(m["moment_id"] for m in ms if m["mined"]["ledger_moment_id"] == "A1")
 517 | +            self.assertEqual(sent, [[mid_a]])                                  # the batch still went out
 518 | +            self.assertTrue(fails[mid_w][0].startswith("CONTEXT_UNAVAILABLE"))
 519 | +            self.assertIn(mid_a, a_by)
 520 | +
 521 |      def test_the_exclusion_verdict_reads_the_caption_context(self):
 522 |          """glm C1 P2-7: the normal path, measured: the verdict's prompt carries the caption's words around the clip."""
 523 |          import package as PK
 524 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 525 | index 6b68f88e..6501f65f 100644
 526 | --- a/tests/package/test_medley.py
 527 | +++ b/tests/package/test_medley.py
 528 | @@ -368,14 +368,14 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 529 |  
 530 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 531 |          pk = self.build()
 532 | -        self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
 533 | +        self.assertEqual(package_pin.required_gates(pk)[-4:], ("medley", "ly_shape", "house_style", "hook_onset"))
 534 |          pk["gates"] = self.gates(pk)
 535 |          pin = package_pin.to_pin(spk(pk), "test")
 536 |          mp = pin["moments_package"]
 537 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 538 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 539 |          self.assertEqual(mp["shape"], "medley")
 540 | -        for missing in ("medley", "ly_shape", "house_style"):
 541 | +        for missing in ("medley", "ly_shape", "house_style", "hook_onset"):
 542 |              g = self.gates(pk)
 543 |              g.pop(missing)
 544 |              with self.assertRaises(package_pin.PinRefused):
 545 | @@ -421,11 +421,11 @@ class Rig:
 546 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 547 |  
 548 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 549 | -                 spend=None):
 550 | +                 spend=None, no_hook=()):
 551 |          import providers as P
 552 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 553 |          self.takeaways, self.spend = list(takeaways or []), spend
 554 | -        self.uncuttable, self.excluded = set(uncuttable), set(excluded)
 555 | +        self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 556 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 557 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 558 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 559 | @@ -475,6 +475,9 @@ class Rig:
 560 |                                                           "backend": "xai:grok"},
 561 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 562 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 563 | +            "hook_onset_for": lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"}
 564 | +                                                  if m["moment_id"] in self.no_hook else
 565 | +                                                  {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"}),
 566 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 567 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 568 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 569 | @@ -617,6 +620,20 @@ class TestBuildLoop(unittest.TestCase):
 570 |          self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
 571 |          self.assertIsNone(out["package"])
 572 |  
 573 | +    def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
 574 | +        """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
 575 | +        only when its hook onset was measured and passed; the proposer's hook gives way to the angle's next."""
 576 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
 577 | +        pk = rig.run()["package"]
 578 | +        self.assertNotEqual(pk["segments"][0]["moment_id"], "h")
 579 | +        self.assertEqual(pk["gates"]["hook_onset"]["status"], "PASS")
 580 | +        self.assertEqual(pk["gates"]["hook_onset"]["lead_ms"], 200)
 581 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h", "x", "y", "z"})
 582 | +        out = rig.run()
 583 | +        self.assertIsNone(out["package"])
 584 | +        self.assertEqual(rig.medley_calls, [])                    # nothing paid for a line-up that cannot open
 585 | +        self.assertIn("no line-up", out["tried"][0]["why"])
 586 | +
 587 |      def test_the_supply_exception_is_recorded(self):
 588 |          ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
 589 |          rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
 590 | @@ -674,7 +691,8 @@ class TestNoVoiceRealGates(unittest.TestCase):
 591 |                 for sg in pk["segments"]}
 592 |          coh = dict(med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 593 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 594 | -                                   shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 595 | +                                   shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 596 | +                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"})
 597 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 598 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 599 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 600 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real
clips). It adds G17a at the PIN stage: a medley's HOOK must keep >= 80 ms (HEAD_LEAD_MIN_S, D1: the hook starts
playback) of GENUINE quiet before its first onset in the prepared clip.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the integrator's render HELD batch pin #1 at 01:39 ET Nov 13 on G17_onset_tail. Its hook kept 30 ms of genuine
lead (the render measures that with sentence_law.gate_g17_prepared = head_tail on the prepared clip).
- The packager's eligibility rule T12 measured the WORD RECORD's gap before the hook (400 ms) and passed it.
- The source audio, measured offline with acoustic.rms_envelope at 10 ms, holds breath (about -27 dBFS), then exact
  DIGITAL ZEROS (a hard edit, -200 dB), then speech.
- Zeros are not room tone (quiet_runs(genuine=True) drops frames under DIGITAL_FLOOR_DBFS), so the genuine lead was
  about 20-30 ms.
- On pin #1's real audio, the new check measures 20 ms for that hook (FAIL), and 200 ms / 30 ms for its two other
  clips (only a hook needs 80 ms).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- the gate inventory is sealed, and a required row missing or not exactly PASS refuses the pin.

The files:
1. pipeline/hook_onset.py (new): measure(src, w0, w1, video_id, start, end, work_dir, audio=None).
   - The moment's cut is planned on the SOURCE audio (the L-v 2 window that transcript_truth.audio_window already
     fetched) with the render's own sentence_law.edge_plan.
   - The planned prepared clip's head is measured with the render's own sentence_law.head_tail, on a slice of the
     source envelope from the planned cut (_Slice).
   - A lead-in pad counts only where edge_plan grants one (a file head).
   - It is not measured (never a pass) on any missing audio, word or plan.
2. pipeline/package.py:
   - hook_onset_for(): a cached wrapper.
   - build(): measures every moment that cleared L-v 2 + CUTTABLE, before the angles.
   - lineup_for(need_onset=True, set by build): a moment OPENS a medley only if its hook onset was measured and
     passed; the proposer's hook gives way to the angle's next one that did.
   - inventory(hook=...): a sealed "hook_onset" row (PASS / FAIL / NOT RUN, with lead_ms, cut_in, why).
3. pipeline/package_pin.py: MEDLEY_GATES gains "hook_onset", so to_pin refuses a medley without it, exactly PASS.
4. tests/package/test_hook_onset.py (new): synthetic envelopes. Breath, then digital zeros, then speech: FAIL. Room
   tone: PASS. No audio, or words outside the window: not measured.
5. tests/package/test_medley.py:
   - the build rig stubs hook_onset_for (no audio);
   - a new test: the proposer's hook gives way, and with none able to open there is no line-up and no paid call;
   - the medley rows include hook_onset.

Check, concretely:
(a) Can a hook with < 80 ms of genuine lead (as the render will measure it) still reach a pin? Look at the slice
    versus the prepared clip, the pad, zeros, and the cut's choice.
(b) Can an unmeasured hook pass or open a line-up?
(c) Does anything change for non-hook clips, or for the full-video and window paths?
(d) Is the hook_onset row really required and sealed for every medley pin, the no-voice path included?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".


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
