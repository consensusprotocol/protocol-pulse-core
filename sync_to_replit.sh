#!/bin/bash
# Sync a file from Ultron to Replit
# Usage: ./sync_to_replit.sh templates/podcasts.html

REPLIT_TOKEN="581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"
REPLIT_URL="https://protocolpulse.replit.app/api/admin/exec"
BASE_DIR="/home/ultron/protocol_pulse"

if [ -z "$1" ]; then
  echo "Usage: $0 <relative_path> [relative_path2] ..."
  echo "Example: $0 templates/podcasts.html templates/clips.html"
  exit 1
fi

for FILE_PATH in "$@"; do
  FULL_PATH="$BASE_DIR/$FILE_PATH"
  REPLIT_PATH="/home/runner/workspace/$FILE_PATH"
  
  if [ ! -f "$FULL_PATH" ]; then
    echo "ERROR: $FULL_PATH does not exist"
    continue
  fi
  
  SIZE=$(wc -c < "$FULL_PATH")
  echo "Syncing $FILE_PATH ($SIZE bytes)..."
  
  if [ "$SIZE" -gt 60000 ]; then
    # Large file - split into chunks
    echo "  Large file, splitting into chunks..."
    CHUNK_SIZE=40000
    split -b $CHUNK_SIZE "$FULL_PATH" /tmp/sync_chunk_
    
    # Clear target file first
    curl -s -X POST "$REPLIT_URL" \
      -H "Content-Type: application/json" \
      -d "{\"token\":\"$REPLIT_TOKEN\",\"cmd\":\"echo -n '' > $REPLIT_PATH\"}" > /dev/null
    
    for CHUNK in /tmp/sync_chunk_*; do
      B64=$(base64 -w0 "$CHUNK")
      curl -s -X POST "$REPLIT_URL" \
        -H "Content-Type: application/json" \
        -d "{\"token\":\"$REPLIT_TOKEN\",\"cmd\":\"echo '$B64' | base64 -d >> $REPLIT_PATH\"}" > /dev/null
      echo "  Chunk $(basename $CHUNK) sent"
    done
    rm -f /tmp/sync_chunk_*
    
    # Verify
    RESULT=$(curl -s -X POST "$REPLIT_URL" \
      -H "Content-Type: application/json" \
      -d "{\"token\":\"$REPLIT_TOKEN\",\"cmd\":\"wc -c $REPLIT_PATH\"}")
    echo "  Result: $RESULT"
  else
    # Small file - single push
    B64=$(base64 -w0 "$FULL_PATH")
    RESULT=$(curl -s -X POST "$REPLIT_URL" \
      -H "Content-Type: application/json" \
      -d "{\"token\":\"$REPLIT_TOKEN\",\"cmd\":\"echo '$B64' | base64 -d > $REPLIT_PATH && wc -c $REPLIT_PATH\"}")
    echo "  Result: $RESULT"
  fi
done

echo ""
echo "All files synced. Restarting Replit gunicorn..."
curl -s -X POST "$REPLIT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$REPLIT_TOKEN\",\"cmd\":\"kill -HUP \$(pgrep -f gunicorn | head -1) 2>/dev/null; sleep 3; echo RESTARTED\"}"
echo ""
echo "Done. Hard refresh your browser (Cmd+Shift+R) to see changes."
