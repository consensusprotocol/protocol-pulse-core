# glm-5.3-flash (z-ai/glm-5.3-flash) 168 s finish=stop usage in 13933 / out 3742 usd~0.098 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0426 (Ruling 34, second pass)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **The `judged != pat` coupling check (K1 / glm P1-1).** In Cycle 1 I flagged the seal-vs-judged drift as a *risk* but concluded it was "not provably a bug from the diff — hence P1, not P0." What I missed: the fixed diff **implements exactly the mitigation I asked for** — `screen_problems` (package_pin.py:161–163) compares `judged = gates.stand_alone.screen` against the sealed `pat` and refuses on mismatch, and the test at test_medley.py:353–358 exercises the "compiles, but not the pattern it was judged with" case. I under-credited the fix; my Cycle 1 framing ("only writer shown is assemble_medley") was correct but I didn't note the fix closes it *by construction now*, not by convention.
- **The 7-argument vs 6-argument seal asymmetry.** I noted the mirror test pins the *constant* but not the *package↔judgement coupling*. The new test at test_medley.py:350–352 does both: `seal(*args, mp.get("btc_screen")) == mp["package_sha256"]` AND `seal(*args) != mp["package_sha256"]`. That second assertion is the one that proves the 8th argument actually changes the digest — I never asked for it. Good catch by whoever wrote the test (and the consensus doc's "check_pin_only's 7-argument call" note).
- **The hook-names-Bitcoin case.** I flagged it as untested in Cycle 1 (glm P1-2, tail). The fixed diff tests it: test_medley.py:323–325 (`"Bitcoin is the hardest money."` as hook → `medley_names_bitcoin.segments == ["hook"]`). Resolved.

What nobody caught, including me, in Cycle 1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**glm P1-1 (seal↔judged coupling) — AGREE, now RESOLVED.** The `judged != pat` check at package_pin.py:161–163 is precisely the coupling. One residual nit: it compares against `gates.stand_alone.screen`, which is *recorded* by inventory (package.py:107–108, `screen=stand.get("screen")`), and `out["screen"] = screen.pattern` (stand_alone.py:251) is set from the *same* `screen` argument the check ran with. So the chain judged→recorded→sealed→re-verified is closed. Agree it's now sound.

**glm P1-2 (BITCOIN's definition) — AGREE, RESOLVED by the consensus's K2.** `stand_alone.py:27` is `BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)`, in the base file, byte-identical to the render's. Note the ruling's words are "bitcoin / btc" — the ruling's *own* phrasing, so the narrower-than-`bitcoins?|btcs?` pattern is the ruling's intent, not a divergence. The plural forms ("bitcoins", "btcs") would NOT match `\b(bitcoin|btc)\b`... wait: `\b(bitcoin|btc)\b` against "bitcoins" — `bitcoin` matches, then `\b` requires a boundary between "n" and "s", which does not exist (both word chars). So "bitcoins" fails. Is that a divergence from the ruling? The ruling says "the speaker's own words (bitcoin / btc)" — singular. And the render's merged code is the same, so pin↔render agree. **P2-level observation at most, and it's the render's own rule, so not a finding against this diff.** I'll note it as P2-1 (see §3/§5) only because the *old* T11 regex was `\b(bitcoins?|btcs?)\b` (plural-tolerant) and the medley rule is now stricter than the retired one — worth one line in the ruling's record, not a code change.

**glm P1-3 (no_topic's "most favourable place") — AGREE, RESOLVED by consensus K3.** `topical()`'s completion rule reads the previous text only through `_mentions(prev_text, {bitcoin, btc})`, so the literal "Bitcoin" predecessor is maximal. The `no_topic` implementation (package.py:67–74) passes `prev_text="Bitcoin"`, which is the maximal case. Sound.

**qwen P0-1 (BITCOIN NameError) — DISAGREE (refuted).** `BITCOIN` is defined at stand_alone.py:27 in the base file; the medley tests exercise that path and pass. Not a P0.

**qwen P0-2 (mirror test parsing) — DISAGREE (refuted).** The consensus reports the test ran, was not skipped, and matched. The skip guard (test_eligibility.py:267–268) covers only environments without the pp-ingest worktree — acceptable, and the consensus confirms it ran.

**qwen P0-3 (no_topic) — DISAGREE (refuted), see glm P1-3 / K3.**

**grok's "SHIP: yes, nothing" — PARTIALLY AGREE.** Grok's verdict is defensible; its *reasoning* ("byte-for-byte match") is stronger than its evidence (137 output tokens, no scenarios). I'd not sign off on "no P1" without the coupling test, but the coupling test now exists, so the verdict lands.

**Consensus K1's claim that `screen_problems` "refuses a medley whose sealed btc_screen.pattern is not the pattern its stand_alone gate row recorded" — AGREE, with one caveat.** See new finding P1-1 below: the *test* covers the mismatch, but the *production path* that guarantees `gates.stand_alone.screen` is populated is thinner than the consensus implies.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-1 — `package_pin.py:161`: the judged↔sealed coupling depends on `gates.stand_alone.screen` being present, and `screen_problems` treats a *missing* judged screen as a mismatch (good) but the *inventory* only records it when `stand` is not None.**

Chain: `inventory` (package.py:102–109) writes `screen=stand.get("screen")` into the `stand_alone` gate row **only when `stand is not None`**. `stand_alone_check` (package.py:59) always returns `out["screen"]` when the screen is passed — which it now always is. So in the *current* production path, `gates.stand_alone.screen` is always the judged pattern, and `screen_problems`'s `judged != pat` catches any divergence. **But**: `screen_problems` reads `((pk.get("gates") or {}).get("stand_alone") or {}).get("screen")` — if a *future* caller builds gates without a `stand_alone` row at all, `judged` is `None`, the check fails, the pin is refused. Fail-closed (L-j). Good. The residual: `required_gates(pk)` presumably already requires a `stand_alone` row for a medley (the test at test_medley.py:297–298 builds it), so this is belt-and-braces. **Downgrade: this is P2, not P1** — the fail-closed direction is correct, and the test at test_medley.py:344–346 proves a missing judged screen refuses.

**P2-1 — `stand_alone.py:247` (via `BITCOIN` at :27): the medley rule's `\b(bitcoin|btc)\b` does not match the plurals "bitcoins"/"btcs", which the *retired* T11 regex (`\b(bitcoins?|btcs?)\b`, eligibility.py:8) did.** Scenario: a medley whose only Bitcoin mention is "they bought more bitcoins" — the medley rule fails, the pin is refused, the render (same code) agrees. Not a pin↔render divergence; it's a strictness change vs. the old editorial line, sanctioned by the ruling's own wording ("bitcoin / btc"). Record it; change nothing.

**P2-2 — `package.py:85`: `no_role_on_screen(m) or no_topic(m)` short-circuits, so the log/`no_role` reason records only the *first* failure.** If a moment fails both the opener rule and the topic rule, the recorded why is the opener's. Cosmetic (the moment is dropped either way, and the log line at :96–98 aggregates), but the `prescreen.failed` map is the operator's diagnostic surface; a topic-dropped moment whose opener also fails shows the wrong reason. P2.

**P2-3 — `screen_problems` (package_pin.py:155) accepts a pattern of exactly 500 characters; the ruling says "at most 500".** `len(pat) > 500` — correct. No finding. (Withdrawn; noting I checked.)

**P2-4 — test_medley.py:346: `pk["gates"]["stand_alone"]["screen"] = PK.stand_alone_check(pk["segments"])["screen"]` re-runs the check to *discover* the judged screen rather than asserting it equals `E.BTC_SCREEN.pattern`.** It does, trivially, since `stand_alone_check` hardcodes `screen=E.BTC_SCREEN` (package.py:59). But the test would still pass if `assemble_medley` sealed a *different* pattern than the check judged — no, wait: the test at :341 asserts `pk["btc_screen"] == {"pattern": E.BTC_SCREEN.pattern, ...}` directly, and :346 sets the gate's screen to what the check judged, and :349 asserts the pin carries `pk["btc_screen"]`. Combined with `screen_problems`'s `judged != pat`, the triangle closes. No finding. (Withdrawn; noting I checked.)

**P2-5 — `topical_screen` (stand_alone.py:211): `screen.search(text or "")` — if the screen pattern itself were, say, `^` (matches empty), every segment passes.** Not a defect; the sealed pattern is the miner's, and `screen_problems` only checks it compiles. The render's acceptance is the same. No finding.

**P2-6 — the mirror test (test_eligibility.py:270) parses the miner's source with a regex expecting the pattern split across exactly two `r"..."` literals.** If the miner's file ever reformats to one or three literals, the test's `_re.search` returns None and `assertIsNotNone` fails — a *test* failure, not a silent pass. Fail-closed. Acceptable; the skip guard covers the missing-worktree case. No finding.

Net: **no new P0 or P1.** The combined analysis (my coupling concern + the implemented `judged != pat` + the 7-arg/6-arg digest test) closes the one question Cycle 1 left genuinely open.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| stand_alone.py sync (topical_screen, check_edl(screen=)) | A− | A | BITCOIN definition confirmed (K2); medley rule exercised incl. hook-only; story path (screen=None) provably untouched by the ternary at :237–238 |
| eligibility.py (BTC_SCREEN, T11 hook rule) | A− | A | Mirror test ran and passed (qwen P0-2 refuted); hook-screen test added (:283–286) |
| package.py (stand_alone_check, no_topic, seal, inventory) | B+ | A− | no_topic maximality verified (K3); residual: the `or`-short-circuit reason记录 (P2-2) — cosmetic |
| package_pin.py (seal, screen_problems, to_pin) | B+ | A | The judged↔sealed coupling is now *checked*, not assumed; 7-arg/6-arg digest asymmetry tested both directions |
| Tests | B | A− | Every Cycle 1 condition I raised is now exercised; the mirror test's regex-fragility is fail-closed |

(No scores were given numerically in Cycle 1; letter grades here are my own scale, revised honestly.)

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (glm's P1-1/P1-2/P1-3 are all resolved in this diff; qwen's three P0s are refuted with evidence.)

**P2 MEDIUM**
1. **package.py:85** — `no_role_on_screen(m) or no_topic(m)`: when both fail, the recorded reason is the opener's; the topic-drop reason is lost from `prescreen.failed`. Diagnostic-only; the drop itself is correct. (P2-2)
2. **stand_alone.py:27 / :247** — the medley rule's `BITCOIN` = `\b(bitcoin|btc)\b` does not match "bitcoins"/"btcs", which the retired T11 regex did. Sanctioned by the ruling's wording; record it in the ruling's implementation notes so a future "why did 'bitcoins' fail" question has an answer. (P2-1)
3. **package_pin.py:161** — the coupling check relies on `gates.stand_alone.screen` being populated by inventory; it is, today, and the failure direction is fail-closed. Belt-and-braces: `screen_problems` could distinguish "no judged screen recorded" from "a different pattern" in its message. (P1-1, downgraded)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Ship it — the one thing that mattered (the sealed screen being provably the one the line-up was judged with, not merely the same constant by construction) is now *checked* at `to_pin` (package_pin.py:161–163) and *proven* by the 7-arg/6-arg digest asymmetry test (test_medley.py:350–352); everything else is diagnostics.

## 7. PRODUCTION READY?

**Yes.** Conditions, precisely:

1. **(P2-2, before the next operator-facing run)** In `package.py:85`, record both reasons when both screens fail — e.g. `no_role_on_screen(m) or no_topic(m)` → concatenate, or key the `prescreen.failed` entry by whichever rule fired, so the operator's diagnostic surface names the topic rule when it fired. The drop behaviour itself is correct; this is observability, not correctness.
2. **(P2-1, documentation)** One line in the ruling-34 implementation note: the medley's "names Bitcoin" test is `\b(bitcoin|btc)\b` (singular, the render's own rule), stricter than the retired `\b(bitcoins?|btcs?|...)\b` — so "bitcoins" alone does not satisfy the medley rule.
3. **(Standing, no code change)** The integrator's `check_pin_only` must keep calling `seal(..., mp.get("btc_screen"))` with the 7th argument; the 6-argument call provably computes a different digest (test_medley.py:352), so a stale integrator would fail every new pin loudly — which is the right failure, but it means the *deploy order* is: this branch's `package_pin.seal` and the integrator's 7-argument call must land together, or new pins fail the recompute. Confirm the integrator's 04:20 ET READY covers the 8-argument seal (7 positional + btc_screen), not just the 7-argument one.

Verified from the diff, not assumed: the story path (screen=None) is untouched (stand_alone.py:237–238's ternary; the render's story path passes no screen); old pins recompute (the conditional body key at :138–139 + the consensus's check_pin_only run on d2677bbe/1b4a63d0/41f29b1f); the pin stage cannot PASS a line-up the render would refuse, because the pin stage *runs the render's own code* (byte-identical sync, condition 1 of the change) with the same compiled constant, and `screen_problems`'s acceptance (non-empty, ≤500, compiles with re.I, source) is the render's own acceptance per the ruling.

**SHIP: yes.**