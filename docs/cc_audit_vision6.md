# CROSS-LLM AUDIT: F-VISION-6 VISION FOR STAGE (PHOTO INTERRUPT)

## Code Under Review
File: templates/stage.html
Functions: _handleInterruptQuestion, _broadcastPaused, runMonologueLoop, stageWake

## Self-Audit Findings

### Q1: How does _handleInterruptQuestion pause/resume?
_broadcastPaused = true is set in _startStageMic (line 1675).
After response plays, _showResumeCountdown → _resumeBroadcast sets
_broadcastPaused = false and calls startBroadcast().

### Q2: Clean "broadcast paused" state?
YES — _broadcastPaused flag. runMonologueLoop while loop checks it.
Camera interrupt can set it the same way.

### Q3: Interrupt latency?
Mic interrupt: speech recognition + /api/oracle/chat + avatar render.
Camera: file upload + vision/analyze (~3-5s) + /oracle/voice (~1s).
Camera should be faster since no avatar render needed for stage.

### Q4: Existing camera elements?
NONE — stage.html has no camera/file input elements.

### Q5: What restarts broadcast?
_resumeBroadcast() sets _broadcastPaused = false and calls startBroadcast()
→ runMonologueLoop(). _loopRunning is reset in finally block (line 2081).

### Q6: Where to inject camera button?
Next to floatingMicBtn (line 792) — bottom-right overlay on avatar.

### Q7: Camera + speech conflict?
Possible if both fire simultaneously. Busy guard prevents this.

### Q8: Minimum viable camera interrupt?
File input + vision/analyze + TTS voice + play audio + resume broadcast.
No avatar render needed — just voice response.

## P0 Issues
- None — _loopRunning is properly reset in finally block (line 2081)

## P1 Issues
- Need camera button + file input added to stage HTML
- Need handleStageCameraInterrupt + handleStageCameraUpload functions
- Need busy guard on camera
