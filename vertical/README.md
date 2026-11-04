# vertical/ — Standalone Vertical Reframing Module

Replaces `render_v*_vertical.py` with a shotmap-driven, per-shot composition engine for 9:16 derivatives. Built offline, tested against a ground truth set before any segment uses it.

## Architecture

```
vertical/
  __init__.py          # GPU env, constants (1080x1920, 24fps, orange accent)
  shotmap.py           # Vendored from boomers_pipeline EP22 + extensions
  compositor.py        # Per-shot 9:16 composition (4 layout rules)
  reframe.py           # CLI pipeline: shotmap -> compose -> assemble -> qa -> critic -> tg
  debug.py             # Debug drawing (ISOLATED — never imported by render path)
  critic.py            # Grok-4 vision critic (xAI API)
  speaker_eval.py      # Lip-activity evaluation (MediaPipe FaceLandmarker)
  audit.py             # Trifecta cross-LLM audit (xAI + OpenAI + Gemini)
  tests/
    test_render_isolation.py  # T2: no debug drawing in render path
    test_face_count.py        # T1: face count matches shot_map
  testset/
    ground_truth.json         # Per-source expected layouts, face counts, speaker truth
  cache/                      # Per-source detection cache (md5-keyed)
  work/                       # Intermediate outputs (shot maps, composed clips, QA)
```

## Composition Rules (Law 18/19 v3)

Per **shot** (shotmap hard-cut boundaries), not per clip:

| Source Layout | Vertical Composition |
|---|---|
| 1 face | Fixed face-centered 9:16 crop (no panning) |
| 2 faces | Two stacked bands (equal or speaker-dominant), orange divider |
| 3 faces | Three stacked bands 1080x607, orange gutters |
| 4+ faces or screen-share | Full 16:9 letterbox top + enlarged guest column below |

- Never a subset of visible faces
- No animated panning (Law 18a)
- Re-composition only at shotmap hard cuts
- Speaker-dominant bands when lip-activity margin >= 0.35 sustained 1.5s (Law 18b)

## Usage

```bash
# Full pipeline
python3 -m vertical.reframe \
    --edl ~/protocol_pulse/segment_v1/cuts_v3.json \
    --sources ~/protocol_pulse/segment_v1/sources_pcm \
    --out out/segment_v14_vertical.mp4

# Shotmap only
python3 -m vertical.reframe --edl cuts_v3.json --sources sources_pcm --out /dev/null --stage shotmap

# No critic / no Telegram
python3 -m vertical.reframe --edl cuts_v3.json --sources sources_pcm --out out.mp4 --no-critic --no-tg
```

## Tests

```bash
# T2: render isolation (no debug drawing in compositor/reframe)
python3 -m pytest vertical/tests/test_render_isolation.py -v

# T1: face count (requires rendered output)
python3 -m pytest vertical/tests/test_face_count.py -v

# All tests
python3 -m pytest vertical/tests/ -v
```

## Audit

```bash
# Trifecta audit (all 3 providers)
python3 -m vertical.audit all

# Cycle 2 cross-examination
python3 -m vertical.audit cycle2 all
```

## Key Design Decisions

1. **Vendored shotmap.py** from boomers_pipeline — extended with screen-share detection, 4+ tile grids, and per-tile face counting via MediaPipe. Config-free entry point.
2. **Detection caching** (Law 21) — per-source results cached in `cache/<md5>.json`. Re-renders never re-detect.
3. **Debug isolation** — all drawing calls in `debug.py` only. Unit test T2 enforces this via AST scanning.
4. **Speaker-dominant bands** (Law 18b) — when lip-activity margin >= 0.35, speaker gets 60% band height.
5. **Grok vision critic** — 1 frame per shot, revised questions from design review (tiles visible, missing tiles, debug artifacts, face cutoff, layout ID).

## v13 Failure Root Causes (QWEN_CONTEXT_BIBLE entries)

- **Debug boxes baked in**: cv2.rectangle calls in render path were not isolated
- **Grid column dropped**: 5-tile source -> 3-band composition (subset of faces)
- **Mid-clip layout switch**: Riverside source changed from 3-up to 5-up without a hard cut; compositor didn't re-detect
