/* ═══════════════════════════════════════════════════════
   PROTOCOL PULSE — MEDIA UNIFIED ENGINE v2.0
   Bloomberg terminal × Linear.app
   Phase 2: Intelligence Grid
   ═══════════════════════════════════════════════════════ */
'use strict';

(function() {

// ─── CONFIG ───────────────────────────────────────────
const NOSTR_RELAYS = [
  'wss://relay.damus.io',
  'wss://nos.lol',
  'wss://relay.nostr.band'
];

const NOSTR_META_RELAY = 'wss://purplepag.es';

const POLL_INTERVALS = {
  telemetry:  30000,
  fng:       300000,
  signal:     15000,
  feed:       60000,
  sentiment: 300000,
  reddit:    300000,
  partners:  600000
};

const SPACES_ACCOUNTS = [
  { handle: 'sabordebitcoin',  name: 'Sabor de Bitcoin'    },
  { handle: 'BitcoinMagazine', name: 'Bitcoin Magazine'    },
  { handle: 'thebitcoinlayer', name: 'The Bitcoin Layer'   },
  { handle: 'WhatBitcoinDid',  name: 'What Bitcoin Did'    }
];

const PLATFORM_CONFIG = {
  x:           { label: 'X',            color: '#1DA1F2' },
  twitter:     { label: 'X',            color: '#1DA1F2' },
  reddit:      { label: 'REDDIT',       color: '#FF4500' },
  rss:         { label: 'RSS',          color: '#6B7280' },
  news:        { label: 'NEWS',         color: '#6B7280' },
  stacker:     { label: 'STACKER NEWS', color: '#F7931A' },
  nostr:       { label: 'NOSTR',        color: '#7c3aed' }
};

// ─── STATE ────────────────────────────────────────────
const state = {
  nostrNotes: [],
  chainData: null,
  fngData: null,
  highlights: [],
  signalScore: 0,
  sparkData: { btc: [], fees: [], mempool: [], hashrate: [] },
  redditPosts: [],
  partnerVideos: [],
  lastSeen: null,
  ambientMode: false,
  ambientQuotes: [
    { text: 'Hard money fixes low time preference.',             author: 'Saifedean Ammous' },
    { text: 'Every generation of cryptographers dreamed of digital cash.', author: 'Adam Back' },
    { text: 'The fiscal deficit remains the single most important macro variable.', author: 'Lyn Alden' },
    { text: 'Bitcoin is the exit from a system that was never designed to serve you.', author: 'Alex Gladstein' },
    { text: 'The sovereign individual will not ask permission.',  author: 'Davidson & Rees-Mogg' },
    { text: 'Fix the money, fix the world.',                     author: 'Bitcoin Proverb' }
  ],
  ambientIdx: 0
};

// ─── UTILITIES ────────────────────────────────────────
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function linkify(text) {
  return text.replace(/(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function formatTimeAgo(ts) {
  const diff = Date.now() - ts;
  const secs = Math.floor(diff / 1000);
  if (secs < 60)   return secs + 's';
  const mins = Math.floor(secs / 60);
  if (mins < 60)   return mins + 'm';
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)    return hrs + 'h';
  return Math.floor(hrs / 24) + 'd';
}

function formatNumber(n) {
  if (n == null) return '--';
  return n.toLocaleString();
}

// ─── SPLIT-FLAP ANIMATION ─────────────────────────────
function splitFlap(el, newVal) {
  if (!el) return;
  if (el.textContent === String(newVal)) return;
  el.classList.add('mu-flap-out');
  setTimeout(() => {
    el.textContent = newVal;
    el.classList.remove('mu-flap-out');
    el.classList.add('mu-flap-in');
    setTimeout(() => el.classList.remove('mu-flap-in'), 150);
  }, 150);
}

// ─── SPARKLINE RENDERER ───────────────────────────────
class SparklineRenderer {
  constructor(canvasId, color) {
    this.canvas = document.getElementById(canvasId);
    this.color = color || 'rgba(255,255,255,0.5)';
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
      this.w   = this.canvas.width;
      this.h   = this.canvas.height;
    }
  }

  draw(data) {
    if (!this.ctx || !data || data.length < 2) return;
    const pts = data.slice(-24);
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;

    this.ctx.clearRect(0, 0, this.w, this.h);
    this.ctx.beginPath();
    this.ctx.strokeStyle = this.color;
    this.ctx.lineWidth = 1;
    this.ctx.lineJoin = 'round';

    for (let i = 0; i < pts.length; i++) {
      const x = (i / (pts.length - 1)) * this.w;
      const y = this.h - ((pts[i] - min) / range) * (this.h - 2) - 1;
      if (i === 0) this.ctx.moveTo(x, y);
      else         this.ctx.lineTo(x, y);
    }
    this.ctx.stroke();
  }
}

// ─── TELEMETRY ENGINE ─────────────────────────────────
class TelemetryEngine {
  constructor() {
    const RED = 'rgba(220,38,38,0.8)';
    this.sparks = {
      btc:      new SparklineRenderer('spark-btc',      RED),
      fees:     new SparklineRenderer('spark-fees',     RED),
      mempool:  new SparklineRenderer('spark-mempool',  RED),
      hashrate: new SparklineRenderer('spark-hashrate', RED)
    };
  }

  start() {
    this.fetchAll();
    this.fetchFNG();
    setInterval(() => this.fetchAll(), POLL_INTERVALS.telemetry);
    setInterval(() => this.fetchFNG(),  POLL_INTERVALS.fng);
  }

  async fetchAll() {
    try {
      const [priceRes, feesRes, mempoolRes, blockRes, hrRes] = await Promise.allSettled([
        fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'),
        fetch('https://mempool.space/api/v1/fees/recommended'),
        fetch('https://mempool.space/api/mempool'),
        fetch('https://mempool.space/api/blocks/tip/height'),
        fetch('https://mempool.space/api/v1/mining/hashrate/3m')
      ]);

      if (priceRes.status === 'fulfilled' && priceRes.value.ok) {
        const pd = await priceRes.value.json();
        const btcUsd = pd?.bitcoin?.usd;
        const chg    = pd?.bitcoin?.usd_24h_change;
        if (btcUsd != null) {
          const price = '$' + Math.round(btcUsd).toLocaleString();
          splitFlap($('#telem-btc-price'), price);
          state.sparkData.btc.push(btcUsd);
          if (state.sparkData.btc.length > 24) state.sparkData.btc.shift();
          this.sparks.btc.draw(state.sparkData.btc);
        }
        if (chg != null) {
          const chgEl = $('#telem-btc-change');
          if (chgEl) {
            const sign = chg >= 0 ? '+' : '';
            chgEl.textContent = sign + chg.toFixed(2) + '%';
            chgEl.className = 'mu-telem-change ' + (chg > 0.05 ? 'up' : chg < -0.05 ? 'down' : 'flat');
          }
        }
      }

      if (feesRes.status === 'fulfilled' && feesRes.value.ok) {
        const fd = await feesRes.value.json();
        const feeVal = fd.fastestFee ?? fd.halfHourFee ?? fd.economyFee ?? '--';
        splitFlap($('#telem-fees'), feeVal);
        state.sparkData.fees.push(parseFloat(feeVal) || 0);
        if (state.sparkData.fees.length > 24) state.sparkData.fees.shift();
        this.sparks.fees.draw(state.sparkData.fees);
      }

      if (mempoolRes.status === 'fulfilled' && mempoolRes.value.ok) {
        const md = await mempoolRes.value.json();
        state.chainData = { mempool: md };
        const mbVal = md.vsize ? (md.vsize / 1e6).toFixed(1) : '--';
        splitFlap($('#telem-mempool'), mbVal);
        state.sparkData.mempool.push(parseFloat(mbVal) || 0);
        if (state.sparkData.mempool.length > 24) state.sparkData.mempool.shift();
        this.sparks.mempool.draw(state.sparkData.mempool);
        this.updateThermalBorder(md);
      }

      if (blockRes.status === 'fulfilled' && blockRes.value.ok) {
        const blk = await blockRes.value.text();
        const blkNum = parseInt(blk.trim());
        if (!isNaN(blkNum)) splitFlap($('#telem-block'), formatNumber(blkNum));
      }

      if (hrRes.status === 'fulfilled' && hrRes.value.ok) {
        const hrd = await hrRes.value.json();
        const hrRaw = hrd.currentHashrate ?? hrd.hashrates?.slice(-1)[0]?.avgHashrate;
        if (hrRaw != null) {
          const ehs = (hrRaw / 1e18).toFixed(0);
          splitFlap($('#telem-hashrate'), ehs);
          state.sparkData.hashrate.push(parseFloat(ehs) || 0);
          if (state.sparkData.hashrate.length > 24) state.sparkData.hashrate.shift();
          this.sparks.hashrate.draw(state.sparkData.hashrate);
        }
      }

      setHealth('health-telemetry', 'connected');
    } catch (e) {
      setHealth('health-telemetry', 'error');
    }
  }

  async fetchFNG() {
    try {
      const res = await fetch('https://api.alternative.me/fng/?limit=1');
      if (!res.ok) return;
      const d = await res.json();
      state.fngData = d;

      const entry = d.data?.[0] || d;
      const val   = parseInt(entry.value || 50);
      const label = entry.value_classification || '';

      const dot = $('#sentiment-dot');
      const num = $('#sentiment-num');
      if (dot) dot.style.left = val + '%';
      if (num) splitFlap(num, val);

      const why = $('#sentiment-why');
      if (why && label) {
        let color = '#ffffff';
        if (val <= 20)      color = '#dc2626';
        else if (val <= 40) color = '#f97316';
        else if (val <= 60) color = '#ffffff';
        else if (val <= 80) color = '#86efac';
        else                color = '#22c55e';
        why.innerHTML = '<span style="color:' + color + '">' + label.toUpperCase() + '</span>';
        why.classList.add('visible');
      }

      setHealth('health-sentiment', 'connected');
    } catch (e) {
      setHealth('health-sentiment', 'error');
    }
  }

  updateThermalBorder(mempoolData) {
    const border = $('#thermal-border');
    if (!border) return;
    border.classList.remove('congested', 'clearing');
    const count = mempoolData?.count || 0;
    if (count > 50000)      border.classList.add('congested');
    else if (count < 10000) border.classList.add('clearing');
  }
}

// ─── AVATAR UTILITIES ─────────────────────────────────
function getAvatarColor(seed) {
  let hash = 0;
  const s = seed || '?';
  for (let i = 0; i < s.length; i++) {
    hash = s.charCodeAt(i) + ((hash << 5) - hash);
  }
  const palette = ['#7c3aed','#2563eb','#059669','#d97706','#0891b2','#be185d','#0369a1','#7e22ce'];
  return palette[Math.abs(hash) % palette.length];
}

function renderAvatar(name, imgUrl, size) {
  const sz = size || 32;
  const letter = (name || '?')[0].toUpperCase();
  const color = getAvatarColor(name || '?');
  const imgHtml = imgUrl
    ? `<img src="${escapeHtml(imgUrl)}" loading="lazy" width="${sz}" height="${sz}" onerror="this.style.display='none';this.nextSibling.style.display='flex'">`
    : '';
  const fallbackStyle = imgUrl ? 'style="display:none"' : '';
  return `<div class="mu-avatar" style="--avatar-color:${color};width:${sz}px;height:${sz}px">${imgHtml}<span class="mu-avatar-fallback" ${fallbackStyle}>${letter}</span></div>`;
}

// ─── NOSTR FEED (connects to relays, shows live notes) ─
class NostrFeed {
  constructor() {
    this.sockets = {};
    this.seen = new Set();
    this.reconnectDelay = {};
    this.allowlist = [];     // [{name, pubkey, tier}]
    this.pubkeyMap = {};     // pubkey (hex) → display name
    this.metaCache = new Map(); // pubkey → {name, picture}
    this.metaWs = null;
    this.metaFetched = new Set();
  }

  async init() {
    // Fetch allowlist from API (hex pubkeys)
    try {
      const res = await fetch('/api/media/sources');
      if (res.ok) {
        const data = await res.json();
        this.allowlist = data.nostr_allowlist || [];
        this.allowlist.forEach(p => {
          if (p.pubkey) this.pubkeyMap[p.pubkey] = p.name;
        });
      }
    } catch (_) {}

    this.connectAll();
    this.connectMetaRelay();
    setHealth('health-nostr', 'loading');
  }

  connectAll() {
    NOSTR_RELAYS.forEach(url => this.connect(url));
  }

  connect(url) {
    try {
      if (this.sockets[url]?.readyState === WebSocket.OPEN) return;

      const ws = new WebSocket(url);
      this.sockets[url] = ws;
      this.reconnectDelay[url] = this.reconnectDelay[url] || 2000;

      ws.onopen = () => {
        this.reconnectDelay[url] = 2000;
        setHealth('health-nostr', 'connected');
        setHealth('health-nostr-col', 'connected');

        const filter = {
          kinds: [1],
          limit: 30,
          since: Math.floor(Date.now() / 1000) - 86400 // last 24h
        };

        // Filter by allowlisted hex pubkeys if available
        const authors = this.allowlist.map(p => p.pubkey).filter(Boolean);
        if (authors.length > 0) filter.authors = authors;

        ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg[0] === 'EVENT' && msg[2]) this.handleEvent(msg[2]);
        } catch (_) {}
      };

      ws.onclose = () => {
        const delay = Math.min((this.reconnectDelay[url] || 2000) * 1.5, 30000);
        this.reconnectDelay[url] = delay;
        if ($('#nostr-count')) {
          $('#nostr-count').textContent = 'reconnecting...';
        }
        setTimeout(() => this.connect(url), delay);
      };

      ws.onerror = () => {
        setHealth('health-nostr', 'error');
        ws.close();
      };
    } catch (_) {
      setHealth('health-nostr', 'error');
    }
  }

  connectMetaRelay() {
    try {
      const ws = new WebSocket(NOSTR_META_RELAY);
      this.metaWs = ws;

      ws.onopen = () => {
        const keys = this.allowlist.map(p => p.pubkey).filter(Boolean);
        if (keys.length > 0) {
          ws.send(JSON.stringify(['REQ', 'pp-meta-init', { kinds: [0], authors: keys }]));
          keys.forEach(k => this.metaFetched.add(k));
        }
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg[0] === 'EVENT' && msg[2] && msg[2].kind === 0) this.handleMeta(msg[2]);
        } catch (_) {}
      };

      ws.onclose = () => { setTimeout(() => this.connectMetaRelay(), 30000); };
      ws.onerror = () => { ws.close(); };
    } catch (_) {}
  }

  handleMeta(evt) {
    if (!evt.pubkey) return;
    try {
      const profile = JSON.parse(evt.content || '{}');
      const name    = profile.display_name || profile.name || '';
      const picture = profile.picture || '';
      this.metaCache.set(evt.pubkey, { name, picture });

      // Update already-rendered notes with this pubkey
      document.querySelectorAll(`.nostr-note[data-pubkey="${CSS.escape(evt.pubkey)}"]`).forEach(el => {
        if (picture) {
          const img = el.querySelector('.mu-avatar img');
          const fb  = el.querySelector('.mu-avatar-fallback');
          if (!img) {
            // Inject img into avatar
            const av = el.querySelector('.mu-avatar');
            if (av) {
              const newImg = document.createElement('img');
              newImg.src = picture;
              newImg.loading = 'lazy';
              newImg.width = 32;
              newImg.height = 32;
              newImg.onerror = function() { this.style.display = 'none'; if (fb) fb.style.display = 'flex'; };
              av.insertBefore(newImg, av.firstChild);
              if (fb) fb.style.display = 'none';
            }
          } else if (!img.src || img.src === window.location.href) {
            img.src = picture;
          }
        }
        if (name) {
          const authorEl = el.querySelector('.nostr-note-author');
          if (authorEl && authorEl.dataset.isDefault === '1') {
            authorEl.textContent = name;
          }
        }
      });
    } catch (_) {}
  }

  handleEvent(evt) {
    const id = evt.id;
    if (!id || this.seen.has(id)) return;
    this.seen.add(id);

    // Keep seen set bounded
    if (this.seen.size > 500) {
      const arr = Array.from(this.seen).slice(-300);
      this.seen = new Set(arr);
    }

    const meta = evt.pubkey ? this.metaCache.get(evt.pubkey) : null;
    const allowlistName = evt.pubkey ? this.pubkeyMap[evt.pubkey] : null;
    const isDefault = !allowlistName && !(meta && meta.name);
    const name = allowlistName || (meta && meta.name) || (evt.pubkey ? evt.pubkey.slice(0, 8) + '...' : 'Anon');
    const picture = meta?.picture || null;

    const note = {
      id,
      name,
      picture,
      content: evt.content || '',
      created_at: evt.created_at || Math.floor(Date.now() / 1000),
      pubkey: evt.pubkey || '',
      isDefault
    };

    state.nostrNotes.unshift(note);
    if (state.nostrNotes.length > 100) state.nostrNotes.pop();

    this.renderNote(note);
    updateNostrCount();

    // Fetch metadata for unknown pubkeys
    if (evt.pubkey && !this.metaFetched.has(evt.pubkey) && this.metaWs?.readyState === WebSocket.OPEN) {
      this.metaFetched.add(evt.pubkey);
      this.metaWs.send(JSON.stringify(['REQ', 'pp-m-' + evt.pubkey.slice(0, 8), { kinds: [0], authors: [evt.pubkey] }]));
    }

    if (state.ambientMode) showAmbientFlash(name + ': ' + note.content.slice(0, 80));
  }

  renderNote(note) {
    const feed = $('#nostr-feed');
    if (!feed) return;

    feed.querySelectorAll('.mu-skeleton').forEach(s => s.remove());

    const truncated = note.content.length > 280;
    const display = truncated ? note.content.slice(0, 280) : note.content;

    const el = document.createElement('div');
    el.className = 'intel-card nostr-note';
    el.dataset.pubkey = note.pubkey;

    el.innerHTML = `
      <div class="intel-card-header">
        ${renderAvatar(note.name, note.picture, 32)}
        <div class="intel-card-meta">
          <span class="nostr-note-author" ${note.isDefault ? 'data-is-default="1"' : ''}>${escapeHtml(note.name)}</span>
          <span class="intel-badge intel-badge-nostr">NOSTR</span>
        </div>
        <span class="intel-card-time">${formatTimeAgo(note.created_at * 1000)}</span>
      </div>
      <div class="intel-card-body">${linkify(escapeHtml(display))}${truncated ? '<span class="intel-expand-btn"> more</span>' : ''}</div>
    `;

    if (truncated) {
      const btn = el.querySelector('.intel-expand-btn');
      if (btn) {
        btn.addEventListener('click', () => {
          const body = el.querySelector('.intel-card-body');
          if (body) body.innerHTML = linkify(escapeHtml(note.content));
        });
      }
    }

    feed.prepend(el);
    while (feed.children.length > 50) feed.removeChild(feed.lastChild);
  }
}

