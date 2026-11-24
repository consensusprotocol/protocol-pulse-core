#!/usr/bin/env bash
# scripts/integrator/launch_pin.sh PIN.json SEAL_PREFIX NAME -- the integrator's one way to render a builder's sealed pin.
# (It replaces a scratch copy outside git: the acceptance test of 08:50 ET Nov 24, item 1.) Stops at the first refusal.
#   1. yield GPU0: /tmp/pulse_gpu0.yield, and wait (<= 240 s) until nothing holds the GPU0 lease
#   2. freeze: the pin is copied to data/moments_pins/NAME.json, the file the render reads
#   3. readiness: scripts/integrator/check_pin_only.py on the frozen copy and the READY line's seal prefix (the builder's
#      gates and seal, ruling 76's 12 hours on this clock, at most 3 kinds); scripts/pulse_check_run.sh checks it again
#   4. launch: scripts/pulse_check_run.sh --pinned (a detached tmux session; its own preflight, lock and GPU0 lease)
#   5. the yield flag is released once the render holds the lease (or at any refusal)
set -u
[ $# -eq 3 ] || { echo "usage: $0 PIN.json SEAL_PREFIX NAME" >&2; exit 64; }
PIN="$1"; SEAL="$2"; NAME="$3"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO" || exit 1
release() { rm -f /tmp/pulse_gpu0.yield; }
echo "== 1. yield GPU0 ($(date '+%H:%M:%S ET'))"
touch /tmp/pulse_gpu0.yield
for i in $(seq 1 120); do
  [ "$(fuser /tmp/pulse_gpu0.lease 2>/dev/null | wc -w)" = 0 ] && break
  sleep 2
done
if [ "$(fuser /tmp/pulse_gpu0.lease 2>/dev/null | wc -w)" != 0 ]; then
  echo "REFUSED: the GPU0 lease is still held: $(cat /tmp/pulse_gpu0.lease 2>/dev/null)"; release; exit 1
fi
echo "== 2. freeze: data/moments_pins/$NAME.json"
cp "$PIN" "data/moments_pins/$NAME.json" || { release; exit 1; }
echo "== 3. readiness"
python3 -B scripts/integrator/check_pin_only.py "data/moments_pins/$NAME.json" "$SEAL" || {
  echo "REFUSED: check_pin_only"; release; exit 1; }
echo "== 4. launch"
env -u TMUX bash scripts/pulse_check_run.sh --pinned "data/moments_pins/$NAME.json" || {
  echo "REFUSED: the launcher"; release; exit 1; }
echo "== 5. release the yield flag once the render holds the lease"
for i in $(seq 1 60); do
  grep -q "pulse_check_run" /tmp/pulse_gpu0.lease 2>/dev/null && [ "$(fuser /tmp/pulse_gpu0.lease 2>/dev/null | wc -w)" != 0 ] && break
  sleep 2
done
release
echo "   lease: $(cat /tmp/pulse_gpu0.lease 2>/dev/null)"
ls -t logs/pulse_check/ | head -1
