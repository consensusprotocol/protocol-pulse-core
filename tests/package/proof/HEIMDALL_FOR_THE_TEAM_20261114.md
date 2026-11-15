# The Heimdall gateway as Protocol Pulse sees it, Nov 12 05:00Z to Nov 15 03:30Z

This page is for the team that runs the Heimdall gateway, written from our own call records only (no new calls).
Protocol Pulse sends short VERDICT prompts (a JSON answer to a fixed question about a video clip or a line of text),
plus some longer code-review prompts, through the gateway to four models. Every time and window below is UTC.

Sources:
- the miner's call log (pp-ingest): 1,692 calls and 29 probes, with HTTP status, latency, tokens and request ids;
- the builder's recorded answers and its deadline log: 214 calls;
- the builder's replay of 753 calls (Nov 14 02-06Z) and a token-cap measurement of 132 calls;
- 295 code-review calls.
The miner logs cache hits and calls to other vendors too; neither is counted here.

What we send:
- temperature 0;
- verdict calls carry max_tokens = 16,000 (our floor), and code reviews 16,000 (qwen) or 24,000 (glm);
- the reasoning effort is "none" in code reviews and the measurement, and the model's default elsewhere;
- our client deadline is 60-300 s a call, set per model since about Nov 14 18:30Z (a flat 120 s before).

## 1. Per model

| model | calls | answered | missed our deadline | transport / HTTP errors | empty | out of our JSON contract | answered p50 / p90 s | output tokens p50 / p90 / max | answers stopped at the cap |
|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.8-27b | 1,815 | 1,602 | 41 (40 at 300 s) | 104 connection refused, 5 HTTP 503, 1 read timeout at 1,800 s | 0 | 62 | 15.9 / 52.2 | 497 / 1,317 / 16,000 | 5 |
| z-ai/glm-5.3-flash | 682 | 476 | 86 (51 at 300 s, 24 at 120 s, 11 at 60 s) | 2 client timeouts at 300 s, 1 HTTP 503, 1 IncompleteRead | 4 | 112 | 33.5 / 230.0 | 1,946 / 9,785 / 24,000 | 44 |
| deepseek/deepseek-v4.1-flash | 463 | 383 | 42 (28 at 300 s, 14 at 120 s) | none recorded (HTTP 429 at 7 in flight, below) | 0 | 38 | 114.5 / 268.9 | 4,202 / 10,777 / 14,865 | 34 (at the 16,000 floor, or at the 2,000-4,000 caps of the measurement) |
| muse | 154 | 58 | 0 | 96 HTTP 502 (62 %) | 0 | 0 | 8.7 / 43.4 | 44 / 62 / 69 | 0 |
| nvidia/nemotron-3.5-super-vl (vision) | 9 | 9 | 0 | 0 | 0 | 0 | 24.0 median, 28.8 max | not recorded | 0 |
| qwen3.8-27b (vision) | 9 | 9 | 0 | 0 | 0 | 0 | 14.0 median, 399.2 max | not recorded | 0 |

- google/gemma-4-31b-it is configured but was never called.
- "Out of our JSON contract" is our own strictness, not a gateway fault: a field too long, broken JSON, or an answer
  cut at the cap. For glm, 61 of the 112 are broken JSON in the replay.

## 2. Latency by prompt size, answered calls

Each cell is p50 / p90 seconds (n). Bucket: prompt characters; for the miner's calls, prompt tokens x 4.

| model | < 4k chars | 4-8k | 8-15k | > 15k |
|---|---|---|---|---|
| qwen3.8-27b | 18.3 / 70.8 (136) | 15.6 / 89.2 (130) | 14.8 / 24.2 (1,170) | 65.0 / 124.0 (166) |
| glm-5.3-flash | 10.3 / 78.9 (193) | 6.7 / 16.2 (58) | 10.8 / 19.3 (7) | 120.0 / 466.0 (188) |
| deepseek-v4.1-flash | 67.2 / 200.8 (151) | 135.1 / 268.6 (139) | 192.8 / 243.6 (17) | 265.9 / 289.6 (47) |
| muse | 8.7 / 43.4 (58) | - | - | - |

