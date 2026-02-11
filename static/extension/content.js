/**
 * Protocol Pulse — Ghost Curation
 * Injects overlay onto X: KOL glow, Pulse Zap button, Alpha count.
 * Shadow DOM keeps our "unlockable layer" isolated from X's CSS.
 */
(function () {
  'use strict';

  const HOST = window.location.hostname;
  if (!/^(twitter|x)\.com$/i.test(HOST)) return;

  const DEFAULT_ORIGIN = 'https://protocolpulse.com';
  const HIGH_SIGNAL_THRESHOLD = 3;
  const GHOST_BORDER = '#DC2626';
  const FONT = '"JetBrains Mono", "SF Mono", Monaco, monospace';

  let alphaList = [];
  let baseOrigin = DEFAULT_ORIGIN;

  function getOrigin(cb) {
    try {
      chrome.runtime.sendMessage({ action: 'getOrigin' }, (r) => {
        if (r && r.origin) baseOrigin = r.origin;
        if (cb) cb();
      });
    } catch (e) {
      if (cb) cb();
    }
  }

  function apiFetch(path, opts = {}) {
    return new Promise((resolve) => {
      getOrigin(() => {
        const url = path.startsWith('http') ? path : `${baseOrigin}${path}`;
        let body = opts.body;
        if (body && typeof body === 'object' && !(body instanceof String)) body = JSON.stringify(body);
        chrome.runtime.sendMessage({ action: 'fetch', url, method: opts.method || 'GET', body: body }, (res) => {
          if (res && res.ok) resolve(res.data);
          else resolve(null);
        });
      });
    });
  }

  function fetchKOLList() {
    getOrigin(() => {
      apiFetch('/api/value-stream/kol-list').then((d) => {
        if (d && d.handles) alphaList = d.handles.map((h) => String(h).toLowerCase());
      });
    });
  }

  function fetchSignal(url, cb) {
    const path = `/api/value-stream/signal-check?url=${encodeURIComponent(url)}`;
    apiFetch(path).then((d) => cb(d || {}));
  }

  function getTweetUrl(article) {
    const link = article.querySelector('a[href*="/status/"]');
    if (!link || !link.href) return null;
    return link.href.split('?')[0];
  }

  function getAuthorHandle(article) {
    const links = article.querySelectorAll('a[href^="/"]');
    for (const a of links) {
      const path = (a.getAttribute('href') || '').trim();
      if (path.includes('/status/')) continue;
      const parts = path.split('/').filter(Boolean);
      if (parts.length >= 1 && /^[a-zA-Z0-9_]+$/.test(parts[0])) return parts[0].toLowerCase();
    }
    return null;
  }

  function injectGhostUI(article, tweetUrl, signal) {
    if (article.dataset.ppGhost === '1') return;
    article.dataset.ppGhost = '1';

    const zapCount = signal.zap_count || 0;
    const totalSats = signal.total_sats || 0;
    const signalHigh = zapCount >= HIGH_SIGNAL_THRESHOLD;
    const postId = signal.post_id;

    const wrap = document.createElement('div');
    wrap.className = 'pp-ghost-wrap';
    wrap.style.cssText = 'position:absolute; top:0; left:0; right:0; bottom:0; pointer-events:none; z-index:1;';
    wrap.style.pointerEvents = 'none';

    const root = wrap.attachShadow({ mode: 'closed' });
    root.innerHTML = `
<style>
  .border { position:absolute; inset:-2px; pointer-events:none; border-radius:16px; border:2px solid ${GHOST_BORDER}; opacity:0.6; box-shadow: 0 0 12px ${GHOST_BORDER}40; }
  .border.high { opacity:0.9; box-shadow: 0 0 20px ${GHOST_BORDER}80; animation: pp-pulse 2s ease-in-out infinite; }
  @keyframes pp-pulse { 0%,100%{ opacity:0.85 } 50%{ opacity:1 } }
  .bar { position:absolute; bottom:8px; right:8px; pointer-events:auto; display:flex; align-items:center; gap:8px; padding:6px 10px; background:rgba(0,0,0,0.85); border-radius:8px; font:11px ${FONT}; color:rgba(255,255,255,0.9); border:1px solid ${GHOST_BORDER}60; }
  .alpha { color:#f7931a; }
  .zap-btn { display:inline-flex; align-items:center; gap:4px; padding:4px 10px; background:linear-gradient(135deg,#f7931a,#e07800); border:none; border-radius:6px; color:#000; font:600 11px ${FONT}; cursor:pointer; pointer-events:auto; }
  .zap-btn:hover { filter:brightness(1.1); }
</style>
<div class="border ${signalHigh ? 'high' : ''}"></div>
<div class="bar">
  ${zapCount > 0 ? `<span class="alpha">⚡ ${zapCount} Alpha-seeker${zapCount !== 1 ? 's' : ''}</span>` : ''}
  <button type="button" class="zap-btn" data-url="${(tweetUrl || '').replace(/"/g, '&quot;')}" data-post-id="${postId || ''}">⚡ Zap</button>
</div>
`;

    const border = root.querySelector('.border');
    const zapBtn = root.querySelector('.zap-btn');

    article.style.position = 'relative';
    article.prepend(wrap);

    zapBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      handleZap(tweetUrl, zapBtn.dataset.postId || null, zapBtn);
    });
  }

  function handleZap(tweetUrl, postId, zapBtnEl) {
    if (typeof window.webln === 'undefined') {
      alert('Install a WebLN wallet (e.g. Alby) to zap from the timeline.');
      return;
    }

    const amount = 1000;
    const origin = baseOrigin;

    function doInvoice(pid) {
      return apiFetch(`${origin}/api/value-stream/invoice/${pid}`, {
        method: 'POST',
        body: JSON.stringify({ amount_sats: amount })
      });
    }

    function doConfirm(pid, hash) {
      return apiFetch(`${origin}/api/value-stream/confirm-zap`, {
        method: 'POST',
        body: JSON.stringify({ post_id: pid, amount_sats: amount, payment_hash: hash })
      });
    }

    (async () => {
      let pid = postId ? parseInt(postId, 10) : null;
      if (!pid && tweetUrl) {
        const sub = await apiFetch(`${origin}/api/value-stream/submit`, { method: 'POST', body: JSON.stringify({ url: tweetUrl }) });
        if (sub && sub.success && sub.id) pid = sub.id;
      }
      if (!pid) {
        alert('Could not add this post to Value Stream.');
        return;
      }

      const inv = await doInvoice(pid);
      if (!inv || !inv.invoice) {
        alert('Could not create invoice.');
        return;
      }

      try {
        await window.webln.enable();
        const res = await window.webln.sendPayment(inv.invoice);
        const hash = res.preimage || res.paymentHash || '';
        await doConfirm(pid, hash);
        if (zapBtnEl) zapBtnEl.textContent = '✓ Zapped';
      } catch (err) {
        if (!/reject|cancel/i.test(err.message || '')) alert(err.message || 'Payment failed');
      }
    })();
  }

  function processArticle(article) {
    const tweetUrl = getTweetUrl(article);
    const handle = getAuthorHandle(article);
    if (!handle || !alphaList.length) return;
    if (!alphaList.includes(handle)) return;
    if (!tweetUrl) return;

    fetchSignal(tweetUrl, (signal) => {
      injectGhostUI(article, tweetUrl, signal);
    });
  }

  function observeFeed() {
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.addedNodes.length) {
          m.addedNodes.forEach((node) => {
            if (node.nodeType !== 1) return;
            if (node.dataset && node.dataset.testid === 'tweet') processArticle(node);
            if (node.querySelectorAll) {
              node.querySelectorAll('article[data-testid="tweet"]').forEach(processArticle);
            }
          });
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    document.querySelectorAll('article[data-testid="tweet"]').forEach(processArticle);
  }

  getOrigin(() => {
    fetchKOLList();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', observeFeed);
    } else {
      observeFeed();
    }
  });
})();
