# pp-selectid audit 1541 (RULING 70: the pin-stage visual check): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no findings.
  - qwen: "SHIP: no", on four "P0"s.
  - glm: ran to its 24k-token limit; "No verified P0", with many P1s, most of them self-resolved in its own text.
- Two consensus items are applied before cycle 2.

## Applied

| # | finding | the change |
|---|---|---|
| C1 | The cache key (moment + span + VERSION) left out inputs the verdict depends on, so a stale verdict could be served (qwen P0-2; glm P1-5, P1-47, P1-77): a change to the clip's words, the prompt or the sheet's parameters without a VERSION bump, or other sheet bytes | key() adds a digest of [PROMPT, TILES, EVERY_S, TILE_W, FORMAT, the clip's words]. A hit is used only when the judged sheet is on disk with its judged sha256. Otherwise the sheet is rebuilt: the same bytes keep the verdict, other bytes are judged afresh. Tests: the same bytes are cached (no call); other bytes are re-judged (a call); other words give another key. |
| C2 | The visual accounting counted only measured attempts as calls (qwen P0-1; glm P0-2 / P2-1) | Every attempt that is not a cache hit counts as a call (asked), and "unmeasured" stays its own counter. The driver's line reads "N sheet(s) asked (U not measured), K cached, F flag(s); measured cost $...". |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0-3: heimdall:qwen/qwen3.8-27b is not defined, so the failover may not be a vision back-end | It is an existing backend of pipeline/model_providers.json ("heimdall:qwen/qwen3.8-27b", vendor heimdall, base_url set). This diff makes HeimdallBackend.vision = True (providers.py), and it is the model the render's pipeline/visual_check.py already sends images to (VISION_MODELS). test_providers' config test checks every chain member is a defined backend. |
| R2 | qwen P0-4: replacing '"' with "'" in the clip's words corrupts them | It only keeps the prompt's own double quotes balanced around the words. The model judges meaning and negativity; the quote mark's shape changes neither. The sealed approved_text is untouched. |
| R3 | qwen P1-5: two threads may judge the same key at once | see() hands visual_for each moment once (its todo list is the line-up's distinct moments, or the passing hooks). Moments already measured in this build are skipped, so one build never asks the same key twice. |
| R4 | qwen P1-9: visual_hook_block may be stale across builds | build() pops visual_hook_block from every cleared moment before it judges the hooks (package.py, right before rated_open), as glm's P1-8 verified. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P1-6, P1-7: download / ffmpeg timeouts | Each fails closed: not measured, then the clip is dropped or the hook blocked. A build that loses clips this way records why. |
| G2 | qwen P1-8, glm P1-4: the xai_vision output cap (8000 tokens) makes a $0.23 reservation per call | It is the spend guard's UPPER bound, booked before the call and settled to the real usage; grok-4.7 reasons inside its output. The measured cost is reported on the first build, as the ruling asks. |
| G3 | glm P1-2: on_screen_text entries are unbounded | It fails closed and seals deterministically. |
| G4 | glm P1-1, P1-5 (the docstring's "image bytes": the sha is over the base64, which is injective), P1-14, P1-27, P1-54, P1-60 | Self-resolved in glm's own text, or records. |

## Verification

- test_visual_pin 10 OK (the cache tests extended); test_medley 138 OK, on dev26 (base 096a86ed).
