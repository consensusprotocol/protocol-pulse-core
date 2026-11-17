# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1135
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)


## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1135, rulings 136 / 137 stage 1)

SEATS ANSWERED: 1 of 3 (qwen3.8-27b, P0/P1 none, a traced review; gpt-oss-20b and gemma-4-31b-it spent their token
caps with no answer). Cycle 2 raises their caps (gpt-oss 32,000, gemma 24,000).

## Findings
- qwen [P2] build(*args, **kw) would forward a caller's soft=True into the CLEAN pass: ACCEPTED. The wrapper strips
  "soft" from kw before the clean pass; a test passes soft=True and shows the passes are still clean then soft.

## Changed since cycle 1's diff
1. RULING 138 (3) (orchestrator 11:40 ET): "each flag is one plain sentence PBX can judge in five seconds (what the
   checker doubted, about which clip), no codes". STEP_A_SOFT now holds the doubt in plain words; flag_sentence(label,
   channel, code) makes "The opening clip (Scott Melker): the checker doubted this is the speaker's own sincere view
   (they may be quoting someone or joking)."; inventory(..., who={label: channel}) builds one sentence per clip and
   code; both inventory calls pass who from the package's segments.
2. RULING 137 (3): the day cap is $1.50 all-in from tonight (today's stop $1.40, passed as --stop-usd), so
   proof_ledger.STOP_CEILING_USD 1.25 -> 1.50 (its test: 1.51 is refused). Without it today's kept line-up's fourth
   vision check could not start under the old $1.25 ceiling (four sheets of 0.6 x list each, after the step-A bill).
3. Suites: 41 files by exit code, 880 tests (before changes 1-2); the touched files' suites pass after them (81 tests).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1135/C2_STEP.diff (468 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 0d4ba34..f26688d 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -79,6 +79,27 @@ PRESCREEN_WORKERS = 6              # ruling 58: the step-A batches run in parall
   6 |  SECOND_VERDICT_DEADLINE_S = 120.0  # RULING 82 (20:02 Nov 13): each second-vendor / off-writer step-A call; at it the next
   7 |  SECOND_VERDICT_BATCH = 2           # model (deepseek -> glm-5.3-flash -> qwen3.8-27b); small batches so one fits in it
   8 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
   9 | +# RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): TWO CLASSES, a HARD gate refuses, a SOFT gate scores and
  10 | +# FLAGS; NEVER EMPTY: when the clean search seals nothing, a second pass seals the best line-up that passes every hard
  11 | +# gate with its soft flags in plain words (the pin's moments_package "review_flags"; the integrator's note opens
  12 | +# "REVIEW FLAGS: ..."); at most FLAGGED_DAY_MAX flagged packages a day, a clean one always first. STAGE 1 (line 1, 11:29
  13 | +# ET Nov 17): step A only. Its SOFT codes, each with the plain words PBX reads; STALE_TIME (stale time), SPEAKER_CHANGE
  14 | +# (speaker credit) and RETRACTION (factual) stay HARD, even from one family, until stage 2 asks the second family.
  15 | +# RULING 138 (3): in the note each flag is ONE plain sentence PBX can judge in five seconds: what the checker doubted,
  16 | +# about which clip, no codes (flag_sentence).
  17 | +STEP_A_SOFT = {"NOT_OWN_SINCERE": "the checker doubted this is the speaker's own sincere view (they may be quoting "
  18 | +                                  "someone or joking)",
  19 | +               "REFERENT_OUTSIDE": "the checker thought it points back to something said before the clip starts",
  20 | +               "CONDITION_OUTSIDE": "the checker thought the claim depends on a condition said outside the clip",
  21 | +               "UNCERTAIN": "the checker was not sure what the speaker means"}
  22 | +CLIP_PLACE = {"hook": "The opening clip", "clip_01": "The second clip", "clip_02": "The third clip",
  23 | +              "clip_03": "The fourth clip", "clip_04": "The fifth clip"}
  24 | +
  25 | +
  26 | +def flag_sentence(label, channel, code):
  27 | +    """RULING 138 (3): one flag as PBX reads it: the clip's place and channel, then what the checker doubted."""
  28 | +    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): {STEP_A_SOFT[code]}."
  29 | +FLAGGED_DAY_MAX = 2
  30 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
  31 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
  32 |  WRITES = 2
  33 | @@ -469,6 +490,27 @@ def is_held(why):
  34 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
  35 |  
  36 |  
  37 | +def soft_step_a(ms, a_by, fails):
  38 | +    """RULING 137 STAGE 1: the moments step A refused for SOFT codes only (STEP_A_SOFT): a step-A answer on file, a
  39 | +    refusal (never a held one, ruling 102), and every code soft (one hard code keeps it out). -> {moment_id: a copy of
  40 | +    the moment carrying "step_a_flags", its codes}."""
  41 | +    out = {}
  42 | +    for m in ms:
  43 | +        f = fails.get(m["moment_id"])
  44 | +        if m["moment_id"] in a_by and f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f):
  45 | +            out[m["moment_id"]] = dict(m, step_a_flags=sorted({str(c) for c in f}))
  46 | +    return out
  47 | +
  48 | +
  49 | +def cleared_pool(ms, a_by, fails, soft=False):
  50 | +    """The moments that cleared step A (an answer on file, no failure), and in the never-empty pass (RULING 137
  51 | +    stage 1, soft=True) also those soft_step_a lets back, flagged. -> (cleared {id: moment}, back {id: moment})."""
  52 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  53 | +    back = soft_step_a(ms, a_by, fails) if soft else {}
  54 | +    cleared.update(back)
  55 | +    return cleared, back
  56 | +
  57 | +
  58 |  def local_held(a):
  59 |      """RULING 127 (2) (orchestrator 21:30 ET Nov 16): a step-A verdict from the local judge (gemma3:27b, ruling 87's last
  60 |      resort), PASS or REFUSE, is never final while a Heimdall family can be asked: HELD, 'local, provisional', never
  61 | @@ -2991,13 +3033,14 @@ def candidate_lineup(router, candidate, cleared, now):
  62 |      return segs, None
  63 |  
  64 |  
  65 | -def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  66 | +def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  67 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  68 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  69 |            join_cache=None,
  70 |            visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None,
  71 | -          ledger_aliases=None):
  72 | -    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  73 | +          ledger_aliases=None, soft=False):
  74 | +    """RULING 137: soft=True is the never-empty pass (build() calls it): step A's soft refusals are let back, flagged.
  75 | +    L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  76 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  77 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  78 |      one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
  79 | @@ -3134,7 +3177,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  80 |              par.update(ahead.result())
  81 |              ahead_pool.shutdown()
  82 |      pre_by = par.pop("by", None) or {}                   # which back-end confirmed each moment ahead (not reported)
  83 | -    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  84 | +    cleared, back = cleared_pool(ms, a_by, fails, soft)  # RULING 137 stage 1: the never-empty pass adds back, flagged
  85 |      levels = current_levels(sources.values(), ctx)
  86 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  87 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
  88 | @@ -3146,6 +3189,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  89 |                           "last_resort_87": {}},                  # RULING 102: held, never refused; the local judge
  90 |             "angles": [], "takeaways": [],
  91 |             "package": None}
  92 | +    if soft:                                                # RULING 137 stage 1: which came back, with which codes
  93 | +        out["prescreen"]["soft_back"] = {mid: m["step_a_flags"] for mid, m in back.items()}
  94 | +        log(f"  RULING 137 NEVER EMPTY (stage 1): {len(back)} moment(s) step A refused for soft codes only come back, "
  95 | +            f"flagged: " + ", ".join(f"{mid[:8]} {m['step_a_flags']}" for mid, m in back.items()))
  96 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
  97 |          f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
  98 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
  99 | @@ -3581,7 +3628,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 100 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 101 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 102 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 103 | -                                last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 104 | +                                last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 105 | +                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]})   # RULING 138 (3)
 106 |          import package_pin
 107 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 108 |          if problems:
 109 | @@ -4064,7 +4112,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 110 |                                              stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 111 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 112 |                                              value=val,                       # ruling 91: the takeaway earned its place
 113 | -                                            last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 114 | +                                            last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 115 | +                                            soft=soft, who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 116 | +                                                            for sg in pk["segments"]})
 117 |                      if not ok_c:
 118 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 119 |                          cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 120 | @@ -4163,6 +4213,23 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 121 |      return out
 122 |  
 123 |  
 124 | +def build(*args, never_empty=False, flagged_today=0, **kw):
 125 | +    """RULINGS 136 / 137, NEVER EMPTY: the clean search first (_build), as before; a clean package always outranks a
 126 | +    flagged one. Only when it seals nothing, never_empty is set and fewer than FLAGGED_DAY_MAX flagged packages went
 127 | +    out today (flagged_today, the caller's count), the never-empty pass: the same search again (_build soft=True) with
 128 | +    step A's soft refusals back in, flagged (stage 1). Its record names both passes ("never_empty")."""
 129 | +    kw = {k: v for k, v in kw.items() if k != "soft"}     # audit 1135 C1 (qwen P2): the clean pass is never soft
 130 | +    out = _build(*args, **kw)
 131 | +    if not never_empty or out.get("package") or flagged_today >= FLAGGED_DAY_MAX:
 132 | +        return out
 133 | +    (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 134 | +                             f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 135 | +    soft = _build(*args, soft=True, **kw)
 136 | +    info = {"stage": 1, "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 137 | +            "soft_back": (soft.get("prescreen") or {}).get("soft_back")}
 138 | +    return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 139 | +
 140 | +
 141 |  def _spent(spend):
 142 |      """(estimate, vendor-reported) from the caller's meter. A bare number is the estimate alone; its reported figure
 143 |      is then taken to be the same (the conservative reading). No meter: (0, 0)."""
 144 | @@ -4173,7 +4240,7 @@ def _spent(spend):
 145 |  
 146 |  
 147 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 148 | -              hook=None, stand=None, visual=None, value=None, last_resort=None):
 149 | +              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None):
 150 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 151 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 152 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 153 | @@ -4196,6 +4263,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 154 |      det = fid["deterministic"]
 155 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 156 |      a_rows = list((a_by or {}).values())
 157 | +    a_codes = sorted({str(c) for a in a_rows for c in CI.a_failures(a)})   # RULING 137 stage 1: step A's codes; in the
 158 | +    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # never-empty pass, soft ones FLAG
 159 |      return {
 160 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
 161 |          "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 162 | @@ -4208,9 +4277,13 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 163 |          "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 164 |                                f"{FINAL_TAIL_S} s tail)"),
 165 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 166 | -        "context_a": dict(row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 167 | +        "context_a": dict(row(bool(a_rows) and (not a_codes or soft_a),
 168 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 169 |                                n=len(a_rows)),
 170 | +                          **({"status": "FLAGGED",            # RULING 137 stage 1; 138 (3): a sentence a clip
 171 | +                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb, a in (a_by or {}).items()
 172 | +                                        for c in sorted({str(x) for x in CI.a_failures(a)})]}
 173 | +                             if soft_a and len(a_rows) >= 1 else {}),
 174 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 175 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 176 |                                measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 177 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 178 | index 3c5ca7d..5fb02f2 100644
 179 | --- a/pipeline/package_pin.py
 180 | +++ b/pipeline/package_pin.py
 181 | @@ -31,6 +31,11 @@ REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate
 182 |  # STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 183 |  MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone",
 184 |                  "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 185 | +# RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): a SOFT gate scores and FLAGS. Its row may say "FLAGGED"
 186 | +# with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 187 | +# (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 188 | +SOFT_GATES = frozenset({"context_a"})
 189 | +REVIEW_FLAGS_MAX = 3
 190 |  
 191 |  
 192 |  # RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
 193 | @@ -375,14 +380,41 @@ def speaker_problems(segments):
 194 |      return out
 195 |  
 196 |  
 197 | +def flagged_ok(g, row):
 198 | +    """RULING 137: a FLAGGED row stands only on a SOFT gate and only with its flags: a non-empty list of plain-word
 199 | +    strings."""
 200 | +    fl = row.get("flags")
 201 | +    return g in SOFT_GATES and isinstance(fl, list) and bool(fl) and all(isinstance(f, str) and f.strip() for f in fl)
 202 | +
 203 | +
 204 | +def review_flags_of(gates):
 205 | +    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once."""
 206 | +    out = []
 207 | +    for _g, row in (gates.items() if isinstance(gates, dict) else ()):
 208 | +        if isinstance(row, dict) and row.get("status") == "FLAGGED":
 209 | +            out += [f for f in row.get("flags") or [] if isinstance(f, str) and f not in out]
 210 | +    return out
 211 | +
 212 | +
 213 | +def review_problems(mp):
 214 | +    """RULING 137: [why] when a pin's moments_package "review_flags" is not exactly what its sealed gates flag, or is
 215 | +    over REVIEW_FLAGS_MAX (empty = it holds)."""
 216 | +    want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
 217 | +    out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
 218 | +    return out + ([f"{len(want)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"]
 219 | +                  if len(want) > REVIEW_FLAGS_MAX else [])
 220 | +
 221 | +
 222 |  def gate_problems(gates, required=REQUIRED_GATES):
 223 | -    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 224 | +    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live;
 225 | +    RULING 137: or FLAGGED on a SOFT gate with its flags, flagged_ok)."""
 226 |      if not isinstance(gates, dict):
 227 |          return ["no gate inventory"]
 228 |      out = []
 229 |      for g in required:
 230 |          row = gates.get(g)
 231 | -        if not isinstance(row, dict) or row.get("status") != "PASS":
 232 | +        if not isinstance(row, dict) or not (row.get("status") == "PASS" or
 233 | +                                             (row.get("status") == "FLAGGED" and flagged_ok(g, row))):
 234 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 235 |          elif row.get("replayed") is not False:
 236 |              out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
 237 | @@ -460,6 +492,9 @@ def to_pin(pk, run_name):
 238 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 239 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
 240 |          spotlight_problems(pk) + takeaway_problems(pk)
 241 | +    rf = review_flags_of(pk.get("gates"))                 # RULING 137: derived from the sealed gates, at most 3
 242 | +    problems += [f"{len(rf)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if len(rf) > REVIEW_FLAGS_MAX \
 243 | +        else []
 244 |      if problems:
 245 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 246 |      segs = []
 247 | @@ -510,6 +545,7 @@ def to_pin(pk, run_name):
 248 |                                      "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 249 |                                     if spot else {}),
 250 |                                  "gates": pk["gates"],
 251 | +                                **({"review_flags": rf} if rf else {}),   # RULING 137: absent when clean
 252 |                                  **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 253 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 254 |                                  **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 255 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 256 | index b3f5a13..3779fe1 100644
 257 | --- a/tests/package/proof_ledger.py
 258 | +++ b/tests/package/proof_ledger.py
 259 | @@ -73,6 +73,32 @@ import package as PK  # noqa: E402
 260 |  import hook_bar as HB  # noqa: E402
 261 |  import package_pin  # noqa: E402
 262 |  import proof_ly as PL  # noqa: E402
 263 | +
 264 | +FLAGGED_DAY = os.path.join(HERE, "proof", "FLAGGED_DAY.json")   # RULING 136 (2): the flagged pins of the 21:10 day
 265 | +
 266 | +
 267 | +def flagged_today(path=FLAGGED_DAY, day=None):
 268 | +    """RULING 136 (2): how many flagged packages this builder sealed in the current 21:10-21:10 day (the day ledger's
 269 | +    name keys it; an unreadable or another day's file counts 0)."""
 270 | +    day = day or os.path.basename(PL.day_ledger())
 271 | +    try:
 272 | +        d = json.load(open(path))
 273 | +    except (OSError, ValueError):
 274 | +        return 0
 275 | +    return len(d.get("pins") or []) if isinstance(d, dict) and d.get("day") == day else 0
 276 | +
 277 | +
 278 | +def record_flagged(pin, path=FLAGGED_DAY, day=None):
 279 | +    """RULING 136 (2): a flagged pin was sealed: add it to the day's count."""
 280 | +    day = day or os.path.basename(PL.day_ledger())
 281 | +    try:
 282 | +        d = json.load(open(path))
 283 | +    except (OSError, ValueError):
 284 | +        d = {}
 285 | +    if not isinstance(d, dict) or d.get("day") != day:
 286 | +        d = {"day": day, "pins": []}
 287 | +    d["pins"].append({"story_id": pin["story_id"], "review_flags": pin["moments_package"].get("review_flags")})
 288 | +    json.dump(d, open(path, "w"), indent=1)
 289 |  import proof_saved_runs as PS  # noqa: E402
 290 |  import providers as P  # noqa: E402
 291 |  import speakers as SP  # noqa: E402
 292 | @@ -217,7 +243,9 @@ def delivered_pins(paths):
 293 |      return spans, newest, pins
 294 |  
 295 |  
 296 | -STOP_CEILING_USD = 1.25          # ORDER 17:50 ET Nov 16: --stop-usd at most this ('ADD 25 CENTS': a day cap of $1.25)
 297 | +STOP_CEILING_USD = 1.50          # RULING 137 (3) (orchestrator 11:05 ET Nov 17): the day cap is $1.50 all-in from the
 298 | +#   21:10 ET day of Nov 17 (today's stop $1.40, given as --stop-usd); --stop-usd at most this. Was 1.25 (ORDER 17:50 ET
 299 | +#   Nov 16, 'ADD 25 CENTS').
 300 |  
 301 |  
 302 |  def lock_off(segs):
 303 | @@ -538,6 +566,7 @@ def main(argv=None):
 304 |      spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
 305 |      sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
 306 |      kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
 307 | +              never_empty=True, flagged_today=flagged_today(),                     # RULINGS 136 / 137 (stage 1)
 308 |                work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 309 |                spend=lambda: (own["est"], own["best"]),
 310 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 311 | @@ -614,6 +643,9 @@ def main(argv=None):
 312 |                                                name="MOMENTS_PIN_LEDGER.json")
 313 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 314 |                            "package_sha256": pin["moments_package"]["package_sha256"]}
 315 | +            if pin["moments_package"].get("review_flags"):        # RULING 136 (2): a flagged pin counts for the day
 316 | +                record_flagged(pin)
 317 | +                res["pin"]["review_flags"] = pin["moments_package"]["review_flags"]
 318 |              import shutil                                # ruling 70: each segment's sheet beside the pin
 319 |              for sg in pin["segments"]:
 320 |                  sh = (sg.get("visual") or {}).get("sheet") or {}
 321 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 322 | new file mode 100644
 323 | index 0000000..5a93bdd
 324 | --- /dev/null
 325 | +++ b/tests/package/test_ruling_137.py
 326 | @@ -0,0 +1,141 @@
 327 | +#!/usr/bin/env python3
 328 | +"""RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17), STAGE 1: NEVER EMPTY for step A. A clean package first;
 329 | +when the clean pass seals nothing, a second pass lets back the moments step A refused for SOFT codes only, each flagged
 330 | +in plain words; the pin's step-A row says FLAGGED with them and moments_package carries them as review_flags (at most
 331 | +3); a hard code, a held moment, a FLAGGED row on a hard gate never pass. Offline."""
 332 | +import json
 333 | +import os
 334 | +import sys
 335 | +import tempfile
 336 | +import unittest
 337 | +from unittest import mock
 338 | +
 339 | +HERE = os.path.dirname(os.path.abspath(__file__))
 340 | +REPO = os.path.dirname(os.path.dirname(HERE))
 341 | +sys.path[:0] = [os.path.join(REPO, "pipeline"), HERE]
 342 | +import package as PK  # noqa: E402
 343 | +import package_pin as PP  # noqa: E402
 344 | +import proof_ledger as PLG  # noqa: E402
 345 | +
 346 | +SINCERE = PK.flag_sentence("hook", "Scott Melker", "NOT_OWN_SINCERE")
 347 | +
 348 | +
 349 | +def answer(**kw):
 350 | +    a = {"backend": "b", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [],
 351 | +         "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 352 | +    a.update(kw)
 353 | +    return a
 354 | +
 355 | +
 356 | +class TestTheNeverEmptyPool(unittest.TestCase):
 357 | +    def test_soft_codes_come_back_flagged_and_nothing_else_does(self):
 358 | +        ms = [{"moment_id": k} for k in ("s", "h", "x", "n", "c")]
 359 | +        a_by = {"s": {}, "h": {}, "x": {}, "c": {}}                       # 'n' has no step-A answer on file
 360 | +        fails = {"s": ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"], "h": ["REFERENT_OUTSIDE", "STALE_TIME"],
 361 | +                 "x": [PK.HELD + " no verdict"], "n": ["NOT_OWN_SINCERE"], "c": []}
 362 | +        clean, back = PK.cleared_pool(ms, a_by, fails)
 363 | +        self.assertEqual((sorted(clean), back), (["c"], {}))              # the clean pass: as before
 364 | +        both, back = PK.cleared_pool(ms, a_by, fails, soft=True)
 365 | +        self.assertEqual(sorted(both), ["c", "s"])
 366 | +        self.assertEqual(back["s"]["step_a_flags"], ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
 367 | +        self.assertNotIn("step_a_flags", ms[0])                           # a copy: the pool's moment is untouched
 368 | +
 369 | +
 370 | +class TestTheStepARow(unittest.TestCase):
 371 | +    def base(self, **a):
 372 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 373 | +               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
 374 | +        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
 375 | +        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"hook": answer(**a)},
 376 | +                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
 377 | +                    truth={"m": {"ok": True, "model": "s", "replayed": False, "edges": {"cuttable": True}}},
 378 | +                    coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})
 379 | +
 380 | +    def test_soft_codes_flag_only_in_the_never_empty_pass_and_a_hard_code_still_fails(self):
 381 | +        self.assertEqual(PK.inventory(**self.base(), soft=True)["context_a"]["status"], "PASS")      # clean: PASS
 382 | +        quoted = self.base(view="quoting_someone_else")
 383 | +        self.assertEqual(PK.inventory(**quoted)["context_a"]["status"], "FAIL")                     # the clean pass
 384 | +        row = PK.inventory(**quoted, soft=True, who={"hook": "Scott Melker"})["context_a"]
 385 | +        self.assertEqual((row["status"], row["flags"], row["replayed"]), ("FLAGGED", [SINCERE], False))
 386 | +        self.assertEqual(SINCERE, "The opening clip (Scott Melker): the checker doubted this is the speaker's own "
 387 | +                                  "sincere view (they may be quoting someone or joking).")   # ruling 138 (3): no code
 388 | +        stale = self.base(view="quoting_someone_else", time_ok="no")                               # a hard code too
 389 | +        self.assertEqual(PK.inventory(**stale, soft=True)["context_a"]["status"], "FAIL")
 390 | +
 391 | +
 392 | +class TestThePin(unittest.TestCase):
 393 | +    def pk(self, **gates):
 394 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in PP.REQUIRED_GATES}
 395 | +        g.update(gates)
 396 | +        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
 397 | +                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
 398 | +                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
 399 | +                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 400 | +                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 401 | +                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 402 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 403 | +                              "speaker": {"name": "unknown", "role": None, "line": None, "basis": None, "why": "t",
 404 | +                                          "people": [], "measured": True},
 405 | +                              "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 406 | +
 407 | +    def flagged(self, flags, gate="context_a", replayed=False):
 408 | +        return {gate: {"status": "FLAGGED", "by": "x", "replayed": replayed, "n": 1, "flags": flags}}
 409 | +
 410 | +    def test_a_flagged_soft_row_seals_with_its_review_flags(self):
 411 | +        pin = PP.to_pin(self.pk(**self.flagged([SINCERE])), "r")
 412 | +        mp = pin["moments_package"]
 413 | +        self.assertEqual((mp["review_flags"], PP.review_problems(mp)), ([SINCERE], []))
 414 | +        self.assertEqual(mp["package_sha256"], PP.pin_seal(pin))                     # the flags are sealed with the gates
 415 | +        self.assertNotEqual(mp["package_sha256"], PP.to_pin(self.pk(), "r")["moments_package"]["package_sha256"])
 416 | +        self.assertTrue(PP.review_problems(dict(mp, review_flags=["something else"])))   # not the sealed flags
 417 | +        self.assertNotIn("review_flags", PP.to_pin(self.pk(), "r")["moments_package"])   # clean: absent
 418 | +
 419 | +    def test_what_never_seals(self):
 420 | +        for bad in (self.flagged([SINCERE], gate="exclusion"),                         # FLAGGED on a HARD gate
 421 | +                    self.flagged([]), self.flagged([""]), self.flagged("not a list"),
 422 | +                    self.flagged([SINCERE], replayed=True),
 423 | +                    self.flagged(["one", "two", "three", "four"])):                    # over 3 (ruling 136 (2))
 424 | +            with self.assertRaises(PP.PinRefused, msg=str(bad)):
 425 | +                PP.to_pin(self.pk(**bad), "r")
 426 | +
 427 | +
 428 | +class TestTheTwoPasses(unittest.TestCase):
 429 | +    def run_build(self, clean_out, soft_out, **kw):
 430 | +        calls = []
 431 | +
 432 | +        def fake(*a, **k):
 433 | +            calls.append(bool(k.get("soft")))
 434 | +            return dict(soft_out if k.get("soft") else clean_out)
 435 | +        with mock.patch.object(PK, "_build", side_effect=fake):
 436 | +            out = PK.build("router", [], {}, None, log=lambda m: None, **kw)
 437 | +        return calls, out
 438 | +
 439 | +    def test_clean_first_then_the_never_empty_pass_within_the_day_limit(self):
 440 | +        none, sealed = {"package": None, "why_none": "x"}, {"package": {"p": 1}}
 441 | +        calls, out = self.run_build(sealed, sealed, never_empty=True)
 442 | +        self.assertEqual((calls, "never_empty" in out), ([False], False))            # a clean package: one pass
 443 | +        calls, out = self.run_build(none, sealed, never_empty=True)
 444 | +        self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
 445 | +        calls, out = self.run_build(none, dict(none, why_none="y"), never_empty=True)
 446 | +        self.assertEqual((calls, out["package"], out["never_empty"]["soft_why_none"]), ([False, True], None, "y"))
 447 | +        self.assertEqual(self.run_build(none, sealed)[0], [False])                   # never_empty off: as before
 448 | +        self.assertEqual(self.run_build(none, sealed, never_empty=True, soft=True)[0], [False, True])   # audit 1135
 449 | +        #   C1 (qwen P2): a caller's soft never reaches the clean pass
 450 | +        self.assertEqual(self.run_build(none, sealed, never_empty=True, flagged_today=PK.FLAGGED_DAY_MAX)[0], [False])
 451 | +
 452 | +
 453 | +class TestTheDayCount(unittest.TestCase):
 454 | +    def test_counted_per_day_ledger(self):
 455 | +        with tempfile.TemporaryDirectory() as d:
 456 | +            p = os.path.join(d, "FLAGGED_DAY.json")
 457 | +            self.assertEqual(PLG.flagged_today(p, day="D1"), 0)
 458 | +            pin = {"story_id": "s1", "moments_package": {"review_flags": [SINCERE]}}
 459 | +            PLG.record_flagged(pin, p, day="D1")
 460 | +            PLG.record_flagged(dict(pin, story_id="s2"), p, day="D1")
 461 | +            self.assertEqual((PLG.flagged_today(p, day="D1"), PLG.flagged_today(p, day="D2")), (2, 0))
 462 | +            PLG.record_flagged(pin, p, day="D2")                                       # a new day starts afresh
 463 | +            self.assertEqual(json.load(open(p))["pins"], [{"story_id": "s1", "review_flags": [SINCERE]}])
 464 | +
 465 | +
 466 | +if __name__ == "__main__":
 467 | +    unittest.main()
 468 | 
