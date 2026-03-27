Read PIPELINE_LAWS.md. Then read templates/oracle_live.html in full.
Then run the cross-LLM audit via utils/cross_llm_audit.py on templates/oracle_live.html

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE FIX — DEDICATED CC + LLM AUDIT
Root cause: After greeting plays, user speaks, but process() never fires.
Server log confirms: /oracle/chat is NEVER received after greeting ends.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KNOWN DIAGNOSTIC FACTS:
1. Greeting video plays fine with lip sync (716KB cached MP4 served from /tmp)
2. After greeting, server receives NO /oracle/chat or /oracle/speak requests
3. The JS chain: playIntent('GREETING') → fetchTO /oracle/speak → playVid(url) → .then() → startRec()
4. playVid() returns a Promise that resolves on vid.onended
5. ON MOBILE (iOS Safari): vid.onended does NOT always fire reliably
   If onended never fires → .then() never fires → startRec() never called → mic dead → busy=true forever
6. .finally() fires setBusy(false) and setOracleState('LISTENING') — but only if the Promise chain completes
7. If playVid() Promise never resolves, the entire chain hangs with busy=true

LLM AUDIT QUESTIONS (8 brutal questions for Gemini + GPT-4o + Grok):
1. In the playIntent() flow, what happens if playVid() Promise never resolves on iOS Safari?
2. How does iOS Safari handle autoplay for blob: URLs — does onended fire reliably?
3. Is there a race between .then() (startRec 400ms timer) and .finally() (setBusy false) that could prevent mic activation?
4. After greeting ends and mic starts, what exact conditions cause process() to not fire even if user speaks?
5. The recognition.onend handler: if recognition fires onend with no final results (empty pending), what happens?
6. Could the busy flag ever be true when the user speaks their response, causing process() to return early?
7. What is the most reliable way to activate microphone AFTER a video plays on iOS Safari mobile browser?
8. Is there any iOS-specific issue with SpeechRecognition.start() being called inside a Promise chain vs directly from a user gesture?

AFTER AUDIT — IMPLEMENT THESE FIXES:

FIX 1 (CRITICAL): Make playVid() always resolve, never hang
In the playVid() function, add a safety timeout:
- If vid.onended hasn't fired within (duration + 3 seconds), resolve the Promise anyway
- Also listen for vid.ended property as a fallback
- Add: vid.ontimeupdate to detect when video reaches end manually

FIX 2 (CRITICAL): Don't depend on Promise chain for mic activation  
Move startRec() OUT of the .then() callback and INTO a separate mechanism:
- After greeting video STARTS playing (not ends), start a timer for (estimated_duration + 500ms)
- When timer fires, if _greeted and !busy and !isRec: call startRec()
- This is independent of the Promise chain

FIX 3: Add explicit busy=false before startRec in greeting handler
Current code checks `if(!busy&&!isRec&&mic)` but busy may still be true if .finally() hasn't run yet
Fix: call setBusy(false) explicitly inside the greeting .then() BEFORE the setTimeout

FIX 4: Add fallback mic activation on user tap anywhere
If greeting played but mic never activated (isRec=false, _greeted=true, !busy):
- Any tap on the screen should call startRec()
- Add a one-time tap handler on the stage div

FIX 5: iOS autoplay workaround for greeting video
On iOS, blob: URL videos require user gesture for audio. Greeting may play silently.
If video plays silently and never fires onended, add: vid.muted=false after play() succeeds.
Also add an explicit play button overlay if autoplay is blocked.

FIX 6: Add console.log breadcrumbs throughout the flow
Add console.log at: playIntent called, video started, video ended, startRec called, 
recognition started, onresult fired, pending set, onend fired, process called.
This will confirm the exact breakpoint on next test.

FIX 7: Persistent greeting cache
The greeting cache keeps reverting to /tmp. Permanently fix:
- In avatar_server.py, change _GREETING_CACHE_PATH to /home/ultron/protocol_pulse/oracle/cache/satomi_greeting_cache.mp4
- Copy existing /tmp/satomi_greeting_cache.mp4 to persistent path
- Restart oracle server

AFTER IMPLEMENTING ALL FIXES:
1. Run regression: bash regression_test.sh — must show 0 FAILs (skip if unrelated)
2. Test oracle/speak endpoint: curl -s -X POST http://localhost:8200/oracle/speak -H "Content-Type: application/json" -d '{"intent":"GREETING"}' | file -
3. Test oracle/chat: python3 -c "import requests; r=requests.post('http://localhost:8200/oracle/chat', json={'text':'daily brief','session_id':'test','visitor_token':'anon','audio_first':True,'avatar_source':'oracle_studio','page_context':{'type':'oracle'}}); print(r.status_code, r.json().get('job_id'))"
4. git add templates/oracle_live.html oracle/avatar_server.py && git commit -m "fix(oracle): iOS video onended race, mic activation after greeting, persistent cache" && git push
