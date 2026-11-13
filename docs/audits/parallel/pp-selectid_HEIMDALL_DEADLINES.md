# Heimdall calls that missed the 300 s deadline, or ran long (order 08:06 item 55)

Written by pp-selectid at 08:07 ET on Nov 13 from the build records (tests/package/proof/*/package.json:
angle_tried) and the reply cache (tests/package/fixtures/replies: every answered call with its seconds and
usage). New misses are appended to HEIMDALL_DEADLINES.jsonl beside this file once the router's logging lands
(in audit).

**The pattern:**
- The angle prompt is small: 3,000-6,200 characters, about 800-1,700 input tokens.
- deepseek/deepseek-v4.1-flash writes 9,400-15,000 OUTPUT tokens (mostly hidden reasoning) for a reply capped at
  max_tokens 3,000. At about 42 tokens/s that lands at 240-311 s, at or past the 300 s deadline every time.
- qwen/qwen3.8-27b, reached after deepseek's miss, missed the deadline 3 times (03:21, 05:48 and 07:14 ET). It
  returned an empty reply once (04:22 ET), and it answered once (Nov 12, fresh_20261112_050611).
- The cost is ~600 s per build (both writers' deadlines) before xAI Grok answers in 100-170 s.

## Missed deadlines (abandoned at 300 s)

| build (UTC) | model | max_tokens | prompt chars | prompt tokens (answering model's count) | answered instead by | its seconds | its output tokens |
|---|---|---|---|---|---|---|---|
| 08:21 (03:21 ET) | deepseek/deepseek-v4.1-flash | 3000 | 3945 | 1222 | grok-4.20-0309-reasoning | 99.97 | 14360 |
| 08:21 (03:21 ET) | qwen/qwen3.8-27b | 3000 | 3945 | 1222 | grok-4.20-0309-reasoning | 99.97 | 14360 |
| 09:22 (04:22 ET) | deepseek/deepseek-v4.1-flash | 3000 | 4728 | 1428 | grok-4.20-0309-reasoning | 167.28 | 19345 |
| 10:48 (05:48 ET) | deepseek/deepseek-v4.1-flash | 3000 | 3734 | 1168 | grok-4.20-0309-reasoning | 166.35 | 20944 |
| 10:48 (05:48 ET) | qwen/qwen3.8-27b | 3000 | 3734 | 1168 | grok-4.20-0309-reasoning | 166.35 | 20944 |
| 12:14 (07:14 ET) | deepseek/deepseek-v4.1-flash | 3000 | 3500 | 1109 | grok-4.20-0309-reasoning | 103.61 | 12598 |
| 12:14 (07:14 ET) | qwen/qwen3.8-27b | 3000 | 3500 | 1109 | grok-4.20-0309-reasoning | 103.61 | 12598 |
| Nov 12 (fresh_20261112_050611) | deepseek/deepseek-v4.1-flash | 3000 | not recoverable | - | qwen/qwen3.8-27b | - | - |

## Heimdall calls that answered, but in 240 s or more

| UTC | role | model | seconds | prompt chars | in tokens | out tokens | max_tokens |
|---|---|---|---|---|---|---|---|
| 02:03 (21:03 ET) | angle_write | deepseek/deepseek-v4.1-flash | 302.37 | 6151 | 1687 | 13755 | 3000 |
| 02:06 (21:06 ET) | angle_write | deepseek/deepseek-v4.1-flash | 240.02 | 3690 | 1000 | 10409 | 3000 |
| 02:24 (21:24 ET) | angle_write | deepseek/deepseek-v4.1-flash | 268.59 | 4757 | 1307 | 11402 | 3000 |
| 02:24 (21:24 ET) | angle_write | deepseek/deepseek-v4.1-flash | 281.63 | 3266 | 895 | 12660 | 3000 |
| 02:32 (21:32 ET) | angle_write | deepseek/deepseek-v4.1-flash | 256.55 | 4096 | 1108 | 12571 | 3000 |
| 02:42 (21:42 ET) | angle_write | deepseek/deepseek-v4.1-flash | 311.09 | 4161 | 1133 | 14865 | 3000 |
| 02:44 (21:44 ET) | angle_write | deepseek/deepseek-v4.1-flash | 263.79 | 4161 | 1142 | 11910 | 3000 |
| 02:52 (21:52 ET) | angle_write | deepseek/deepseek-v4.1-flash | 275.35 | 4161 | 1133 | 12703 | 3000 |
| 05:09 (00:09 ET) | angle_write | deepseek/deepseek-v4.1-flash | 270.28 | 3506 | 951 | 11491 | 3000 |
| 05:09 (00:09 ET) | angle_write | deepseek/deepseek-v4.1-flash | 260.69 | 4110 | 1129 | 12297 | 3000 |
| 05:41 (00:41 ET) | angle_write | deepseek/deepseek-v4.1-flash | 259.0 | 3334 | 915 | 10766 | 3000 |
| 05:50 (00:50 ET) | angle_write | deepseek/deepseek-v4.1-flash | 249.8 | 3334 | 915 | 10757 | 3000 |
| 07:17 (02:17 ET) | angle_write | deepseek/deepseek-v4.1-flash | 290.64 | 2995 | 807 | 12139 | 3000 |
| 09:48 (04:48 ET) | angle_write | deepseek/deepseek-v4.1-flash | 293.44 | 4537 | 1246 | 12806 | 3000 |
| 10:32 (05:32 ET) | angle_write | deepseek/deepseek-v4.1-flash | 285.04 | 4753 | 1293 | 12229 | 3000 |
| 11:22 (06:22 ET) | angle_write | deepseek/deepseek-v4.1-flash | 240.38 | 3734 | 1022 | 9462 | 3000 |
| 12:24 (07:24 ET) | context_verdict | deepseek/deepseek-v4.1-flash | 474.31 | 23765 | 5919 | 12236 | 4000 |

- The 474 s context_verdict call is the 07:14 build's second-vendor step-A screen (order 06:22 item 45): one call
  with 8 excerpts. It had no deadline; it is listed for the same pattern (12,236 output tokens on a 4,000 cap).