// ─── PLATFORM DETECTION ───────────────────────────────
function detectPlatform(item) {
  const src  = (item.source || '').toLowerCase();
  const type = (item.source_type || '').toLowerCase();
  const icon = (item.platform_icon || '').toLowerCase();

  if (src.includes('stacker') || src.includes('stackernews')) return PLATFORM_CONFIG.stacker;
  if (type === 'x' || type === 'twitter' || src.includes('twitter') || icon.includes('twitter')) return PLATFORM_CONFIG.x;
  if (type === 'reddit' || src.includes('reddit')) return PLATFORM_CONFIG.reddit;
  if (type === 'nostr' || src.includes('nostr')) return PLATFORM_CONFIG.nostr;
  return PLATFORM_CONFIG.rss;
}

// ─── COMBINED INTELLIGENCE FEED ───────────────────────
class CombinedFeed {
  constructor() {
    this.lastReceived = {}; // platform_key → timestamp
    this.items = [];
    this._firstLoad = true;
  }

  start() {
    this.fetch();
    setInterval(() => this.fetch(), POLL_INTERVALS.feed);
  }

  async fetch() {
    try {
      const res = await fetch('/api/media/feed');
      if (!res.ok) return;
      const data = await res.json();
      if (!Array.isArray(data)) return;

      this.items = data;

      // Track last-received timestamps per platform
      data.forEach(item => {
        const p = detectPlatform(item);
        const key = p.label.toLowerCase().replace(/\s+/g, '_');
        this.lastReceived[key] = Date.now();
      });

      this.render(data);
      updateSourceHealth(this.lastReceived);
    } catch (_) {}
  }

