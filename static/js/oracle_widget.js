/**
 * PROTOCOL PULSE — ORACLE WIDGET v2
 * ===================================
 * Site-wide floating Oracle bubble with full page-context awareness.
 *
 * Features:
 *  - Appears on every page EXCEPT /oracle-live and /admin/*
 *  - Reads current page URL, title, and content metadata
 *  - On article pages: extracts article title + summary from meta tags
 *  - Passes page context into Oracle iframe via postMessage
 *  - Oracle dialogue engine uses context to discuss what user is reading
 *  - Session persists across page navigations via sessionStorage
 *  - Bubble pulses green when Oracle is speaking
 *  - Page-specific hint nudges (e.g. "Ask Oracle about this article")
 *  - Smooth slide-up on mobile, floating panel on desktop
 *  - ESC closes panel, minimize returns to bubble
 *  - Zero external dependencies. Fully self-contained.
 */
(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────────────────
  var ORACLE_URL       = '/oracle-live';
  var AVATAR_IMG       = '/static/oracle_avatar.png';
  var SKIP_PATHS       = ['/oracle-live', '/admin', '/internal', '/login', '/signup'];
  var BUBBLE_DELAY     = 3500;   // ms before bubble appears
  var NUDGE_DELAY      = 14000;  // ms before hint nudge shows
  var NUDGE_DURATION   = 6000;   // ms nudge stays visible

  // ── Skip on excluded paths ────────────────────────────────────────────
  var currentPath = window.location.pathname;
  for (var i = 0; i < SKIP_PATHS.length; i++) {
    if (currentPath.indexOf(SKIP_PATHS[i]) === 0) return;
  }

  // ── Session storage helpers ───────────────────────────────────────────
  var SS_PREFIX = 'oracle_widget_';
  function ss(key, val) {
    try {
      if (val === undefined) return sessionStorage.getItem(SS_PREFIX + key);
      if (val === null) { sessionStorage.removeItem(SS_PREFIX + key); return; }
      sessionStorage.setItem(SS_PREFIX + key, val);
    } catch (e) {}
  }

  // ── Page context extraction ───────────────────────────────────────────
  function getPageContext() {
    var ctx = {
      url:      window.location.href,
      path:     currentPath,
      title:    document.title || '',
      type:     'general',
      content:  null,
    };

    // Article page: extract from meta tags (already rendered in template)
    var ogTitle = getMeta('og:title') || getMeta('twitter:title') || '';
    var ogDesc  = getMeta('og:description') || getMeta('twitter:description') || getMeta('description') || '';
    var section = getMeta('article:section') || '';

    if (currentPath.match(/^\/articles\/\d+/)) {
      ctx.type    = 'article';
      ctx.content = (ogTitle ? 'Article: ' + ogTitle + '. ' : '') +
                    (ogDesc  ? 'Summary: ' + ogDesc  + '. ' : '') +
                    (section ? 'Category: ' + section + '.' : '');
    } else if (currentPath.indexOf('/articles') === 0) {
      ctx.type = 'articles_index';
    } else if (currentPath.indexOf('/terminal') === 0) {
      ctx.type = 'terminal';
    } else if (currentPath.indexOf('/mining') === 0) {
      ctx.type = 'mining';
    } else if (currentPath.indexOf('/whale-watcher') === 0) {
      ctx.type = 'whale_watcher';
    } else if (currentPath.indexOf('/charts') === 0) {
      ctx.type = 'charts';
    } else if (currentPath.indexOf('/podcasts') === 0 || currentPath.indexOf('/podcast') === 0) {
      ctx.type = 'podcasts';
    } else if (currentPath.indexOf('/bitcoin-insurance') === 0) {
      ctx.type = 'bitcoin_insurance';
    } else if (currentPath.indexOf('/curated-mining') === 0) {
      ctx.type = 'curated_mining';
    } else if (currentPath.indexOf('/solo-slayers') === 0) {
      ctx.type = 'solo_slayers';
    } else if (currentPath.indexOf('/briefing') === 0) {
      ctx.type = 'briefing';
    } else if (currentPath === '/' || currentPath === '') {
      ctx.type = 'home';
    }

    return ctx;
  }

  function getMeta(name) {
    var el = document.querySelector(
      'meta[property="' + name + '"],meta[name="' + name + '"]'
    );
    return el ? (el.getAttribute('content') || '').trim() : '';
  }

  // Page-specific hint text
  var PAGE_HINTS = {
    'article':          '&#9889; Ask Oracle about this article',
    'articles_index':   '&#9889; Ask Oracle about any headline',
    'terminal':         '&#9889; Ask Oracle about this intel',
    'mining':           '&#9889; Ask Oracle about Bitcoin mining',
    'whale_watcher':    '&#9889; Ask Oracle about whale moves',
    'charts':           '&#9889; Ask Oracle to explain this chart',
    'podcasts':         '&#9889; Ask Oracle about this episode',
    'bitcoin_insurance':'&#9889; Ask Oracle about Bitcoin insurance',
    'curated_mining':   '&#9889; Ask Oracle about Curated Mining',
    'solo_slayers':     '&#9889; Ask Oracle about solo mining',
    'briefing':         '&#9889; Ask Oracle about today\'s brief',
    'home':             '&#9889; Ask the Oracle anything',
    'general':          '&#9889; Ask the Oracle anything',
  };

  // ── CSS ────────────────────────────────────────────────────────────────
  var css = [
    // Bubble
    '#ow-bubble{position:fixed;bottom:24px;right:24px;width:64px;height:64px;',
    'border-radius:50%;background:#080a0e;border:2px solid rgba(255,59,95,.5);',
    'cursor:pointer;z-index:9000;display:flex;align-items:center;justify-content:center;',
    'overflow:hidden;transition:transform .15s,border-color .25s;',
    'animation:ow-pulse 2.8s ease-in-out infinite;',
    'box-shadow:0 6px 28px rgba(0,0,0,.6);}',
    '#ow-bubble:hover{transform:scale(1.1);border-color:rgba(255,59,95,.9)}',
    '#ow-bubble:active{transform:scale(.94)}',
    '#ow-bubble.speaking{border-color:rgba(74,222,128,.8);animation:ow-pulse-green .85s ease-in-out infinite}',
    '#ow-bubble img{width:100%;height:100%;object-fit:cover;border-radius:50%;pointer-events:none}',
    '#ow-bubble-fb{font-size:26px;line-height:1;pointer-events:none}',
    '@keyframes ow-pulse{',
    '0%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 0 rgba(255,59,95,.45)}',
    '70%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 12px rgba(255,59,95,0)}',
    '100%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 0 rgba(255,59,95,0)}}',
    '@keyframes ow-pulse-green{',
    '0%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 0 rgba(74,222,128,.55)}',
    '70%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 14px rgba(74,222,128,0)}',
    '100%{box-shadow:0 6px 28px rgba(0,0,0,.6),0 0 0 0 rgba(74,222,128,0)}}',
    // Nudge tooltip
    '#ow-nudge{position:fixed;bottom:34px;right:96px;z-index:9001;',
    'background:#0d0f16;border:1px solid rgba(255,59,95,.28);border-radius:6px;',
    'padding:9px 28px 9px 12px;pointer-events:none;',
    'font-family:"JetBrains Mono",monospace;font-size:11px;color:#a0b0cc;',
    'white-space:nowrap;opacity:0;transition:opacity .4s;',
    'box-shadow:0 4px 16px rgba(0,0,0,.5);}',
    '#ow-nudge.on{opacity:1;pointer-events:all}',
    '#ow-nudge::after{content:"";position:absolute;right:-6px;top:50%;',
    'transform:translateY(-50%);border:6px solid transparent;',
    'border-left-color:rgba(255,59,95,.28);border-right:none}',
    '#ow-nudge-x{position:absolute;top:5px;right:7px;cursor:pointer;',
    'color:#445;font-size:10px;line-height:1;padding:2px}',
    '#ow-nudge-x:hover{color:#88a}',
    // Backdrop
    '#ow-bd{position:fixed;inset:0;z-index:8998;background:rgba(0,0,0,.6);',
    'backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);',
    'display:none;opacity:0;transition:opacity .3s}',
    '#ow-bd.on{opacity:1}',
    // Panel
    '#ow-panel{position:fixed;z-index:8999;background:#06070b;',
    'border:1px solid rgba(255,59,95,.18);overflow:hidden;',
    'box-shadow:0 24px 90px rgba(0,0,0,.85);',
    'display:none;opacity:0;transition:transform .38s cubic-bezier(.32,.72,0,1),opacity .3s;',
    // Mobile: full bottom sheet
    'bottom:0;left:0;right:0;height:93vh;border-radius:14px 14px 0 0;',
    'transform:translateY(100%)}',
    '@media(min-width:600px){#ow-panel{',
    'left:auto;right:24px;bottom:96px;',
    'width:min(430px,calc(100vw - 48px));',
    'height:min(680px,calc(100vh - 116px));',
    'border-radius:12px;transform:scale(.88) translateY(20px) translateY(0);',
    'transform-origin:bottom right}}',
    '#ow-panel.on{opacity:1;transform:translateY(0) !important}',
    '@media(min-width:600px){#ow-panel.on{transform:scale(1) translateY(0) !important}}',
    // Panel header bar
    '#ow-hdr{position:absolute;top:0;left:0;right:0;height:46px;z-index:2;',
    'display:flex;align-items:center;justify-content:space-between;padding:0 14px;',
    'background:linear-gradient(to bottom,rgba(6,7,11,1) 55%,rgba(6,7,11,0))}',
    '#ow-hdr-label{font-family:"JetBrains Mono",monospace;font-size:10px;',
    'letter-spacing:.32em;color:rgba(255,59,95,.65);text-transform:uppercase}',
    '#ow-hdr-ctx{font-family:"JetBrains Mono",monospace;font-size:9px;',
    'color:#334;letter-spacing:.05em;max-width:160px;overflow:hidden;',
    'text-overflow:ellipsis;white-space:nowrap}',
    '.ow-btn{width:26px;height:26px;border-radius:50%;cursor:pointer;',
    'background:transparent;border:1px solid #1a2030;',
    'display:flex;align-items:center;justify-content:center;',
    'opacity:.45;transition:opacity .15s,border-color .15s;flex-shrink:0}',
    '.ow-btn:hover{opacity:1;border-color:#445}',
    '#ow-iframe{width:100%;height:100%;border:none;background:#06070b;display:block}',
    // Context badge inside panel (top right of iframe area)
    '#ow-ctx-badge{position:absolute;top:48px;right:10px;z-index:3;',
    'background:rgba(6,7,11,.9);border:1px solid rgba(255,59,95,.15);border-radius:4px;',
    'padding:3px 8px;font-family:"JetBrains Mono",monospace;font-size:9px;',
    'color:rgba(255,59,95,.5);letter-spacing:.06em;display:none;',
    'max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
  ].join('');

  // ── Inject CSS ─────────────────────────────────────────────────────────
  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── DOM creation ───────────────────────────────────────────────────────

  // Backdrop
  var bd = el('div', 'ow-bd');
  bd.addEventListener('click', closePanel);
  document.body.appendChild(bd);

  // Panel
  var panel = el('div', 'ow-panel');
  panel.innerHTML = [
    '<div id="ow-hdr">',
      '<span id="ow-hdr-label">Oracle</span>',
      '<span id="ow-hdr-ctx"></span>',
      '<div style="display:flex;gap:6px;align-items:center">',
        '<button class="ow-btn" id="ow-min-btn" title="Minimize">',
          '<svg width="10" height="2" viewBox="0 0 10 2"><rect width="10" height="1.5" rx=".75" fill="#556"/></svg>',
        '</button>',
        '<button class="ow-btn" id="ow-close-btn" title="Close Oracle">',
          '<svg width="10" height="10" viewBox="0 0 10 10">',
            '<line x1="1" y1="1" x2="9" y2="9" stroke="rgba(255,59,95,.7)" stroke-width="1.5" stroke-linecap="round"/>',
            '<line x1="9" y1="1" x2="1" y2="9" stroke="rgba(255,59,95,.7)" stroke-width="1.5" stroke-linecap="round"/>',
          '</svg>',
        '</button>',
      '</div>',
    '</div>',
    '<div id="ow-ctx-badge"></div>',
    '<iframe id="ow-iframe" src="about:blank" allow="microphone;autoplay;camera" allowfullscreen></iframe>',
  ].join('');
  document.body.appendChild(panel);

  var iframe = document.getElementById('ow-iframe');
  var ctxBadge = document.getElementById('ow-ctx-badge');
  var hdrCtx = document.getElementById('ow-hdr-ctx');

  document.getElementById('ow-close-btn').addEventListener('click', closePanel);
  document.getElementById('ow-min-btn').addEventListener('click', minimizePanel);

  // Nudge
  var nudge = el('div', 'ow-nudge');
  nudge.innerHTML = '<span id="ow-nudge-x" onclick="window._owDismissNudge()">&#10005;</span><span id="ow-nudge-txt"></span>';
  document.body.appendChild(nudge);

  // Bubble (created last so it's topmost)
  var bubble = el('div', 'ow-bubble');
  bubble.style.display = 'none';
  bubble.title = 'Talk to the Oracle';
  bubble.addEventListener('click', openPanel);

  var avatarImg = document.createElement('img');
  avatarImg.src = AVATAR_IMG;
  avatarImg.alt = 'Oracle';
  avatarImg.onerror = function () {
    avatarImg.style.display = 'none';
    var fb = el('span', 'ow-bubble-fb');
    fb.textContent = '⚡';
    bubble.appendChild(fb);
  };
  bubble.appendChild(avatarImg);
  document.body.appendChild(bubble);

  // ── State ──────────────────────────────────────────────────────────────
  var _loaded       = false;
  var _open         = false;
  var _pageCtx      = getPageContext();
  var _sessionId    = ss('sid') || ('s_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7));
  ss('sid', _sessionId);

  // ── Show bubble after delay ─────────────────────────────────────────────
  setTimeout(function () {
    bubble.style.display = 'flex';
    // Nudge if not dismissed this session
    if (ss('nudge_off') !== '1') {
      setTimeout(showNudge, NUDGE_DELAY);
    }
  }, BUBBLE_DELAY);

  // ── Nudge ───────────────────────────────────────────────────────────────
  function showNudge() {
    if (ss('nudge_off') === '1' || _open) return;
    var hint = PAGE_HINTS[_pageCtx.type] || PAGE_HINTS.general;
    document.getElementById('ow-nudge-txt').innerHTML = hint;
    nudge.classList.add('on');
    setTimeout(function () { nudge.classList.remove('on'); }, NUDGE_DURATION);
  }

  window._owDismissNudge = function () {
    nudge.classList.remove('on');
    ss('nudge_off', '1');
  };

  // ── Open panel ─────────────────────────────────────────────────────────
  function openPanel() {
    nudge.classList.remove('on');
    _open = true;

    // Load iframe first time
    if (!_loaded) {
      // Pass session_id and page context via URL params so Oracle can pick them up
      var url = ORACLE_URL + '?session_id=' + encodeURIComponent(_sessionId) +
                '&page_type=' + encodeURIComponent(_pageCtx.type) +
                '&page_path=' + encodeURIComponent(_pageCtx.path);
      iframe.src = url;
      _loaded = true;
    }

    // Update header context label
    var ctxLabel = _getCtxLabel();
    hdrCtx.textContent = ctxLabel;
    if (ctxLabel) {
      ctxBadge.textContent = ctxLabel;
      ctxBadge.style.display = 'block';
    }

    // Show
    bd.style.display = 'block';
    panel.style.display = 'block';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bd.classList.add('on');
        panel.classList.add('on');
      });
    });

    // Send context to iframe after it loads
    iframe.onload = function () {
      sendContextToIframe();
    };
    // Also send now if already loaded
    if (_loaded) {
      setTimeout(sendContextToIframe, 600);
    }
  }

  function _getCtxLabel() {
    if (_pageCtx.type === 'article') {
      var t = getMeta('og:title');
      return t ? t.slice(0, 28) + (t.length > 28 ? '…' : '') : 'article';
    }
    var labels = {
      terminal: 'Intel Terminal', mining: 'Mining Intel',
      whale_watcher: 'Whale Watcher', charts: 'Charts',
      podcasts: 'Podcasts', bitcoin_insurance: 'BTC Insurance',
      curated_mining: 'Curated Mining', solo_slayers: 'Solo Mining',
      briefing: 'Daily Brief', home: '', general: '',
    };
    return labels[_pageCtx.type] || '';
  }

  // ── Send page context into iframe via postMessage ───────────────────────
  function sendContextToIframe() {
    try {
      iframe.contentWindow.postMessage({
        type: 'oracle:context',
        sessionId: _sessionId,
        pageContext: _pageCtx,
      }, window.location.origin);
    } catch (e) {}
  }

  // ── Close / minimize ───────────────────────────────────────────────────
  function closePanel() {
    _open = false;
    panel.classList.remove('on');
    bd.classList.remove('on');
    setTimeout(function () {
      panel.style.display = 'none';
      bd.style.display = 'none';
    }, 400);
    // Reset so next open re-sends context (page may have changed)
    _loaded = false;
    iframe.src = 'about:blank';
    ctxBadge.style.display = 'none';
  }

  function minimizePanel() {
    _open = false;
    panel.classList.remove('on');
    bd.classList.remove('on');
    setTimeout(function () {
      panel.style.display = 'none';
      bd.style.display = 'none';
    }, 400);
    // Keep iframe loaded so session persists on re-open
  }

  // ── postMessage from Oracle iframe ────────────────────────────────────
  window.addEventListener('message', function (e) {
    if (!e.data || typeof e.data !== 'object') return;
    var d = e.data;
    if (d === 'oracle:speaking' || d.type === 'oracle:speaking') bubble.classList.add('speaking');
    if (d === 'oracle:idle'     || d.type === 'oracle:idle')     bubble.classList.remove('speaking');
    if (d === 'oracle:close'    || d.type === 'oracle:close')    closePanel();
    if (d === 'oracle:minimize' || d.type === 'oracle:minimize') minimizePanel();
    // Oracle requests context refresh
    if (d.type === 'oracle:context_request') sendContextToIframe();
  });

  // ── ESC to close ──────────────────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && _open) closePanel();
  });

  // ── Handle page navigation (SPA-style) ───────────────────────────────
  // Re-read page context if URL changes (e.g. articles list → article detail)
  var _lastPath = currentPath;
  setInterval(function () {
    if (window.location.pathname !== _lastPath) {
      _lastPath = window.location.pathname;
      _pageCtx  = getPageContext();
      var lbl = _getCtxLabel();
      hdrCtx.textContent = lbl;
      if (_open) sendContextToIframe();
    }
  }, 1200);

  // ── Utility ───────────────────────────────────────────────────────────
  function el(tag, id) {
    var e = document.createElement(tag);
    if (id) e.id = id;
    return e;
  }

})();
