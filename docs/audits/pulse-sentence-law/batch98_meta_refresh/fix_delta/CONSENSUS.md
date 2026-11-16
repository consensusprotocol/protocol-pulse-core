# Batch 98, the fix delta (306ab688..9ecccc26): two cycles, PASS; one single-seat finding judged not a defect

The cycles:
- Cycle 1 (D1-D4): yt-dlp failures end in a logged AcquisitionError; the latest read wins; the re-read interval uses the same read time; nothing else changed.
- Cycle 2 (Y1-Y3, break it).

| Cycle | qwen27b (medium) | gpt-oss (medium) |
|---|---|---|
| 1 | PASS 0.92, 64.6 s, 9,890 characters of reasoning, $0.0022 | PASS 1.0, 11.0 s, 4,571 characters, $0.0002 |
| 2 | PASS 0.82, 161.4 s, 22,193 characters, $0.0049 | FAIL, one finding (high), 23.3 s, 15,243 characters, $0.0005 |

**gpt-oss's finding: "_fetch_meta does not catch CalledProcessError from yt-dlp, so non-zero exits propagate uncaught." NOT A DEFECT; no change.**
- The unchanged _ytdlp is `return subprocess.run(cmd + args, capture_output=True, text=True, timeout=timeout)`, at pipeline/transcript_store.py, with no `check=True`.
- subprocess.run raises CalledProcessError only when `check=True`. A non-zero exit returns a CompletedProcess with an empty or non-JSON stdout.
- That stdout fails json.loads, and _fetch_meta turns it into a logged AcquisitionError, as before. test_a_failed_re_read_appends_nothing_and_the_next_run_tries_again covers exactly that reply (a 429 on stderr, nothing on stdout).

Consensus: no defect. No change.
