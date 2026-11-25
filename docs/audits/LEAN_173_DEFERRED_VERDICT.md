# LEAN 173: the deferred second-vendor verdict (A-F), built offline, 25 Nov 2026
The owner's approval of 15:55 ET. No paid call, model, build or service; sockets blocked in every test and in the
demonstration. pp-lean: code 8d26113fd, tests to 7a17a7df0, demonstration 36046bb91. lean-release: 0ab66236c.

## 1. What changed, with its tests
Tests: tests/package/test_deferred_second.py, 30, all pass. Must-fail: 29 mutations, each alone on a copy of 7a17a7df0,
network cut; the control passed 30 of 30 before and after; 28 killed by their named assertion, 1 survived (B2).
- **A. Deferred second verdict** (package.py).
  - :675 PENDING; :686-718 the seal rule; :3876 ruling 101's confirm-ahead off on the lean path; :4147 and :4571 every
    first-vendor-cleared moment, and lock-first's corrected clips, PENDING.
  - :4104 and :4973-4995 after the join table and clips-alone, ONE call for the line-up's segments not yet judged. A FAIL
    or no answer drops the line-up (that segment out for good) and the next is tried; money stops it BUDGET_REFUSED.
  - :5377 and :5391 the seal (and the no-voice shape) refuse any segment, opener first, without a PASS off its first
    verdict's vendor and family. lean=False is as it was.
  - Tests (14): positive, one deferred call after clips-alone, on its own segments; the package seals. Must-fail: a
    pending, FAIL, unanswered, same-vendor or local-judge segment cannot seal; FAIL or no answer drops; money stops;
    confirm-ahead stays off; the seal is wired in. Mutations A1-A10: 10 of 10 killed.
