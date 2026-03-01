/* ═══════════════════════════════════════════════════════
   PROTOCOL PULSE — MEDIA UNIFIED ENGINE v2.0
   Bloomberg terminal × Linear.app
   ═══════════════════════════════════════════════════════ */
'use strict';

(function() {

// ─── CONFIG ───────────────────────────────────────────
const NOSTR_RELAYS = [
  'wss://relay.damus.io',
  'wss://nos.lol',
  'wss://relay.nostr.band'
];

const NOSTR_PUBKEYS = [
  'npub1sg6plzptd64u62a878hep2kev3zqhgejj56mgql54nnhej7uga7sh3y37r', // jack dorsey
  'npub1a2cww4kn9wqte4ry70vyfdc443v0nyg383q3sek724pjhg3s2hqssn709e', // Lyn Alden
  'npub1zuuajd7u3sx8xu92yav9jwxpr839cs0kc3q6t56vd5u9q033xmhsk6c2uc', // Adam Back
  'npub16c0nh3dnadzqpm76uctf5hqhe2lny344zsmpm6feee9p5rdxaa9q586nvr', // NVK
  'npub1gcxzte5zlkncx26j68ez60fzkvtkm9e0vrwdcvsjakxf9mu9qewqlfnj5z', // Saifedean
  'npub1s5yq6wadwrxde4lhfs56gn64hwzuhnfa6r9mj476r5s4hkunzgzqrs6q7z', // Preston Pysh
];

const POLL_INTERVALS = {
  telemetry: 30000,
  fng: 300000,
  signal: 15000,
  highlights: 60000,
  reddit: 300000,
  partners: 600000
};

// ─── STATE ────────────────────────────────────────────
const state = {
  nostrNotes: [],
  chainData: null,
  fngData: null,
  highlights: [],
  signalScore: 0,
  sparkData: {
    fees: [],
    mempool: [],
    hashrate: []
  },
  redditPosts: [],
  partnerVideos: [],
  lastSeen: null,
  ambientMode: false,
  ambientQuotes: [
    { text: 'Hard money fixes low time preference.', author: 'Saifedean Ammous' },
    { text: 'Every generation of cryptographers dreamed of digital cash.', author: 'Adam Back' },
    { text: 'The fiscal deficit remains the single most important macro variable.', author: 'Lyn Alden' },
    { text: 'Bitcoin is the exit from a system that was never designed to serve you.', author: 'Alex Gladstein' },
    { text: 'The sovereign individual will not ask permission.', author: 'Davidson & Rees-Mogg' },
    { text: 'Fix the money, fix the world.', author: 'Bitcoin Proverb' }
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
  return text.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function formatTimeAgo(ts) {
  const diff = Date.now() - ts;
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return secs + 's';
  const mins = Math.floor(secs / 60);
  if (mins < 60) return mins + 'm';
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + 'h';
  return Math.floor(hrs / 24) + 'd';
}

function formatNumber(n) {
  if (n == null) return '--';
  return n.toLocaleString();
}

// ─── SPLIT-FLAP ANIMATION ─────────────────────────────
function splitFlap(el, newVal) {
  if (!el) return;
  const old = el.textContent;
  if (old === String(newVal)) return;
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
      this.w = this.canvas.width;
      this.h = this.canvas.height;
    }
  }

  draw(data) {
    if (!this.ctx || !data || data.length < 2) return;
    const ctx = this.ctx;
    const pts = data.slice(-24);
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;

    ctx.clearRect(0, 0, this.w, this.h);
    ctx.beginPath();
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 1;
    ctx.lineJoin = 'round';

    for (let i = 0; i < pts.length; i++) {
      const x = (i / (pts.length - 1)) * this.w;
      const y = this.h - ((pts[i] - min) / range) * (this.h - 2) - 1;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

// ─── TELEMETRY ENGINE ─────────────────────────────────
class TelemetryEngine {
  constructor() {
    this.sparks = {
      fees: new SparklineRenderer('spark-fees', 'rgba(255,255,255,0.5)'),
      mempool: new SparklineRenderer('spark-mempool', 'rgba(255,255,255,0.5)'),
      hashrate: new SparklineRenderer('spark-hashrate', 'rgba(255,255,255,0.5)')
    };
  }

  start() {
    this.fetchTelemetry();
    this.fetchFNG();
    setInterval(() => this.fetchTelemetry(), POLL_INTERVALS.telemetry);
    setInterval(() => this.fetchFNG(), POLL_INTERVALS.fng);
  }

  async fetchTelemetry() {
    try {
      const res = await fetch('/api/media/telemetry');
      if (!res.ok) return;
      const d = await res.json();
      state.chainData = d;

      // Update values with split-flap
      if (d.fees != null) {
        const feeVal = typeof d.fees === 'object' ? (d.fees.fastest || d.fees.fastestFee || d.fees.economy || '--') : d.fees;
        splitFlap($('#telem-fees'), feeVal);
        state.sparkData.fees.push(parseFloat(feeVal) || 0);
        if (state.sparkData.fees.length > 24) state.sparkData.fees.shift();
        this.sparks.fees.draw(state.sparkData.fees);
      }

      if (d.mempool != null) {
        const mpVal = d.mempool.vsize ? (d.mempool.vsize / 1e6).toFixed(1) : d.mempool;
        splitFlap($('#telem-mempool'), mpVal);
        state.sparkData.mempool.push(parseFloat(mpVal) || 0);
        if (state.sparkData.mempool.length > 24) state.sparkData.mempool.shift();
        this.sparks.mempool.draw(state.sparkData.mempool);
      }

      if (d.hashrate != null) {
        const hrVal = typeof d.hashrate === 'number' ? Math.round(d.hashrate) : d.hashrate;
        splitFlap($('#telem-hashrate'), hrVal);
        state.sparkData.hashrate.push(parseFloat(hrVal) || 0);
        if (state.sparkData.hashrate.length > 24) state.sparkData.hashrate.shift();
        this.sparks.hashrate.draw(state.sparkData.hashrate);
      }

      if (d.blockHeight != null || d.block != null) {
        const blk = d.blockHeight || d.block;
        splitFlap($('#telem-block'), formatNumber(blk));
      }

      // Thermal border
      this.updateThermalBorder(d);

      // Mark telemetry healthy
      setHealth('health-telemetry', 'connected');
    } catch (e) {
      setHealth('health-telemetry', 'error');
    }
  }

  async fetchFNG() {
    try {
      const res = await fetch('/api/media/fng');
      if (!res.ok) return;
      const d = await res.json();
      state.fngData = d;

      const val = parseInt(d.value || d.data?.[0]?.value || 50);
      const label = d.value_classification || d.data?.[0]?.value_classification || '';

      // Sentiment track
      const dot = $('#sentiment-dot');
      const num = $('#sentiment-num');
      if (dot) dot.style.left = val + '%';
      if (num) splitFlap(num, val);

      // Show "why" on sentiment
      const why = $('#sentiment-why');
      if (why && label) {
        why.textContent = 'driven by: ' + label.toLowerCase();
        why.classList.add('visible');
      }

      setHealth('health-sentiment', 'connected');
    } catch (e) {
      setHealth('health-sentiment', 'error');
    }
  }

  updateThermalBorder(d) {
    const border = $('#thermal-border');
    if (!border) return;
    border.classList.remove('congested', 'clearing');

    if (d.mempool) {
      const count = d.mempool.count || 0;
      if (count > 50000) border.classList.add('congested');
      else if (count < 10000) border.classList.add('clearing');
    }
  }
}

// ─── RELAY MANAGER (Nostr WebSocket) ──────────────────
class RelayManager {
  constructor() {
    this.sockets = {};
    this.seen = new Set();
    this.reconnectDelay = {};
  }

  connectAll() {
    NOSTR_RELAYS.forEach(url => this.connect(url));
  }

  connect(url) {
    if (this.sockets[url]?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(url);
      this.sockets[url] = ws;
      this.reconnectDelay[url] = this.reconnectDelay[url] || 2000;

      ws.onopen = () => {
        this.reconnectDelay[url] = 2000;
        setHealth('health-nostr', 'connected');
        setHealth('health-nostr-col', 'connected');

        // Subscribe to notes from tracked pubkeys
        const filter = {
          kinds: [1],
          limit: 30,
          since: Math.floor(Date.now() / 1000) - 3600
        };

        // Convert npub to hex if needed (simplified — just use as-is for filter)
        ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg[0] === 'EVENT' && msg[2]) {
            this.handleEvent(msg[2]);
          }
        } catch {}
      };

      ws.onclose = () => {
        const delay = Math.min(this.reconnectDelay[url] * 1.5, 30000);
        this.reconnectDelay[url] = delay;
        setTimeout(() => this.connect(url), delay);
      };

      ws.onerror = () => {
        setHealth('health-nostr', 'error');
        ws.close();
      };
    } catch (e) {
      setHealth('health-nostr', 'error');
    }
  }

  handleEvent(evt) {
    const id = evt.id;
    if (this.seen.has(id)) return;
    this.seen.add(id);
    if (this.seen.size > 500) {
      const arr = Array.from(this.seen);
      arr.splice(0, 200);
      this.seen = new Set(arr);
    }

    // Extract display name from tags
    let name = 'Anon';
    if (evt.tags) {
      // Look for 'p' tag profile name
      for (const t of evt.tags) {
        if (t[0] === 'p' && t.length > 2) {
          name = t[2] || name;
          break;
        }
      }
    }

    // Use pubkey as fallback name
    if (name === 'Anon' && evt.pubkey) {
      name = evt.pubkey.slice(0, 8) + '...';
    }

    const note = {
      id: id,
      name: name,
      content: evt.content || '',
      created_at: evt.created_at || Math.floor(Date.now() / 1000),
      pubkey: evt.pubkey
    };

    state.nostrNotes.unshift(note);
    if (state.nostrNotes.length > 100) state.nostrNotes.pop();

    this.renderNote(note);
    updateNostrCount();

    // Ambient mode flash
    if (state.ambientMode) {
      showAmbientFlash(name + ': ' + note.content.slice(0, 80));
    }
  }

  renderNote(note) {
    const feed = $('#nostr-feed');
    if (!feed) return;

    // Remove skeleton loaders
    feed.querySelectorAll('.mu-skeleton').forEach(s => s.remove());

    const el = document.createElement('div');
    el.className = 'mu-feed-item';
    el.innerHTML = `
      <span class="mu-feed-time">${formatTimeAgo(note.created_at * 1000)}</span>
      <div class="mu-feed-author">${escapeHtml(note.name)}</div>
      <div class="mu-feed-content">${linkify(escapeHtml(note.content.slice(0, 280)))}</div>
    `;

    feed.prepend(el);

    // Cap feed items
    while (feed.children.length > 30) {
      feed.removeChild(feed.lastChild);
    }
  }
}

// ─── SIGNAL STRENGTH ──────────────────────────────────
function updateSignalStrength() {
  const oneHourAgo = Date.now() / 1000 - 3600;
  const recentNotes = state.nostrNotes.filter(n => n.created_at > oneHourAgo).length;
  const nostrScore = Math.min(recentNotes / 30 * 100, 100);

  let chainScore = 50;
  if (state.chainData?.mempool) {
    const count = state.chainData.mempool.count || 0;
    chainScore = Math.min(count / 100000 * 100, 100);
  }

  const sentimentScore = state.fngData?.value ? parseInt(state.fngData.value) : 50;

  let freshScore = 50;
  if (state.highlights.length > 0 && state.highlights[0].timestamp) {
    const hoursSince = (Date.now() - new Date(state.highlights[0].timestamp).getTime()) / 3600000;
    freshScore = Math.max(0, 100 - hoursSince * 10);
  }

  state.signalScore = Math.round(
    nostrScore * 0.3 +
    chainScore * 0.25 +
    sentimentScore * 0.25 +
    freshScore * 0.2
  );

  const fill = $('#signal-fill');
  const label = $('#telem-signal');
  if (fill) {
    fill.style.width = state.signalScore + '%';
    if (state.signalScore > 70) fill.style.background = '#22c55e';
    else if (state.signalScore > 40) fill.style.background = '#f7931a';
    else fill.style.background = '#dc2626';
  }
  if (label) splitFlap(label, state.signalScore);

  // Ambient signal
  const ambSig = $('.mu-ambient-signal');
  if (ambSig) ambSig.textContent = state.signalScore;
}

function updateNostrCount() {
  const el = $('#nostr-count');
  if (el) el.textContent = state.nostrNotes.length + ' notes';
}

// ─── DELTA TRACKER (FIXED) ────────────────────────────
function renderDelta() {
  // Read stored timestamp BEFORE writing
  const stored = localStorage.getItem('pp_last_seen');
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
  const newHighlights = state.highlights.filter(h => {
    const ts = h.timestamp ? new Date(h.timestamp).getTime() : 0;
    return ts > since.getTime();
  }).length;
  const total = newNotes + newHighlights;

  if (countEl) countEl.textContent = '+' + total;
  if (labelEl) {
    const ago = formatTimeAgo(since.getTime());
    labelEl.textContent = 'signals since ' + ago + ' ago';
  }

  if (itemsEl) {
    const items = [];
    if (newNotes > 0) items.push(newNotes + ' new Nostr notes');
    if (newHighlights > 0) items.push(newHighlights + ' new highlights');
    if (state.redditPosts.length > 0) items.push(state.redditPosts.length + ' Reddit posts trending');

    // Show top sources
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

// ─── HIGHLIGHTS FEED ──────────────────────────────────
async function fetchHighlights() {
  try {
    const res = await fetch('/api/media/highlights');
    if (!res.ok) return;
    const data = await res.json();
    state.highlights = data;
    renderHighlights(data);
    setHealth('health-highlights-col', 'connected');
  } catch (e) {
    setHealth('health-highlights-col', 'error');
  }
}

function renderHighlights(items) {
  const feed = $('#highlights-feed');
  if (!feed) return;

  feed.querySelectorAll('.mu-skeleton').forEach(s => s.remove());

  if (!items || items.length === 0) {
    feed.innerHTML = '<div class="mu-feed-item"><div class="mu-feed-content" style="color:var(--text-secondary)">No highlights yet today. Check back soon.</div></div>';
    return;
  }

  feed.innerHTML = items.slice(0, 15).map(h => {
    const quote = h.excerpt || h.description || h.title || '';
    const source = h.host || h.source || 'Protocol Pulse';
    const ep = h.episode || '';
    const link = h.url || '#';
    return `
      <div class="mu-highlight-item">
        <div class="mu-highlight-quote">&ldquo;${escapeHtml(quote.slice(0, 200))}&rdquo;</div>
        <div class="mu-highlight-source">
          &mdash; ${escapeHtml(source)}${ep ? ' \u00b7 ' + escapeHtml(ep) : ''}
          ${link !== '#' ? ' <a href="' + escapeHtml(link) + '" target="_blank" rel="noopener">[source]</a>' : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ─── REDDIT FEED ──────────────────────────────────────
async function fetchReddit() {
  try {
    const res = await fetch('/api/media/reddit');
    if (!res.ok) return;
    const posts = await res.json();
    state.redditPosts = posts;
    renderReddit(posts);
  } catch {}
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
  } catch {}
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
    const url = vidId ? 'https://youtube.com/watch?v=' + vidId : '#';
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
    const vidId = playBtn.dataset.vid;
    if (!vidId) return;

    const featured = $('#mu-featured');
    const embed = $('#hero-embed');
    if (!featured || !embed) return;

    featured.classList.add('playing');
    embed.innerHTML = `<iframe src="https://www.youtube.com/embed/${vidId}?autoplay=1&rel=0&modestbranding=1"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen></iframe>`;
  });
}

// ─── LIBRARY INTERACTIONS ─────────────────────────────
function initLibrary() {
  // Full library toggle
  const toggle = $('#lib-toggle');
  const full = $('#lib-full');
  if (toggle && full) {
    toggle.addEventListener('click', () => {
      const isVis = full.classList.contains('visible');
      full.classList.toggle('visible');
      toggle.innerHTML = isVis ? '&darr; VIEW FULL LIBRARY' : '&uarr; HIDE FULL LIBRARY';
    });
  }

  // Vote buttons
  initVotes();
}

function initVotes() {
  const votes = JSON.parse(localStorage.getItem('pp_book_votes') || '{}');

  $$('.mu-vote-btn').forEach(btn => {
    const book = btn.dataset.book;
    if (!book) return;

    // Restore vote state
    if (votes[book]) {
      btn.classList.add('voted');
    }

    // Update count display
    const countEl = btn.nextElementSibling;
    if (countEl && countEl.classList.contains('mu-vote-count')) {
      countEl.textContent = votes[book] || 0;
    }

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (votes[book]) {
        // Un-vote
        delete votes[book];
        btn.classList.remove('voted');
      } else {
        // Vote
        votes[book] = (votes[book] || 0) + 1;
        btn.classList.add('voted');
      }

      localStorage.setItem('pp_book_votes', JSON.stringify(votes));

      const ct = btn.nextElementSibling;
      if (ct && ct.classList.contains('mu-vote-count')) {
        ct.textContent = votes[book] || 0;
      }
    });
  });
}

// ─── EPISODE FILTER CHIPS ─────────────────────────────
function initEpisodeFilters() {
  const chips = $$('.mu-chip[data-filter]');
  const items = $$('.mu-ep-item');

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      // For now, all items show — filtering by type would need data attrs
      // This is a UI stub that can be wired to real data
    });
  });
}

// ─── SERIES HOVER BACKGROUND ──────────────────────────
function initSeriesHover() {
  $$('.mu-series-item').forEach(item => {
    const thumb = item.dataset.thumb;
    if (thumb) {
      item.style.setProperty('--series-bg', `url(${thumb})`);
      const before = item.querySelector('::before');
      // Set via CSS background
      item.addEventListener('mouseenter', () => {
        item.style.backgroundImage = `url(${thumb})`;
      });
      item.addEventListener('mouseleave', () => {
        item.style.backgroundImage = 'none';
      });
    }
  });
}

// ─── COMMAND PALETTE ──────────────────────────────────
class CommandPalette {
  constructor() {
    this.overlay = $('#cmd-overlay');
    this.input = $('#cmd-input');
    this.results = $('#cmd-results');
    this.selectedIdx = -1;
    this.commands = [
      { group: 'ACTIONS', icon: '\u25cb', label: 'Toggle Ambient Mode', action: () => toggleAmbient() },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Toggle Evidence Mode', action: () => {} },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Library', action: () => $('#mu-library')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Reddit', action: () => $('#mu-reddit')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Go to Series', action: () => $('#mu-series')?.scrollIntoView({ behavior: 'smooth' }) },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Fullscreen', action: () => document.documentElement.requestFullscreen?.() },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Open mempool.space', action: () => window.open('https://mempool.space', '_blank') },
      { group: 'ACTIONS', icon: '\u25cb', label: 'Copy share link', action: () => { navigator.clipboard?.writeText(location.href); } },
      { group: 'FILTER', icon: '\u25cb', label: 'Filter: Mining', action: () => {} },
      { group: 'FILTER', icon: '\u25cb', label: 'Filter: Macro', action: () => {} },
      { group: 'FILTER', icon: '\u25cb', label: 'Filter: Lightning', action: () => {} },
    ];
    this._bind();
  }

  _bind() {
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }
      if (e.key === 'Escape' && this.overlay?.classList.contains('active')) {
        e.preventDefault();
        this.close();
      }
    });

    if (this.input) {
      this.input.addEventListener('input', () => this._render());
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') { this.selectedIdx++; this._render(); e.preventDefault(); }
        if (e.key === 'ArrowUp') { this.selectedIdx--; this._render(); e.preventDefault(); }
        if (e.key === 'Enter') { this._execute(); e.preventDefault(); }
      });
    }

    if (this.overlay) {
      this.overlay.addEventListener('click', (e) => {
        if (e.target === this.overlay) this.close();
      });
    }
  }

  toggle() {
    if (this.overlay?.classList.contains('active')) this.close();
    else this.open();
  }

  open() {
    this.overlay?.classList.add('active');
    this.input?.focus();
    this.selectedIdx = -1;
    if (this.input) this.input.value = '';
    this._render();
  }

  close() {
    this.overlay?.classList.remove('active');
  }

  _render() {
    if (!this.results) return;
    const q = (this.input?.value || '').toLowerCase();
    const filtered = q ? this.commands.filter(c => c.label.toLowerCase().includes(q)) : this.commands;
    this.selectedIdx = Math.max(-1, Math.min(this.selectedIdx, filtered.length - 1));

    // Group by group label
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

    // Create ambient layer if not exists
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

    // Exit on ESC
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

function ambientEscHandler(e) {
  if (e.key === 'Escape') {
    exitAmbient();
  }
}

function rotateAmbientQuote() {
  const q = state.ambientQuotes[state.ambientIdx % state.ambientQuotes.length];
  const quoteEl = $('#ambient-quote');
  const authorEl = $('#ambient-author');
  if (quoteEl) quoteEl.textContent = q.text;
  if (authorEl) authorEl.textContent = '\u2014 ' + q.author;
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
  const relay = new RelayManager();
  const telemetry = new TelemetryEngine();
  const cmdPalette = new CommandPalette();

  // Start data flows
  relay.connectAll();
  telemetry.start();

  // Fetch content feeds
  fetchHighlights();
  fetchReddit();
  fetchPartnerVideos();

  // Periodic refreshes
  setInterval(fetchHighlights, POLL_INTERVALS.highlights);
  setInterval(fetchReddit, POLL_INTERVALS.reddit);
  setInterval(fetchPartnerVideos, POLL_INTERVALS.partners);
  setInterval(updateSignalStrength, POLL_INTERVALS.signal);
  setTimeout(updateSignalStrength, 5000);

  // Delta tracker — wait for some data to arrive
  setTimeout(renderDelta, 3000);
  // Re-render delta as more data comes in
  setInterval(renderDelta, 30000);

  // Save last seen on unload
  window.addEventListener('beforeunload', () => {
    localStorage.setItem('pp_last_seen', Date.now().toString());
  });

  // UI init
  initHeroPlayer();
  initLibrary();
  initEpisodeFilters();
  initSeriesHover();
  initShowMe();

  // Cmd+K hint click
  const cmdHint = $('#cmd-k-hint');
  if (cmdHint) {
    cmdHint.addEventListener('click', () => cmdPalette.open());
  }

  // Ambient mode: Cmd+Shift+A
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'A') {
      e.preventDefault();
      toggleAmbient();
    }
  });

  // Loading skeletons
  ['#nostr-feed', '#highlights-feed'].forEach(sel => {
    const el = $(sel);
    if (el && !el.children.length) {
      el.innerHTML = Array(3).fill('<div class="mu-skeleton mu-skel-block"></div>').join('');
    }
  });

  console.log('[Media Unified v2] Engine started. Relays:', NOSTR_RELAYS.length);
});

})();