  render(items) {
    const feed = $('#combined-feed');
    if (!feed) return;
    feed.querySelectorAll('.mu-skeleton').forEach(s => s.remove());

    if (!items.length) {
      feed.innerHTML = '<div class="intel-empty">No feed items available.</div>';
      return;
    }

    // Sort by published_at descending
    const sorted = [...items].sort((a, b) => {
      const ta = a.published_at ? new Date(a.published_at).getTime() : 0;
      const tb = b.published_at ? new Date(b.published_at).getTime() : 0;
      return tb - ta;
    });

    // Animate new items in on refresh
    const isRefresh = !this._firstLoad;
    this._firstLoad = false;

    if (isRefresh) {
      // Fade out current, replace
      feed.style.opacity = '0.5';
      feed.style.transition = 'opacity 200ms ease';
      setTimeout(() => {
        feed.innerHTML = sorted.slice(0, 30).map(item => this.renderCard(item)).join('');
        feed.style.opacity = '1';
        this.bindExpand(feed);
      }, 200);
    } else {
      feed.innerHTML = sorted.slice(0, 30).map(item => this.renderCard(item)).join('');
      this.bindExpand(feed);
    }
  }

  bindExpand(feed) {
    feed.querySelectorAll('.intel-expand-btn[data-full]').forEach(btn => {
      btn.addEventListener('click', function() {
        const body = this.closest('.intel-card-body');
        if (body) {
          const full = this.dataset.full || '';
          body.innerHTML = linkify(escapeHtml(full));
        }
      });
    });
  }

