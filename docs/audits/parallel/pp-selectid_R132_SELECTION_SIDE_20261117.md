# RULING 132 END-TO-END REPLAY: the builder's (selection-side) half

Written 08:48 ET Nov 17. Code: worktree HEAD 549b5a54, pipeline/ clean against it (0 changed files). Replay output: out_all2.json, run 2026-11-17 08:38 local time. Free only: $0.00, with no outside call, no Heimdall call and no Scribe call.

## How it was run (assumptions, stated before the table)

- **Free only.** The network was blocked: proxies pointed at 127.0.0.1:9, `urlopen` refused, and yt-dlp/curl/wget refused. The router ran with `replay=True` over the recorded replies (`proof_ly.REPLIES`). It answers only a call identical to a recorded one (role, model, prompt, max_tokens, seed, system), so **a changed prompt is a miss, and a miss is UNTESTED**. Every verdict cache (STEP_A, HOOK, JOIN, VISUAL, LAYOUT) was a scratch copy. No tracked file was written; everything went to this folder. The runs were not started with `-B`, so on import Python rewrote git-ignored byte-code caches under the worktree's `pipeline/__pycache__`: package, providers and lock_precheck at 08:33, and `replay.pyc` at 08:42. The last came from a mistaken `import replay` (pipeline/replay.py) in the first try of `checks.py`, since fixed. The replay's router has no breakers, so it does not touch BREAKERS.json.
- **Code:** the worktree at the HEAD in the header, with `pipeline/` clean against it. Each gate is today's function, called on each package's clips **one gate at a time**. An earlier REFUSE does not stop the later rows.
- **Moments:** each clip was looked up in **today's ledger adapter** (`ledger_build.rows` + `build_inputs`, read-only), at a clock 1 h after the video's ledger publish time. Where today's moment has the approved span, the gates judged today's moment. Where it does not (row 1), they judged the producing record's moment, and the appendix says so.
- **Ignored, as ruled:** the 12-hour age rule (`package.expired` patched off; the adapter was asked at a fresh clock) and the registry's never-re-form rule (row 20). Novelty is read as never delivered (delivered=(), spotlit=()). Every other date gate ran at each package's own build clock. L-v 3 (time words) is not the 12-hour rule, so it ran.
- **Lines:** the writes are not gates. The line gates (rows 27-31) judged **each package's own approved lines**, which is what PBX approved. Build 114 never wrote any lines.
- **Ruling 72 onward** (the lock pre-check, the render, captions, delivery) is the integrator's half, on line 9.
- **Not judged here:** the seal's `replayed` flag. Every recorded answer served in replay is `replayed=True`, which the pin refuses by design, so that is a replay artifact and not a gate result. Also not judged: Plan B chains, deadlines and breakers, which only apply to live calls.

## THE TABLE (selection side; rows in today's pipeline order)

