# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_2342
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 431 s finish=stop usage in 12307 / out 4520 usd_reported=0.000942 usd~0.105 (upper-bound price)

The code implements the coherence panel as specified in RULING 118 (2) and RULING 130 (4).

### Audit Findings

1.  **Replay Rule Compliance**:
    *   **Member/Seed Logic**: The implementation correctly iterates through the configured members and seeds (`[7, 8]`), with a retry at `seed + 100` if the first attempt fails or violates the contract.
    *   **Verdict Threshold**: The "no verdict" condition (`len(votes) < min_members`) is correctly implemented as a hard stop that returns `False` and `measured: False`, ensuring it can never pass.
    *   **Pass Condition**: The majority rule (`sum(passes) * 2 > len(answers)`) correctly implements "more than half of all answers."
    *   **The Bar**: It uses `lineup_floors("coherence", ...)` to establish the standard bar, and the `passes` lambda correctly validates both the `through_line` (via `_line_ok`) and the ratings against those floors.
    *   **Output Values**: The use of `statistics.median_low` for `clips` and `vo_point`, and the selection of the first sound `through_line`, matches the replay requirements.

2.  **Writer Exclusion**:
    *   The code filters the `names` list to exclude the `writer_vendor` and `writer_family`.
    *   Furthermore, it passes `avoid_family=others` (where `others` includes other panel members and the writer's family) to `P.call_parsed`, ensuring strict isolation.

3.  **Contract and Parsing**:
    *   The `PANEL_CONTRACT` is correctly passed as the system prompt.
    *   The `parse` function correctly handles the "closing-brace rule" by routing through `hook_answer(text)[0]` when `braces=True`.

4.  **Integration and Fallbacks**:
    *   `coherence_panel_spec` allows the system to fall back to a single rater if the panel is not configured in the router, preserving existing behavior.
    *   The hook's cached rating (`own["passes"]`) is correctly required for a final `ok` verdict, adhering to Ruling 61.

5.  **Test Coverage**:
    *   `TestRuling130CoherencePanel` comprehensively covers the critical paths: majority pass, exactly-half failure, member-count failure (including retry seed verification), writer exclusion, and the brace-parsing rule.

### Conclusion
The implementation is precise, fail-closed, and adheres to all governing laws and the specific replay rules provided.

P1_OR_WORSE: 0

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_2342 (RULING 130 (4): the coherence panel, ruling 118 (2))

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 1 of 3.
- gemma: P1_OR_WORSE 0.
- qwen: cut off at its 24,000 cap with no closing count: NO ANSWER. Its one tagged finding before the cut, [P2] "staging
  base_url in production model config": NOT SO: the two new back-ends copy qwen's spec, and the worktree's config gives
  that base_url to 5 of 5 Heimdall back-ends (the gateway's own address, every Heimdall call goes there).
- mimo: EMPTY at 32,000.
Cycle 2: qwen at effort medium with a 32,000 budget (this audit's driver only; the package is larger than earlier ones).
dev53: mutations P1-P8 8 of 8 killed after a control run; 40 suite files by exit code, 863 tests.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2342/C2_STEP.diff (265 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 9322b8c..73dcbf9 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -180,6 +180,30 @@
   6 |     "family": "gemma",
   7 |     "deadline_floor_s": 2400,
   8 |     "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min. RULING 102 (13:02 Nov 14): also the LAST leg of step A's second family (ruling 87's last resort), reached without declaring Heimdall down; recorded as such on the pin and on STATE line 1."
   9 | +  },
  10 | +  "heimdall:minimax/minimax-m3.1-flash": {
  11 | +   "vendor": "heimdall",
  12 | +   "model": "minimax/minimax-m3.1-flash",
  13 | +   "price_usd_per_1m": [
  14 | +    3,
  15 | +    15
  16 | +   ],
  17 | +   "temperature": 0,
  18 | +   "min_out": 16000,
  19 | +   "family": "minimax",
  20 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  21 | +  },
  22 | +  "heimdall:openai/gpt-oss-20b": {
  23 | +   "vendor": "heimdall",
  24 | +   "model": "openai/gpt-oss-20b",
  25 | +   "price_usd_per_1m": [
  26 | +    3,
  27 | +    15
  28 | +   ],
  29 | +   "temperature": 0,
  30 | +   "min_out": 16000,
  31 | +   "family": "gpt-oss",
  32 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  33 |    }
  34 |   },
  35 |   "roles": {
  36 | @@ -302,6 +326,20 @@
  37 |      "elevenlabs_stt:scribe_v1"
  38 |     ],
  39 |     "what": "transcript_truth.py: law L-v 2's second, independent recognition pass with speaker turns on the selected segment's source audio (CPU fetch; no GPU, no Whisper)"
  40 | +  },
  41 | +  "coherence_panel": {
  42 | +   "chain": [
  43 | +    "heimdall:qwen/qwen3.8-27b",
  44 | +    "heimdall:minimax/minimax-m3.1-flash",
  45 | +    "heimdall:openai/gpt-oss-20b"
  46 | +   ],
  47 | +   "seeds": [
  48 | +    7,
  49 | +    8
  50 | +   ],
  51 | +   "min_members": 3,
  52 | +   "deadline_s": 900,
  53 | +   "what": "RULING 118 (2) / RULING 130 (4): the free panel measured on ruling 85.1's recorded Grok coherence verdicts (tests/package/proof/panel118/TABLE.md: qwen+minimax+gptoss TAKES: 18 units, no unit without a verdict, 94 % agreement against Grok's own 83 %, anchors 5/5), asked as the replay asked it: each member at seeds 7 and 8, the JSON-only contract line, a malformed answer re-asked once (seed + 100), 900 s; THE RULE: fewer than 3 members answering is no verdict (never a pass); the panel passes when more than half of all its answers pass the bar"
  54 |    }
  55 |   },
  56 |   "routing": {
  57 | diff --git a/pipeline/package.py b/pipeline/package.py
  58 | index c8e7874..0d4ba34 100644
  59 | --- a/pipeline/package.py
  60 | +++ b/pipeline/package.py
  61 | @@ -1874,6 +1874,75 @@ def _line_ok(tl):
  62 |      return bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4
  63 |  
  64 |  
  65 | +PANEL_CONTRACT = "Answer with the JSON object only: no code fences and no text before or after it."   # ruling 118 (2)
  66 | +
  67 | +
  68 | +def coherence_panel_spec(router):
  69 | +    """RULING 118 (2) / 130 (4): the configured coherence panel (model_providers.json role "coherence_panel": its own
  70 | +    role, so it is no verdict role whose deadline-table row would replace its deadline, and no shadow role) ->
  71 | +    {"members": the role's chain as this router has it, "seeds", "min_members", "deadline_s"}, or None (no panel
  72 | +    configured, or a router without a config: the coherence verdict is one rater's, as before)."""
  73 | +    p = ((getattr(router, "config", None) or {}).get("roles") or {}).get("coherence_panel")
  74 | +    if not isinstance(p, dict) or not p.get("chain") or not hasattr(router, "chain"):
  75 | +        return None
  76 | +    return {"members": list(router.chain("coherence_panel")), "seeds": list(p.get("seeds") or [7]),
  77 | +            "min_members": int(p.get("min_members") or 3), "deadline_s": p.get("deadline_s")}
  78 | +
  79 | +
  80 | +def coherence_by_panel(router, pk, spec, parse, prompt, labs, own, writer_vendor=None, writer_family=None):
  81 | +    """RULING 118 (2) / 130 (4): the coherence verdict of the free panel, asked as the panel replay measured it. Each
  82 | +    member (never the writers' vendor or family) at each seed, once more at seed + 100 when its answer is out of contract
  83 | +    or missing; a member with no answer at either seed casts no vote. THE RULE: fewer than spec["min_members"] members
  84 | +    answering is NO VERDICT (never a pass); the panel passes when MORE THAN HALF of all its answers pass the bar (the
  85 | +    through-line, every clip after the hook and the VO point at the bar's floors). The verdict's clips and vo_point are
  86 | +    the answers' lower medians and its through-line the first sound one, for the redo and the re-line that read them.
  87 | +    -> (ok, verdict)."""
  88 | +    import statistics
  89 | +    import providers as P
  90 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  91 | +    names = [n for n in spec["members"] if n in router.backends and router.backends[n].vendor not in wv
  92 | +             and router.backends[n].family not in wf]
  93 | +    fams = {n: router.backends[n].family for n in names}
  94 | +    votes, misses = {}, {}
  95 | +    for n in names:
  96 | +        others = {fams[o] for o in names if o != n} | wf
  97 | +        for sd in spec.get("seeds") or (7,):
  98 | +            for s in (sd, sd + 100):                     # the replay's rule: a malformed answer is asked once more
  99 | +                try:
 100 | +                    r, v = P.call_parsed(router, "coherence_panel", prompt, parse, 1200, s, system=PANEL_CONTRACT,
 101 | +                                         avoid_vendor=writer_vendor, avoid_family=others,
 102 | +                                         deadline_s=spec.get("deadline_s"))
 103 | +                except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 104 | +                    misses.setdefault(n, []).append(f"seed {s}: {type(e).__name__}: {str(e)[:160]}")
 105 | +                    continue
 106 | +                votes.setdefault(n, []).append(dict(v, backend=r.backend, seed=s,
 107 | +                                                    replayed=bool(getattr(r, "replayed", False))))
 108 | +                break
 109 | +    rec = {"members": spec["members"], "answered": sorted(votes), "misses": misses,
 110 | +           "rule": "ruling 118 (2): fewer than %d members answering is no verdict; more than half of all answers pass"
 111 | +                   % int(spec.get("min_members") or 3)}
 112 | +    if len(votes) < int(spec.get("min_members") or 3):
 113 | +        return False, {"error": f"the coherence panel gave no verdict: {len(votes)} of {len(spec['members'])} members "
 114 | +                                f"answered (ruling 118 (2): no verdict, never a pass)", "measured": False, "panel": rec}
 115 | +    fl, which, csha = lineup_floors("coherence", sorted(votes)[0])     # a Heimdall member: the standard bar
 116 | +    answers = [v for n in sorted(votes) for v in votes[n]]
 117 | +    passes = lambda v: _line_ok(v["through_line"]) and min(v["clips"].values()) >= fl["clip"] and \
 118 | +        v["vo_point"] >= fl["vo_point"]
 119 | +    rec["answers"] = [{"backend": v["backend"], "seed": v["seed"], "pass": passes(v), "clips": v["clips"],
 120 | +                       "vo_point": v["vo_point"], "through_line": v["through_line"]} for v in answers]
 121 | +    ok_panel = sum(passes(v) for v in answers) * 2 > len(answers)
 122 | +    tl = next((v["through_line"] for v in answers if _line_ok(v["through_line"])), answers[0]["through_line"])
 123 | +    v = {"through_line": tl,
 124 | +         "clips": {**({labs[0]: own["rating"]} if own else {}),
 125 | +                   **{lb: statistics.median_low([a["clips"][lb] for a in answers]) for lb in labs[1:]}},
 126 | +         "vo_point": statistics.median_low([a["vo_point"] for a in answers]),
 127 | +         "hook_own": own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): fail closed"},
 128 | +         "panel": rec}
 129 | +    ok = own is not None and own["passes"] and ok_panel
 130 | +    return ok, dict(v, backend="panel:" + "+".join(sorted(votes)), measured=True, bar=which, floors=fl,
 131 | +                    calibration_sha256=csha, replayed=any(a["replayed"] for a in answers))
 132 | +
 133 | +
 134 |  def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 135 |      """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
 136 |      (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
 137 | @@ -1884,13 +1953,18 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 138 |      labs = [sg["label"] for sg in pk["segments"]]
 139 |      own = hook_own(hook)
 140 |  
 141 | -    def parse(text):
 142 | -        v = json.loads(text.strip())
 143 | +    def parse(text, braces=False):
 144 | +        v = hook_answer(text)[0] if braces else json.loads(text.strip())   # ruling 118 (2): the panel's brace rule
 145 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 146 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 147 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 148 |              raise ValueError("coherence verdict out of contract")
 149 |          return v
 150 | +    spec = coherence_panel_spec(router)
 151 | +    if spec is not None:                         # RULING 118 (2) / 130 (4): the free panel decides coherence
 152 | +        return coherence_by_panel(router, pk, spec, lambda t: parse(t, True), COHERENCE_PROMPT.format(
 153 | +            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])), labs, own,
 154 | +            writer_vendor, writer_family)
 155 |      try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 156 |          r, v = P.call_parsed(router, "coherence_verdict", COHERENCE_PROMPT.format(
 157 |                                   package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 158 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 159 | index 935d77a..3fc3227 100644
 160 | --- a/tests/package/test_medley.py
 161 | +++ b/tests/package/test_medley.py
 162 | @@ -243,6 +243,102 @@ class TestClipsAloneVerdict(unittest.TestCase):
 163 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 164 |  
 165 |  
 166 | +class TestRuling130CoherencePanel(unittest.TestCase):
 167 | +    """RULING 130 (4) / RULING 118 (2): the coherence verdict of the free panel (qwen + minimax + gpt-oss), asked as the
 168 | +    panel replay measured it: each member at seeds 7 and 8 under the JSON-only contract line and 900 s, a malformed
 169 | +    answer asked once more (seed + 100), the closing-brace rule; fewer than 3 members answering is no verdict; the panel
 170 | +    passes when MORE THAN HALF of all its answers pass the bar; never the writers' vendor or family."""
 171 | +    M = ["heimdall:qwen/qwen3.8-27b", "heimdall:minimax/minimax-m3.1-flash", "heimdall:openai/gpt-oss-20b"]
 172 | +    FAM = {M[0]: "qwen", M[1]: "minimax", M[2]: "gpt-oss"}
 173 | +    GOOD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 4}, "vo_point": 4}
 174 | +    BAD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 3}, "vo_point": 2}
 175 | +
 176 | +    def router(self, answers):
 177 | +        """answers: {member: {seed: dict | str (raw text) | Exception}}; a seed with no entry raises ProviderError."""
 178 | +        import providers as P
 179 | +        calls, M, FAM = [], self.M, self.FAM
 180 | +
 181 | +        class R:
 182 | +            config = {"roles": {"coherence_panel": {"chain": M, "seeds": [7, 8], "min_members": 3, "deadline_s": 900}}}
 183 | +            backends = {n: type("B", (), {"vendor": "heimdall/" + FAM[n], "family": FAM[n]})() for n in M}
 184 | +
 185 | +            def chain(self, role, kind=None):
 186 | +                return list(M) if role == "coherence_panel" else []
 187 | +
 188 | +            def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 189 | +                     avoid_family=None, deadline_s=None, kind=None):
 190 | +                left = [n for n in M if FAM[n] not in set(avoid_family or ()) and n not in set(avoid_model or ())]
 191 | +                if role != "coherence_panel" or not left:
 192 | +                    raise P.ProviderError(f"{role}: every back-end unavailable")
 193 | +                n = left[0]
 194 | +                calls.append({"role": role, "member": n, "seed": seed, "system": system, "deadline_s": deadline_s})
 195 | +                a = (answers.get(n) or {}).get(seed)
 196 | +                if a is None or isinstance(a, Exception):
 197 | +                    raise a if isinstance(a, Exception) else P.ProviderError(f"{n}: no answer")
 198 | +                return P.Reply(a if isinstance(a, str) else json.dumps(a), n, "heimdall")
 199 | +        return R(), calls
 200 | +
 201 | +    def run_it(self, answers, writer_family=None):
 202 | +        r, calls = self.router(answers)
 203 | +        ok, v = PK.coherence(r, TestCoherenceHookRatedOnce.PK_, {"xai"}, writer_family=writer_family,
 204 | +                             hook=TestCoherenceHookRatedOnce.HOOK)
 205 | +        return ok, v, calls
 206 | +
 207 | +    def test_the_panel_passes_on_more_than_half_of_its_answers(self):
 208 | +        G, B = self.GOOD, self.BAD
 209 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}, self.M[2]: {7: B, 8: B}})
 210 | +        self.assertTrue(ok)                                            # 4 of 6 answers pass
 211 | +        self.assertEqual(v["backend"], "panel:" + "+".join(sorted(self.M)))
 212 | +        self.assertEqual(sorted((c["member"], c["seed"]) for c in calls), sorted((n, s) for n in self.M for s in (7, 8)))
 213 | +        self.assertTrue(all(c["system"] == PK.PANEL_CONTRACT and c["deadline_s"] == 900 for c in calls))
 214 | +        self.assertEqual((v["measured"], v["replayed"], v["bar"]), (True, False, "standard"))
 215 | +
 216 | +    def test_half_is_not_a_pass_and_the_fields_are_lower_medians(self):
 217 | +        G, B = self.GOOD, self.BAD
 218 | +        ok, v, _ = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: B}, self.M[2]: {7: B, 8: B}})
 219 | +        self.assertFalse(ok)                                           # 3 of 6: not more than half
 220 | +        self.assertEqual((v["clips"]["clip_02"], v["vo_point"]), (3, 2))   # the redo and the re-line read these
 221 | +        self.assertEqual(v["clips"]["hook"], 4)                        # the hook's own cached rating (ruling 61)
 222 | +
 223 | +    def test_fewer_than_three_members_answering_is_no_verdict(self):
 224 | +        G = self.GOOD
 225 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}})
 226 | +        self.assertFalse(ok)
 227 | +        self.assertFalse(v["measured"])
 228 | +        self.assertIn("no verdict", v["error"])
 229 | +        self.assertEqual(sorted(c["seed"] for c in calls if c["member"] == self.M[2]), [7, 8, 107, 108])
 230 | +
 231 | +    def test_the_writers_family_is_never_asked(self):
 232 | +        G = self.GOOD
 233 | +        ok, v, calls = self.run_it({n: {7: G, 8: G} for n in self.M}, writer_family={"qwen"})
 234 | +        self.assertNotIn(self.M[0], {c["member"] for c in calls})
 235 | +        self.assertFalse(ok)                                           # two members left: no verdict
 236 | +        self.assertIn("no verdict", v["error"])
 237 | +
 238 | +    def test_a_malformed_answer_is_asked_once_more_and_trailing_braces_are_read(self):
 239 | +        G = self.GOOD
 240 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: "not json", 107: G, 8: G},
 241 | +                                    self.M[2]: {7: json.dumps(G) + "}", 8: G}})
 242 | +        self.assertTrue(ok)
 243 | +        self.assertEqual(sorted(v["panel"]["answered"]), sorted(self.M))
 244 | +        self.assertIn((self.M[1], 107), [(c["member"], c["seed"]) for c in calls])
 245 | +        read = [(a["backend"], a["seed"]) for a in v["panel"]["answers"]]
 246 | +        self.assertIn((self.M[2], 7), read)                            # the trailing brace dropped, the object read
 247 | +        self.assertIn((self.M[1], 107), read)
 248 | +
 249 | +    def test_a_router_without_the_panel_keeps_one_rater(self):
 250 | +        self.assertIsNone(PK.coherence_panel_spec(Canned(coherence_verdict=[self.GOOD])))
 251 | +
 252 | +    def test_the_configured_panel_is_the_measured_one(self):
 253 | +        """The build's own router: the role's chain resolves to back-ends it holds, of the three families measured."""
 254 | +        sys.path.insert(0, HERE)
 255 | +        import proof_ledger as PLG
 256 | +        r = PLG.build_router("heimdall_first", {}, os.devnull)
 257 | +        spec = PK.coherence_panel_spec(r)
 258 | +        self.assertEqual(sorted(r.backends[n].family for n in spec["members"]), ["gpt-oss", "minimax", "qwen"])
 259 | +        self.assertEqual((spec["seeds"], spec["min_members"], spec["deadline_s"]), ([7, 8], 3, 900))
 260 | +
 261 | +
 262 |  class TestCoherenceHookRatedOnce(unittest.TestCase):
 263 |      """RULING 61 (12:00): the coherence verdict after the takeaway does not rate the hook either: its cached own-job
 264 |      rating stands (hook_own); the clips after the hook and vo_point are judged as before."""
 265 | 