- **B. Cache.** package.py:835-841, the key, unchanged: words sha, context sha (with the cut's `<selected>` marks),
  prompt version. :902 a cached second verdict counts only from a model in the chain; FAILs cached, no answer never.
  Tests (4): paid once; a changed word, cut, context or version misses; another model never stands in; a later line-up
  asks only for what it lacks. Killed: B1, B3-B6. B2 (the words' own sha removed) survives: the context's sha holds them.
- **C. Misclassification.** package.py:657-673 and :4088 (budget_102 beside held_102; ruling 102's line names providers
  only); spotlight.py:951-958; outcomes.py:50, :187, :193, :395, :405; proof_ledger.py:1086 (FINGERPRINT.json, its log).
  Tests (2, plus A's money case): build 172's two refused Gemini calls replayed give 15 budget_refused, 0
  provider_unavailable. 172's record as it ran now reads 21 budget_refused (those 15 plus its 6 refused calls), 0
  provider_unavailable, 2 unmeasured. Mutations C1-C4 killed.
- **D. Reserve and stop unchanged** (providers.py:1058 untouched). Tests (2): $0.60 spent and $0.8651 held back, a
  speculative call is refused unasked and made once completing; the deferred call and the alternatives run while
  searching. Mutations D1, D2 killed.
- **E. Ceiling.** spend_ceiling.py:58-78 ($1.50 default; PP_SPEND_CAP_USD; above $5.00 or not a positive number
  refused), byte-identical on lean-release, where the lock service and the renderer read it. proof_ly.py:80, the
  builder's router. lean_ops.py:135/147/150 pass it to every program; :1388-1404 it comes only from --ceiling-usd; :1120
  the launch record. outcomes.py:582, the outcome line. Tests (6): default 1.50; 3.00 honoured by the ledger, the
  builder (a subprocess), lean-release's module and the launcher; 5.01, 0, -1, nan, inf and text refused. Mutations
  E1-E5 killed; lean-release test_lean_ceiling.py 8 of 8, with the byte check.
- **F. Stop waste.** package.py:679 DEFERRED_LINEUPS_MAX = 3, checked at :4975; proof_ledger.py:499/934 a sealed medley
  pays for no spotlight. Why 3: at $3.00 the worst case (every call billed at its reservation) fits 4 evaluations; 3
  ends the search before the ceiling does, one evaluation ($0.28 reserved) to spare; 172's pool had 2 openers over the
  bar. Tests (2); mutations F1, F2 killed.

**Suites:** pp-lean (36046bb91): 54 files, 0 failing, 1,229 passed. lean-release (0ab66236c): 89 files, 1,257 passed,
13 failing: the files that failed before this work, none touched.

## 2. $1.50 against $3.00 (tests/package/lean/replay_deferred_172.py: build 172 replayed offline)
| | $1.50 | $3.00 |
|---|---|---|
| search room after the reserve, at the line-up | $0.1614 | $1.6614 ($1.3012 after 0f140b0d's vision, reserved) |
| line-ups fully evaluated, recorded bills | 1 | 3 (the bound; 18 without it) |
| the same, every call billed at its reservation | 0 | 3 (4 without the bound) |
| openers tried (one a line-up) | 1 | up to 3 |
| where 172's replay stops | the angle for 71f0a551 / 621e263e~trim: UNMEASURED | the same; 0f140b0d's vision also: UNMEASURED |
| expected spend, line-up 1 seals | $0.78 | $0.78 + 0f140b0d's vision (UNMEASURED, at most $0.36 reserved) |
| expected spend, line-up 2 / 3 seals | not reached: BUDGET_REFUSED, no video | $0.85 / $0.92, + that vision |
| a build that seals nothing | about $0.54 | about $0.67 + that vision |
| COST PER PUBLISHABLE VIDEO, line-up 1 / 2 / 3 | $0.78 / at least $1.32 over 2 builds (the next spend day) | $0.78 / $0.85 / $0.92, + at most $0.36 |

**Assumptions:** before the line-up, 172's recorded calls without its Gemini call ($0.4735, with the lock service's
$0.0262). One evaluation: the larger join table ($0.0964 reserved, $0.0171 billed), clips-alone ($0.0763, $0.0108), the
deferred call ($0.1067 reserved on 172's prompt cut to 3 excerpts; $0.0393 billed, ESTIMATED from 11 Gemini bills).
Completion: 171's passed line-up ($0.1618 billed; it did not seal) + $0.0803 reserved outside the router. Pass rates are
unknown; "2 builds" assumes the next build's line-up 1 seals.

## 3. Billing exposure, the calibrated model (rulings 121, 123, 130)
- **$3.00:** reservation ceiling $3.00: no call starts unless spent + held + its reservation fits (plus the $0.8651
  reserve while searching); one paid call in flight across builder, lock service and renderer. ESTIMATED exposure about
  $3.23 ($3.00 + $0.2185 + $0.0154): one call can pass its reservation before the next is refused. The largest recorded Grok
  call is reserved $0.0993 (25% of its $0.3972 bound) and would bill $0.3178 at full list inside its 12,000-token cap,
  $0.2185 above (vision $0.0523); the first such bill sets that vendor at list for the day; Heimdall is uncapped ($0.0154
  in 172). Assumption: that call's output stays inside its cap. Estimated, not a guaranteed maximum: xAI's reasoning
  tokens are not capped by max_tokens, Gemini reports no cost, the voice bills ElevenLabs characters. Recorded: the
  highest Grok bill was 0.21 of its reservation (46 calls); vision 0.78 (4 calls).
- **$1.50:** ceiling $1.50; ESTIMATED exposure about $1.73 ($1.50 + $0.2185 + $0.0154), on the same assumption; estimated,
  not a guaranteed maximum.

## 4. Remaining limitations, under both ceilings
- **Local judge not routed (unchanged, as ordered):** the builder writes pp-lean's judge_requests; production reads pp-selectid's.
- **deepseek's outage:** in 172 it failed the writer probe (45 s, then HTTP 503) and was skipped all build
  (proof_ledger.py:495); the deferred verdict then falls to Gemini alone, and a Gemini outage drops line-ups as HELD.
- **One paid call in flight:** join table 32-45 s, clips-alone 35 s, deferred call 12-27 s (recorded): about 80-107 s per
  evaluation, about 5 minutes for 3 of the 2,700 s deadline.
- **Stale Nov 14 lock requests are still answered first:** $0.0262 in 172, 16% of the $1.50 room at the line-up.
- **At $1.50** the deferred verdict is affordable once: a second line-up never completes in the same build.
- **Unmeasured:** every verdict 172 never recorded (angle, join table, clips-alone, deferred verdicts on 71f0a551 and
  621e263e~trim, coherence, lock, render); 0f140b0d's vision at $3.00 (classed unmeasured: its record names no cause);
  the 3-segment Gemini bill; a sealing completion's bill; whether 172's pool holds a passing line-up.

## 5. Build 173's command: NOT AUTHORIZED (it needs the owner's separate authorization; it was not run)
`cd /home/ultron/worktrees/pp-lean && python3 -B tests/package/lean/lean_ops.py run --build-no 173 --deadline-s 2700 --ceiling-usd 3.00`

## 6. end to end: NOT DEMONSTRATED.
