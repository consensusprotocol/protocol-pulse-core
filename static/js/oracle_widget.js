/**
 * PROTOCOL PULSE — ORACLE WIDGET
 * Site-wide floating Oracle bubble.
 *
 * Injects a persistent ⚡ bubble (bottom-right) on every page.
 * Click → opens full Oracle in an iframe overlay.
 * Session state persists across page navigation via sessionStorage.
 * Does NOT load on /oracle-live (the full page) or /admin/* routes.
 *
 * Zero external dependencies. Self-contained.
 */
(function () {
  'use strict';

  // ── Config ──────────────────────────────────────────────────────────
  var ORACLE_URL   = '/oracle-live';
  var AVATAR_IMG   = '/static/oracle_avatar.png';
  var SKIP_PATHS   = ['/oracle-live', '/admin', '/internal'];
  var SHOW_DELAY   = 4000;   // ms before bubble appears on page load
  var SPEAK_HINT_DELAY = 12000; // ms before showing "Ask the Oracle" nudge

  // ── Skip on excluded pages ───────────────────────────────────────────
  var path = window.location.pathname;
  for (var i = 0; i < SKIP_PATHS.length; i++) {
    if (path.indexOf(SKIP_PATHS[i]) === 0) return;
  }

  // ── Session state ────────────────────────────────────────────────────
  function ss(key, val) {
    try {
      if (val === undefined) return sessionStorage.getItem('oracle_widget_' + key);
      sessionStorage.setItem('oracle_widget_' + key, val);
    } catch (e) {}
  }

  // ── Styles ───────────────────────────────────────────────────────────
  var css = [
    /* Bubble */
    '#ow-bubble{',
      'position:fixed;bottom:24px;right:24px;',
      'width:64px;height:64px;border-radius:50%;',
      'background:#0a0b0f;',
      'border:2px solid rgba(255,59,95,.55);',
      'cursor:pointer;z-index:9000;',
      'display:flex;align-items:center;justify-content:center;',
      'box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 0 rgba(255,59,95,.4);',
      'transition:transform .15s,border-color .2s,box-shadow .2s;',
      'overflow:hidden;',
      'animation:ow-ring 2.5s ease-in-out infinite;',
    '}',
    '#ow-bubble:hover{transform:scale(1.08);border-color:rgba(255,59,95,.9)}',
    '#ow-bubble.speaking{',
      'border-color:rgba(74,222,128,.8);',
      'animation:ow-ring-green .9s ease-in-out infinite;',
    '}',
    '#ow-bubble img{width:100%;height:100%;object-fit:cover;border-radius:50%}',
    '#ow-bubble .ow-fallback{font-size:26px;line-height:1}',

    /* Pulse rings */
    '@keyframes ow-ring{',
      '0%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 0 rgba(255,59,95,.4)}',
      '70%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 10px rgba(255,59,95,0)}',
      '100%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 0 rgba(255,59,95,0)}',
    '}',
    '@keyframes ow-ring-green{',
      '0%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 0 rgba(74,222,128,.5)}',
      '70%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 12px rgba(74,222,128,0)}',
      '100%{box-shadow:0 4px 24px rgba(0,0,0,.55),0 0 0 0 rgba(74,222,128,0)}',
    '}',

    /* Tooltip nudge */
    '#ow-nudge{',
      'position:fixed;bottom:32px;right:98px;',
      'background:#0f1117;border:1px solid rgba(255,59,95,.3);border-radius:6px;',
      'padding:8px 12px;z-index:9001;',
      'font-family:"JetBrains Mono",monospace;font-size:11px;color:#b8c2d9;',
      'white-space:nowrap;pointer-events:none;',
      'opacity:0;transition:opacity .4s;',
    '}',
    '#ow-nudge.visible{opacity:1}',
    '#ow-nudge::after{',
      'content:"";position:absolute;right:-6px;top:50%;transform:translateY(-50%);',
      'border:6px solid transparent;border-left-color:rgba(255,59,95,.3);',
      'border-right:none;',
    '}',

    /* Close nudge X */
    '#ow-nudge-close{',
      'position:absolute;top:3px;right:5px;',
      'cursor:pointer;color:#556;font-size:10px;pointer-events:all;line-height:1;',
    '}',

    /* Overlay backdrop */
    '#ow-overlay{',
      'position:fixed;inset:0;z-index:8999;',
      'background:rgba(0,0,0,.65);backdrop-filter:blur(3px);',
      '-webkit-backdrop-filter:blur(3px);',
      'display:none;opacity:0;transition:opacity .3s;',
    '}',
    '#ow-overlay.visible{opacity:1}',

    /* Oracle iframe panel */
    '#ow-panel{',
      'position:fixed;z-index:9000;',
      'background:#06070b;border:1px solid rgba(255,59,95,.2);',
      'border-radius:12px;overflow:hidden;',
      'box-shadow:0 20px 80px rgba(0,0,0,.8);',
      /* Mobile: near-fullscreen */
      'bottom:0;right:0;left:0;height:92vh;border-bottom-left-radius:0;border-bottom-right-radius:0;',
      'display:none;',
      'transition:transform .35s cubic-bezier(.32,.72,0,1),opacity .3s;',
      'transform:translateY(100%);opacity:0;',
    '}',
    '@media(min-width:600px){',
      '#ow-panel{',
        'right:24px;left:auto;bottom:96px;',
        'width:min(440px,calc(100vw - 48px));',
        'height:min(700px,calc(100vh - 120px));',
        'border-radius:12px;',
        'transform:scale(.9) translateY(20px);',
      '}',
    '}',
    '#ow-panel.open{transform:translateY(0) !important;opacity:1 !important}',
    '#ow-panel.open.desktop{transform:scale(1) translateY(0) !important}',

    /* Panel header */
    '#ow-panel-header{',
      'position:absolute;top:0;left:0;right:0;height:44px;',
      'display:flex;align-items:center;justify-content:space-between;',
      'padding:0 14px;z-index:1;',
      'background:linear-gradient(to bottom,rgba(6,7,11,1) 60%,rgba(6,7,11,0));',
    '}',
    '#ow-panel-title{',
      'font-family:"JetBrains Mono",monospace;font-size:10px;',
      'letter-spacing:.3em;color:rgba(255,59,95,.7);text-transform:uppercase;',
    '}',
    '.ow-panel-btn{',
      'width:26px;height:26px;border-radius:50%;',
      'background:transparent;border:1px solid #1e2235;',
      'cursor:pointer;display:flex;align-items:center;justify-content:center;',
      'opacity:.5;transition:opacity .15s,border-color .15s;',
    '}',
    '.ow-panel-btn:hover{opacity:1;border-color:#556}',

    /* iframe */
    '#ow-iframe{width:100%;height:100%;border:none;background:#06070b}',
  ].join('');

  // ── Inject styles ────────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // ── Build DOM ────────────────────────────────────────────────────────

  // Overlay backdrop
  var overlay = document.createElement('div');
  overlay.id = 'ow-overlay';
  overlay.addEventListener('click', closePanel);
  document.body.appendChild(overlay);

  // Oracle panel
  var panel = document.createElement('div');
  panel.id = 'ow-panel';
  panel.innerHTML = [
    '<div id="ow-panel-header">',
      '<span id="ow-panel-title">Oracle</span>',
      '<div style="display:flex;gap:6px">',
        '<button class="ow-panel-btn" onclick="document.getElementById(\'ow-panel\').classList.remove(\'open\')" title="Minimize to bubble">',
          '<svg width="10" height="10" viewBox="0 0 10 10"><rect x="0" y="4.25" width="10" height="1.5" rx=".75" fill="#556"/></svg>',
        '</button>',
        '<button class="ow-panel-btn" id="ow-close-btn" title="Close Oracle">',
          '<svg width="10" height="10" viewBox="0 0 10 10">',
            '<line x1="1" y1="1" x2="9" y2="9" stroke="rgba(255,59,95,.7)" stroke-width="1.5" stroke-linecap="round"/>',
            '<line x1="9" y1="1" x2="1" y2="9" stroke="rgba(255,59,95,.7)" stroke-width="1.5" stroke-linecap="round"/>',
          '</svg>',
        '</button>',
      '</div>',
    '</div>',
    '<iframe id="ow-iframe" src="about:blank" allow="microphone;autoplay" allowfullscreen></iframe>',
  ].join('');
  document.body.appendChild(panel);

  panel.querySelector('#ow-close-btn').addEventListener('click', closePanel);
  // Minimize button (first btn) - just close panel, keep bubble
  panel.querySelectorAll('.ow-panel-btn')[0].addEventListener('click', function() {
    panel.classList.remove('open', 'desktop');
    setTimeout(function() { panel.style.display = 'none'; }, 350);
    overlay.classList.remove('visible');
    setTimeout(function() { overlay.style.display = 'none'; }, 300);
  });

  // Tooltip nudge
  var nudge = document.createElement('div');
  nudge.id = 'ow-nudge';
  nudge.innerHTML = [
    '<span id="ow-nudge-close" onclick="dismissNudge()">&#10005;</span>',
    '&#9889; Ask the Oracle',
  ].join('');
  document.body.appendChild(nudge);

  // Bubble (shown after delay)
  var bubble = document.createElement('div');
  bubble.id = 'ow-bubble';
  bubble.title = 'Talk to the Oracle';
  bubble.style.display = 'none';
  bubble.addEventListener('click', openPanel);

  var img = document.createElement('img');
  img.src = AVATAR_IMG;
  img.alt = 'Oracle';
  img.onerror = function () {
    img.style.display = 'none';
    var fb = document.createElement('span');
    fb.className = 'ow-fallback';
    fb.textContent = '⚡';
    bubble.appendChild(fb);
  };
  bubble.appendChild(img);
  document.body.appendChild(bubble);

  // ── Show bubble after delay ──────────────────────────────────────────
  var _bubbleShown = ss('bubble_shown') === '1';
  setTimeout(function () {
    bubble.style.display = 'flex';
    bubble.style.animation = 'ow-ring 2.5s ease-in-out infinite';
    // Show nudge if user hasn't dismissed it this session
    if (!_bubbleShown && ss('nudge_dismissed') !== '1') {
      setTimeout(showNudge, SPEAK_HINT_DELAY);
    }
    ss('bubble_shown', '1');
  }, SHOW_DELAY);

  // ── Page-context nudge: customize per page ───────────────────────────
  var PAGE_HINTS = {
    '/articles':       'Ask Oracle about this article',
    '/mining':         'Ask Oracle about mining',
    '/terminal':       'Ask Oracle about this intel',
    '/whale-watcher':  'Ask Oracle about this whale move',
    '/charts':         'Ask Oracle to explain this chart',
    '/curated-mining': 'Ask Oracle about Curated Mining',
    '/bitcoin-insurance': 'Ask Oracle about Bitcoin insurance',
    '/digital-residency': 'Ask Oracle about digital residency',
  };
  var hint = null;
  for (var p in PAGE_HINTS) {
    if (path.indexOf(p) === 0) { hint = PAGE_HINTS[p]; break; }
  }
  if (!hint) hint = 'Ask the Oracle';
  nudge.querySelector('span + span, :not(#ow-nudge-close)');
  // Update nudge text
  nudge.lastChild.textContent = ' ' + hint;

  function showNudge() {
    if (ss('nudge_dismissed') === '1') return;
    nudge.classList.add('visible');
    setTimeout(function () { nudge.classList.remove('visible'); }, 5000);
  }

  window.dismissNudge = function () {
    nudge.classList.remove('visible');
    ss('nudge_dismissed', '1');
  };

  // ── Open / close panel ───────────────────────────────────────────────
  var _iframeLoaded = false;

  function openPanel() {
    nudge.classList.remove('visible');

    // Load iframe if not yet
    var iframe = document.getElementById('ow-iframe');
    if (!_iframeLoaded) {
      iframe.src = ORACLE_URL;
      _iframeLoaded = true;
    }

    // Show overlay + panel
    overlay.style.display = 'block';
    requestAnimationFrame(function () {
      overlay.classList.add('visible');
    });

    panel.style.display = 'block';
    requestAnimationFrame(function () {
      panel.classList.add('open');
      // Desktop vs mobile class for transform origin
      if (window.innerWidth >= 600) panel.classList.add('desktop');
    });

    ss('panel_opened', '1');
  }

  function closePanel() {
    panel.classList.remove('open', 'desktop');
    overlay.classList.remove('visible');
    setTimeout(function () {
      panel.style.display = 'none';
      overlay.style.display = 'none';
    }, 350);
  }

  // Expose for iframe postMessage (Oracle can close itself)
  window.addEventListener('message', function (e) {
    if (!e.data) return;
    if (e.data === 'oracle:close') closePanel();
    if (e.data === 'oracle:minimize') {
      panel.classList.remove('open', 'desktop');
      setTimeout(function () { panel.style.display = 'none'; }, 350);
      overlay.classList.remove('visible');
      setTimeout(function () { overlay.style.display = 'none'; }, 300);
    }
    if (e.data === 'oracle:speaking') bubble.classList.add('speaking');
    if (e.data === 'oracle:idle')     bubble.classList.remove('speaking');
  });

  // ── ESC to close ────────────────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closePanel();
  });

})();