  renderCard(item) {
    const platform = detectPlatform(item);
    const author   = item.author || item.source || 'Unknown';
    const content  = item.summary || item.description || item.title || '';
    const truncated = content.length > 280;
    const display  = truncated ? content.slice(0, 280) : content;
    const ts = item.published_at ? new Date(item.published_at).getTime() : Date.now();
    const avatarColor = getAvatarColor(author);

    // For X authors try unavatar
    let imgSrc = '';
    const isX = platform.label === 'X';
    const cleanHandle = author.replace(/^@/, '');
    if (isX && cleanHandle && !cleanHandle.includes(' ')) {
      imgSrc = 'https://unavatar.io/twitter/' + encodeURIComponent(cleanHandle);
    }

    const letter = author[0]?.toUpperCase() || '?';
    const avatarHtml = `<div class="mu-avatar" style="--avatar-color:${avatarColor};width:28px;height:28px">${
      imgSrc ? `<img src="${escapeHtml(imgSrc)}" loading="lazy" width="28" height="28" onerror="this.style.display='none';this.nextSibling.style.display='flex'">` : ''
    }<span class="mu-avatar-fallback"${imgSrc ? ' style="display:none"' : ''}>${letter}</span></div>`;

    const badgeHtml = `<span class="intel-badge" style="background:${platform.color}1a;color:${platform.color};border-color:${platform.color}40">${platform.label}</span>`;

    const expandHtml = truncated
      ? `<span class="intel-expand-btn" data-full="${escapeHtml(content)}"> more</span>`
      : '';

    return `<div class="feed-card" style="--platform-color:${platform.color}">
      <div class="intel-card-left-border"></div>
      <div class="intel-card-content">
        <div class="intel-card-header">
          ${avatarHtml}
          <div class="intel-card-meta">
            <span class="intel-card-author">${escapeHtml(author)}</span>
            ${badgeHtml}
          </div>
          <span class="intel-card-time">${formatTimeAgo(ts)}</span>
        </div>
        <div class="intel-card-body">${linkify(escapeHtml(display))}${expandHtml}</div>
        <div class="intel-card-source">via ${escapeHtml(item.source || '')}</div>
      </div>
    </div>`;
  }
}

