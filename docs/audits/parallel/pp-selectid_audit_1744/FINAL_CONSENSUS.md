# pp-selectid audit 1744 (rulings 68 / 72: the render's lock pre-check): FINAL consensus (cycle 2)

**Cycle 2:** no P0 and no P1 from any reviewer.
- grok: "SHIP: yes with conditions".
- qwen: "Production ready: Yes".
- glm: "Ship it".

All three verify both cycle-1 fixes:
- a pre-check that raises is no verdict, never a crash;
- the pin stage compares the text the lock passed.

No code change after cycle 1.

## The conditions

| # | condition | resolution |
|---|---|---|
| 1 | grok (a), qwen 1, glm P1-1 (downgraded to P2): are answers context-free per segment, so reusing one is sound? | CONFIRMED by the integrator (protocol-pulse-68, 18:0x ET): "YES, context-free per segment, given its KEY". The key is the video, its span, the acquisition window (from that video's segments), role, approved_text, trimmed_leading, untrimmed_start, the decoder_sha (the file name) and "rules". "Other videos' segments in the line-up change nothing. Reusing the newest matching pass / adopt_spoken / hold entry is right, and so is re-asking only on a missing entry or an error." |
| 2 | grok (b): a stale hold from another decoder version could be reused | The decoder sha is in the result file's NAME (`<video>.<start>-<end>.<decoder[:12]>.json`), and the rules string must match exactly. An answer from another decoder or another rules string is never read. Ruling 73 will change both; the integrator will send the new values, and RULES / DECODER change with them. |
| 3 | grok (c): an end-to-end run against the live results | Done by the next build that forms a line-up. Ruling 76 (18:08) withdrew the two line-ups that would have run it first: their clips are over 12 h. |
| 4 | qwen 3: the lock_requests directory must be writable | It is this worktree's own (send() creates it). A failure to write is no verdict (C1-a), never a crash. |

## Recorded

- glm N4: "carried" in the attested record is prose. It is the same wording as ruling 67's re-seal, and a ruling
  change would change the code that writes it.

## Cost of this audit

Upper-bound price estimates, not on the ruling-48 ledger:

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | $0.111 | $0.095 | $0.378 |
| 2 | $0.139 | $0.111 | $0.112 |

About $0.95 in all.
