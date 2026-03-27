Read ~/protocol_pulse/templates/stage.html FULLY.
Read ~/protocol_pulse/services/stage_broadcast_service.py lines 1-100 and 560-640 (symbol sanitizer area).
Read ~/protocol_pulse/PIPELINE_LAWS.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE AVATAR — 6 TARGETED FIXES (surgical, no regressions)
SNAPSHOT TAG: stage-avatar-working-v1 at fa684484 — DO NOT break this baseline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — REMOVE CAMERA BUTTON FROM STAGE (keep in Oracle only)
In stage.html find the camera button block (around line 807-818):
  <button id="stage-cam-btn" onclick="handleStageCameraInterrupt()" ...>&#128247;</button>
  <input type="file" id="stage-cam-input" ...>
Remove BOTH elements completely. Also remove any camera-related
JS functions that are stage-specific (handleStageCameraInterrupt,
handleStageCameraUpload) if they exist only in stage.html.
Do NOT touch oracle_live.html camera code.

FIX 2 — SYMBOL SANITIZER for TTS scripts
The avatar is reading "*//*" as "asterisk slash asterisk slash".
In stage_broadcast_service.py, find _generate_script() or wherever
scripts are sent to TTS. Add a sanitize_for_tts() function:

def sanitize_for_tts(text):
    import re
    # Remove markdown symbols
    text = re.sub(r'\*+', '', text)        # asterisks
    text = re.sub(r'_+', ' ', text)        # underscores  
    text = re.sub(r'#+\s*', '', text)      # hash headers
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # markdown links
    text = re.sub(r'`+', '', text)         # backticks
    text = re.sub(r'~+', '', text)         # tildes
    text = re.sub(r'>{1,}', '', text)      # blockquotes
    text = re.sub(r'\|', ' ', text)        # pipes
    text = re.sub(r'\\+', ' ', text)       # backslashes
    # Clean up multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

Call sanitize_for_tts() on every script BEFORE it is sent to ElevenLabs.
Find where text is passed to the TTS call and wrap it.

Also add same sanitizer call in oracle/avatar_server.py before TTS:
Find where text is passed to ElevenLabs generate() and sanitize first.

FIX 3 — STAGE GOES BLACK AFTER BROADCAST (continuous loop fix)
Root cause: after vid.onended fires, startBroadcast() is called
but if queue is empty it has no fallback and goes silent/black.

In stage.html find startBroadcast() function.
After a broadcast ends (onended), if no new queue item is available:
  1. Show the "stage-wake" overlay with "TUNING SIGNAL..." 
  2. Poll /api/stage/consume-broadcast every 15 seconds
  3. When a new item arrives, immediately play it
  4. Do NOT leave a black silent screen — always show the overlay

Also fix: when user REFRESHES the page, if a broadcast was 
previously playing, the new page load should immediately call
consume-broadcast and start playing. The current code has
session memory that may block this.
Find any code that tracks "already played" state in sessionStorage
or window variables and ensure a page refresh always starts fresh.

FIX 4 — MOBILE VIDEO PLAYBACK
iOS Safari requires user interaction before video plays with audio.
The "TUNING SIGNAL..." overlay with the lightning bolt IS the tap-to-start.
The stage-wake overlay click calls stageWake() which should unlock audio.

Find stageWake() and ensure it:
  1. Sets window._stageAudioUnlocked = true
  2. Calls a silent audio unlock trick before playing the real video:
     var unlock = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==");
     unlock.volume = 0.001;
     unlock.play().catch(function(){});
  3. Then immediately calls startBroadcast()

Also ensure the video element has these attributes:
  playsinline webkit-playsinline muted (initially) preload="auto"
The muted attribute is required for iOS autoplay. Then unmute after canplay.

FIX 5 — STAGE BROADCAST RESTARTS AFTER USER INTERACTION
When user refreshes: page should show overlay → user taps → plays immediately.
When broadcast ends naturally: show "Next briefing in Xs" countdown
then auto-fetch next item.

In the onended handler, after the video finishes:
  - Show the stage-wake overlay
  - Display a message: "Stand by — next signal incoming"
  - After 3 seconds, call startBroadcast() to fetch next item
  - If nothing in queue, poll every 15s and update overlay text

FIX 6 — ORACLE VIDEO ERROR / BLACK FLASH ON MOBILE
In oracle_live.html find the video error handler (line ~1325):
  vid.onerror = function() { ... }
When video fails, instead of going black, show the thinking video again
and retry the fetch once after 2 seconds.

Also the black flash during voice input:
Find where the video src is cleared when mic is activating.
Do NOT clear vid.src during mic recording — keep last frame frozen.
Instead just pause the video but keep the src.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION (run all before committing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/stage — must be 200
  grep -c "stage-cam-btn" ~/protocol_pulse/templates/stage.html — must be 0
  curl -s --max-time 5 http://localhost:5000/api/stage/consume-broadcast | python3 -m json.tool | grep video_url
  kill -HUP $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1)
  
COMMIT:
  git add templates/stage.html templates/oracle_live.html services/stage_broadcast_service.py oracle/avatar_server.py
  git commit -m "fix(stage+oracle): remove camera from stage, symbol sanitizer, continuous loop, mobile audio unlock, video error recovery"
  git push
