# pp-ingest: mining back-end A/B (orchestrator 02:45 ET Nov 12, law L-x)

Harness: pipeline/ingest/ab.py (`tools/ingest_watch.py ab`). Run: 2026-11-12 08:26-08:55 UTC, tmux pp_ingest_ab, 8 in
flight (beside the live watcher's 12), budget $25 (spent $3.19 + judge). Videos: the 30 in videos.json below, from the
saved universes runs/fresh_20261110_093150, fresh_20261111_213954, fresh_20261112_050611 (records read read-only from
the main store, each hash-checked against the sha its run recorded): 21 channels, records {'whisper_words': 4, 'yt_auto': 20, 'yt_manual': 4, 'whisper': 1, 'whisper_words_punct': 1}, the four
videos of the PBX-approved Nov 11 preview first. Same windows per back-end: the first 8 Bitcoin-bearing windows of each
video (127 windows). Judge: grok-4.20-0309-reasoning (xAI), a model that is neither generator; per video both top-5
lists shown as X / Y in a seeded random order, no back-end names; strict JSON verdict.

# Mining back-end A/B (2026-11-12T09:00:22.678581+00:00)

30 videos from the saved universes; same windows per back-end; judge {'backend': 'xai_frontier', 'model': 'grok-4.20-0309-reasoning'} (none of the generators; sides blind and shuffled).

| back-end | model | videos | windows | failed | invalid attempts | transport errors | p50 s | p95 s | $ total | $/video | moments/video | approved recall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heimdall_qwen27b | qwen/qwen3.8-27b | 30 | 127 | 1 | 5 | 0 | 18.8 | 28.4 | 0.0827 | 0.0028 | 13.13 | 1/3 (1 unmeasured: the approved sentence is not in the offered windows) |
| anthropic_frontier | claude-opus-5-5 | 30 | 127 | 0 | 0 | 0 | 5.0 | 7.0 | 3.1083 | 0.1036 | 11.8 | 2/3 (1 unmeasured: the approved sentence is not in the offered windows) |

| pair | videos | top-5 overlap | hard-flag agreement | judge wins | judge quality | flag errors | judge failures |
|---|---|---|---|---|---|---|---|
| heimdall_qwen27b vs anthropic_frontier | 25 | 0.565 | 0.758 | {'heimdall_qwen27b': 11, 'anthropic_frontier': 15, 'tie': 4} | {'heimdall_qwen27b': 2.77, 'anthropic_frontier': 2.8} | {'heimdall_qwen27b': 27, 'anthropic_frontier': 31} | 0 |

Reading:
- Quality: a near tie by the blind judge (Anthropic 15 wins, Heimdall 11, 4 ties; mean quality 2.80 vs 2.77 of 5;
  flag errors 31 vs 27). Top-5 agreement 0.57; hard-flag agreement on matched moments 0.76.
- Reliability: Heimdall 1 failed window of 127 (5 invalid attempts, all retried or fallen back in production); Anthropic
  0 / 0. Latency p50 18.8 s vs 5.0 s per window.
- Cost: Heimdall $0.0028 vs Anthropic $0.10 per video for the first 8 windows of each video (37x). Whole-video
  costs on the live watcher are in pp-ingest_STATE.md.
- Approved-passage recall (the preview's passages in the offered windows; small sample): Heimdall 1/3, Anthropic 2/3;
  neither puts them in its top 5. The packager ranks across all moments, not the miner's top 5.
- Decision (data, providers.json): Heimdall stays the primary API back-end for mining, Anthropic the first fallback,
  xAI the second. The local gemma3:27b (ULTRON FIRST) is the default only after it is measured on the same 30 videos
  under the GPU0 lease (REQUESTS R6.4): `PP_INGEST_GPU0_LEASE_HELD=1 python3 tools/ingest_watch.py ab --video-list
  <this run's videos.json> --backends local_gemma,heimdall_qwen27b --enable local_gemma`.

Videos:
- RXTVaDsN11M DataDash (whisper_words, fresh_20261112_050611) [approved preview]
- lusJ1m-J0Mc Natalie Brunell (whisper_words, fresh_20261112_050611) [approved preview]
- jbDqdLytkNM Bitcoin Magazine (whisper_words, fresh_20261111_213954) [approved preview]
- 36HPi9UZPOc Yahoo Finance (yt_auto:en-orig, fresh_20261110_093150) [approved preview]
- OwH00y15Ups Altcoin Daily (yt_auto:en-orig, fresh_20261112_050611)
- d5RWmgfcqUE Fox Business (yt_manual:en-JkeT_87f4cc, fresh_20261112_050611)
- KBhHlc83Bag BTC Sessions (yt_auto:en-orig, fresh_20261112_050611)
- Noq6txZU91c Simply Bitcoin (yt_auto:en-orig, fresh_20261112_050611)
- dxZc2esQmAw Bloomberg Television (yt_manual:en, fresh_20261112_050611)
- f22H17BKYRw The Bitcoin Layer (yt_auto:en-orig, fresh_20261112_050611)
- Sjb6lUiL0m4 Stephan Livera (whisper_words, fresh_20261112_050611)
- bk40WI1XgV0 Yahoo Finance (yt_auto:en-orig, fresh_20261112_050611)
- qUTntqXojVo Bitcoin Audible (yt_auto:en-orig, fresh_20261112_050611)
- RzvUEk8uTLs TFTC (yt_auto:en-orig, fresh_20261112_050611)
- EjzQS-l-bIw DataDash (yt_auto:en-orig, fresh_20261112_050611)
- SIbzTHUCJWY Coin Bureau (yt_auto:en-orig, fresh_20261112_050611)
- CM3oXmVoxWo Bankless (whisper, fresh_20261112_050611)
- Irt0jKj7ISw BTC Sessions (yt_manual:en, fresh_20261112_050611)
- vgsSZ4mAHfQ Saifedean Ammous (whisper_words_punct, fresh_20261112_050611)
- bzjnh8DQ1Ew Swan Bitcoin (yt_auto:en-orig, fresh_20261112_050611)
- eqT2rFCvR0o Swan Bitcoin (yt_auto:en-orig, fresh_20261112_050611)
- PWMNwdI360M Anthony Pompliano (yt_auto:en-orig, fresh_20261112_050611)
- DcUbBkyeh9M Simply Bitcoin (yt_auto:en-orig, fresh_20261112_050611)
- R-iKNbc7-zk Altcoin Daily (yt_auto:en-orig, fresh_20261112_050611)
- gSZP493Dxis CoinTelegraph (yt_manual:en, fresh_20261112_050611)
- xQvOm1CqMwY Stacker News (yt_auto:en-orig, fresh_20261112_050611)
- wdk5JZ9hPzs Natalie Brunell (yt_auto:en-orig, fresh_20261112_050611)
- UJFQBaMh3yg Coin Bureau (yt_auto:en-orig, fresh_20261112_050611)
- agm-IxIFXrE Robert Breedlove (yt_auto:en-orig, fresh_20261112_050611)
- wO4A4TR0dw0 Anthony Pompliano (yt_auto:en-orig, fresh_20261112_050611)
