# CROSS-LLM AUDIT: F-VISION-4 MULTI-IMAGE PROGRESSIVE GUIDANCE

## Code Under Review
File: templates/oracle_live.html
Functions: sendVisionImage, _visionSessionId handling, camera button UX

## Self-Audit Findings

### Q1: _visionSessionId persistence
YES — correctly persists. Set at line 1575 after first vision response. Cleared only
on transcript CLEAR (line 1680). Follow-up photos correctly route to /vision/guide.

### Q2: Context passed to vision/guide
PARTIAL — session_id is sent, and GuideSession has full conversation history in memory.
However, no last_context is sent from client side. The GuideSession.send_image already
has the history, so Gemini sees prior turns. But adding explicit last_context would help
if session expired or for robustness.

### Q3: No UI feedback for follow-up photo
CONFIRMED GAP — After Oracle finishes speaking, there's no prompt telling user to
take another photo. User has no idea multi-turn is supported.

### Q4: Camera button never changes label
CONFIRMED GAP — Button shows "SHOW ORACLE" always. No visual distinction between
first-use and follow-up mode.

### Q5: Accidental new session
LOW RISK — _visionSessionId correctly gates the endpoint selection. But if busy=true,
the tap just fires and gets rejected by the endpoint, not by UI guard.

### Q6: Transcript context
OK — _addVisionEntry stores steps and guidance. Could be passed as last_context.

### Q7: Mid-speech camera tap
NO GUARD — handleVisionUpload has no busy check. Could fire mid-speech.

### Q8: Overall UX rating: 4/10
Highest-impact fix: Post-guidance camera prompt + camera button label change

## P0 Issues
- No busy guard in handleVisionUpload (could fire mid-speech)

## P1 Issues
- Camera button label never changes to "FOLLOW-UP PHOTO"
- No post-guidance prompt for next photo
- No last_context injection in sendVisionImage body