// ─── VOICE INTEL (Sentiment + Keywords + Spaces + Health) ─
class VoiceIntel {
  constructor() {
    this.gaugeScore = null;
    this._healthInit = false;
  }

  start() {
    this.fetchSentiment();
    this.renderSpacesRadar();
    this.renderSourceHealth();
    setInterval(() => this.fetchSentiment(), POLL_INTERVALS.sentiment);
  }

  async fetchSentiment() {
    try {
      const res = await fetch('/api/media/sentiment');
      if (!res.ok) return;
      const data = await res.json();

      // Prefer Fear & Greed Index from telemetry if loaded, else use API score
      const fngScore = state.fngData?.data?.[0]?.value
        ? parseInt(state.fngData.data[0].value)
        : null;
      const score = fngScore !== null ? fngScore : (data.score || 50);

      this.gaugeScore = score;
      this.drawGauge(score);
      this.renderKeywords(data.keywords || []);
      setHealth('health-sentiment', 'connected');
    } catch (_) {}
  }

  // Draw arc gauge on canvas
  drawGauge(score) {
    const canvas = document.getElementById('sentiment-gauge');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h - 6;
    const r = Math.min(cx - 4, cy) * 0.9;

    ctx.clearRect(0, 0, w, h);

    // Background arc (full semicircle)
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, 0, false);
    ctx.strokeStyle = 'rgba(255,255,255,0.07)';
    ctx.lineWidth = 10;
    ctx.lineCap = 'butt';
    ctx.stroke();

    // Score color
    let color;
    if      (score <= 20) color = '#dc2626';
    else if (score <= 40) color = '#f97316';
    else if (score <= 60) color = '#e2e2e2';
    else if (score <= 80) color = '#86efac';
    else                  color = '#22c55e';

    // Foreground arc: score/100 of the semicircle
    const endAngle = Math.PI + (score / 100) * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, endAngle, false);
    ctx.strokeStyle = color;
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Update overlay text
    const valEl = document.getElementById('gauge-val');
    if (valEl) {
      valEl.textContent = Math.round(score);
      valEl.style.color = color;
    }
    this.updateGaugeLabel(score, color);
  }

  updateGaugeLabel(score, color) {
    const labelEl = document.getElementById('gauge-label');
    if (!labelEl) return;
    let label;
    if      (score <= 20) label = 'EXTREME FEAR';
    else if (score <= 40) label = 'FEAR';
    else if (score <= 60) label = 'NEUTRAL';
    else if (score <= 80) label = 'GREED';
    else                  label = 'EXTREME GREED';
    labelEl.textContent = label;
    labelEl.style.color = color || '#e2e2e2';
  }

  renderKeywords(keywords) {
    const el = document.getElementById('intel-keywords');
    if (!el) return;
    el.querySelectorAll('.mu-skeleton').forEach(s => s.remove());

    if (!keywords.length) {
      el.innerHTML = '<span class="intel-empty-sm">No keywords available</span>';
      return;
    }

    const maxWeight = Math.max(...keywords.map(k => k.weight || 1));
    el.innerHTML = keywords.slice(0, 14).map(kw => {
      const w = kw.weight || 1;
      const ratio = w / maxWeight;
      const fontSize = 9 + Math.round(ratio * 5); // 9-14px range
      const opacity  = 0.5 + ratio * 0.5;
      const word = kw.keyword || '';
      const isBear = /FUD|BEAR|DUMP|CRASH|FEAR/i.test(word);
      const color = isBear ? '#f97316' : 'rgba(220,38,38,0.85)';
      return `<span class="intel-keyword" style="font-size:${fontSize}px;opacity:${opacity};border-color:${color}25;color:${color}">${escapeHtml(word)}</span>`;
    }).join('');
  }

  renderSpacesRadar() {
    const el = document.getElementById('intel-spaces');
    if (!el) return;

    el.innerHTML = SPACES_ACCOUNTS.map(acc => {
      const imgUrl     = `https://unavatar.io/twitter/${encodeURIComponent(acc.handle)}`;
      const profileUrl = `https://x.com/${encodeURIComponent(acc.handle)}`;
      const avatarColor = getAvatarColor(acc.handle);
      return `<a class="intel-spaces-row" href="${escapeHtml(profileUrl)}" target="_blank" rel="noopener">
        <div class="mu-avatar" style="--avatar-color:${avatarColor};width:28px;height:28px">
          <img src="${escapeHtml(imgUrl)}" loading="lazy" width="28" height="28"
               onerror="this.style.display='none';this.nextSibling.style.display='flex'">
          <span class="mu-avatar-fallback" style="display:none">${acc.name[0].toUpperCase()}</span>
        </div>
        <div class="intel-spaces-info">
          <span class="intel-spaces-name">@${escapeHtml(acc.handle)}</span>
          <span class="intel-spaces-sub">${escapeHtml(acc.name)}</span>
        </div>
        <span class="intel-spaces-link">&rarr;</span>
      </a>`;
    }).join('');
  }

  renderSourceHealth() {
    const el = document.getElementById('intel-health');
    if (!el) return;

    const sources = [
      { key: 'nostr',    label: 'Nostr'        },
      { key: 'x',        label: 'X / Twitter'  },
      { key: 'reddit',   label: 'Reddit'       },
      { key: 'rss',      label: 'RSS / News'   }
    ];

    el.innerHTML = sources.map(s =>
      `<div class="intel-health-row">
        <div class="mu-health-dot loading" id="sh-dot-${s.key}"></div>
        <span class="intel-health-label">${s.label}</span>
        <span class="intel-health-time" id="sh-time-${s.key}">--</span>
      </div>`
    ).join('');

    this._healthInit = true;
  }
}