```

---

pp-selectid: RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17), STAGE 1 of the hard/soft switch: NEVER EMPTY
for step A. Approved design (docs/audits/parallel/pp-selectid_R136_DESIGN_20261117.md): "(1) TWO CLASSES. HARD gates
still refuse ... Every OTHER gate becomes SOFT: it scores and FLAGS, it does not refuse ... (2) NEVER EMPTY. When no
line-up passes clean, the build seals the BEST line-up that passes every hard gate, with its soft flags listed in plain
words at the top of the Telegram note ('REVIEW FLAGS: ...'), at most one such flagged package per build window and at
most two a day, and only if it has no more than 3 soft flags; PBX decides. A clean package always outranks a flagged
one." Stage 1 covers step A only (today's kept line-up was refused there for soft codes only); every other gate is
unchanged here (stage 2). Files: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py,
tests/package/test_ruling_137.py. package_pin.py is imported LIVE by the integrator's check_pin_only, which calls
PP.gate_problems(mp["gates"], PP.required_gates(mp)) (its message of 11:3x): it changes nothing on its side.

THE CHANGE:
(a) package.STEP_A_SOFT (the plain words PBX reads per soft code): NOT_OWN_SINCERE, REFERENT_OUTSIDE,
    CONDITION_OUTSIDE, UNCERTAIN. STALE_TIME, SPEAKER_CHANGE and RETRACTION stay HARD even from one family in stage 1
    (context_integrity.a_failures, UNCHANGED, gives the codes). FLAGGED_DAY_MAX = 2.
(b) package.soft_step_a (:483) / cleared_pool (:495): the clean pool exactly as before; with soft=True also the moments
    step A refused for soft codes ONLY (an answer on file, not held, every code soft), each a copy carrying
    "step_a_flags".
(c) package.build (:4204) is now a wrapper over the former build (renamed _build, one new parameter soft=False, used
    only at cleared_pool and the two inventory calls): the clean pass first; only when it seals nothing, never_empty is
    set and fewer than FLAGGED_DAY_MAX flagged packages went out today, the soft pass; its record names both
    ("never_empty"). Every gate after step A runs on the soft pass's line-ups exactly as on the clean pass (L-v 2,
    CUTTABLE, hook onset, the hook bar, joins, clips-alone, the lock, vision, writes, coherence, value: all UNCHANGED).
(d) package.inventory (:4229): the "context_a" row is FLAGGED with "flags" (STEP_A_SOFT's words) only in the soft pass
    and only when every step-A code of the package's segments is soft; otherwise exactly as before (FAIL on any code).
(e) package_pin: SOFT_GATES = {"context_a"}; flagged_ok; gate_problems (:408) accepts a FLAGGED row only on a SOFT gate
    with a non-empty list of non-empty string flags, and still needs replayed False; review_flags_of derives the pin's
    moments_package "review_flags" from the sealed FLAGGED rows (to_pin :489, at most REVIEW_FLAGS_MAX 3, absent when
    clean); review_problems binds the unsealed list to the sealed rows. The flags sit inside the sealed gate inventory,
    so seal()/pin_seal (UNCHANGED, :249) bind them; an old pin has no FLAGGED row and recomputes as before.
(f) proof_ledger: never_empty=True and flagged_today (FLAGGED_DAY.json, keyed by the 21:10 day ledger) into every
    build call; record_flagged after a flagged pin is written.

TESTS (test_ruling_137, 6): the pool (soft codes back flagged; a hard code, a held moment, no answer stay out; the clean
pass unchanged; a copy); the step-A row (PASS clean; FAIL in the clean pass; FLAGGED with the words in the soft pass; a
hard code FAILS even then); the pin (seals with review_flags, sealed, bound; absent when clean; FLAGGED on a hard gate,
empty or non-string flags, replayed, and 4 flags never seal); the two passes (clean first; soft only after an empty
clean pass; the day limit; never_empty off); the day count (per day ledger, resets). Mutations P1-P14 after a control:
13 of 14 killed; P2 survives as an EQUIVALENT mutant (a held reason is never a soft code, so not is_held is redundant
with the all-soft test; kept as ruling 102's explicit intent).

PLEASE CHECK: (1) that no HARD gate can be passed by this change (a hard step-A code, any other gate's FAIL, a FLAGGED
row on a hard gate); (2) that a clean package always comes first and the soft pass runs only after an empty clean pass,
within the day limit; (3) that the pin's flags are bound by the seal and the live check accepts exactly this; (4) that
every pin sealed before this recomputes; (5) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