- qwen on the miner's prompts (most of them 6-12k characters) is steady: p50 14.6 s, p90 23.9 s over 1,232 answers.
- deepseek is slow at every size; its time grows with the prompt and with the reasoning tokens it emits.
- glm is fast with reasoning off and very slow with it on (section 3).
- The > 15k rows are mostly 40-170 KB code-review prompts.
- One glm burst: on Nov 14 01:24-01:35Z the miner's short flag checks (400-480 prompt tokens, 934-1,596 output tokens)
  took 185-222 s each. That is about 6 output tokens a second. Request ids:
  gen-1794619279-mb9nnc12o05yjn9d, gen-1794619879-qj6u58j1mier5u72, gen-1794619429-xil3jyzrl2rnbwdu,
  gen-1794619669-ldfwmhv8t2ri9p2u.

## 3. Output tokens against the cap sent (the max_tokens control IS honoured; reasoning is the cost)

The gateway stops every answer at the max_tokens we send. But with its default reasoning on, glm spends the budget
thinking. Our measurement (Nov 14, 10 verdict prompts per row, glm-5.3-flash):

| max_tokens sent | reasoning effort | p50 seconds | p50 output tokens | answers stopped at the cap |
|---|---|---|---|---|
| 16,000 | none | 8.8 | 314 | 0 of 10 |
| 16,000 | default | 324.4 | 16,000 | 6 of 10 (260-468 s each) |
| 4,000 | none | 9.6 | 314 | 0 of 10 |
| 4,000 | default | 106.5 | 4,000 | 10 of 10 (no usable answer) |
| 2,000 | default | 57.3 | 2,000 | 10 of 10 (no usable answer) |
| 400 (a one-word probe) | default | 15.0 | 400 | 2 of 3 |

- THE ONE-WORD PROBE: a 27-token health probe to glm, under default reasoning with the 16,000 floor, answered after
  390.9 s with 10,455 output tokens (2026-11-14T15:04:23Z; our deadline was 60 s, so it arrived late).
- In code reviews glm reached its 24,000 cap.
- deepseek's reasoning answers run 4,202 tokens at p50 and 10,777 at p90; 34 stopped at the cap they were sent.
- "effort": "none" is honoured by glm and qwen: about 300-900 output tokens in 6-22 s. We have not measured deepseek
  with reasoning off.

## 4. Incidents (UTC)