```

---

pp-selectid: RULING 130 (4) (orchestrator 23:00 ET Nov 16): "Then coherence panel wiring (ruling 118)." RULING 118 (2):
the free panel decides a verdict type only where its replay proved it (tests/package/proof/panel118/TABLE.md: on
ruling 85.1's recorded Grok coherence verdicts, qwen+minimax+gptoss TAKES: 18 units, no unit without a verdict, 94 %
agreement against Grok's own 83 %, stricter 0, looser 1, anchors 5/5; no other type took). Files: pipeline/package.py,
pipeline/model_providers.json, tests/package/test_medley.py.

THE REPLAY'S RULE, AS MEASURED (scratchpad panel118.py): each member at seeds 7 and 8, the JSON-only contract as the system
line, a malformed answer re-asked once (seed + 100), the closing-brace rule, 900 s; fewer than 3 members answering is
NO VERDICT (never a pass); the panel passes when MORE THAN HALF of all its answers (members x seeds) pass; each answer
judged on the standard bar (replay85.decide: the through-line and every rating >= COHERENCE_MIN 4).

THE CHANGE:
(a) model_providers.json: two Heimdall back-ends (minimax-m3.1-flash, gpt-oss-20b: the replay's spec), and a ROLE
    "coherence_panel" (chain: qwen, minimax, gpt-oss; seeds [7, 8]; min_members 3; deadline_s 900; its why). Its own
    role, so it is not a verdict role (whose deadline-table row would replace the 900 s: qwen's coherence row is 60 s)
    and not a shadow role. proof_ly.chains gives it its chain as for any role.
(b) package.coherence_panel_spec(router): the role's spec, or None (no such role, or a router without a config: then
    coherence() is ONE rater's, exactly as before; every existing coherence test runs that path).
(c) package.coherence_by_panel: each member never of the writers' vendor or family, at each seed, through
    providers.call_parsed on the role (one member a call: the others' families avoided), system PANEL_CONTRACT,
    deadline 900 s; out of contract or no answer: once more at seed + 100; the parse is coherence's own contract after
    package.hook_answer's brace rule (UNCHANGED, package.py:923). < min_members answering: (False, {"error": "... no
    verdict ...", "measured": False}). The bar: lineup_floors("coherence", <a member>) (UNCHANGED, :1538): the standard
    bar for a Heimdall member. ok = the hook's own cached rating passes (ruling 61, as before) and more than half of
    the answers pass. The verdict carries, for the code that reads a failed one (UNCHANGED, :4069: the takeaway's redo
    when only vo_point is under its floor; else the weak clips dropped), the answers' LOWER MEDIANS of every clip and of
    vo_point and the first sound through-line; backend "panel:<members>"; replayed only if an answer was replayed (the
    router's offline replay); measured True; every answer in v["panel"]. The pin's gate check (package_pin.gate_problems,
    UNCHANGED, :378) reads only status PASS and replayed False, never the back-end's name.

TESTS (TestRuling130CoherencePanel): more than half passes; exactly half does not, and the fields are the lower medians;
fewer than 3 members is no verdict (the missing member asked at 7, 8, 107, 108); the writers' family is never asked;
a malformed answer is asked once more and a trailing brace is read; a router without the panel keeps one rater; the
build's own router resolves the role to the three measured families. Mutations P1-P8 after a control run: 8 of 8
killed. Suites: 40 files by exit code, 863 tests.

PLEASE CHECK: (1) that the rule is the replay's, exactly (no verdict below 3 members; majority over all answers;
the standard bar); (2) that the writers' vendor and family are never asked; (3) that a failed panel verdict routes the
redo / re-line as a single rater's did; (4) that a no-verdict can never pass; (5) the tests.


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
