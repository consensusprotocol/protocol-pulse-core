# heimdall_minimax (minimax/minimax-m3.1-flash, 528.4 s, $0.010, finish length)

# CYCLE 2 REVIEW — pp-ingest `cycles.py` (post-C1 state, 47c7939b + C1-1..C1-9)

I read the current code (the diff as it now stands, with the nine C1 fixes in it) against the three questions, and against the three Cycle-1 reviews.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

I had no Cycle-1 output, so this is my first pass. The Cycle-1 reviewers' findings were largely **real and now fixed**; I verified each fix in the current code rather than taking the consensus on trust:

| Cycle-1 finding | Status in the current code (verified) |
|---|---|
| glm BUG 1: "newest with one" could be days old, unlabelled | **Fixed.** `cycles.py:141-146` labels it "before this window" and prints the date. I checked the label is *true*: `last` selects `windows > windows_screened` over the whole table, but any such video inside the window that is MINED/MINED_PARTIAL makes `_quiet` return `""` (line 137), and a non-mined video has `windows` NULL → `0 > 0` false. So `last` is always outside the window. The label cannot lie. |
| glm BUG 2: the note's counts did not add up | **Fixed.** `cycles.py:148-150`: `other = len(seen) - len(known) - shorts - queued`, printed as "not minable". The three sub-counts now sum to `len(seen)`. |
| glm BUG 5 / muse 1.3: N+1 video query | **Fixed.** `_videos` (lines 33-39), 500 ids per query. |
| glm BUG 9: a channel's first listing listed 30 lines | **Fixed.** `SEEN_OLD` is counted, not listed (lines 108-111). |
| muse Bug A: `n` vs the events' count | **Fixed and disclosed.** `found = "" if len(evs) == n else f" ({len(evs)} found in its events)"` (line 113). |
| glm P0 "the vanish" | **Fixed.** A window with any cycle always has a line (line 128). |
| glm P0: a multi-line reason made the writer refuse the line | **Fixed.** `_one` (lines 26-30) folds every field and the whole line. |

**What I add that nobody caught** is in §3 — the headline scope of the 09:02 note, a whole-line crash on one bad row, a soft ceiling, and the notice ordering.

---

## 2. WHERE I AGREE / DISAGREE

**glm BUG 1 (stale "newest with one") — agree, and it is now correctly fixed.** I re-derived the guarantee above; the "before this window" wording is honest, not a cosmetic patch.

**glm BUG 2 (counts) — agree, fixed.** One residual: `other` lumps `UNAVAILABLE` (age-gated, retryable) with `DUPLICATE`/`NO_CAPTIONS`/`TOO_LONG`/`OPTOUT` under "not minable". An age-gated video is not "not minable", it is "not fetchable". Cosmetic (P3).