// ─── SOURCE HEALTH UPDATER ────────────────────────────
function updateSourceHealth(lastReceived) {
  const now = Date.now();
  const fiveMin = 5 * 60 * 1000;

  // Map platform labels back to source slot keys
  const labelToKey = {
    'X':            'x',
    'REDDIT':       'reddit',
    'RSS':          'rss',
    'NEWS':         'rss',
    'STACKER NEWS': 'rss',
    'NOSTR':        'nostr'
  };

  const slotBest = {};
  Object.entries(lastReceived).forEach(([platformLabel, ts]) => {
    const key = labelToKey[platformLabel.toUpperCase()] || 'rss';
    if (!slotBest[key] || ts > slotBest[key]) slotBest[key] = ts;
  });

  ['nostr', 'x', 'reddit', 'rss'].forEach(key => {
    const dotEl  = document.getElementById('sh-dot-' + key);
    const timeEl = document.getElementById('sh-time-' + key);
    const ts = slotBest[key];

    if (!dotEl) return;
    if (ts && now - ts < fiveMin) {
      dotEl.classList.remove('loading', 'error');
      dotEl.classList.add('connected');
      if (timeEl) timeEl.textContent = formatTimeAgo(ts) + ' ago';
    } else if (ts) {
      dotEl.classList.remove('loading', 'connected');
      dotEl.classList.add('error');
      if (timeEl) timeEl.textContent = formatTimeAgo(ts) + ' ago';
    }
  });
}

// Nostr source health is updated separately from RelayManager events
function markNostrSourceHealthActive() {
  const dotEl  = document.getElementById('sh-dot-nostr');
  const timeEl = document.getElementById('sh-time-nostr');
  if (dotEl) {
    dotEl.classList.remove('loading', 'error');
    dotEl.classList.add('connected');
  }
  if (timeEl) timeEl.textContent = 'live';
}

// ─── SIGNAL STRENGTH ──────────────────────────────────
function updateSignalStrength() {
  const oneHourAgo = Date.now() / 1000 - 3600;
  const recentNotes = state.nostrNotes.filter(n => n.created_at > oneHourAgo).length;
  const nostrScore  = Math.min(recentNotes / 30 * 100, 100);

  let chainScore = 50;
  if (state.chainData?.mempool) {
    const count = state.chainData.mempool.count || 0;
    chainScore = Math.min(count / 100000 * 100, 100);
  }

  const sentimentScore = state.fngData?.data?.[0]?.value
    ? parseInt(state.fngData.data[0].value)
    : (state.fngData?.value ? parseInt(state.fngData.value) : 50);

  state.signalScore = Math.round(
    nostrScore     * 0.35 +
    chainScore     * 0.30 +
    sentimentScore * 0.35
  );

  const fill  = $('#signal-fill');
  const label = $('#telem-signal');
  if (fill) {
    fill.style.width = state.signalScore + '%';
    if      (state.signalScore > 70) fill.style.background = '#22c55e';
    else if (state.signalScore > 40) fill.style.background = '#f7931a';
    else                             fill.style.background = '#dc2626';
  }
  if (label) splitFlap(label, state.signalScore);

  const ambSig = $('.mu-ambient-signal');
  if (ambSig) ambSig.textContent = state.signalScore;
}

function updateNostrCount() {
  const el = $('#nostr-count');
  if (el) {
    el.textContent = state.nostrNotes.length + ' notes';
    markNostrSourceHealthActive();
  }
}

// ─── DELTA TRACKER ────────────────────────────────────
function renderDelta() {
  const stored  = localStorage.getItem('pp_last_seen');
  const countEl = $('#delta-count');
  const labelEl = $('#delta-label');
  const itemsEl = $('#delta-items');

  if (!stored) {
    if (countEl) countEl.textContent = 'Welcome.';
    if (labelEl) labelEl.textContent = 'First time here? Explore the intelligence feeds below.';
    if (itemsEl) {
      itemsEl.innerHTML = `
        <div class="mu-delta-item">Live Nostr feeds from Bitcoin thought leaders</div>
        <div class="mu-delta-item">Real-time on-chain data from mempool.space</div>
        <div class="mu-delta-item">Original podcast series and curated library</div>
      `;
    }
    return;
  }

  const since = new Date(parseInt(stored));
  const newNotes = state.nostrNotes.filter(n => n.created_at * 1000 > since.getTime()).length;
  const total = newNotes;

  if (countEl) countEl.textContent = '+' + total;
  if (labelEl) {
    const ago = formatTimeAgo(since.getTime());
    labelEl.textContent = 'signals since ' + ago + ' ago';
  }

  if (itemsEl) {
    const items = [];
    if (newNotes > 0) items.push(newNotes + ' new Nostr notes');
    if (state.redditPosts.length > 0) items.push(state.redditPosts.length + ' Reddit posts trending');

    const sourceCount = {};
    state.nostrNotes.filter(n => n.created_at * 1000 > since.getTime()).slice(0, 20).forEach(n => {
      sourceCount[n.name] = (sourceCount[n.name] || 0) + 1;
    });
    const topSources = Object.entries(sourceCount).sort((a, b) => b[1] - a[1]).slice(0, 3);
    if (topSources.length > 0) {
      items.push(topSources.map(([name, ct]) => ct + ' from ' + name).join(' \u00b7 '));
    }

    itemsEl.innerHTML = items.map(i => `<div class="mu-delta-item">${escapeHtml(i)}</div>`).join('');
  }
}

// ─── REDDIT FEED ──────────────────────────────────────
async function fetchReddit() {
  try {
    const res = await fetch('/api/media/reddit');
    if (!res.ok) return;
    const posts = await res.json();
    state.redditPosts = posts;
    renderReddit(posts);
  } catch (_) {}
}

function renderReddit(posts) {
  const feed = $('#reddit-feed');
  if (!feed || !posts || posts.length === 0) return;

  feed.innerHTML = posts.slice(0, 10).map(p => `
    <div class="mu-reddit-item">
      <div class="mu-reddit-score">${p.score || 0}</div>
      <div>
        <div class="mu-reddit-title"><a href="${escapeHtml(p.url)}" target="_blank" rel="noopener">${escapeHtml(p.title)}</a></div>
        <div class="mu-reddit-meta">u/${escapeHtml(p.author)} \u00b7 ${p.comments || 0} comments${p.flair ? ' \u00b7 ' + escapeHtml(p.flair) : ''}</div>
      </div>
    </div>
  `).join('');
}