| when | model | what | records |
|---|---|---|---|
| 2026-11-12 08:36:30-08:37:16 | qwen3.8-27b | 104 calls refused (connection refused): the gateway was unreachable for about 46 s | miner's log; no request id |
| 2026-11-13 20:10:38 | qwen3.8-27b | 5 x HTTP 503 "No endpoints for qwen/qwen3.8-27b satisfy the request (provider_not_allowed: 1)" | miner's log |
| 2026-11-14 01:12:55-01:20:47 | muse | 23 x HTTP 502 "The provider returned an error" (upstream vLLM 500 Internal server error) | miner's log; no request id |
| 2026-11-14 04:04:35-04:05:03 | muse | 4 x HTTP 502 | |
| 2026-11-14 13:10:05-13:14:52 | muse | 17 x HTTP 502 | |
| 2026-11-14 13:56:18-14:05:04 | muse | 21 x HTTP 502 | |
| 2026-11-14 15:39:17-15:53:54 | muse | 31 x HTTP 502 | |
| 2026-11-14 01:25:48 and 01:35:19 | glm-5.3-flash | client timeouts at 300 s | |
| 2026-11-14 01:27:39 and 13:56:12 | glm-5.3-flash | empty answers (stopped at the cap, no content) | |
| 2026-11-14 about 03:00 (22:02 ET Nov 13) | deepseek | HTTP 429 at 7 calls in flight from one process; we dropped to 3 | builder's replay notes |
| 2026-11-14 14:01:08-14:22:49 | all | our "Heimdall down" signal (no family answered inside its deadline for 15 min; back after 3 answered probes). Judged FALSE: it came from muse's 502s and slow glm calls, and the probes answered | health file |
| 2026-11-14 14:57:43-15:18:49 | all | the same signal. FALSE: glm answers ran 483-532 s against a 120 s deadline; qwen probes answered in about 1 s | health file |
| 2026-11-13 about 15:29 | qwen3.8-27b | a code-review call: read timeout at 1,800 s | audit folder (file time) |
| 2026-11-14 about 04:35 | glm-5.3-flash | a code-review call: IncompleteRead (43,669 bytes read, 41,242 more expected) | audit folder (file time) |
| 2026-11-14 about 06:11 | glm-5.3-flash | a code-review call: HTTP 503 Service Unavailable | audit folder (file time) |
| 2026-11-13 23:23-23:29 (the orchestrator's window) | ? | NOT FOUND in the builder's or the miner's records. The miner's log has no Heimdall error then; the integrator may hold it | |

## 5. Breaker openings (our client: two deadline misses in a row, or an answer over 2x the cap sent)

| opened (UTC) | model | trigger | closed |
|---|---|---|---|
| 2026-11-14 16:31:53 | glm-5.3-flash | missed its 120 s deadline twice in a row | expired 17:01:53 |
| 2026-11-14 16:45:05 | deepseek-v4.1-flash | missed its 120 s deadline twice | closed by hand 17:11:26 (120 s was below its normal step time) |
| 2026-11-14 17:05:29 | glm-5.3-flash | its trial call missed | 18:05:29 |
| 2026-11-14 17:36:29 | deepseek-v4.1-flash | two misses at 120 s | by hand 17:39:27 |
| 2026-11-14 17:43:59 | deepseek-v4.1-flash | two misses at 120 s | its trial answered 18:40:57 (265.5 s, 11,916 tokens, deadline now 300 s) |
| 2026-11-14 18:35:36 | glm-5.3-flash | its trial missed (60 s) | 19:35:36 |
| 2026-11-14 23:03:15 | glm-5.3-flash | its trial missed (60 s) | open until 2026-11-15 00:03:15 |

Request ids are recorded only on the miner's answered calls (format gen-<number>-<id>). No failure carries one: none
of the 502s, 503s, refusals or timeouts.

## 6. What we need from a dedicated endpoint

| need | number | what we measured |
|---|---|---|
| input | verdict prompts of 4,000-15,000 characters (our p50 is 5,476, p90 10,749, max 27,769); code reviews 40-170 KB | builder's recorded prompts |
| output | a short JSON: 50-1,500 tokens with reasoning off | qwen p50 497, muse 44, glm with effort none 314 |
| latency | p90 under 30 s for verdicts | today: qwen 23.9 s on 6-12k prompts (meets it); glm 78.9 s on < 4k prompts; deepseek 200-290 s; glm with reasoning on 466 s at > 15k |
| controls | max_tokens and reasoning effort honoured on EVERY model | max_tokens is honoured (answers stop at the cap). "effort": "none" works on glm and qwen; deepseek's switch is not measured. A cap alone does not help, because the reasoning eats the budget (section 3) |
| concurrency | 8 requests in flight from one client | deepseek answered HTTP 429 at 7 in flight |
| availability | no 5xx and no refusals | measured: 96 x 502 on muse in 5 windows on Nov 14; 104 refused on Nov 12; 5 x 503 on Nov 13 |
| volume | about 500-2,000 calls a day now; 10x if the other niches come | gateway calls with a time: Nov 12 526, Nov 13 288, Nov 14 1,121, plus about 750 replay calls (Nov 14 early UTC) and about 300 code reviews |
| traceability | a request id on every response, failures included | today failures carry none |

## 7. Numbers we could not measure

- The Nov 13 23:23-23:29Z window: no record in our files.
- deepseek's output tokens with reasoning off: never asked.
- Vision output tokens: not recorded.
- Prompt characters on the miner's calls: estimated as tokens x 4.
- glm's time-to-first-token and queueing versus generation time: not exposed to us.
- The gateway's own server-side timings: none recorded.
