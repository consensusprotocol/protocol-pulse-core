Read ~/protocol_pulse/templates/stage.html lines 1720-1810 (mic button and stopRec function).
Read ~/protocol_pulse/templates/stage.html lines 1480-1560 (playBroadcastItem function).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE BROADCAST INTERRUPT — INTELLIGENT VOICE RESPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The lightning bolt "TAP TO SPEAK" button currently exists but does NOT
interrupt the broadcast or respond intelligently. Build this system:

DESIRED BEHAVIOR:
1. User taps ⚡ during broadcast → broadcast PAUSES
2. Satomi shows "Listening..." state visually
3. User speaks their question
4. User taps again (or 3s silence) → sends to intelligence layer
5. Satomi queries live data + generates spoken response (~5-10s)
6. Satomi responds to the specific question via TTS + avatar
7. After response: "Did that answer your question? Tap to continue broadcast."
8. After 4s of no response (or user confirms): broadcast RESUMES from where it stopped

IMPLEMENTATION:

In stage.html, find the lightning bolt button (around line 1723-1738).
Currently it calls _startStageMic() but does nothing with the response.

STEP 1: Add broadcast pause/resume logic
  Add these variables near the top of the script:
    var _broadcastPaused = false;
    var _broadcastResumeCallback = null;
    var _currentBroadcastItem = null;  // track what's playing

  In playBroadcastItem(), save a reference to current item:
    _currentBroadcastItem = item;

  Add pauseBroadcast() function:
    function pauseBroadcast() {
      _broadcastPaused = true;
      // Pause the video element
      var v = document.getElementById('stageVideo') || document.querySelector('video');
      if (v) { v.pause(); _broadcastResumePosition = v.currentTime; }
      setStatus('Listening — tap to ask Satomi', '#F8C15C', false);
      updateSignalSource('🎤 INTERRUPT');
    }
  
  Add resumeBroadcast() function:
    function resumeBroadcast() {
      _broadcastPaused = false;
      var v = document.getElementById('stageVideo') || document.querySelector('video');
      if (v && _broadcastResumePosition > 0) {
        v.currentTime = _broadcastResumePosition;
        v.play().catch(function(){});
      }
      setStatus('Resuming broadcast', 'rgba(255,255,255,.4)', false);
      updateSignalSource('📡 BROADCASTING');
      _broadcastResumePosition = 0;
    }

STEP 2: Wire the mic button to interrupt mode
  When the mic button is tapped DURING broadcast (check if video is playing):
    function toggleInterruptMic() {
      var v = document.querySelector('video');
      var isPlaying = v && !v.paused && !v.ended;
      if (isPlaying || _broadcastPaused) {
        // INTERRUPT MODE
        if (!_stageIsRec) {
          pauseBroadcast();
          _startStageMic();
        } else {
          _stopStageMic();
          // will process in onend
        }
      } else {
        // Normal mode when broadcast not active
        toggleMicNormal();
      }
    }

STEP 3: Handle the spoken input with real intelligence
  After mic captures text, instead of discarding it:
  
  async function processInterruptQuery(text) {
    if (!text || !text.trim()) { resumeBroadcast(); return; }
    
    setStatus('Satomi is thinking...', '#F8C15C', true);
    
    // Show thinking video
    var vid = document.getElementById('stageVideo') || document.querySelector('video');
    
    try {
      // Query the oracle/intelligence endpoint with the question
      var resp = await fetch('/api/oracle/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          query: text,
          context: _currentBroadcastTopic || 'Bitcoin market intelligence',
          mode: 'stage_interrupt'
        })
      });
      
      if (!resp.ok) throw new Error('Query failed');
      var data = await resp.json();
      var answer = data.response || 'I need a moment to process that signal.';
      
      // Generate TTS for the response
      var ttsResp = await fetch('https://avatar.protocolpulse.io/oracle/voice', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: answer})
      });
      
      if (ttsResp.ok) {
        var blob = await ttsResp.blob();
        var audioUrl = URL.createObjectURL(blob);
        var audio = new Audio(audioUrl);
        
        setStatus(answer.substring(0, 80) + '...', '#F8C15C', false);
        
        audio.onended = function() {
          // After response, offer to continue
          setStatus('Did that answer your question? Continuing in 4s...', 'rgba(255,255,255,.5)', false);
          setTimeout(function() {
            resumeBroadcast();
          }, 4000);
        };
        audio.play();
      } else {
        // Fallback: just resume
        resumeBroadcast();
      }
    } catch(err) {
      console.warn('[Interrupt] query failed:', err);
      resumeBroadcast();
    }
  }

STEP 4: Add /api/oracle/query route to core/routes.py
  This route takes a question, fetches live BTC data, queries Claude Haiku,
  returns a concise spoken answer (max 2 sentences, 150 chars):
  
  @app.route('/api/oracle/query', methods=['POST'])
  def api_oracle_query():
      from flask import request, jsonify
      data = request.get_json() or {}
      query = data.get('query', '')[:200]
      context = data.get('context', 'Bitcoin')
      
      if not query:
          return jsonify({'response': 'I did not catch that. Stay sovereign.'}), 200
      
      try:
          import anthropic
          client = anthropic.Anthropic()
          
          # Get live BTC price for context
          btc_price = 'unknown'
          try:
              import requests as rq
              r = rq.get('https://api.coinbase.com/v2/prices/BTC-USD/spot', timeout=3)
              if r.ok:
                  btc_price = '$' + r.json()['data']['amount']
          except:
              pass
          
          msg = client.messages.create(
              model='claude-haiku-4-5',
              max_tokens=150,
              messages=[{
                  'role': 'user',
                  'content': f'''You are Satomi, Protocol Pulse's live Bitcoin intelligence anchor.
Current BTC price: {btc_price}. Context: {context}.
Answer this question in 1-2 concise sentences max (under 150 chars). 
Be direct, insightful, and stay in character as a sharp Bitcoin analyst.
Question: {query}'''
              }]
          )
          response_text = msg.content[0].text.strip()
          return jsonify({'response': response_text})
      except Exception as e:
          return jsonify({'response': f'Signal unclear. Current context: {context}. Stay sovereign.'}), 200

STEP 5: Visual feedback
  During interrupt mode, show a subtle visual indicator on the stage:
  - The stage container gets a gold border pulse animation
  - Status bar shows "⚡ INTERRUPT MODE"
  - After response: "▶ RESUMING BROADCAST"

WIRING:
  Replace the current mic button onclick to call toggleInterruptMic()
  In _stopStageMic onend handler, call processInterruptQuery(pending) 
  instead of discarding the text

VERIFY:
  - Stage still broadcasts normally when mic not used
  - Tapping mic during broadcast pauses video
  - Question is sent to /api/oracle/query
  - Response plays as audio
  - Broadcast resumes after 4s

COMMIT:
  git add templates/stage.html core/routes.py
  git commit -m "feat(stage): broadcast interrupt — tap to ask Satomi, real-time response, auto-resume"
  git push