// ─── PARTNER CHANNELS FEED ────────────────────────────
async function fetchPartnerVideos() {
  try {
    const res = await fetch('/api/media/partner-videos');
    if (!res.ok) return;
    const videos = await res.json();
    state.partnerVideos = videos;
    renderPartnerVideos(videos);
  } catch (_) {}
}

function renderPartnerVideos(videos) {
  const rail = $('#partner-rail');
  if (!rail || !videos || videos.length === 0) {
    if (rail) rail.innerHTML = '<span style="color:var(--text-secondary);font-family:var(--font-mono);font-size:var(--type-micro)">No partner uploads today.</span>';
    return;
  }

  rail.innerHTML = videos.slice(0, 20).map(v => {
    const thumb = v.thumbnail || '';
    const vidId = v.video_id || '';
    const url   = vidId ? 'https://youtube.com/watch?v=' + vidId : '#';
    return `
      <a class="mu-partner-card" href="${escapeHtml(url)}" target="_blank" rel="noopener">
        <div class="mu-partner-thumb">
          ${thumb ? '<img src="' + escapeHtml(thumb) + '" alt="" loading="lazy" width="320" height="180">' : ''}
        </div>
        <div class="mu-partner-channel">${escapeHtml(v.channel || v.host || '')}</div>
        <div class="mu-partner-title">${escapeHtml(v.title || '')}</div>
      </a>
    `;
  }).join('');
}

// ─── HERO PLAYER ──────────────────────────────────────
function initHeroPlayer() {
  const playBtn = $('#hero-play');
  if (!playBtn) return;

  playBtn.addEventListener('click', () => {
    const vidId    = playBtn.dataset.vid;
    if (!vidId) return;
    const featured = $('#mu-featured');
    const embed    = $('#hero-embed');
    if (!featured || !embed) return;

    featured.classList.add('playing');
    embed.innerHTML = `<iframe src="https://www.youtube.com/embed/${vidId}?autoplay=1&rel=0&modestbranding=1"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen></iframe>`;
  });
}

// ─── LIBRARY INTERACTIONS ─────────────────────────────
function initLibrary() {
  const toggle = $('#lib-toggle');
  const full   = $('#lib-full');
  if (toggle && full) {
    toggle.addEventListener('click', () => {
      const isVis = full.classList.contains('visible');
      full.classList.toggle('visible');
      toggle.innerHTML = isVis ? '&darr; VIEW FULL LIBRARY' : '&uarr; HIDE FULL LIBRARY';
    });
  }
  initVotes();
}

function initVotes() {
  const votes = JSON.parse(localStorage.getItem('pp_book_votes') || '{}');

  $$('.mu-vote-btn').forEach(btn => {
    const book = btn.dataset.book;
    if (!book) return;

    if (votes[book]) btn.classList.add('voted');

    const countEl = btn.nextElementSibling;
    if (countEl && countEl.classList.contains('mu-vote-count')) {
      countEl.textContent = votes[book] || 0;
    }

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (votes[book]) {
        delete votes[book];
        btn.classList.remove('voted');
      } else {
        votes[book] = (votes[book] || 0) + 1;
        btn.classList.add('voted');
      }
      localStorage.setItem('pp_book_votes', JSON.stringify(votes));
      const ct = btn.nextElementSibling;
      if (ct && ct.classList.contains('mu-vote-count')) ct.textContent = votes[book] || 0;
    });
  });
}

// ─── EPISODE FILTER CHIPS ─────────────────────────────
function initEpisodeFilters() {
  const chips = $$('.mu-chip[data-filter]');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });
}

// ─── SERIES HOVER BACKGROUND ──────────────────────────
function initSeriesHover() {
  $$('.mu-series-item').forEach(item => {
    const thumb = item.dataset.thumb;
    if (thumb) {
      item.addEventListener('mouseenter', () => { item.style.backgroundImage = `url(${thumb})`; });
      item.addEventListener('mouseleave', () => { item.style.backgroundImage = 'none'; });
    }
  });
}

// ─── COMMAND PALETTE ──────────────────────────────────
class CommandPalette {
  constructor() {
    this.overlay   = $('#cmd-overlay');
    this.input     = $('#cmd-input');
    this.results   = $('#cmd-results');
    this.selectedIdx = -1;
    this.commands = [
      { group: 'ACTIONS', icon: '\u25cb', label: 'Toggle Ambient Mode',   action: () => toggleAmbient() },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Intelligence Feed', action: () => $('#mu-signals')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Library',          action: () => $('#mu-library')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Series',           action: () => $('#mu-series')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Reddit',           action: () => $('#mu-reddit')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Fullscreen',             action: () => document.documentElement.requestFullscreen?.() },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Open mempool.space',     action: () => window.open('https://mempool.space', '_blank') },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Copy share link',        action: () => navigator.clipboard?.writeText(location.href) },
      { group: 'FILTER',  icon: '\u25cb', label: 'Filter: Mining',         action: () => {} },
      { group: 'FILTER',  icon: '\u25cb', label: 'Filter: Macro',          action: () => {} },
      { group: 'FILTER',  icon: '\u25cb', label: 'Filter: Lightning',      action: () => {} }
    ];
    this._bind();
  }

