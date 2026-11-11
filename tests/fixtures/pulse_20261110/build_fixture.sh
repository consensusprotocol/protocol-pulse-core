#!/usr/bin/env bash
# Builds tests/fixtures/pulse_20261110 from the READ-ONLY run dir runs/pinned_20261110_150345
# (PBX review of 2026-11-11: D1 clipped opening word, D2/D3 non-sentence edges, D4 warped credit avatars).
# Copies only; never writes to the run dir. Audio is stored as mono 24 kHz FLAC (envelope analysis only).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
RUN="$REPO/runs/pinned_20261110_150345"
OUT="$REPO/tests/fixtures/pulse_20261110"
mkdir -p "$OUT/run/transcripts" "$OUT/audio" "$OUT/video" "$OUT/selection"
for f in cuts_final.json edl.json PINNED_DECISION.json CLIP_CONTRACT.json CUT_ACCEPTANCE.json \
         vertical_overrides.json status.json; do cp "$RUN/$f" "$OUT/run/$f"; done
cp "$RUN/qa/concat_manifest_16x9.json" "$RUN/qa/concat_manifest_9x16.json" "$OUT/run/"
cp "$RUN"/transcripts/*.json "$OUT/run/transcripts/"
python3 - "$REPO" "$OUT" <<'PY'
import json, sys
repo, out = sys.argv[1], sys.argv[2]
b3 = json.load(open(f"{repo}/runs/fresh_20261110_093150/B3_CLIP_QUALITY.json"))
keep = ("video_id", "channel", "start", "end", "duration", "text", "clip_score", "source_chunk_id")
json.dump({"source": "runs/fresh_20261110_093150/B3_CLIP_QUALITY.json (chosen)",
           "note": "the editor's selection-time decision (canonical store transcript, full-video seconds)",
           "chosen": [{k: p.get(k) for k in keep} for p in b3["chosen"]]},
          open(f"{out}/selection/B3_chosen.json", "w"), indent=2)
PY
A="-v error -y -vn -ac 1 -ar 24000 -c:a flac"
for v in RXTVaDsN11M lusJ1m-J0Mc 36HPi9UZPOc; do ffmpeg -i "$RUN/sources/$v.mp4" $A "$OUT/audio/src_$v.flac"; done
for c in hook clip_01 clip_02; do ffmpeg -i "$RUN/qa/final_$c.mp4" $A "$OUT/audio/prepared_$c.flac"; done
ffmpeg -i "$RUN/out/segment.mp4" $A "$OUT/audio/out_16x9.flac"
ffmpeg -i "$RUN/out/segment_vertical.mp4" $A "$OUT/audio/out_9x16.flac"
cp "$RUN/qa/shoutout_16x9.mp4" "$RUN/qa/shoutout_9x16.mp4" "$OUT/video/"
cp "$RUN"/avatars/*.jpg "$OUT/video/" 2>/dev/null || true
( cd "$RUN" && sha256sum cuts_final.json edl.json transcripts/*.json sources/*.mp4 qa/final_*.mp4 \
    out/segment.mp4 out/segment_vertical.mp4 qa/shoutout_16x9.mp4 qa/shoutout_9x16.mp4 ) > "$OUT/ORIGINALS.sha256"
( cd "$OUT" && find . -type f ! -name FIXTURE.sha256 ! -name build_fixture.sh -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/FIXTURE.sha256"
echo "fixture built: $(du -sh "$OUT" | cut -f1)"