**glm BUG 3 (partial re-mine moves the line's time) — agree it is not a bug.** `video_entry` returns `max(mined, hook_ts)`; a re-mined partial advances the head time, which is a real change.

**glm BUG 4 / muse 1.5 (not one snapshot) — agree, benign.** `compose` reads events, then video rows, then channels in three statements. A video mined between the `disc` read and the row read yields a line one pass stale; the next pass (60 s) re-reads everything. No writer races: `write_cycles_notice` holds the notices' flock and `_rewrite_top` rewrites only when the text differs.

**muse Bug B (`start` heuristic fragile when `seconds` is missing) — partially agree, still open.** `start = ts - float(d.get("seconds") or 0) - 2` (line 105). If `seconds` is absent/0, `start = ts - 2` and the cycle's discoveries are missed: the line then says "N new (0 found in its events)" and lists **no videos**. The mismatch is disclosed (good), but the videos are silently absent from the standing order's line. See N6.

**muse 1.4 (the 09:02 note is suppressed when the watcher is stopped) — agree it is a choice, not a bug.** `compose` returns `None` when no cycle ran in the window (line 96). Claiming "nothing Bitcoin in 3 h" from a stopped watcher would be a claim about a stopped watcher. Defensible; it should be stated in the design (P3).

**qwen (the "nothing Bitcoin" note does not lie) — partially agree.** The *body* is honest: "none of the **K mined** with a Bitcoin term", with "Q not mined yet" counted apart. But the *headline* is unqualified — see N1. qwen read the body and generalised to the line; the line is what a reader of STATE line 1 sees.

**qwen (the N+1 lookup acceptable) — moot, fixed.**

---

## 3. NEW FINDINGS FROM THIS REVIEW

### N1 — P1 — the 09:02 headline is unqualified while its body is scoped (`cycles.py:139-150`)
The line reads:

> `NOTHING BITCOIN IN THE LAST 3 H: 3 upload(s) seen (3 not mined yet), none of the 0 mined with a Bitcoin term in any window`

The body is precise. The **headline asserts a blanket fact about the last 3 h** that the body immediately contradicts in scope: three uploads were seen and none of them is known to be Bitcoin-free — they are simply not mined yet. On a quiet Saturday (the exact case the 09:02 order was written for) discovery runs ahead of mining, so `queued > 0` is the *normal* case, and the headline is then wrong as written. This is the one place where the line can over-claim, and it is the line's most prominent words.

Fix (cheap): qualify the headline when `queued > 0`, e.g. `NOTHING BITCOIN IN THE LAST 3 H AMONG THE {len(known)} MINED ({queued} NOT MINED YET)`, or move the qualifier into the headline itself. A test that fails without the fix: a window with one queued upload and no mined one must not contain the bare string "NOTHING BITCOIN IN THE LAST 3 H:".

### N2 — P1 — one malformed video row loses the *whole* line (`cycles.py:60-77`)
`video_entry` is called per video with no guard. For a row in state MINED/MINED_PARTIAL with `mined_ts` NULL (a row written by an older schema, a hand-edited DB, a partial migration):

* `lag` degrades safely (`if pub and seen and mined` → "publish time not measured"),
* but `_et(mined)` (line 71/74) raises `TypeError` on `None`, and
* `max(t for t in (mined, v["hook_ts"]) if t)` (line 77) raises `ValueError: max() arg is an empty sequence` when both are falsy.

Either exception propagates out of `compose`, so **the entire line is not written** — not just that video — and the only trace is one log line in the service log (`service.py:775-779`). The watcher keeps running; STATE keeps a stale cycles line indefinitely. Fail-closed is right; losing the whole standing order over one row is not.

Fix: wrap the per-video rendering in a try/except and render the video as "mined no (its row is unreadable: …)"; and make `mined = v["mined_ts"] or 0` plus `changed = max([t for t in (mined, v["hook_ts"]) if t] or [0])`.

### N3 — P2 — the ceiling is soft (`cycles.py:120-126`)
The drop loop keeps at least one cycle (`while len(out) > 1`), and `_one(head + body + tail)` is called **without a limit** (line 129), so nothing truncates. A single cycle that found many new uploads (a busy channel set: `new` is summed over all channels in the cycle) produces a body of ~200 chars per video; 60 new videos in one cycle ⇒ ~12 k chars in one entry, over `MAX_CHARS` with no way to shed it. The `+ 80` fudge in the length estimate also makes the check approximate.

Fix: after the drop loop, if the line is still over `max_chars`, truncate the last kept cycle's body and say so ("… (truncated)"), or call `_one(line, max_chars)` as a final backstop.

### N4 — P2 — the standing order's line is not kept next to the switch line (`spend.py:36-64`)
`_rewrite_top` builds `block = [line] + kept + others` and then hoists **only** `SWITCH_RE` lines to the front. So after the spend meter trips, the order is: switch line, **spend notice**, cycles line — the cycles line is line 3, not line 2. The orchestrator's order says "line 1 carries, after each cycle that finds something: video, channel, mined…". The switch line legitimately owns line 1 (ruling 87), but the cycles line should sit directly under it, above the transient notices.

Fix: hoist the cycles line to position 1 of the non-switch block, the way `SWITCH_RE` is hoisted (e.g. a `CYCLES_RE` hoist in `_rewrite_top`, or by ordering `others` so the cycles line comes first).

### N5 — P2 — the quiet note contradicts the cycle body when the window's only discoveries were backfill (`cycles.py:139-140` vs `108-111`)
A channel's first listing records its old uploads as `SEEN_OLD`. Those are excluded from `seen` (line 133) but **counted** in the cycle body ("N older upload(s) recorded at a channel's first listing"). If the window's only discoveries were backfill, the note says "no new upload in N cycle(s)" while the body says the cycle found N new uploads. Both are