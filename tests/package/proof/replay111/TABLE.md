# Ruling 111: the v4 abliterated in the gateway's JSON mode

Built 2026-11-15 02:25 EST. deepseek/deepseek-v4-flash-0731-abliterated, response_format {"type": "json_object"}, reasoning_effort none. Ruling 85.1's records; ruling 100's deadline (the gateway's 120 s); each call cut at 300 s (replay110).

## The effort, on the sample (the first records in ruling 85.1's order)

| effort | rows | answers | valid | valid-answer rate | agreement on valid answers | p50 s |
|---|---|---|---|---|---|---|
| none (kept) | 40 | 40 | 34 | 85% | 75% | 3 |
| medium | 40 | 38 | 27 | 71% | 76% | 51 |

## All 319 records, effort none (ruling 110's columns, then the two this order adds)

| type | records | in time | late | timeouts | errors | out of contract | missed | units in time | agree | stricter | looser | different | agree % in time | p50 s | p90 s | usd reported | VALID-ANSWER RATE | AGREEMENT ON VALID ANSWERS | ruling 110 (no JSON mode): valid-answer rate / agreement |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| step_a | 96 | 32 | 0 | 0 | 0 | 64 | 0 | 232 | 147 | 47 | 38 | 0 | 63% | 15 | 25 | 0.0325 | 33% | 63% | 6% / 74% |
| step_c | 33 | 31 | 0 | 0 | 0 | 2 | 0 | 95 | 83 | 10 | 2 | 0 | 87% | 3 | 5 | 0.0020 | 94% | 87% | 94% / 89% |
| clips_alone | 91 | 47 | 0 | 0 | 0 | 44 | 0 | 94 | 60 | 8 | 2 | 24 | 64% | 4 | 5 | 0.0031 | 52% | 64% | 62% / 53% |
| coherence | 18 | 16 | 0 | 0 | 0 | 2 | 0 | 16 | 10 | 5 | 1 | 0 | 62% | 2 | 3 | 0.0005 | 89% | 62% | 100% / 67% |
| hook | 6 | 5 | 0 | 0 | 0 | 1 | 0 | 19 | 14 | 2 | 3 | 0 | 74% | 4 | 6 | 0.0002 | 83% | 74% | 100% / 87% |
| fidelity | 39 | 35 | 0 | 0 | 0 | 4 | 0 | 131 | 96 | 20 | 15 | 0 | 73% | 7 | 10 | 0.0037 | 90% | 73% | 85% / 79% |
| exclusion | 27 | 24 | 0 | 0 | 0 | 3 | 0 | 24 | 21 | 3 | 0 | 0 | 88% | 2 | 3 | 0.0012 | 89% | 88% | 93% / 100% |
| speaker | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 9 | 8 | 1 | 0 | 0 | 89% | 3 | 4 | 0.0007 | 100% | 89% | 89% / 100% |

## Out of contract: 120 answers (texts in RESULTS.jsonl and OUT_OF_CONTRACT.jsonl)

- 93 truncated
- 27 valid JSON, not the contract
  - step_a: 43 truncated, 21 valid JSON, not the contract
  - step_c: 2 truncated
  - clips_alone: 43 truncated, 1 valid JSON, not the contract
  - coherence: 1 valid JSON, not the contract, 1 truncated
  - hook: 1 truncated
  - fidelity: 3 valid JSON, not the contract, 1 truncated
  - exclusion: 2 truncated, 1 valid JSON, not the contract

## Anchor decisions Grok passed that it failed: 22

- step_c tests/package/fixtures/replies/1c/1c64f285710ab2a84bf10e0b5b761af5e9ae086e952532ab2fee7a2d150781f8.json unit hook (pins 37c5b5f5, 41f29b1f)
- step_c tests/package/fixtures/replies/1d/1d9080a526df8d21d8c108224e42337fdb585efecab636608afca82b62ed7cd3.json unit clip_01 (pins 41f29b1f)
- coherence tests/package/fixtures/replies/b6/b63b1452143000122f375adce8a097024af95bc29475d579bf1f4a3bbb47bf70.json unit package (pins 37c5b5f5)
- fidelity tests/package/fixtures/replies/72/7284ff4ae458538ca50de5e3dd7ac9e0a0b06a5f54faf68cd3b84cff5ad1f059.json unit title (pins 37c5b5f5)
- fidelity tests/package/fixtures/replies/72/7284ff4ae458538ca50de5e3dd7ac9e0a0b06a5f54faf68cd3b84cff5ad1f059.json unit caption (pins 37c5b5f5)
- step_c tests/package/fixtures/replies/41/417b6e4a42687e8432e837b84bf1892b797556e5696b503c14425a63f44ebb75.json unit hook (pins 37c5b5f5, 41f29b1f)
- step_c tests/package/fixtures/replies/41/417b6e4a42687e8432e837b84bf1892b797556e5696b503c14425a63f44ebb75.json unit clip_02 (pins 37c5b5f5, 41f29b1f)
- step_c tests/package/fixtures/replies/22/222a4e7e38acafd3fc66a8a4fd08099a5e960a2fc1c99af03ff6b8c2b363649e.json unit hook (pins 37c5b5f5, 41f29b1f)
- exclusion tests/package/fixtures/replies/95/95264c044fa625a9909f559031ed4ec548f0967b5242c3b0335c2b323f2c9196.json unit moment (pins 37c5b5f5)
- step_c tests/package/fixtures/replies/61/615d90a03c0c83ef6424b25eff0d0e9c4d5df5ce157e0809718e272469856050.json unit clip_02 (pins 41f29b1f)
- step_c tests/package/fixtures/replies/bc/bc04be7471b1a405dac0ca9cb90329eb9d7c195c3c7c87dcb85c1350ce3087c0.json unit clip_01 (pins 41f29b1f)
- step_c tests/package/fixtures/replies/dd/dd707bb8cb58d84812cfb2b0180654684261b8725e3d6514006c657b03d46e28.json unit clip_02 (pins 41f29b1f)
- step_a tests/package/fixtures/replies/05/054ce704cfb8eaca0d5738d4069342da296508f5f45eb0e3ade882cca46f4c42.json unit hook (pins 37c5b5f5)
- step_a tests/package/fixtures/replies/05/054ce704cfb8eaca0d5738d4069342da296508f5f45eb0e3ade882cca46f4c42.json unit clip_01 (pins 37c5b5f5, 41f29b1f)
- step_a tests/package/fixtures/replies/3a/3ae4520a414e1aeecbbe1b823e1b6abcf084e57f04dcb77aea8b21cbba11db55.json unit b0b787f8a62d97d81dbb (pins 41f29b1f)
- step_a tests/package/fixtures/replies/3a/3ae4520a414e1aeecbbe1b823e1b6abcf084e57f04dcb77aea8b21cbba11db55.json unit 3b3050f4afd6f3c011e7 (pins 37c5b5f5)
- clips_alone tests/package/fixtures/replies/23/230f8936e44cef19144f8793f1f4bd4e9885c66a78394901f5853426a2e56237.json unit lineup (pins 41f29b1f)
- step_a tests/package/fixtures/replies/bb/bbc94f85744e63430af45da278efad152bda15b7301efa253216b5dbbb2bf1de.json unit clip_01 (pins 37c5b5f5, 41f29b1f)
- step_a tests/package/fixtures/replies/cd/cd226a7498081605363c2462b04173647048bf6f78f2d059e797f49dbd674cb6.json unit 3b3050f4afd6f3c011e7 (pins 37c5b5f5)
- step_a tests/package/fixtures/replies/ca/caeca27a260e31a61e87b0c7b1c8a230a7005b141b2a62d6dcf0ac39a3ed1989.json unit 876662b7dc4e961d47e1 (pins 37c5b5f5, 41f29b1f)
- step_a tests/package/fixtures/replies/ce/ce780b7c4b1e5743d258baf9da569a8bf7fbb767a2f01637c58155d0c7adfbb4.json unit 316f66f81603ea55899a (pins 41f29b1f)
- step_a tests/package/fixtures/replies/fc/fcedd68df1b1fa456a60b2ac4c7428b5c280a38073359aad41d31f42862ca81f.json unit 316f66f81603ea55899a (pins 41f29b1f)

## The bars of rulings 85/88/96, per verdict type (replay85.passes)

- step_a: DOES NOT: an anchor decision Grok passed is failed; 27 REFERENT_OUTSIDE refusal(s) let through; agreement 63% < the bar 85%; 64 of 96 answers out of contract
- step_c: DOES NOT: an anchor decision Grok passed is failed
- clips_alone: DOES NOT: an anchor decision Grok passed is failed; agreement 64% < the bar 79%; 44 of 91 answers out of contract
- coherence: DOES NOT: an anchor decision Grok passed is failed; agreement 62% < the bar 75%; 2 of 18 answers out of contract
- hook: DOES NOT: agreement 74% < the bar 75%; 1 of 6 answers out of contract
- fidelity: DOES NOT: an anchor decision Grok passed is failed; 4 of 39 answers out of contract
- exclusion: DOES NOT: an anchor decision Grok passed is failed; 3 of 27 answers out of contract
- speaker: DOES NOT: only 9 decisions (< 10)