Cells: PASS / REFUSE: the reason / UNTESTED: why / N/A / IGNORED (ruling 132) / INTEGRATOR (line 9).
The packages: **0c68b589** (medley, approved 14:12 ET Nov 13, published), **41f29b1f** (medley, approved 22:01 ET Nov 12, published), **37c5b5f5** (VO-led moments, approved 08:43 ET Nov 12, review only), **3f481f5a** (spotlight, approved 18:23 ET Nov 14, PBX posted it) and **B114** (build 114's line-up [4d14201f, 185e37a6, d6adeb54, 93cfa865], never approved).

| # | Gate (ruling; code) | 0c68b589 | 41f29b1f | 37c5b5f5 | 3f481f5a | B114 |
|---|---|---|---|---|---|---|
| 1 | Ledger adapter: the approved span is a moment today (ledger_build.py:87, :447) | PASS | **REFUSE: 3.5 s hook inside 19.9 s moment** | **REFUSE: approved spans are not ledger moments** | PASS | PASS |
| 2 | Ruling 104 tail variants (tail_variant.py:113) | PASS | PASS | PASS | PASS | PASS |
| 3 | usable: L-u eligibility, hard exclusion, opt-out, 20 s per source (35 s spotlight), L-v 3, L-v 1 (package.py:166). Age IGNORED | PASS | PASS | PASS | PASS | PASS |
| 4 | Ruling 53, a re-posted speech once (package.py:1248) | PASS | PASS | PASS | PASS | PASS |
| 5 | Rulings 56/60/33/94 (a): clip scorer, STAND_ALONE opener, topic rule (package.py:1453, :1489, :1479) | PASS | PASS | PASS | PASS | PASS |
| 6 | Exclusion's free part, the ad-read marker (package.py:1159) | PASS | PASS | PASS | PASS | PASS |
| S1 | *Spotlight:* ruling 90 pool, 12-35 s snap, ruling 94 opener; one per channel per ET day read as never spotlit (spotlight.py:200) | N/A | N/A | N/A | PASS | N/A |
| S2 | *Spotlight:* ruling 90 ALONE >= 4, free, before any paid call (spotlight.py:488) | N/A | N/A | N/A | UNTESTED: no verdict in today's scorer file | N/A |
| 7 | Ruling 109: 3 channels after the free stages (package.py:3104) | PASS | PASS | PASS | N/A | PASS |
| 8 | Step A, first screen (rulings 58/85/88 c/101/102/126 (1)/127 (2); package.py:560) | PASS | UNTESTED: no cached verdict, key changed | UNTESTED: no cached verdict, key changed | PASS | PASS |
| 9 | 3 channels cleared step A (package.py:3162) | PASS | UNTESTED (row 8) | UNTESTED (row 8) | N/A | PASS |
| 10 | L-v 2 second recognition + CUTTABLE (package.py:2856) | PASS | UNTESTED: audio window not on disk | UNTESTED: audio window not on disk | PASS | PASS |
| 11 | G17a hook onset; ruling 33 (a) trimmed cut, none trimmed (package.py:2867) | PASS | UNTESTED: audio window not on disk | UNTESTED: audio window not on disk | PASS | PASS |
| 12 | Hook eligibility + the render's STAND_ALONE hook rule (package.py:1629) | PASS | PASS | PASS | PASS | PASS |
| 13 | Rulings 59/61/115, the calibrated hook bar (package.py:939, :1581) | UNTESTED: no cached rating, prompt changed | UNTESTED: never rated (before ruling 59) | UNTESTED: never rated (before ruling 59) | UNTESTED: no cached rating | PASS (3/5/4) |
| 14 | Rulings 70/93/123 (2), the hook's frames; *spotlight:* ruling 90 visual clean (visual_pin.py:366; spotlight.py:477) | UNTESTED: never seen, no cached sheet | UNTESTED: never seen | UNTESTED: never seen | UNTESTED: cached as visual-2, today visual-3 | PASS |
| 15 | Second screen, step A off the writer (item 45; rulings 82/102/127; package.py:795) | PASS | UNTESTED (row 8) | UNTESTED (row 8) | PASS | PASS |
| S4 | *Spotlight:* ruling 92 source test, the layout verdict (spotlight.py:327) | N/A | N/A | N/A | UNTESTED: needs row 14's judged sheet | N/A |
| 16 | 3 channels after the second screen (package.py:3279) | PASS | UNTESTED (row 15) | UNTESTED (row 15) | N/A | PASS |
| 17 | Angle writer (rulings 59 c/64/118 (4)): a write | N/A | N/A | N/A | N/A | N/A |
| 18 | Ruling 117 join table, at most 1 flagged join (package.py:2231) | UNTESTED: no cached join answers | UNTESTED: no cached join answers | UNTESTED: no cached join answers | N/A | PASS (1 of 3 flagged) |
| 19 | Line-up rules: one per channel / L-y 4, at most 1 price prediction, short clip, at most 1 trimmed, 36.7-51.5 s, STAND_ALONE (package.py:1667) | PASS (39.3 s) | **REFUSE: two price-prediction clips, max one** | **REFUSE: 21.5 s of clips, needs 36.7** | N/A | PASS (37.9 s, L-y 4) |
| 20 | Ruling 66 registry, never re-formed | IGNORED | IGNORED | IGNORED | IGNORED | IGNORED |
| 21 | Ruling 116 clips-alone verdict, the hook's slot by ruling 115 (package.py:2002, :1538) | UNTESTED: clips 4/4 pass, hook unrated | UNTESTED: no recorded verdict | UNTESTED: no recorded verdict | N/A | PASS (3/5/3/4, no flag) |
| 22 | Ruling 37, a question hook (package.py:2702) | PASS | PASS | PASS | N/A | PASS |
| 23 | Rulings 72/130 (2), the lock pre-check | INTEGRATOR | INTEGRATOR | INTEGRATOR | INTEGRATOR | INTEGRATOR |
| 24 | Rulings 70/93, every clip's frames (package.py:3817) | UNTESTED: never seen | UNTESTED: never seen | UNTESTED: never seen | (row 14) | PASS (flags only) |
| 25 | Exclusion verdict (package.py:2813) | PASS (recorded keep) | PASS (recorded keep) | PASS (recorded keep) | PASS (recorded keep) | PASS (recorded keep) |
| 26 | The writes (takeaway, bridge, title, caption) | N/A: own lines judged | N/A: own lines judged | N/A: own lines judged | N/A: own lines judged | N/A: never written |
| 27 | Cheap line gates: fidelity rules, DUPLICATE, runtime, R4, L-y shape, house style, recency (package.py:2778; spotlight.py:702) | PASS (61.8 s) | **REFUSE: six house-style faults in lines** | UNTESTED: VO-led lines have no L-y form | **REFUSE: caption gives the speaker a "guest" role** | N/A |
| 28 | Ruling 91 value verdict (the takeaway; the spotlight's closing line) (package.py:2500; spotlight.py:591) | UNTESTED: no recorded verdict | UNTESTED: no recorded verdict | UNTESTED (row 27) | UNTESTED: no recorded verdict | N/A |
| 29 | VO fidelity verdict (vo_fidelity.py:754) | UNTESTED: no recorded verdict | PASS (recorded) | UNTESTED (row 27) | UNTESTED: no recorded verdict | N/A |
| 30 | Context integrity (context_integrity.py:476) | PASS (recorded) | PASS (recorded) | UNTESTED (row 27) | UNTESTED: no recorded verdict | N/A |
| 31 | Coherence, the ruling 118 (2)/130 (4) panel (package.py:1946, :1892) | UNTESTED: panel never asked | UNTESTED: panel never asked | UNTESTED: panel never asked | N/A | N/A |
| 32 | The seal: every required row exactly PASS (package_pin.py:378) | follows the UNTESTED rows | follows rows 1, 19, 27 | follows rows 1, 19 | follows row 27 | not reached (row 23) |

The spotlight runs its own order: S1 and S2 come before row 8; its visual-clean gate is row 14; S4 follows row 15. Row 32 is derived from the rows above and is not counted as a cell of its own.

## REFUSE cells on PBX-approved packages: 6 cells at 3 gates

None of the four refuses at the gates named in ruling 132 (hook bar, line-up bar, stand-alone floor, UTC date) wherever this replay could test them. Rows 12, 5 and 3 PASS for all four. Rows 13 and 21 are UNTESTED for the four, because no cached answer exists for today's prompts. The records' own answers are given below as notes, not as cells.

**(a) Row 19, line-up rules, L-u's price-prediction cap (41f29b1f).** Today's ledger miner tags two of its clips `price_prediction`, and `PRICE_PREDICTIONS_MAX` is 1. The Nov 12 fresh miner tagged neither.
- What Bitcoin Did (c1JGheQBPH4 2403.23-2422.07): *"price-wise, some people would say when it's persecuted ... it tends to do pretty well."* This has no figure.
- Stephan Livera (Sjb6lUiL0m4 1826.54-1843.48): *"Bitcoin gold parity is around like $1.5, $1.4 million per Bitcoin."* This states a figure.
- With the tags removed, `lineup_ok` passes this line-up (run: `checks.py`).
- **Recommended fix:** count a clip toward the cap only when its own words state a price figure: a number with a currency or price unit, a multiple, or "zeros". The tag still down-weights the rank (moments.SOFT_RISKS).
- *It would pass* 41f29b1f: one clip counts.
- *It would still refuse* two clips that each state a price or target in one video.
- Measured on the whole ledger with a rough regex: 372 moments tagged, 129 state a figure, 243 do not. So the change takes 243 out of the count. The 243 include directional calls with no figure ("you know exactly where Bitcoin is going"). Ruling 132 asks for a calibrated gate; the trade-off is yours.

**(b) Row 19, line-up rules, the medley's seconds (37c5b5f5).** Its clips run 21.5 s as cut (30.7 s as the ledger's moments). The L-y medley needs 36.7-51.5 s.
- 37c5b5f5 is the pre-L-y **VO-led** shape: an intro after the hook, a bridge after clip 1 and a closing line; the pin runs 60.8 s.
- The L-y medley (one takeaway, at most one bridge) has been the default since 20:30 ET Nov 12, after PBX approved this one at 08:43 ET.
- **No fix recommended.** Lowering the seconds floor would let thin medleys through. A VO-led shape needs its own ruling. PBX kept this one for review only.

**(c) Row 1, the ledger adapter's moment spans (41f29b1f's hook; all three of 37c5b5f5's clips).** This is supply, not a threshold.
- The Nov 12 fresh miner cut single sentences. The ledger mines whole passages, and `build_inputs` re-anchors them on whole sentences.
- 41f29b1f's 3.5 s hook *"Bitcoin imposes a global free market for the first time ever."* is today the LAST sentence of a 19.9 s moment (2db4015f, 3201.7-3221.64), which opens on "And the people moving to the US...".
- 37c5b5f5's hook is today's cc72a523 (5142.11-5153.37) minus its first sentence, "No, the difference is very very fundamental." Its What Bitcoin Did clip was cut by hand at 2412.85, inside moment 4f9d38e1 (2403.23-2422.07).
- **Recommended fix (it needs a ruling: a new free variant, not a loosened bar):** a head-side sentence variant, the mirror of ruling 104's tail variant. It is the moment without its leading sentence(s), made when the parent cannot open (ruling 94 (a): a conjunction or reply opener). Every gate runs again on it.
- *It would form* 41f29b1f's hook and 37c5b5f5's hook.
- *It would still refuse* any cut that does not end on a sentence edge (37c5b5f5's hand cut, unless 2412.85 is a sentence end, which is not checked here) and every gate's own refusals.

**(d) Row 27, cheap line gates, house style (41f29b1f's own lines).** There are six faults: a 29-word takeaway (at most 20), the opener "what stands out", a "which makes" clause, a 10-word title (at most 8), a possessive title opener, and the hedge "may" in the caption.
- These are PBX's copy rules (ruling 6, 22:40 ET Nov 12; commit 88397a53 at 23:00 ET). They were adopted after his 22:01 ET approval of this package.
- **No fix recommended.** A line is a write. The gate refuses the line, never the clips, and the line is written again: two writes and the takeaway alone twice (ruling 66 amended), a lone caption or title alone (ruling 65), and the fixed caption (65 b).

**(e) Row 27, cheap line gates, the ROLE rule (3f481f5a's caption: "a guest sold his retirement stocks...").** Law L-v: the clip's own words never say "guest".
- The rule landed at 21:53 ET Nov 14 (commit 1e4fb5a9, "the orchestrator's three 21:10 fixes"), after PBX's 18:23 ET approval.
- **No fix recommended.** The spotlight writes a failing title, caption or comment once more (spotlight.package_for), so the clip is not lost.

## The UNTESTED cells, and the records' own answers (notes, never cells)

- The verdicts asked of Nov 12-13 packages are UNTESTED mostly because **today's questions are new or changed**:
  - step A's key (ruling 126 (1)) and its prompt version;
  - the hook asked alone (ruling 115, Nov 15);
  - the join table (ruling 117, Nov 15);
  - the visual check (ruling 70; visual-3 since 21:10 Nov 14);
  - the coherence panel (130 (4), landed last night).
  
  The 41f29b1f and 37c5b5f5 audio windows were cut by the fresh pipeline at other pads, so rows 10-11 would need a fetch.
- The records' answers, read against today's bars:
  - 0c68b589's hook was rated scroll 4, alone 5, setup 5 by Grok 4.20, which **passes** today's calibrated hook bar (3/4/3).
  - 0c68b589's clips-alone on record was 4/4/4, and 41f29b1f's was 5/4/4. Both were Grok 4.20 with no flagged join, so both **pass** today's line-up floor (clip >= 3).
  - Their coherence on record was 4/4/4 with VO point 4 (0c68b589) and 5/4/4 with VO point 5 (41f29b1f).
  - 3f481f5a's record has ALONE 4.0 and hook_own 4.
- Answers recorded for **today's** prompts, served free:
  - 0c68b589: the clips-alone (seed 8: clips 4/4, no flag, a through-line), context integrity and exclusion.
  - 41f29b1f: VO fidelity, context integrity and exclusion.
  - 37c5b5f5: exclusion.
  - B114: every selection-side gate up to the lock.
- **B114** passes every selection-side row. Its stop is row 23 (the integrator's: d6adeb54 held at three word pairs).
- To close the UNTESTED cells for real, each Nov 12-13 package would need paid Grok calls: a hook rating (1 call), join-table pairs (6 for 3 moments), a clips-alone verdict (1 call) and a vision sheet per clip (xai_vision: about $0.18 held per sheet, which is 0.6 of the roughly $0.30 list upper bound). None was paid.

## Selection side: every remaining way a fully passing line-up can still fail to reach PBX, and its guard

1. **Spend guard** ($1.00/day outside dollars, `--stop-usd`; Scribe counts since ruling 131). A call that does not fit raises SpendLimit, with no failover. Guard: ruling 131's fit check before the first paid call (Scribe + step A + vision reserve at 0.6 of list < $1.00), and `start_refused` at the build's start.
2. **Vision reserve** (about $0.18 held per sheet: 0.6 of the roughly $0.30 list upper bound). Under a small stop, no vision call starts. Guard: the same fit check; the reserve is priced from real bills with the over-held tripwire (ruling 130 (3)).
3. **Search and package budgets** (ruling 41: 2400 s, $3.00; ruling 5: 900 s, $1.50 per package). A stop mid-writes leaves the line-up a candidate of class "budget". Guard: the registry retries open candidates first, free from recordings (candidates.due).
4. **Registry closure** (ruling 66). A class "clip" outcome, such as B114's lock hold, is closed for good, and the search never re-forms it, even after a later ruling changes that gate. Guard: **none automatic.** Proposed: when a ruling changes a gate, re-open the candidates that gate closed, by hand with `--from-candidate`.
5. **Expiry** (ruling 76: 12 h on the render clock; `CA.expire`; the pin's `window_problems`). A line-up found late in its 12 h can expire during the lock pre-check, vision or the render. Guard: fresher line-ups rank first (ruling 57) and the seal checks the window; render-time expiry is the integrator's.
6. **Grok-only verdicts** (the hook, ruling 115; joins, ruling 117; clips-alone, Grok then Gemini). Grok down or rate-limited means no rating, so no hook (law L-m). Guard: none but the next build (the watcher's fire or its 30-minute fallback).
7. **Heimdall down or slow** (ruling 87 Plan B; ruling 100 deadlines of 60-300 s). The second screen HOLDS the moment for this build (ruling 102). Guard: a held moment is never refused and is retried next build (ruling 102).
8. **Lock pre-check left off.** The scratch driver `build_and_record.sh` defaults to LOCK=off (`proof_ledger --lock-precheck` defaults to on), so a line-up that reaches ruling 72 waits as a candidate. Guard: ruling 131's attempt order runs the lock first, with `--lock-precheck on`.
9. **Nothing new** (ruling 107). A build with the same fingerprint as a finished build asks no model. Guard: a build that left open work (`open_work` > 0 in its FINGERPRINT.json) never stands in for a later one.
10. **The clip scorer's verdict** (rulings 56/60). An opener on a conjunction or reply, or a trimmed clip, needs the integrator's scorer verdict on its current text; with none, STAND_ALONE fails closed. Guard: `scorer_pass` writes the candidates for the integrator's pass, and the spotlight waits for it.
11. **Word pass.** A moment without a sentence-ready word record is not in the pool. Guard: the watcher fires on newly word-ready moments.
12. **The seal** (`package_pin.gate_problems`: every required row exactly PASS and not replayed; `PinRefused` at write). Guard: the refusal is recorded and never treated as a pass, and the build line names the row.
13. **A build during a render, or two builds at once.** `build_and_record.sh` refuses both (the render lock, a build already running). Guard: the watcher's next fire.
14. **A question on line 1 holding a build.** Guard: ruling 123's 20-minute default.

## Files (all in this folder, scratch only)

`replay.py` (the replay; run as `python3 replay.py OUT.json [names]`), `out_all2.json` (every row, every clip, the notes), `checks.py` (row 19's follow-up and the records' verdicts), `show.py` / `appendix.py` (readers), `caches/` (the scratch cache copies), `lv2/` (symlinks to the L-v 2 windows and sheets already on disk).

## Evidence: every row, every clip (from out_all2.json)

### 0c68b589 (medley, published)

Judged moments (the ids, spans and risk flags each gate read):

- hook: f29c27fb49bdc3fd050e 236.688-253.308 (16.62 s), risk [], published 2026-11-10T22:55:16+00:00
- clip_01: a45d26b88cd5b176ae13 124.157-138.097 (13.94 s), risk [], published 2026-11-12T20:55:09+00:00
- clip_02: c3be6f1c71c4397b081a 755.454-764.214 (8.76 s), risk ['doom'], published 2026-11-12T14:05:19+00:00

| row | clip | state | why (as the code gave it) |
|---|---|---|---|
| adapter | hook | PASS | today's moment f29c27fb49bdc3fd050e 236.688-253.308 |
| adapter | clip_01 | PASS | today's moment a45d26b88cd5b176ae13 124.157-138.097 |
| adapter | clip_02 | PASS | today's moment c3be6f1c71c4397b081a 755.454-764.214 |
| r104_variants | hook | PASS | kept |
| r104_variants | clip_01 | PASS | kept |
| r104_variants | clip_02 | PASS | kept |
| usable | hook | PASS |  |
| usable | clip_01 | PASS |  |
| usable | clip_02 | PASS |  |
| r53_reposted | hook | PASS |  |
| r53_reposted | clip_01 | PASS |  |
| r53_reposted | clip_02 | PASS |  |
| r56_scorer_stand_alone | hook | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_01 | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_02 | PASS | scorer no verdict |
| ad_read | hook | PASS |  |
| ad_read | clip_01 | PASS |  |
| ad_read | clip_02 | PASS |  |
| r109_channels | - | PASS | 3 channels |
| stepA_first | hook | PASS | xai:grok-4.20-0309-reasoning |
| stepA_first | clip_01 | PASS | xai:grok-4.20-0309-reasoning |
| stepA_first | clip_02 | PASS | xai:grok-4.20-0309-reasoning |
| Lv2_cuttable | hook | PASS |  |
| Lv2_cuttable | clip_01 | PASS |  |
| Lv2_cuttable | clip_02 | PASS |  |
| G17a_hook_onset | - | PASS |  |
| hook_eligible_opener | - | PASS |  |
| r115_hook_bar | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| r70_93_visual | hook | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_01 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_02 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| stepA_second | hook | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| stepA_second | clip_01 | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| stepA_second | clip_02 | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| r117_join_table | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| lineup_rules | - | PASS | 39.3 s in 36.7-51.5 s |
| stand_alone | - | PASS |  |
| r116_clips_alone | - | UNTESTED | seed 8: the clips {'clip_01': 4, 'clip_02': 4} flagged [] through-line yes, floors {'clip': 3}; the hook's slot needs its own rating (ruling 115), not cached |
| r37_question_hook | - | PASS | the hook is not a question |
| r72_lock | - | INTEGRATOR | line 9 |
| exclusion | hook | PASS |  |
| exclusion | clip_01 | PASS |  |
| exclusion | clip_02 | PASS |  |
| cheap_gates | - | PASS | runtime 61.82 s |
| r91_value | - | UNTESTED | no recorded value verdict: ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('heimdall:deepseek/deepseek-v4.1-flash', 'same  |
| fidelity | - | UNTESTED | no recorded fidelity verdict: ReplayMiss: fidelity_verdict: no recorded exchange ([('heimdall:qwen/qwen3.8-27b', 'replay: not recorded'), ('xai:grok-4.20-0309-reasoning', 'replay: not record |
| context | - | PASS |  |
| coherence | - | UNTESTED | ReplayMiss: coherence_panel: no recorded exchange ([('heimdall:qwen/qwen3.8-27b', 'replay: not recorded'), ('heimdall:minimax/minimax-m3.1-flash', 'same model family as the generator (minimax): skipped'), ('heimd |

### 41f29b1f (medley, published)

Judged moments (the ids, spans and risk flags each gate read):

- hook: f216541bd2f9e5eb672d 3218.14-3221.64 (3.5 s), risk [], published 2026-11-10T13:45:51+00:00
- clip_01: 4f9d38e1d86556b36d9c 2403.23-2422.07 (18.84 s), risk ['price_prediction'], published 2026-11-09T17:00:09+00:00
- clip_02: b0b787f8a62d97d81dbb 1826.54-1843.48 (16.94 s), risk ['price_prediction'], published 2026-11-11T18:03:23+00:00

| row | clip | state | why (as the code gave it) |
|---|---|---|---|
| adapter | hook | PASS | today's moment 2db4015fcdee15090558 3201.7-3221.64 (record's 3218.14-3221.64: span differs) |
| adapter | clip_01 | PASS | today's moment 4f9d38e1d86556b36d9c 2403.23-2422.07 |
| adapter | clip_02 | PASS | today's moment b0b787f8a62d97d81dbb 1826.54-1843.48 |
| r104_variants | hook | PASS | kept |
| r104_variants | clip_01 | PASS | kept |
| r104_variants | clip_02 | PASS | kept |
| usable | hook | PASS |  |
| usable | clip_01 | PASS |  |
| usable | clip_02 | PASS |  |
| r53_reposted | hook | PASS |  |
| r53_reposted | clip_01 | PASS |  |
| r53_reposted | clip_02 | PASS |  |
| r56_scorer_stand_alone | hook | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_01 | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_02 | PASS | scorer no verdict |
| ad_read | hook | PASS |  |
| ad_read | clip_01 | PASS |  |
| ad_read | clip_02 | PASS |  |
| r109_channels | - | PASS | 3 channels |
| stepA_first | hook | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| stepA_first | clip_01 | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| stepA_first | clip_02 | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| Lv2_cuttable | hook | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| Lv2_cuttable | clip_01 | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| Lv2_cuttable | clip_02 | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| G17a_hook_onset | - | UNTESTED | no source audio: OSError: network blocked (ruling 132 replay): yt-dlp |
| hook_eligible_opener | - | PASS |  |
| r115_hook_bar | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| r70_93_visual | hook | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_01 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_02 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| stepA_second | hook | UNTESTED | the first screen gave no cleared verdict to confirm |
| stepA_second | clip_01 | UNTESTED | the first screen gave no cleared verdict to confirm |
| stepA_second | clip_02 | UNTESTED | the first screen gave no cleared verdict to confirm |
| r117_join_table | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| lineup_rules | - | REFUSE | price predictions |
| stand_alone | - | PASS |  |
| r116_clips_alone | - | UNTESTED | no recorded clips-alone verdict for today's prompt (seeds 7-29 tried): ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('google:gemini-2.5-pro', 'replay: no |
| r37_question_hook | - | PASS | the hook is not a question |
| r72_lock | - | INTEGRATOR | line 9 |
| exclusion | hook | PASS |  |
| exclusion | clip_01 | PASS |  |
| exclusion | clip_02 | PASS |  |
| cheap_gates | - | REFUSE | STYLE: takeaway-words: 29 words (at most 20); STYLE: takeaway-opener: opens with 'what stands out' (make the point; no throat-clearing); STYLE: which-makes: a 'which makes ...' clause (end the sentence; say the point in  |
| r91_value | - | UNTESTED | no recorded value verdict: ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('heimdall:deepseek/deepseek-v4.1-flash', 'same  |
| fidelity | - | PASS |  |
| context | - | PASS |  |
| coherence | - | UNTESTED | ReplayMiss: coherence_panel: no recorded exchange ([('heimdall:qwen/qwen3.8-27b', 'replay: not recorded'), ('heimdall:minimax/minimax-m3.1-flash', 'same model family as the generator (minimax): skipped'), ('heimd |

Notes:

- hook: judged on the record's moment f216541bd2f9e5eb672d (today's adapter gave 2db4015fcdee15090558 3201.7-3221.64)
- f216541bd2f9e5eb672d: step A item from the record (no cached verdict today)
- 4f9d38e1d86556b36d9c: step A item from the record (no cached verdict today)
- b0b787f8a62d97d81dbb: step A item from the record (no cached verdict today)
- cheap gates: LY_SHAPE's 'clips-alone verdict not measured' left out (it is the r116 row's UNTESTED, not a cheap-gate refusal)

### 37c5b5f5 (VO-led moments, review only)

Judged moments (the ids, spans and risk flags each gate read):

- hook: 3b3050f4afd6f3c011e7 5144.99-5153.37 (8.38 s), risk [], published 2026-11-10T08:21:50+00:00
- clip_01: 4f9d38e1d86556b36d9c 2403.23-2422.07 (18.84 s), risk ['price_prediction'], published 2026-11-09T17:00:09+00:00
- clip_02: f216541bd2f9e5eb672d 3218.14-3221.64 (3.5 s), risk [], published 2026-11-10T13:45:51+00:00

| row | clip | state | why (as the code gave it) |
|---|---|---|---|
| adapter | hook | PASS | today's moment cc72a523d6fd0132400d 5142.11-5153.37 (record's 5144.99-5153.37: span differs) |
| adapter | clip_01 | PASS | today's moment 4f9d38e1d86556b36d9c 2403.23-2422.07 |
| adapter | clip_02 | PASS | today's moment 2db4015fcdee15090558 3201.7-3221.64 (record's 3218.14-3221.64: span differs) |
| r104_variants | hook | PASS | kept |
| r104_variants | clip_01 | PASS | kept |
| r104_variants | clip_02 | PASS | kept |
| usable | hook | PASS |  |
| usable | clip_01 | PASS |  |
| usable | clip_02 | PASS |  |
| r53_reposted | hook | PASS |  |
| r53_reposted | clip_01 | PASS |  |
| r53_reposted | clip_02 | PASS |  |
| r56_scorer_stand_alone | hook | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_01 | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_02 | PASS | scorer no verdict |
| ad_read | hook | PASS |  |
| ad_read | clip_01 | PASS |  |
| ad_read | clip_02 | PASS |  |
| r109_channels | - | PASS | 3 channels |
| stepA_first | hook | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| stepA_first | clip_01 | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| stepA_first | clip_02 | UNTESTED | no cached step-A verdict for today's prompt/key: STEP_A_HELD (ruling 102): no step-A verdict (ReplayMiss: context_verdict: no recorded exchange ([('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the t |
| Lv2_cuttable | hook | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| Lv2_cuttable | clip_01 | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| Lv2_cuttable | clip_02 | UNTESTED | no recorded transcription / window: OSError: network blocked (ruling 132 replay): yt-dlp |
| G17a_hook_onset | - | UNTESTED | no source audio: OSError: network blocked (ruling 132 replay): yt-dlp |
| hook_eligible_opener | - | PASS |  |
| r115_hook_bar | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| r70_93_visual | hook | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_01 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| r70_93_visual | clip_02 | UNTESTED | no cached sheet verdict: no contact sheet: OSError: network blocked (ruling 132 replay): yt-dlp |
| stepA_second | hook | UNTESTED | the first screen gave no cleared verdict to confirm |
| stepA_second | clip_01 | UNTESTED | the first screen gave no cleared verdict to confirm |
| stepA_second | clip_02 | UNTESTED | the first screen gave no cleared verdict to confirm |
| r117_join_table | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| lineup_rules | - | REFUSE | 30.7 s outside 36.7-51.5 s |
| stand_alone | - | PASS |  |
| r116_clips_alone | - | UNTESTED | no recorded clips-alone verdict for today's prompt (seeds 7-29 tried): ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('google:gemini-2.5-pro', 'replay: no |
| r37_question_hook | - | PASS | the hook is not a question |
| r72_lock | - | INTEGRATOR | line 9 |
| exclusion | hook | PASS |  |
| exclusion | clip_01 | PASS |  |
| exclusion | clip_02 | PASS |  |
| cheap_gates | - | UNTESTED | the package's own lines are not on record in today's form |
| r91_value | - | UNTESTED | the package's own lines are not on record in today's form |
| fidelity | - | UNTESTED | the package's own lines are not on record in today's form |
| context | - | UNTESTED | the package's own lines are not on record in today's form |
| coherence | - | UNTESTED | the package's own lines are not on record in today's form |

Notes:

- hook: judged on the record's moment 3b3050f4afd6f3c011e7 (today's adapter gave cc72a523d6fd0132400d 5142.11-5153.37)
- clip_02: judged on the record's moment f216541bd2f9e5eb672d (today's adapter gave 2db4015fcdee15090558 3201.7-3221.64)

### 3f481f5a (spotlight, PBX posted it)

Judged moments (the ids, spans and risk flags each gate read):

- hook: 06d34e155feae654ee56 0.0-22.94 (22.94 s), risk [], published 2026-11-14T17:00:22+00:00

| row | clip | state | why (as the code gave it) |
|---|---|---|---|
| adapter | hook | PASS | today's moment 06d34e155feae654ee56 0.0-22.94 |
| r104_variants | hook | PASS | kept |
| usable | hook | PASS |  |
| r53_reposted | hook | PASS |  |
| r56_scorer_stand_alone | hook | PASS | scorer no verdict |
| ad_read | hook | PASS |  |
| r109_channels | - | N/A | the spotlight's own path (ruling 90) |
| stepA_first | hook | PASS | xai:grok-4.20-0309-reasoning |
| Lv2_cuttable | hook | PASS |  |
| G17a_hook_onset | - | PASS |  |
| hook_eligible_opener | - | PASS |  |
| r115_hook_bar | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| r70_93_visual | hook | UNTESTED | no cached sheet verdict: no verdict in contract after two tries: seed 7: out of contract: ReplayMiss: visual_check: no recorded exchange ([('xai_vision:grok-4.7', 'replay: not recorded' |
| spot_pool_r90 | - | PASS | in the pool as ['06d34e155feae654ee56'] |
| spot_alone_r90 | - | UNTESTED | no ALONE score on record |
| spot_visual_clean_r90 | - | UNTESTED | no cached sheet |
| stepA_second | - | PASS |  |
| spot_source_r92 | - | UNTESTED | no cached layout verdict: no judged contact sheet (the visual check is not measured) |
| exclusion | - | PASS |  |
| r72_lock | - | INTEGRATOR | line 9 |
| spot_never_delivered_day | - | N/A | ruling 132: novelty read as never delivered (one per channel per ET day: no spotlight that day) |
| cheap_gates | - | REFUSE | ROLE: gives someone a role the cited clips' own words do not state (law L-v): ['guest'] |
| fidelity | - | UNTESTED | ReplayMiss: fidelity_verdict: no recorded exchange ([('heimdall:qwen/qwen3.8-27b', 'replay: not recorded'), ('xai:grok-4.20-0309-reasoning', 'replay: not recorded')]) |
| context | - | UNTESTED | ReplayMiss: viewer_takeaway: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the  |
| r91_closing_value | - | UNTESTED | ReplayMiss: coherence_verdict: no recorded exchange ([('xai:grok-4.20-0309-reasoning', 'replay: not recorded'), ('heimdall:deepseek/deepseek-v4.1-flash', 'same vendor as the text it judges (heimdall/d |

### build 114's line-up (not approved)

Judged moments (the ids, spans and risk flags each gate read):

- hook: 4d14201f553f57dc7672 0.0-7.34 (7.34 s), risk ['time_sensitive'], published 2026-11-16T22:00:18+00:00
- clip_01: 185e37a64058e69111ae 0.0-8.68 (8.68 s), risk ['time_sensitive'], published 2026-11-16T17:41:24+00:00
- clip_02: d6adeb54ad64062081c5 3339.9-3354.68 (14.78 s), risk [], published 2026-11-16T16:00:15+00:00
- clip_03: 93cfa865d13a0c3e1709 54.26-61.38 (7.12 s), risk ['time_sensitive'], published 2026-11-16T21:33:56+00:00

| row | clip | state | why (as the code gave it) |
|---|---|---|---|
| adapter | hook | PASS | today's moment 4d14201f553f57dc7672 0.0-7.34 |
| adapter | clip_01 | PASS | today's moment 185e37a64058e69111ae 0.0-8.68 |
| adapter | clip_02 | PASS | today's moment d6adeb54ad64062081c5 3339.9-3354.68 |
| adapter | clip_03 | PASS | today's moment 93cfa865d13a0c3e1709 54.26-61.38 |
| r104_variants | hook | PASS | kept |
| r104_variants | clip_01 | PASS | kept |
| r104_variants | clip_02 | PASS | no variant: the held word cannot be placed |
| r104_variants | clip_03 | PASS | no variant: the held word cannot be placed |
| usable | hook | PASS |  |
| usable | clip_01 | PASS |  |
| usable | clip_02 | PASS |  |
| usable | clip_03 | PASS |  |
| r53_reposted | hook | PASS |  |
| r53_reposted | clip_01 | PASS |  |
| r53_reposted | clip_02 | PASS |  |
| r53_reposted | clip_03 | PASS |  |
| r56_scorer_stand_alone | hook | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_01 | PASS | scorer no verdict |
| r56_scorer_stand_alone | clip_02 | PASS | scorer 2.0 |
| r56_scorer_stand_alone | clip_03 | PASS | scorer no verdict |
| ad_read | hook | PASS |  |
| ad_read | clip_01 | PASS |  |
| ad_read | clip_02 | PASS |  |
| ad_read | clip_03 | PASS |  |
| r109_channels | - | PASS | 3 channels |
| stepA_first | hook | PASS | xai:grok-4.20-0309-reasoning |
| stepA_first | clip_01 | PASS | xai:grok-4.20-0309-reasoning |
| stepA_first | clip_02 | PASS | xai:grok-4.20-0309-reasoning |
| stepA_first | clip_03 | PASS | xai:grok-4.20-0309-reasoning |
| Lv2_cuttable | hook | PASS |  |
| Lv2_cuttable | clip_01 | PASS |  |
| Lv2_cuttable | clip_02 | PASS |  |
| Lv2_cuttable | clip_03 | PASS |  |
| G17a_hook_onset | - | PASS |  |
| hook_eligible_opener | - | PASS |  |
| r115_hook_bar | - | PASS | scroll 3 alone 5 setup 4 |
| r70_93_visual | hook | PASS | flags [{'in_9x16': 'whole', 'item': 'bug', 'kind': 'burned_in', 'text': 'SIMPLY BITCOIN'}] |
| r70_93_visual | clip_01 | PASS | flags [{'kind': 'on_screen_text', 'text': 'Where the selling actually happened', 'why': 'The chart title asserts where the selling occurred, which the spoken line about a weekend liquidation and a 25% pullback does not s |
| r70_93_visual | clip_02 | PASS | flags [{'in_9x16': 'out', 'item': 'bug', 'kind': 'burned_in', 'text': 'Ledn'}, {'in_9x16': 'out', 'item': 'bug', 'kind': 'burned_in', 'text': 'WHAT BITCOIN DID'}] |
| r70_93_visual | clip_03 | PASS |  |
| stepA_second | hook | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| stepA_second | clip_01 | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| stepA_second | clip_02 | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| stepA_second | clip_03 | PASS | heimdall:deepseek/deepseek-v4.1-flash |
| r117_join_table | - | PASS | 1 flagged of 3: {'4d14201f -> 185e37a6': True, '185e37a6 -> d6adeb54': True, 'd6adeb54 -> 93cfa865': False} |
| lineup_rules | - | PASS | 37.9 s in 36.7-51.5 s (L-y 4: two clips of one channel, two videos) |
| stand_alone | - | PASS |  |
| r116_clips_alone | - | PASS | seed 10: clips {'hook': 3, 'clip_01': 5, 'clip_02': 3, 'clip_03': 4} flagged [] through-line yes; hook_own True |
| r37_question_hook | - | PASS | the hook is not a question |
| r72_lock | - | INTEGRATOR | line 9 |
| exclusion | hook | PASS |  |
| exclusion | clip_01 | PASS |  |
| exclusion | clip_02 | PASS |  |
| exclusion | clip_03 | PASS |  |
| cheap_gates | - | UNTESTED | the package's own lines are not on record in today's form |
| r91_value | - | UNTESTED | the package's own lines are not on record in today's form |
| fidelity | - | UNTESTED | the package's own lines are not on record in today's form |
| context | - | UNTESTED | the package's own lines are not on record in today's form |
| coherence | - | UNTESTED | the package's own lines are not on record in today's form |

