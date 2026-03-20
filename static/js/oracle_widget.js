/**
 * PROTOCOL PULSE — ORACLE AMBIENT COMPANION WIDGET v4 (Production Ship)
 * =====================================================================
 * Site-wide floating Oracle bubble. Chat via /api/oracle/chat.
 * Mobile bottom sheet, nudge tooltips, recommendation cards,
 * full a11y, analytics wired.
 *
 * Replaces v2 iframe-based widget entirely.
 * Zero external dependencies. Self-contained.
 */
(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────────────────
  var AVATAR_IMG       = '/static/oracle_avatar.png';
  var AVATAR_IDLE_VID  = '/static/img/oracle_avatar_idle.mp4';
  var SKIP_PATHS       = ['/oracle-live', '/oracle', '/admin', '/internal', '/login', '/signup', '/stage'];
  var BUBBLE_DELAY     = 3500;
  var NUDGE_DELAY      = 12000;
  var SESSION_CAP      = 20;
  var SEND_COOLDOWN    = 3000;
  var JOB_POLL_MS      = 1500;
  var JOB_POLL_TIMEOUT = 15000;

  // ── Skip on excluded paths ────────────────────────────────────────────
  var currentPath = window.location.pathname;
  for (var i = 0; i < SKIP_PATHS.length; i++) {
    if (currentPath.indexOf(SKIP_PATHS[i]) === 0) return;
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function ss(key, val) {
    try {
      if (val === undefined) return sessionStorage.getItem('ow_' + key);
      if (val === null) { sessionStorage.removeItem('ow_' + key); return; }
      sessionStorage.setItem('ow_' + key, val);
    } catch (e) { return null; }
  }

  function getMeta(name) {
    var el = document.querySelector('meta[property="' + name + '"],meta[name="' + name + '"]');
    return el ? (el.getAttribute('content') || '').trim() : '';
  }

  function el(tag, id, attrs) {
    var e = document.createElement(tag);
    if (id) e.id = id;
    if (attrs) { for (var k in attrs) { if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]); } }
    return e;
  }

  function isMobile() { return window.innerWidth <= 768; }

  function track(event, props) {
    try {
      fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: event, properties: props || {} })
      }).catch(function () {});
    } catch (e) {}
  }

  // ── Page context ──────────────────────────────────────────────────────
  function getPageContext() {
    var ctx = { url: window.location.href, path: currentPath, pageType: 'general', title: document.title || '', content: null };
    var ogTitle = getMeta('og:title') || getMeta('twitter:title') || '';
    var ogDesc = getMeta('og:description') || getMeta('twitter:description') || '';
    var section = getMeta('article:section') || '';

    if (currentPath.match(/^\/article(s)?\/\d+/)) {
      ctx.pageType = 'article';
      ctx.content = (ogTitle ? 'Article: ' + ogTitle + '. ' : '') + (ogDesc ? 'Summary: ' + ogDesc + '. ' : '') + (section ? 'Category: ' + section + '.' : '');
      ctx.category = section;
      ctx.articleTitle = ogTitle;
    } else if (currentPath === '/' || currentPath === '') {
      ctx.pageType = 'homepage';
    } else if (currentPath.indexOf('/articles') === 0) {
      ctx.pageType = 'index';
    } else if (currentPath.indexOf('/podcast') === 0) {
      ctx.pageType = 'podcast';
    } else if (currentPath.indexOf('/terminal') === 0) {
      ctx.pageType = 'terminal';
    } else if (currentPath.indexOf('/mining') === 0) {
      ctx.pageType = 'mining';
    } else if (currentPath.indexOf('/charts') === 0) {
      ctx.pageType = 'charts';
    }
    return ctx;
  }

  // ── State ─────────────────────────────────────────────────────────────
  var _open = false;
  var _processing = false;
  var _history = [];
  var _pageCtx = getPageContext();
  var _fingerprint = ss('fp') || '';
  var _sessionId = ss('sid') || ('s_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7));
  var _pendingNudge = null;
  var _tooltipEl = null;
  var _lastSendTime = 0;
  var _isMomentumScrolling = false;
  var _momentumTimer = null;
  var _touchStartY = 0;
  var _msgCount = parseInt(ss('msg_count') || '0', 10);
  var _recoLoaded = false;
  var _currentTier = 2;   // detected before each send
  var _jobPollTimer = null;
  ss('sid', _sessionId);

  // ── Audio context (lazy) ──────────────────────────────────────────────
  var _audioCtx = null;
  function getAudioCtx() {
    if (!_audioCtx) { _audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
    return _audioCtx;
  }

  // ── Build DOM ─────────────────────────────────────────────────────────

  // Widget container
  var widget = el('div', 'oracle-widget', { 'role': 'complementary', 'aria-label': 'Oracle AI Guide' });

  // Backdrop (desktop only)
  var bd = el('div', 'ow-bd');
  widget.appendChild(bd);

  // Mobile overlay
  var mobileOverlay = el('div', 'ow-mobile-overlay');
  widget.appendChild(mobileOverlay);

  // Panel
  var panel = el('div', 'ow-panel', { 'role': 'dialog', 'aria-labelledby': 'ow-panel-title', 'aria-modal': 'false' });
  panel.innerHTML =
    '<div class="oracle-sheet-handle"></div>' +
    '<div id="ow-hdr">' +
      '<h2 id="ow-panel-title">Oracle</h2>' +
      '<span id="ow-hdr-ctx"></span>' +
      '<div style="display:flex;gap:6px;align-items:center">' +
        '<button class="ow-btn" id="ow-close-btn" aria-label="Close Oracle panel">' +
          '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">' +
            '<line x1="1" y1="1" x2="9" y2="9" stroke="rgba(220,38,38,.7)" stroke-width="1.5" stroke-linecap="round"/>' +
            '<line x1="9" y1="1" x2="1" y2="9" stroke="rgba(220,38,38,.7)" stroke-width="1.5" stroke-linecap="round"/>' +
          '</svg>' +
        '</button>' +
      '</div>' +
    '</div>' +
    '<div id="ow-reco"></div>' +
    '<div id="ow-messages" aria-live="polite" aria-atomic="false" aria-relevant="additions">' +
      '<div class="ow-msg ow-msg-oracle">Ask me about Bitcoin.</div>' +
    '</div>' +
    '<div id="ow-typing" class="ow-hidden" aria-hidden="true"><span></span><span></span><span></span></div>' +
    '<div id="ow-limit-banner" style="display:none"></div>' +
    '<div id="ow-input-area">' +
      '<input type="text" id="ow-input" placeholder="Ask The Oracle..." maxlength="500" aria-label="Message the Oracle" autocomplete="off">' +
      '<button id="ow-send" aria-label="Send message">&#x27A4;</button>' +
    '</div>';
  widget.appendChild(panel);

  // Bubble (button for a11y)
  var bubble = document.createElement('button');
  bubble.id = 'ow-bubble';
  bubble.setAttribute('aria-label', 'Open Oracle AI Guide');
  bubble.setAttribute('aria-expanded', 'false');
  bubble.setAttribute('aria-haspopup', 'dialog');
  bubble.style.display = 'none';

  // Idle video loop in bubble (Tier 1 avatar preview)
  var bubbleVideo = document.createElement('video');
  bubbleVideo.src = AVATAR_IDLE_VID;
  bubbleVideo.loop = true;
  bubbleVideo.autoplay = true;
  bubbleVideo.muted = true;
  bubbleVideo.playsInline = true;
  bubbleVideo.setAttribute('playsinline', '');
  bubbleVideo.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%;pointer-events:none;';
  bubbleVideo.onerror = function () {
    // Fall back to static image if idle video fails
    bubbleVideo.style.display = 'none';
    var fallbackImg = document.createElement('img');
    fallbackImg.src = AVATAR_IMG;
    fallbackImg.alt = 'Oracle';
    fallbackImg.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%;pointer-events:none;';
    bubble.appendChild(fallbackImg);
  };
  bubble.appendChild(bubbleVideo);
  widget.appendChild(bubble);

  // Inject into page
  document.body.appendChild(widget);

  // Cache DOM refs
  var msgs = document.getElementById('ow-messages');
  var hdrCtx = document.getElementById('ow-hdr-ctx');
  var inputEl = document.getElementById('ow-input');
  var sendBtn = document.getElementById('ow-send');
  var typingEl = document.getElementById('ow-typing');
  var recoEl = document.getElementById('ow-reco');
  var limitBanner = document.getElementById('ow-limit-banner');
  var closeBtn = document.getElementById('ow-close-btn');

  // ── Event bindings (no inline handlers) ───────────────────────────────
  bd.addEventListener('click', closePanel);
  mobileOverlay.addEventListener('click', closePanel);
  closeBtn.addEventListener('click', closePanel);
  bubble.addEventListener('click', onBubbleClick);
  sendBtn.addEventListener('click', doSend);
  inputEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); doSend(); } });

  // ESC closes panel
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && _open) {
      closePanel();
      bubble.focus();
    }
  });

  // Tab trap inside open panel
  panel.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab' || !_open) return;
    var focusable = panel.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])');
    if (focusable.length === 0) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) { e.preventDefault(); last.focus(); }
    } else {
      if (document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // ── Momentum scroll detection ─────────────────────────────────────────
  var _lastTouchY = 0;
  document.addEventListener('touchmove', function (e) {
    var touch = e.touches[0];
    if (touch) {
      var velocity = Math.abs(touch.clientY - _lastTouchY);
      _lastTouchY = touch.clientY;
      if (velocity > 50) {
        _isMomentumScrolling = true;
        clearTimeout(_momentumTimer);
        _momentumTimer = setTimeout(function () { _isMomentumScrolling = false; }, 200);
      }
    }
  }, { passive: true });

  // ── Swipe-to-dismiss (mobile panel) ───────────────────────────────────
  panel.addEventListener('touchstart', function (e) {
    _touchStartY = e.touches[0].clientY;
  }, { passive: true });

  panel.addEventListener('touchmove', function (e) {
    if (!_open || !isMobile()) return;
    // Only allow swipe from header/handle area (top 60px)
    var touch = e.touches[0];
    if (_touchStartY < 60 || (touch.clientY - _touchStartY) < 0) return;
    if ((touch.clientY - _touchStartY) > 80) {
      closePanel();
    }
  }, { passive: true });

  // ── Show bubble after delay ───────────────────────────────────────────
  setTimeout(function () {
    bubble.style.display = 'flex';
    bubble.classList.add('ow-pulsing');

    var hasFingerprint = !!_fingerprint;
    track('oracle_initialized', { tier: 1, has_fingerprint_match: hasFingerprint });

    // Nudge logic — only on article pages for return visitors
    if (_pageCtx.pageType === 'article' && hasFingerprint && ss('tooltip_dismissed') !== '1') {
      setTimeout(function () {
        if (_isMomentumScrolling || _open) return;
        fetchNudge();
      }, NUDGE_DELAY);
    }
  }, BUBBLE_DELAY);

  // ── Nudge fetch ───────────────────────────────────────────────────────
  function fetchNudge() {
    fetch('/oracle/nudge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        page_context: {
          title: _pageCtx.articleTitle || _pageCtx.title,
          category: _pageCtx.category || '',
          tags: [],
          slug: currentPath.split('/').pop() || ''
        },
        fingerprint: _fingerprint,
        trigger_type: 'dwell'
      })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.nudge) {
        _pendingNudge = data.nudge;
        showTooltip(data.nudge);
        track('oracle_triggered', { trigger_type: 'dwell', page_type: _pageCtx.pageType, nudge_shown: true });
        track('oracle_tooltip_shown', { nudge_first_5_words: data.nudge.split(' ').slice(0, 5).join(' ') });
      }
    })
    .catch(function () {});
  }

  // ── Tooltip ───────────────────────────────────────────────────────────
  function showTooltip(text) {
    removeTooltip();
    _tooltipEl = document.createElement('div');
    _tooltipEl.className = 'oracle-tooltip';
    _tooltipEl.setAttribute('role', 'status');
    _tooltipEl.innerHTML = '<span class="oracle-tooltip__text"></span><button class="oracle-tooltip__dismiss" aria-label="Dismiss">\u2715</button>';
    _tooltipEl.querySelector('.oracle-tooltip__text').textContent = text;
    _tooltipEl.querySelector('.oracle-tooltip__dismiss').addEventListener('click', function () {
      removeTooltip();
      ss('tooltip_dismissed', '1');
      track('oracle_tooltip_dismissed', {});
    });
    widget.appendChild(_tooltipEl);
  }

  function removeTooltip() {
    if (_tooltipEl && _tooltipEl.parentNode) {
      _tooltipEl.parentNode.removeChild(_tooltipEl);
    }
    _tooltipEl = null;
  }

  // ── Bubble click ──────────────────────────────────────────────────────
  function onBubbleClick() {
    var source = _tooltipEl ? 'tooltip_click' : 'avatar_click';
    removeTooltip();
    track('oracle_opened', { source: source, page_type: _pageCtx.pageType });
    window.location.href = '/oracle-live';
  }

  // ── Open panel ────────────────────────────────────────────────────────
  function openPanel() {
    _open = true;
    bubble.setAttribute('aria-expanded', 'true');

    // Update context label
    var ctxLabel = getCtxLabel();
    hdrCtx.textContent = ctxLabel;

    if (isMobile()) {
      mobileOverlay.classList.add('ow-overlay-active');
      document.body.style.overflow = 'hidden';
    } else {
      bd.style.display = 'block';
      requestAnimationFrame(function () { bd.classList.add('ow-on'); });
    }

    panel.style.display = 'flex';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        panel.classList.add('ow-on');
      });
    });

    // Focus input after animation
    setTimeout(function () { inputEl.focus(); }, 100);

    // Fetch recommendations on non-article pages
    if (!_recoLoaded && _pageCtx.pageType !== 'article') {
      fetchRecommendations();
    }
  }

  // ── Close panel ───────────────────────────────────────────────────────
  function closePanel() {
    _open = false;
    bubble.setAttribute('aria-expanded', 'false');
    panel.classList.remove('ow-on');
    bd.classList.remove('ow-on');
    mobileOverlay.classList.remove('ow-overlay-active');
    document.body.style.overflow = '';

    track('oracle_closed', { session_message_count: _msgCount });

    setTimeout(function () {
      panel.style.display = 'none';
      bd.style.display = 'none';
    }, 400);
  }

  // ── Context label ─────────────────────────────────────────────────────
  function getCtxLabel() {
    if (_pageCtx.pageType === 'article') {
      var t = getMeta('og:title');
      return t ? t.slice(0, 28) + (t.length > 28 ? '\u2026' : '') : 'article';
    }
    var labels = {
      terminal: 'Intel Terminal', mining: 'Mining Intel',
      charts: 'Charts', podcast: 'Podcasts',
      homepage: '', index: '', general: ''
    };
    return labels[_pageCtx.pageType] || '';
  }

  // ── Add message to chat ───────────────────────────────────────────────
  function addMsg(text, role) {
    var d = document.createElement('div');
    d.className = 'ow-msg ow-msg-' + role;
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
  }

  // ── Detect tier before sending ───────────────────────────────────────
  function detectTier(callback) {
    fetch('/oracle/status')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        _currentTier = d.recommended_tier || 2;
        callback(_currentTier);
      })
      .catch(function () {
        _currentTier = 2;
        callback(2);
      });
  }

  // ── Send message ──────────────────────────────────────────────────────
  function doSend() {
    if (_processing) return;

    var now = Date.now();
    if (now - _lastSendTime < SEND_COOLDOWN) return;

    var text = inputEl.value.trim();
    if (!text) return;

    // Session cap check
    if (_msgCount >= SESSION_CAP) {
      limitBanner.textContent = "You've reached the Oracle's session limit.";
      limitBanner.style.display = 'block';
      inputEl.disabled = true;
      sendBtn.disabled = true;
      return;
    }

    inputEl.value = '';
    _processing = true;
    _lastSendTime = now;
    sendBtn.disabled = true;

    addMsg(text, 'user');
    _history.push({ role: 'user', content: text });
    _msgCount++;
    ss('msg_count', String(_msgCount));

    // Hide recommendations after first message
    if (recoEl.children.length > 0) {
      recoEl.classList.add('ow-reco-hidden');
    }

    typingEl.classList.remove('ow-hidden');
    typingEl.setAttribute('aria-hidden', 'false');
    msgs.scrollTop = msgs.scrollHeight;

    var turnNumber = _msgCount;
    track('oracle_message_sent', { message_length: text.length, turn_number: turnNumber });

    var t0 = Date.now();

    // Detect tier, then send to appropriate endpoint
    detectTier(function (tier) {
      if (tier === 1) {
        sendTier1(text, t0, turnNumber);
      } else {
        sendTier2(text, t0, turnNumber);
      }
    });
  }

  // ── Tier 1: Avatar server (Chatterbox TTS + Wav2Lip) ─────────────────
  function sendTier1(text, t0, turnNumber) {
    fetch('/oracle/chat/tier1', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: _history.slice(-6),
        fingerprint: _fingerprint || _sessionId,
        page_context: { type: _pageCtx.pageType, path: _pageCtx.path }
      })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      typingEl.classList.add('ow-hidden');
      typingEl.setAttribute('aria-hidden', 'true');
      var latencyMs = Date.now() - t0;

      if (data.error) {
        addMsg('The Oracle is momentarily unavailable. Try again in a moment.', 'oracle');
        finishSend();
        return;
      }

      addMsg(data.response, 'oracle');
      _history.push({ role: 'assistant', content: data.response });
      saveFingerprint();

      var usedTier = data.tier || 2;
      var hasJobId = !!data.job_id;

      track('oracle_response_received', {
        latency_ms: latencyMs,
        has_audio: !!data.audio,
        has_video: hasJobId,
        tier_used: usedTier
      });

      if (hasJobId) {
        // Tier 1 path: poll for video
        pollForVideo(data.job_id, t0);
      } else if (data.audio) {
        // Tier 2 fallback with audio
        playAudio(data.audio);
        track('oracle_tier_fallback', { from_tier: 1, to_tier: 2, reason: 'no_job_id' });
        finishSend();
      } else {
        finishSend();
      }
    })
    .catch(function () {
      typingEl.classList.add('ow-hidden');
      typingEl.setAttribute('aria-hidden', 'true');
      addMsg('The Oracle is momentarily unavailable. Try again in a moment.', 'oracle');
      finishSend();
    });
  }

  // ── Tier 2: Claude + ElevenLabs audio ─────────────────────────────────
  function sendTier2(text, t0, turnNumber) {
    fetch('/api/oracle/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: _history.slice(-6) })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      typingEl.classList.add('ow-hidden');
      typingEl.setAttribute('aria-hidden', 'true');
      var latencyMs = Date.now() - t0;

      if (data.error) {
        addMsg('The Oracle is momentarily unavailable. Try again in a moment.', 'oracle');
      } else {
        addMsg(data.response, 'oracle');
        _history.push({ role: 'assistant', content: data.response });
        saveFingerprint();

        track('oracle_response_received', {
          latency_ms: latencyMs,
          has_audio: !!data.audio,
          has_video: false,
          tier_used: 2
        });

        if (data.audio) {
          playAudio(data.audio);
        }
      }
    })
    .catch(function () {
      typingEl.classList.add('ow-hidden');
      typingEl.setAttribute('aria-hidden', 'true');
      addMsg('The Oracle is momentarily unavailable. Try again in a moment.', 'oracle');
    })
    .finally(function () { finishSend(); });
  }

  function saveFingerprint() {
    if (!_fingerprint) {
      _fingerprint = _sessionId;
      ss('fp', _fingerprint);
    }
  }

  function finishSend() {
    _processing = false;
    setTimeout(function () { sendBtn.disabled = false; }, SEND_COOLDOWN);
  }

  // ── Video polling for Tier 1 ──────────────────────────────────────────
  function pollForVideo(jobId, startTime) {
    var pollStart = Date.now();

    function doPoll() {
      if (Date.now() - pollStart > JOB_POLL_TIMEOUT) {
        // Timeout — silent fallback, no video
        track('oracle_tier_fallback', { from_tier: 1, to_tier: 2, reason: 'poll_timeout' });
        finishSend();
        return;
      }

      fetch('/oracle/job/' + jobId)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'complete' && data.video_url) {
            playVideo(data.video_url);
            track('oracle_video_played', { duration_s: 0 });
            finishSend();
          } else if (data.status === 'failed') {
            track('oracle_tier_fallback', { from_tier: 1, to_tier: 2, reason: data.reason || 'render_failed' });
            finishSend();
          } else {
            // Still pending — poll again
            _jobPollTimer = setTimeout(doPoll, JOB_POLL_MS);
          }
        })
        .catch(function () {
          // Network error — try again once
          _jobPollTimer = setTimeout(doPoll, JOB_POLL_MS);
        });
    }

    _jobPollTimer = setTimeout(doPoll, JOB_POLL_MS);
  }

  // ── Video playback (Tier 1 speaking) ──────────────────────────────────
  function playVideo(videoUrl) {
    bubble.classList.add('ow-speaking');

    // Swap bubble video to speaking video
    bubbleVideo.loop = false;
    bubbleVideo.src = videoUrl;
    bubbleVideo.muted = false;
    bubbleVideo.play().catch(function () {
      // Autoplay blocked — fall back silently
      restoreIdleVideo();
    });

    bubbleVideo.addEventListener('ended', function onEnded() {
      bubbleVideo.removeEventListener('ended', onEnded);
      restoreIdleVideo();
    });
  }

  function restoreIdleVideo() {
    bubble.classList.remove('ow-speaking');
    bubbleVideo.muted = true;
    bubbleVideo.loop = true;
    bubbleVideo.src = AVATAR_IDLE_VID;
    bubbleVideo.play().catch(function () {});
  }

  // ── Audio playback ────────────────────────────────────────────────────
  function playAudio(b64) {
    try {
      var ctx = getAudioCtx();
      if (ctx.state === 'suspended') ctx.resume();
      var raw = atob(b64);
      var buf = new ArrayBuffer(raw.length);
      var v = new Uint8Array(buf);
      for (var i = 0; i < raw.length; i++) v[i] = raw.charCodeAt(i);
      ctx.decodeAudioData(buf.slice(0), function (ab) {
        var src = ctx.createBufferSource();
        src.buffer = ab;
        src.connect(ctx.destination);
        src.start(0);
        bubble.classList.add('ow-speaking');
        track('oracle_audio_played', { duration_s: Math.round(ab.duration) });
        src.onended = function () { bubble.classList.remove('ow-speaking'); };
      }, function () {
        // Audio decode failed — silent fallback, no error shown
      });
    } catch (e) {
      // Audio failure — show text silently
    }
  }

  // ── Recommendation cards ──────────────────────────────────────────────
  function fetchRecommendations() {
    _recoLoaded = true;
    fetch('/oracle/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fingerprint: _fingerprint, page_type: _pageCtx.pageType })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data.articles || data.articles.length === 0) return;

      var html = '<p class="oracle-reco-label">' + escapeHtml(data.context || 'Continue reading') + '</p>';
      var articles = data.articles.slice(0, 2);

      for (var i = 0; i < articles.length; i++) {
        var a = articles[i];
        var ariaLabel = escapeAttr(a.title) + ' — ' + escapeAttr(a.category) + ', ' + a.read_time_minutes + ' min read';
        html += '<a class="oracle-reco-card" href="/article/' + escapeAttr(String(a.slug)) + '" ' +
          'data-slug="' + escapeAttr(String(a.slug)) + '" data-pos="' + i + '" ' +
          'aria-label="' + ariaLabel + '">' +
          '<div class="oracle-reco-card__meta">' + escapeHtml(a.category) + ' \u00b7 ' + a.read_time_minutes + ' min read</div>' +
          '<div class="oracle-reco-card__title">' + escapeHtml(a.title) + '</div>' +
          '<span class="oracle-reco-card__link">Read \u2192</span>' +
          '</a>';
      }

      recoEl.innerHTML = html;
      track('oracle_recommendation_shown', { count: articles.length, page_type: _pageCtx.pageType });

      // Bind card clicks
      var cards = recoEl.querySelectorAll('.oracle-reco-card');
      for (var j = 0; j < cards.length; j++) {
        cards[j].addEventListener('click', function (e) {
          track('oracle_recommendation_clicked', {
            slug: this.getAttribute('data-slug'),
            position: parseInt(this.getAttribute('data-pos'), 10)
          });
        });
      }
    })
    .catch(function () {});
  }

  // ── Escape helpers ────────────────────────────────────────────────────
  function escapeHtml(str) {
    var d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
  }
  function escapeAttr(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

})();