  _bind() {
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); this.toggle(); }
      if (e.key === 'Escape' && this.overlay?.classList.contains('active')) { e.preventDefault(); this.close(); }
    });

    if (this.input) {
      this.input.addEventListener('input', () => this._render());
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') { this.selectedIdx++; this._render(); e.preventDefault(); }
        if (e.key === 'ArrowUp')   { this.selectedIdx--; this._render(); e.preventDefault(); }
        if (e.key === 'Enter')     { this._execute(); e.preventDefault(); }
      });
    }

    if (this.overlay) {
      this.overlay.addEventListener('click', (e) => { if (e.target === this.overlay) this.close(); });
    }
  }

  toggle() { this.overlay?.classList.contains('active') ? this.close() : this.open(); }

  open() {
    this.overlay?.classList.add('active');
    this.input?.focus();
    this.selectedIdx = -1;
    if (this.input) this.input.value = '';
    this._render();
  }

  close() { this.overlay?.classList.remove('active'); }

  _render() {
    if (!this.results) return;
    const q = (this.input?.value || '').toLowerCase();
    const filtered = q ? this.commands.filter(c => c.label.toLowerCase().includes(q)) : this.commands;
    this.selectedIdx = Math.max(-1, Math.min(this.selectedIdx, filtered.length - 1));

    let html = '';
    let lastGroup = '';
    filtered.forEach((cmd, i) => {
      if (cmd.group !== lastGroup) {
        html += `<div class="mu-cmd-group-label">${cmd.group}</div>`;
        lastGroup = cmd.group;
      }
      html += `<div class="mu-cmd-item${i === this.selectedIdx ? ' selected' : ''}" data-idx="${i}">
        <span class="icon">${cmd.icon}</span>
        <span class="label">${cmd.label}</span>
      </div>`;
    });
    this.results.innerHTML = html;

    this.results.querySelectorAll('.mu-cmd-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.dataset.idx);
        const q2 = (this.input?.value || '').toLowerCase();
        const f2 = q2 ? this.commands.filter(c => c.label.toLowerCase().includes(q2)) : this.commands;
        if (f2[idx]) { f2[idx].action(); this.close(); }
      });
    });
  }

  _execute() {
    const q = (this.input?.value || '').toLowerCase();
    const filtered = q ? this.commands.filter(c => c.label.toLowerCase().includes(q)) : this.commands;
    const cmd = filtered[Math.max(0, this.selectedIdx)];
    if (cmd) { cmd.action(); this.close(); }
  }
}

// ─── AMBIENT MODE ─────────────────────────────────────
function toggleAmbient() {
  state.ambientMode = !state.ambientMode;
  if (state.ambientMode) {
    document.body.classList.add('mu-ambient');
    if (!$('.mu-ambient-layer')) {
      const layer = document.createElement('div');
      layer.className = 'mu-ambient-layer';
      layer.innerHTML = `
        <div class="mu-ambient-quote" id="ambient-quote"></div>
        <div class="mu-ambient-author" id="ambient-author"></div>
        <div class="mu-ambient-signal">${state.signalScore}</div>
        <div class="mu-ambient-flash" id="ambient-flash"></div>
      `;
      document.querySelector('.mu-page')?.appendChild(layer);
    }
    rotateAmbientQuote();
    state.ambientTimer = setInterval(rotateAmbientQuote, 15000);
    document.addEventListener('keydown', ambientEscHandler);
  } else {
    exitAmbient();
  }
}

function exitAmbient() {
  state.ambientMode = false;
  document.body.classList.remove('mu-ambient');
  if (state.ambientTimer) clearInterval(state.ambientTimer);
  document.removeEventListener('keydown', ambientEscHandler);
}

function ambientEscHandler(e) { if (e.key === 'Escape') exitAmbient(); }

function rotateAmbientQuote() {
  const q = state.ambientQuotes[state.ambientIdx % state.ambientQuotes.length];
  const qEl = $('#ambient-quote');
  const aEl = $('#ambient-author');
  if (qEl) qEl.textContent = q.text;
  if (aEl) aEl.textContent = '\u2014 ' + q.author;
  state.ambientIdx++;
}

function showAmbientFlash(text) {
  const flash = $('#ambient-flash');
  if (!flash) return;
  flash.textContent = text;
  flash.classList.add('visible');
  setTimeout(() => flash.classList.remove('visible'), 3000);
}

// ─── HEALTH HELPER ────────────────────────────────────
function setHealth(id, status) {
  const dot = document.getElementById(id);
  if (!dot) return;
  dot.classList.remove('loading', 'connected', 'error');
  dot.classList.add(status);
}

// ─── SHOW ME BUTTON ───────────────────────────────────
function initShowMe() {
  const btn = $('#delta-showme');
  if (btn) {
    btn.addEventListener('click', () => {
      const signals = $('#mu-signals');
      if (signals) signals.scrollIntoView({ behavior: 'smooth' });
    });
  }
}

// ─── INIT ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Core engines
  const nostrFeed    = new NostrFeed();
  const telemetry    = new TelemetryEngine();
  const combinedFeed = new CombinedFeed();
  const voiceIntel   = new VoiceIntel();
  const cmdPalette   = new CommandPalette();

  // Start data flows
  nostrFeed.init();
  telemetry.start();
  combinedFeed.start();
  voiceIntel.start();

  // Reddit + partner channels (graceful 404)
  fetchReddit();
  fetchPartnerVideos();
  setInterval(fetchReddit,        POLL_INTERVALS.reddit);
  setInterval(fetchPartnerVideos, POLL_INTERVALS.partners);

  // Signal strength ticker
  setInterval(updateSignalStrength, POLL_INTERVALS.signal);
  setTimeout(updateSignalStrength, 5000);

  // Delta tracker
  setTimeout(renderDelta, 3000);
  setInterval(renderDelta, 30000);

  // Persist last-seen on unload
  window.addEventListener('beforeunload', () => {
    localStorage.setItem('pp_last_seen', Date.now().toString());
  });

  // UI modules
  initHeroPlayer();
  initLibrary();
  initEpisodeFilters();
  initSeriesHover();
  initShowMe();

  // Cmd+K hint
  const cmdHint = $('#cmd-k-hint');
  if (cmdHint) cmdHint.addEventListener('click', () => cmdPalette.open());

  // Cmd+Shift+A = Ambient mode
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'A') {
      e.preventDefault();
      toggleAmbient();
    }
  });

  // Initial loading skeletons (already in HTML, this is a safety net)
  ['#nostr-feed', '#combined-feed'].forEach(sel => {
    const el = $(sel);
    if (el && !el.children.length) {
      el.innerHTML = Array(3).fill('<div class="mu-skeleton mu-skel-block"></div>').join('');
    }
  });

  console.log('[Media Unified v2.1] Phase 2 Intelligence Grid online. Relays:', NOSTR_RELAYS.length);
});

})();
