Read PIPELINE_LAWS.md, then read these files completely before writing a single line of code:
- oracle/avatar_server.py
- oracle/face_enhancer.py
- oracle/model_registry.py
- oracle/blink_engine.py
- oracle/vision_guide.py (if exists)

NEW LAW: Fix entirely and verify live before moving on. Do not commit until live test passes.

## CURRENT STATE (verified right now)
- Avatar process was just killed (was at 173s latency — unacceptable)
- Previous CC session committed code but GFPGAN was still loading in logs
- vision_enabled: True, /vision/analyze and /vision/guide endpoints exist
- vision_guide.py exists with Bitcoin hardware analysis capability

## TASK 1: GFPGAN — FULLY REMOVE IT
Search every file in oracle/ for gfpgan references:
  grep -rn "gfpgan\|GFPGAN\|face_enhancer\|enhance_frames" oracle/

For EVERY file that imports or uses GFPGAN:
- Comment out the import
- Replace enhance_frames_batch() body with: return frames
- Remove any gfpgan model loading from model_registry.py
- Replace with ONLY sharpen_mouth_region() CV2 bilateral filter

Verify zero GFPGAN references remain:
  grep -rni "gfpgan" oracle/ -- must return nothing

## TASK 2: FIX THE 503 BUSY LOCK
The Flask server is returning 503 under concurrent load. Find the threading lock in generate endpoint.
- Add lock acquisition timeout of 10s: if not lock.acquire(timeout=10): return jsonify({"error":"busy"}), 503
- Add Flask app.run(threaded=True) if not already set
- Ensure the lock is always released in a finally block

## TASK 3: WIRE VISION INTO ORACLE PAGE
The vision endpoints exist but check if oracle.html actually uses them.
  grep -n "vision\|analyze\|guide\|camera\|upload\|image" templates/oracle.html | head -20

The Oracle page should have:
- A "Show your device" button that opens camera/file picker
- Sends image to /vision/analyze
- Oracle responds with spoken guidance via /generate
- If vision_guide.py already has Bitcoin device knowledge, ensure it covers:
  * Coldcard setup and navigation
  * Ledger setup
  * Trezor setup  
  * Casa node setup
  * Umbrel node setup
  * Bitcoin Core wallet setup
  * Mining rig configuration (ASIC basics)
  * Hardware wallet seed phrase backup
  * Multisig setup walkthrough

Add any missing devices to vision_guide.py's knowledge base. Keep it factual and security-focused.

## TASK 4: RESTART AND VERIFY LIVE (mandatory, no exceptions)
1. Start server: cd ~/protocol_pulse/oracle && nohup python3 avatar_server.py > logs/avatar_server.log 2>&1 &
2. Wait 25s for model load
3. Check GFPGAN in logs: grep -i gfpgan logs/avatar_server.log -- must be EMPTY
4. Health check: curl http://localhost:8200/health -- requests_tracked must be 0 (fresh start)
5. Timed generate test:
   START=$(date +%s)
   curl -s -X POST http://localhost:8200/generate -H 'Content-Type: application/json' -d '{"text":"Stack sats every day. Bitcoin is freedom."}' -o /tmp/avatar_v1.mp4
   END=$(date +%s)
   echo "Time: $((END-START))s"
   ls -lh /tmp/avatar_v1.mp4
6. Must be: under 15s, file >50KB, valid mp4
7. Run a SECOND test immediately after to confirm no 503:
   curl -s -o /dev/null -w "HTTP:%{http_code}" -X POST http://localhost:8200/generate -H 'Content-Type: application/json' -d '{"text":"Bitcoin is the exit."}'
8. Test vision endpoint:
   curl -s http://localhost:8200/vision/status

## TASK 5: COMMIT ONLY AFTER ALL TESTS PASS
git add oracle/ templates/oracle.html && git commit -m "fix(avatar): remove GFPGAN fully, fix 503 lock, wire vision+Bitcoin device guide into Oracle page - VERIFIED LIVE" && git push

## TASK 6: REPORT
Output these exact numbers from your live test:
- Generate time (seconds)
- File size (bytes)
- HTTP code of second consecutive request
- GFPGAN lines in log (must be 0)
- Vision status endpoint response