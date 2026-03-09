/* ═══════════════════════════════════════════════════════
   PROTOCOL PULSE — MEDIA UNIFIED ENGINE v3.0
   Phase 3: The Network — Merged Intelligence Terminal
   ═══════════════════════════════════════════════════════ */
'use strict';

(function() {

// ─── BECH32 HELPER ────────────────────────────────────
function bech32ToHex(bech32Str) {
  var ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
  var data = bech32Str.slice(bech32Str.indexOf('1') + 1);
  var values = [];
  for (var i = 0; i < data.length; i++) {
    var idx = ALPHABET.indexOf(data[i]);
    if (idx === -1) continue;
    values.push(idx);
  }
  // Remove checksum (last 6 values) and convert 5-bit to 8-bit
  var payload = values.slice(0, -6);
  var bits = '';
  for (var j = 0; j < payload.length; j++) bits += payload[j].toString(2).padStart(5, '0');
  var hex = '';
  for (var k = 0; k + 8 <= bits.length; k += 8) {
    hex += parseInt(bits.slice(k, k + 8), 2).toString(16).padStart(2, '0');
  }
  return hex;
}

// ─── CONFIG ───────────────────────────────────────────
// npub-encoded pubkeys for Nostr REQ filter (supplement allowlist)
var NOSTR_PUBKEYS = [];
var NOSTR_RELAYS = [
  'wss://relay.damus.io',
  'wss://nos.lol',
  'wss://relay.nostr.band'
];

var NOSTR_META_RELAY = 'wss://purplepag.es';

var POLL_INTERVALS = {
  telemetry:  30000,
  fng:       300000,
  signal:     15000,
  feed:       60000,
  sentiment: 300000
};

var SPACES_ACCOUNTS = [
  { handle: 'sabordebitcoin',  name: 'Sabor de Bitcoin'  },
  { handle: 'BitcoinMagazine', name: 'Bitcoin Magazine'  },
  { handle: 'thebitcoinlayer', name: 'The Bitcoin Layer' },
  { handle: 'WhatBitcoinDid',  name: 'What Bitcoin Did'  }
];

var PLATFORM_CONFIG = {
  x:       { label: 'X',            color: '#1DA1F2' },
  twitter: { label: 'X',            color: '#1DA1F2' },
  reddit:  { label: 'REDDIT',       color: '#FF4500' },
  rss:     { label: 'RSS',          color: '#6B7280' },
  news:    { label: 'NEWS',         color: '#6B7280' },
  stacker: { label: 'STACKER NEWS', color: '#F7931A' },
  nostr:   { label: 'NOSTR',        color: '#7c3aed' }
};

// Series data (all episodes for expandable panels)
var SD = {
  everything_21m: {
    title: 'Everything Divided by 21 Million',
    host: 'Matty Ice & Knut Svanholm',
    episodes: [
      {id:'FA8tvWEydcA',title:'Time | Episode 1'},
      {id:'VDordtHAJhg',title:'Alchemy | Episode 2'},
      {id:'yKbQq66AInU',title:'Ownership | Episode 3'},
      {id:'rkTbEpAOADI',title:'Energy | Episode 4'},
      {id:'qG2xYvTVkw0',title:'Morality | Episode 5'},
      {id:'v7xZPqcXyLk',title:'Memetics | Episode 6'},
      {id:'RZv_1Qcqik4',title:'Symbiosis | Episode 7'},
      {id:'UlYSv9SwQGk',title:'Violence | Episode 8'},
      {id:'_ygND311kVE',title:'Deflation | Episode 9'},
      {id:'Nf0LtAk4VBs',title:'Adoption | Episode 10'},
      {id:'Gt8ycm3-NV8',title:'Transition | Episode 11'}
    ]
  },
  big_print: {
    title: 'The Big Print',
    host: 'Matty Ice & Lawrence Lepard',
    episodes: [
      {id:'W09CNU_q6Yo',title:'Why Fixing the Money is the Only Way | Episode 1'},
      {id:'tnthM3uaHbI',title:'How Govt Stole 98.5% Since 1971 | Episode 2'},
      {id:'FRH5w_joMP0',title:'How Inflation Steals Your Life | Episode 3'},
      {id:'JLjG8jAJxbw',title:'The Path to Pure Fiat | Episode 4'},
      {id:'tq_ZYhpW4Vw',title:'How Powell & Yellen Broke It | Episode 5'},
      {id:'Sjp-Kaic2CE',title:'Austrian vs Keynesian | Episode 6'},
      {id:'n6Bi8Kf6ar0',title:'The Sovereign Currency Bubble | Episode 7'},
      {id:'M3M61rLBTl0',title:'Bitcoin is God\'s Gift | Episode 8'},
      {id:'uzUEJZ38RV8',title:'Bitcoin & Real Estate | Episode 9'},
      {id:'y9snxWoEkaU',title:'End of Centralized Power | Episode 10'},
      {id:'hKa8lRDwIos',title:'Digital Scarcity | Episode 11'},
      {id:'FyMWELymqAM',title:'Fix the Money, Fix the World | Episode 12'}
    ]
  },
  daylight_robbery: {
    title: 'Daylight Robbery',
    host: 'Matty Ice & Dominic Frisby',
    episodes: [
      {id:'ZCc78wvwd6U',title:'The Hidden History of Taxation | Episode 1'},
      {id:'j_V3fjvEuS0',title:'How Taxes Shaped Civilization | Episode 2'},
      {id:'W_TNwftaVMk',title:'Death, Taxes, or Islam | Episode 3'},
      {id:'3VDVbbSZYPc',title:'The Peasants\' Revolt | Episode 4'},
      {id:'brho571r5rY',title:'Tax Wars That Created Nations | Episode 5'},
      {id:'zltb_tXZiWI',title:'How the Richest Controlled Nations | Episode 6'},
      {id:'0MDv0d-3t_k',title:'How Tariffs Caused Civil War | Episode 7'},
      {id:'Ym5W3t9WvB8',title:'The Birth of Big Government | Episode 8'},
      {id:'YUHM88mtRxU',title:'Hitler, Banks & Nations | Episode 9'},
      {id:'LcIT9Tgbkm8',title:'How Govts Silently Rob You | Episode 10'},
      {id:'VRSXUD4L2eA',title:'Digital Nomads & Borderless Money | Episode 11'},
      {id:'1OAn6QDSsJs',title:'How Data & AI Reshape Taxation | Episode 12'},
      {id:'xPPbMsz8qso',title:'The Perfect Tax System | Episode 13'}
    ]
  },
  genesis_book: {
    title: 'The Genesis Book',
    host: 'Matty Ice & Aaron van Wirdum',
    episodes: [
      {id:'y7KBeC4jfbo',title:'Origins of Digital Cash | Episode 1'},
      {id:'LNEsJjYZ57o',title:'The Cypherpunks | Episode 2'},
      {id:'KcTVg0b7kDw',title:'Hash Cash & Digital Gold | Episode 3'},
      {id:'TwkR0ncLh0Y',title:'Satoshi\'s Vision | Episode 4'},
      {id:'mAe_F5G6gUE',title:'The Genesis Block | Episode 5'}
    ]
  }
};

// ─── STATE ────────────────────────────────────────────
var state = {
  nostrNotes: [],
  chainData: null,
  fngData: null,
  signalScore: 0,
  sentimentScore: 0,
  spacesScore: 0,
  highlights: null,
  sparkData: { btc: [], fees: [], mempool: [], hashrate: [] },
  currentSeries: null,
  audioPlaying: false
};

// ─── UTILITIES ────────────────────────────────────────
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function escapeHtml(str) {
  if (!str) return '';
  var d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function linkify(text) {
  return text.replace(/(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function formatTimeAgo(ts) {
  var diff = Date.now() - ts;
  var secs = Math.floor(diff / 1000);
  if (secs < 60)   return secs + 's';
  var mins = Math.floor(secs / 60);
  if (mins < 60)   return mins + 'm';
  var hrs = Math.floor(mins / 60);
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
  setTimeout(function() {
    el.textContent = newVal;
    el.classList.remove('mu-flap-out');
    el.classList.add('mu-flap-in');
    setTimeout(function() { el.classList.remove('mu-flap-in'); }, 150);
  }, 150);
}

// ─── SPARKLINE RENDERER ───────────────────────────────
function SparklineRenderer(canvasId, color) {
  this.canvas = document.getElementById(canvasId);
  this.color = color || 'rgba(255,255,255,0.5)';
  if (this.canvas) {
    this.ctx = this.canvas.getContext('2d');
    this.w = this.canvas.width;
    this.h = this.canvas.height;
  }
}

SparklineRenderer.prototype.draw = function(data) {
  if (!this.ctx || !data || data.length < 2) return;
  var pts = data.slice(-24);
  var min = Math.min.apply(null, pts);
  var max = Math.max.apply(null, pts);
  var range = max - min || 1;

  this.ctx.clearRect(0, 0, this.w, this.h);
  this.ctx.beginPath();
  this.ctx.strokeStyle = this.color;
  this.ctx.lineWidth = 1;
  this.ctx.lineJoin = 'round';

  for (var i = 0; i < pts.length; i++) {
    var x = (i / (pts.length - 1)) * this.w;
    var y = this.h - ((pts[i] - min) / range) * (this.h - 2) - 1;
    if (i === 0) this.ctx.moveTo(x, y);
    else         this.ctx.lineTo(x, y);
  }
  this.ctx.stroke();
};

// ─── TELEMETRY ENGINE ─────────────────────────────────
function TelemetryEngine() {
  var RED = 'rgba(204,0,0,0.8)';
  this.sparks = {
    btc:      new SparklineRenderer('spark-btc', RED),
    fees:     new SparklineRenderer('spark-fees', RED),
    mempool:  new SparklineRenderer('spark-mempool', RED),
    hashrate: new SparklineRenderer('spark-hashrate', RED)
  };
}

TelemetryEngine.prototype.start = function() {
  this.fetchAll();
  this.fetchFNG();
  var self = this;
  setInterval(function() { self.fetchAll(); }, POLL_INTERVALS.telemetry);
  setInterval(function() { self.fetchFNG(); }, POLL_INTERVALS.fng);
};

TelemetryEngine.prototype.fetchAll = function() {
  var self = this;
  Promise.allSettled([
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'),
    fetch('https://mempool.space/api/v1/fees/recommended'),
    fetch('https://mempool.space/api/mempool'),
    fetch('https://mempool.space/api/blocks/tip/height'),
    fetch('https://mempool.space/api/v1/mining/hashrate/3m')
  ]).then(function(results) {
    var priceRes = results[0], feesRes = results[1], mempoolRes = results[2], blockRes = results[3], hrRes = results[4];

    if (priceRes.status === 'fulfilled' && priceRes.value.ok) {
      priceRes.value.json().then(function(pd) {
        var btcUsd = pd && pd.bitcoin && pd.bitcoin.usd;
        var chg = pd && pd.bitcoin && pd.bitcoin.usd_24h_change;
        if (btcUsd != null) {
          splitFlap($('#telem-btc-price'), '$' + Math.round(btcUsd).toLocaleString());
          state.sparkData.btc.push(btcUsd);
          if (state.sparkData.btc.length > 24) state.sparkData.btc.shift();
          self.sparks.btc.draw(state.sparkData.btc);
        }
        if (chg != null) {
          var chgEl = $('#telem-btc-change');
          if (chgEl) {
            chgEl.textContent = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';
            chgEl.className = 'mu-telem-change ' + (chg > 0.05 ? 'up' : chg < -0.05 ? 'down' : 'flat');
          }
        }
      });
    }

    if (feesRes.status === 'fulfilled' && feesRes.value.ok) {
      feesRes.value.json().then(function(fd) {
        var feeVal = fd.fastestFee || fd.halfHourFee || fd.economyFee || '--';
        splitFlap($('#telem-fees'), feeVal);
        state.sparkData.fees.push(parseFloat(feeVal) || 0);
        if (state.sparkData.fees.length > 24) state.sparkData.fees.shift();
        self.sparks.fees.draw(state.sparkData.fees);
      });
    }

    if (mempoolRes.status === 'fulfilled' && mempoolRes.value.ok) {
      mempoolRes.value.json().then(function(md) {
        state.chainData = { mempool: md };
        var mbVal = md.vsize ? (md.vsize / 1e6).toFixed(1) : '--';
        splitFlap($('#telem-mempool'), mbVal);
        state.sparkData.mempool.push(parseFloat(mbVal) || 0);
        if (state.sparkData.mempool.length > 24) state.sparkData.mempool.shift();
        self.sparks.mempool.draw(state.sparkData.mempool);
        self.updateThermalBorder(md);
      });
    }

    if (blockRes.status === 'fulfilled' && blockRes.value.ok) {
      blockRes.value.text().then(function(blk) {
        var blkNum = parseInt(blk.trim());
        if (!isNaN(blkNum)) splitFlap($('#telem-block'), formatNumber(blkNum));
      });
    }

    if (hrRes.status === 'fulfilled' && hrRes.value.ok) {
      hrRes.value.json().then(function(hrd) {
        var hrRaw = hrd.currentHashrate || (hrd.hashrates && hrd.hashrates.length && hrd.hashrates[hrd.hashrates.length - 1].avgHashrate);
        if (hrRaw != null) {
          var ehs = (hrRaw / 1e18).toFixed(0);
          splitFlap($('#telem-hashrate'), ehs);
          state.sparkData.hashrate.push(parseFloat(ehs) || 0);
          if (state.sparkData.hashrate.length > 24) state.sparkData.hashrate.shift();
          self.sparks.hashrate.draw(state.sparkData.hashrate);
        }
      });
    }

    setHealth('health-telemetry', 'connected');
  }).catch(function() {
    setHealth('health-telemetry', 'error');
  });
};

TelemetryEngine.prototype.fetchFNG = function() {
  fetch('https://api.alternative.me/fng/?limit=1').then(function(res) {
    if (!res.ok) return;
    return res.json();
  }).then(function(d) {
    if (!d) return;
    state.fngData = d;
    var entry = (d.data && d.data[0]) || d;
    var val = parseInt(entry.value || 50);

    var dot = $('#sentiment-dot');
    var num = $('#sentiment-num');
    if (dot) dot.style.left = val + '%';
    if (num) splitFlap(num, val);

    setHealth('health-sentiment', 'connected');
  }).catch(function() {
    setHealth('health-sentiment', 'error');
  });
};

TelemetryEngine.prototype.updateThermalBorder = function(mempoolData) {
  var border = $('#thermal-border');
  if (!border) return;
  border.classList.remove('congested', 'clearing');
  var count = (mempoolData && mempoolData.count) || 0;
  if (count > 50000)      border.classList.add('congested');
  else if (count < 10000) border.classList.add('clearing');
};

// ─── AVATAR UTILITIES ─────────────────────────────────
function getAvatarColor(seed) {
  var hash = 0;
  var s = seed || '?';
  for (var i = 0; i < s.length; i++) {
    hash = s.charCodeAt(i) + ((hash << 5) - hash);
  }
  var palette = ['#7c3aed','#2563eb','#059669','#d97706','#0891b2','#be185d','#0369a1','#7e22ce'];
  return palette[Math.abs(hash) % palette.length];
}

function renderAvatar(name, imgUrl, size) {
  var sz = size || 32;
  var letter = (name || '?')[0].toUpperCase();
  var color = getAvatarColor(name || '?');
  var imgHtml = imgUrl
    ? '<img src="' + escapeHtml(imgUrl) + '" loading="lazy" width="' + sz + '" height="' + sz + '" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
    : '';
  var fallbackStyle = imgUrl ? ' style="display:none"' : '';
  return '<div class="mu-avatar" style="--avatar-color:' + color + ';width:' + sz + 'px;height:' + sz + 'px">' + imgHtml + '<span class="mu-avatar-fallback"' + fallbackStyle + '>' + letter + '</span></div>';
}

// ─── NOSTR FEED ───────────────────────────────────────
function NostrFeed() {
  this.sockets = {};
  this.seen = new Set();
  this.reconnectDelay = {};
  this.allowlist = [];
  this.pubkeyMap = {};
  this.metaCache = new Map();
  this.metaWs = null;
  this.metaFetched = new Set();
}

NostrFeed.prototype.init = function() {
  var self = this;
  fetch('/api/media/sources').then(function(res) {
    if (res.ok) return res.json();
  }).then(function(data) {
    if (data) {
      self.allowlist = data.nostr_allowlist || [];
      self.allowlist.forEach(function(p) {
        if (p.pubkey) self.pubkeyMap[p.pubkey] = p.name;
      });
    }
  }).catch(function() {}).finally(function() {
    self.connectAll();
    self.connectMetaRelay();
    setHealth('health-nostr', 'loading');
  });
};

NostrFeed.prototype.connectAll = function() {
  var self = this;
  NOSTR_RELAYS.forEach(function(url) { self.connect(url); });
};

NostrFeed.prototype.connect = function(url) {
  var self = this;
  try {
    if (this.sockets[url] && this.sockets[url].readyState === WebSocket.OPEN) return;

    var ws = new WebSocket(url);
    this.sockets[url] = ws;
    this.reconnectDelay[url] = this.reconnectDelay[url] || 2000;

    ws.onopen = function() {
      self.reconnectDelay[url] = 2000;
      setHealth('health-nostr', 'connected');
      setHealth('health-nostr-col', 'connected');

      var filter = {
        kinds: [1],
        limit: 30,
        since: Math.floor(Date.now() / 1000) - 86400
      };

      var authors = self.allowlist.map(function(p) { return p.pubkey; }).filter(Boolean);
      if (authors.length > 0) filter.authors = authors;

      var hexPubkeys = NOSTR_PUBKEYS.map(function(npub) { return bech32ToHex(npub); });
      if (hexPubkeys.length > 0) filter.authors = hexPubkeys;
      ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));
    };

    ws.onmessage = function(evt) {
      try {
        var msg = JSON.parse(evt.data);
        if (msg[0] === 'EVENT' && msg[2]) self.handleEvent(msg[2]);
      } catch (e) {}
    };

    ws.onclose = function() {
      var delay = Math.min((self.reconnectDelay[url] || 2000) * 1.5, 30000);
      self.reconnectDelay[url] = delay;
      var countEl = $('#nostr-count');
      if (countEl) countEl.textContent = 'reconnecting...';
      setTimeout(function() { self.connect(url); }, delay);
    };

    ws.onerror = function() {
      setHealth('health-nostr', 'error');
      ws.close();
    };
  } catch (e) {
    setHealth('health-nostr', 'error');
  }
};

NostrFeed.prototype.connectMetaRelay = function() {
  var self = this;
  try {
    var ws = new WebSocket(NOSTR_META_RELAY);
    this.metaWs = ws;

    ws.onopen = function() {
      var keys = self.allowlist.map(function(p) { return p.pubkey; }).filter(Boolean);
      if (keys.length > 0) {
        ws.send(JSON.stringify(['REQ', 'pp-meta-init', { kinds: [0], authors: keys }]));
        keys.forEach(function(k) { self.metaFetched.add(k); });
      }
    };

    ws.onmessage = function(evt) {
      try {
        var msg = JSON.parse(evt.data);
        if (msg[0] === 'EVENT' && msg[2] && msg[2].kind === 0) self.handleMeta(msg[2]);
      } catch (e) {}
    };

    ws.onclose = function() { setTimeout(function() { self.connectMetaRelay(); }, 30000); };
    ws.onerror = function() { ws.close(); };
  } catch (e) {}
};

NostrFeed.prototype.handleMeta = function(evt) {
  if (!evt.pubkey) return;
  try {
    var profile = JSON.parse(evt.content || '{}');
    var name = profile.display_name || profile.name || '';
    var picture = profile.picture || '';
    this.metaCache.set(evt.pubkey, { name: name, picture: picture });

    // Update rendered notes
    document.querySelectorAll('.nostr-note[data-pubkey="' + CSS.escape(evt.pubkey) + '"]').forEach(function(el) {
      if (picture) {
        var av = el.querySelector('.mu-avatar');
        var fb = el.querySelector('.mu-avatar-fallback');
        var existingImg = el.querySelector('.mu-avatar img');
        if (!existingImg && av) {
          var newImg = document.createElement('img');
          newImg.src = picture;
          newImg.loading = 'lazy';
          newImg.width = 32;
          newImg.height = 32;
          newImg.onerror = function() { this.style.display = 'none'; if (fb) fb.style.display = 'flex'; };
          av.insertBefore(newImg, av.firstChild);
          if (fb) fb.style.display = 'none';
        }
      }
      if (name) {
        var authorEl = el.querySelector('.nostr-note-author');
        if (authorEl && authorEl.dataset.isDefault === '1') {
          authorEl.textContent = name;
        }
      }
    });
  } catch (e) {}
};

NostrFeed.prototype.handleEvent = function(evt) {
  var id = evt.id;
  if (!id || this.seen.has(id)) return;
  this.seen.add(id);

  if (this.seen.size > 500) {
    var arr = Array.from(this.seen).slice(-300);
    this.seen = new Set(arr);
  }

  var meta = evt.pubkey ? this.metaCache.get(evt.pubkey) : null;
  var allowlistName = evt.pubkey ? this.pubkeyMap[evt.pubkey] : null;
  var isDefault = !allowlistName && !(meta && meta.name);
  var name = allowlistName || (meta && meta.name) || (evt.pubkey ? evt.pubkey.slice(0, 8) + '...' : 'Anon');
  var picture = (meta && meta.picture) || null;

  var note = {
    id: id,
    name: name,
    picture: picture,
    content: evt.content || '',
    created_at: evt.created_at || Math.floor(Date.now() / 1000),
    pubkey: evt.pubkey || '',
    isDefault: isDefault
  };

  state.nostrNotes.unshift(note);
  if (state.nostrNotes.length > 100) state.nostrNotes.pop();

  this.renderNote(note);
  updateNostrCount();

  // Fetch metadata for unknown pubkeys
  if (evt.pubkey && !this.metaFetched.has(evt.pubkey) && this.metaWs && this.metaWs.readyState === WebSocket.OPEN) {
    this.metaFetched.add(evt.pubkey);
    this.metaWs.send(JSON.stringify(['REQ', 'pp-m-' + evt.pubkey.slice(0, 8), { kinds: [0], authors: [evt.pubkey] }]));
  }
};

NostrFeed.prototype.renderNote = function(note) {
  var feed = $('#nostr-feed');
  if (!feed) return;

  feed.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });

  var truncated = note.content.length > 280;
  var display = truncated ? note.content.slice(0, 280) : note.content;

  var el = document.createElement('div');
  el.className = 'intel-card nostr-note nostr-new';
  el.dataset.pubkey = note.pubkey;

  el.innerHTML =
    '<div class="intel-card-header">' +
      renderAvatar(note.name, note.picture, 32) +
      '<div class="intel-card-meta">' +
        '<span class="nostr-note-author"' + (note.isDefault ? ' data-is-default="1"' : '') + '>' + escapeHtml(note.name) + '</span>' +
        '<span class="intel-badge intel-badge-nostr">NOSTR</span>' +
      '</div>' +
      '<span class="intel-card-time">' + formatTimeAgo(note.created_at * 1000) + '</span>' +
    '</div>' +
    '<div class="intel-card-body">' + linkify(escapeHtml(display)) + (truncated ? '<span class="intel-expand-btn"> more</span>' : '') + '</div>';

  if (truncated) {
    var btn = el.querySelector('.intel-expand-btn');
    if (btn) {
      btn.addEventListener('click', function() {
        var body = el.querySelector('.intel-card-body');
        if (body) {
          body.innerHTML = linkify(escapeHtml(note.content));
          body.classList.add('expanded');
        }
      });
    }
  }

  // Remove new glow after animation
  setTimeout(function() { el.classList.remove('nostr-new'); }, 600);

  feed.prepend(el);
  while (feed.children.length > 30) feed.removeChild(feed.lastChild);
};

// ─── PLATFORM DETECTION ───────────────────────────────
function detectPlatform(item) {
  var src = (item.source || '').toLowerCase();
  var type = (item.source_type || '').toLowerCase();
  var icon = (item.platform_icon || '').toLowerCase();

  if (src.indexOf('stacker') >= 0 || src.indexOf('stackernews') >= 0) return PLATFORM_CONFIG.stacker;
  if (type === 'x' || type === 'twitter' || src.indexOf('twitter') >= 0 || icon.indexOf('twitter') >= 0) return PLATFORM_CONFIG.x;
  if (type === 'reddit' || src.indexOf('reddit') >= 0) return PLATFORM_CONFIG.reddit;
  if (type === 'nostr' || src.indexOf('nostr') >= 0) return PLATFORM_CONFIG.nostr;
  return PLATFORM_CONFIG.rss;
}

// ─── COMBINED INTELLIGENCE FEED ───────────────────────
function CombinedFeed() {
  this.lastReceived = {};
  this.items = [];
  this._firstLoad = true;
  this.activeFilter = 'all';
}

CombinedFeed.prototype.start = function() {
  this.fetch();
  var self = this;
  setInterval(function() { self.fetch(); }, POLL_INTERVALS.feed);
};

CombinedFeed.prototype.fetch = function() {
  var self = this;
  fetch('/api/media/feed').then(function(res) {
    if (!res.ok) return null;
    return res.json();
  }).then(function(data) {
    if (!data || !Array.isArray(data)) return;
    self.items = data;
    data.forEach(function(item) {
      var p = detectPlatform(item);
      var key = p.label.toLowerCase().replace(/\s+/g, '_');
      self.lastReceived[key] = Date.now();
    });
    self.render(data);
    updateSourceHealth(self.lastReceived);
  }).catch(function() {});
};

CombinedFeed.prototype.render = function(items) {
  var feed = $('#combined-feed');
  if (!feed) return;
  feed.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });

  if (!items.length) {
    feed.innerHTML = '<div class="intel-empty"><i class="fas fa-satellite-dish"></i>Monitoring signal channels...<div class="intel-loader"></div></div>';
    return;
  }

  var sorted = items.slice().sort(function(a, b) {
    var ta = a.published_at ? new Date(a.published_at).getTime() : 0;
    var tb = b.published_at ? new Date(b.published_at).getTime() : 0;
    return tb - ta;
  });

  // Apply filter
  var self = this;
  var filtered = sorted;
  if (this.activeFilter !== 'all') {
    filtered = sorted.filter(function(item) {
      var p = detectPlatform(item);
      var label = p.label.toLowerCase();
      if (self.activeFilter === 'x') return label === 'x';
      if (self.activeFilter === 'reddit') return label === 'reddit';
      if (self.activeFilter === 'stacker') return label === 'stacker news';
      if (self.activeFilter === 'rss') return label === 'rss' || label === 'news';
      return true;
    });
  }

  var isRefresh = !this._firstLoad;
  this._firstLoad = false;

  if (isRefresh) {
    feed.style.opacity = '0.5';
    feed.style.transition = 'opacity 200ms ease';
    setTimeout(function() {
      feed.innerHTML = filtered.slice(0, 30).map(function(item) { return self.renderCard(item); }).join('');
      feed.style.opacity = '1';
      self.bindExpand(feed);
    }, 200);
  } else {
    feed.innerHTML = filtered.slice(0, 30).map(function(item) { return self.renderCard(item); }).join('');
    this.bindExpand(feed);
  }
};

CombinedFeed.prototype.bindExpand = function(feed) {
  feed.querySelectorAll('.intel-expand-btn[data-full]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var body = this.closest('.intel-card-body');
      if (body) {
        body.innerHTML = linkify(escapeHtml(this.dataset.full || ''));
        body.classList.add('expanded');
      }
    });
  });
};

CombinedFeed.prototype.renderCard = function(item) {
  var platform = detectPlatform(item);
  var author = item.author || item.source || 'Unknown';
  var content = item.summary || item.description || item.title || '';
  var truncated = content.length > 280;
  var display = truncated ? content.slice(0, 280) : content;
  var ts = item.published_at ? new Date(item.published_at).getTime() : Date.now();
  var avatarColor = getAvatarColor(author);

  var imgSrc = '';
  var isX = platform.label === 'X';
  var cleanHandle = author.replace(/^@/, '');
  if (isX && cleanHandle && cleanHandle.indexOf(' ') < 0) {
    imgSrc = 'https://unavatar.io/twitter/' + encodeURIComponent(cleanHandle);
  }

  var letter = (author[0] || '?').toUpperCase();
  var avatarHtml = '<div class="mu-avatar" style="--avatar-color:' + avatarColor + ';width:28px;height:28px">' +
    (imgSrc ? '<img src="' + escapeHtml(imgSrc) + '" loading="lazy" width="28" height="28" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' : '') +
    '<span class="mu-avatar-fallback"' + (imgSrc ? ' style="display:none"' : '') + '>' + letter + '</span></div>';

  var badgeHtml = '<span class="intel-badge" style="background:' + platform.color + '1a;color:' + platform.color + ';border-color:' + platform.color + '40">' + platform.label + '</span>';

  var expandHtml = truncated
    ? '<span class="intel-expand-btn" data-full="' + escapeHtml(content) + '"> more</span>'
    : '';

  return '<div class="feed-card" style="--platform-color:' + platform.color + '">' +
    '<div class="intel-card-left-border"></div>' +
    '<div class="intel-card-content">' +
      '<div class="intel-card-header">' +
        avatarHtml +
        '<div class="intel-card-meta">' +
          '<span class="intel-card-author">' + escapeHtml(author) + '</span>' +
          badgeHtml +
        '</div>' +
        '<span class="intel-card-time">' + formatTimeAgo(ts) + '</span>' +
      '</div>' +
      '<div class="intel-card-body">' + linkify(escapeHtml(display)) + expandHtml + '</div>' +
      '<div class="intel-card-source">via ' + escapeHtml(item.source || '') + '</div>' +
    '</div>' +
  '</div>';
};

// ─── VOICE INTEL ──────────────────────────────────────
function VoiceIntel() {
  this.gaugeScore = null;
}

VoiceIntel.prototype.start = function() {
  this.fetchSentiment();
  this.renderSpacesRadar();
  this.renderSourceHealth();
  var self = this;
  setInterval(function() { self.fetchSentiment(); }, POLL_INTERVALS.sentiment);
};

VoiceIntel.prototype.fetchSentiment = function() {
  var self = this;
  fetch('/api/media/sentiment').then(function(res) {
    if (!res.ok) return null;
    return res.json();
  }).then(function(data) {
    if (!data) return;
    var fngScore = state.fngData && state.fngData.data && state.fngData.data[0]
      ? parseInt(state.fngData.data[0].value) : null;
    var score = fngScore !== null ? fngScore : (data.score || 50);

    self.gaugeScore = score;
    self.drawGauge(score);
    self.renderKeywords(data.keywords || []);
    setHealth('health-sentiment', 'connected');
  }).catch(function() {});
};

VoiceIntel.prototype.drawGauge = function(score) {
  var canvas = document.getElementById('sentiment-gauge');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var w = canvas.width, h = canvas.height;
  var cx = w / 2, cy = h - 6;
  var r = Math.min(cx - 4, cy) * 0.9;

  ctx.clearRect(0, 0, w, h);

  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0, false);
  ctx.strokeStyle = 'rgba(255,255,255,0.07)';
  ctx.lineWidth = 10;
  ctx.lineCap = 'butt';
  ctx.stroke();

  var color;
  if      (score <= 20) color = '#dc2626';
  else if (score <= 40) color = '#f97316';
  else if (score <= 60) color = '#e2e2e2';
  else if (score <= 80) color = '#86efac';
  else                  color = '#22c55e';

  var endAngle = Math.PI + (score / 100) * Math.PI;
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, endAngle, false);
  ctx.strokeStyle = color;
  ctx.lineWidth = 10;
  ctx.lineCap = 'round';
  ctx.stroke();

  var valEl = document.getElementById('gauge-val');
  if (valEl) { valEl.textContent = Math.round(score); valEl.style.color = color; }

  var labelEl = document.getElementById('gauge-label');
  if (labelEl) {
    var label;
    if      (score <= 20) label = 'EXTREME FEAR';
    else if (score <= 40) label = 'FEAR';
    else if (score <= 60) label = 'NEUTRAL';
    else if (score <= 80) label = 'GREED';
    else                  label = 'EXTREME GREED';
    labelEl.textContent = label;
    labelEl.style.color = color;
  }
};

VoiceIntel.prototype.renderKeywords = function(keywords) {
  var el = document.getElementById('intel-keywords');
  if (!el) return;
  el.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });

  if (!keywords.length) {
    el.innerHTML = '<span class="intel-empty-sm">No keywords available</span>';
    return;
  }

  var maxWeight = Math.max.apply(null, keywords.map(function(k) { return k.weight || 1; }));
  el.innerHTML = keywords.slice(0, 14).map(function(kw) {
    var w = kw.weight || 1;
    var ratio = w / maxWeight;
    var fontSize = 9 + Math.round(ratio * 5);
    var opacity = 0.5 + ratio * 0.5;
    var word = kw.keyword || '';
    var isBear = /FUD|BEAR|DUMP|CRASH|FEAR/i.test(word);
    var color = isBear ? '#f97316' : 'rgba(204,0,0,0.85)';
    return '<span class="intel-keyword" style="font-size:' + fontSize + 'px;opacity:' + opacity + ';border-color:' + color + '25;color:' + color + '">' + escapeHtml(word) + '</span>';
  }).join('');
};

VoiceIntel.prototype.renderSpacesRadar = function() {
  var el = document.getElementById('intel-spaces');
  if (!el) return;

  el.innerHTML = SPACES_ACCOUNTS.map(function(acc) {
    var imgUrl = 'https://unavatar.io/twitter/' + encodeURIComponent(acc.handle);
    var profileUrl = 'https://x.com/' + encodeURIComponent(acc.handle);
    var avatarColor = getAvatarColor(acc.handle);
    return '<a class="intel-spaces-row" href="' + escapeHtml(profileUrl) + '" target="_blank" rel="noopener">' +
      '<div class="mu-avatar" style="--avatar-color:' + avatarColor + ';width:28px;height:28px">' +
        '<img src="' + escapeHtml(imgUrl) + '" loading="lazy" width="28" height="28" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' +
        '<span class="mu-avatar-fallback" style="display:none">' + acc.name[0].toUpperCase() + '</span>' +
      '</div>' +
      '<div class="intel-spaces-info">' +
        '<span class="intel-spaces-name">@' + escapeHtml(acc.handle) + '</span>' +
        '<span class="intel-spaces-sub">' + escapeHtml(acc.name) + '</span>' +
      '</div>' +
      '<span class="intel-spaces-link">&rarr;</span>' +
    '</a>';
  }).join('');
};

VoiceIntel.prototype.renderSourceHealth = function() {
  var el = document.getElementById('intel-health');
  if (!el) return;

  var sources = [
    { key: 'nostr',  label: 'Nostr'       },
    { key: 'x',      label: 'X / Twitter'  },
    { key: 'reddit', label: 'Reddit'       },
    { key: 'rss',    label: 'RSS / News'   }
  ];

  el.innerHTML = sources.map(function(s) {
    return '<div class="intel-health-row">' +
      '<div class="mu-health-dot loading" id="sh-dot-' + s.key + '"></div>' +
      '<span class="intel-health-label">' + s.label + '</span>' +
      '<span class="intel-health-time" id="sh-time-' + s.key + '">--</span>' +
    '</div>';
  }).join('');
};

// ─── SOURCE HEALTH UPDATER ────────────────────────────
function updateSourceHealth(lastReceived) {
  var now = Date.now();
  var fiveMin = 5 * 60 * 1000;

  var labelToKey = {
    'X': 'x', 'REDDIT': 'reddit', 'RSS': 'rss', 'NEWS': 'rss',
    'STACKER NEWS': 'rss', 'NOSTR': 'nostr'
  };

  var slotBest = {};
  Object.keys(lastReceived).forEach(function(platformLabel) {
    var ts = lastReceived[platformLabel];
    var key = labelToKey[platformLabel.toUpperCase()] || 'rss';
    if (!slotBest[key] || ts > slotBest[key]) slotBest[key] = ts;
  });

  ['nostr', 'x', 'reddit', 'rss'].forEach(function(key) {
    var dotEl = document.getElementById('sh-dot-' + key);
    var timeEl = document.getElementById('sh-time-' + key);
    var ts = slotBest[key];

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

function markNostrSourceHealthActive() {
  var dotEl = document.getElementById('sh-dot-nostr');
  var timeEl = document.getElementById('sh-time-nostr');
  if (dotEl) { dotEl.classList.remove('loading', 'error'); dotEl.classList.add('connected'); }
  if (timeEl) timeEl.textContent = 'live';
}

// ─── SIGNAL STRENGTH ──────────────────────────────────
function updateSignalStrength() {
  var oneHourAgo = Date.now() / 1000 - 3600;
  var recentNotes = state.nostrNotes.filter(function(n) { return n.created_at > oneHourAgo; }).length;
  var nostrScore = Math.min(recentNotes / 30 * 100, 100);

  var chainScore = 50;
  if (state.chainData && state.chainData.mempool) {
    var count = state.chainData.mempool.count || 0;
    chainScore = Math.min(count / 100000 * 100, 100);
  }

  var sentimentScore = (state.fngData && state.fngData.data && state.fngData.data[0])
    ? parseInt(state.fngData.data[0].value) : 50;

  state.signalScore = Math.round(nostrScore * 0.35 + chainScore * 0.30 + sentimentScore * 0.35);

  state.sentimentScore = sentimentScore;

  var fill = $('#signal-fill');
  if (fill) {
    fill.style.width = state.signalScore + '%';
    if      (state.signalScore > 70) fill.style.background = '#22c55e';
    else if (state.signalScore > 40) fill.style.background = '#f7931a';
    else                             fill.style.background = '#cc0000';
  }
  splitFlap($('#sig-composite'), state.signalScore);
  splitFlap($('#sig-sentiment'), state.sentimentScore || 0);
  splitFlap($('#sig-spaces'), state.spacesScore || 0);
}

function updateNostrCount() {
  var el = $('#nostr-count');
  if (el) {
    el.textContent = state.nostrNotes.length + ' notes';
    markNostrSourceHealthActive();
  }
  // Update hero live notes count
  var liveN = $('#liveN');
  if (liveN) liveN.textContent = state.nostrNotes.length;
}

// ─── HIGHLIGHTS ───────────────────────────────────────
function renderHighlights() {
  var container = $('#highlights-container');
  if (!container || !state.highlights) return;
  container.innerHTML = state.highlights.map(function(h) {
    return '<div class="highlight-item">' + (h.content || h.text || '') + '</div>';
  }).join('');
}

function fetchHighlights() {
  fetch('/api/media/highlights').then(function(res) {
    if (res.ok) return res.json();
  }).then(function(data) {
    if (data) {
      state.highlights = data;
      renderHighlights();
    }
  }).catch(function() {});
}

// ─── HEALTH HELPER ────────────────────────────────────
function setHealth(id, status) {
  var dot = document.getElementById(id);
  if (!dot) return;
  dot.classList.remove('loading', 'connected', 'error');
  dot.classList.add(status);
}

// ═══════════════════════════════════════════════════════
// OLD /media FUNCTIONS — Series Panel, Podcast, Books
// ═══════════════════════════════════════════════════════

// ─── SERIES EPISODE PANEL ─────────────────────────────
window.toggleSD = function(k) {
  var p = document.getElementById('sdPanel');
  if (state.currentSeries === k && p.classList.contains('active')) {
    window.closeSD();
    return;
  }
  var s = SD[k];
  if (!s || !s.episodes || !s.episodes.length) return;
  state.currentSeries = k;
  document.getElementById('sdTitle').textContent = s.title || k;
  var e0 = s.episodes[0];
  document.getElementById('sdIf').src = 'https://www.youtube.com/embed/' + e0.id + '?autoplay=1';
  var sb = document.getElementById('sdEps');
  sb.innerHTML = s.episodes.map(function(ep, i) {
    return '<div class="sd-ep' + (i === 0 ? ' active' : '') + '" onclick="playSE(\'' + ep.id + '\',' + i + ',this)">' +
      '<img class="sd-ep-img" src="https://img.youtube.com/vi/' + ep.id + '/mqdefault.jpg" loading="lazy">' +
      '<div class="sd-ep-info"><div class="sd-ep-n">EP ' + (i + 1) + '</div><div class="sd-ep-t">' + ep.title + '</div></div></div>';
  }).join('');
  p.classList.add('active');
  setTimeout(function() { p.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);
};

window.playSE = function(id, i, el) {
  document.getElementById('sdIf').src = 'https://www.youtube.com/embed/' + id + '?autoplay=1';
  document.querySelectorAll('.sd-ep').forEach(function(e) { e.classList.remove('active'); });
  if (el) el.classList.add('active');
};

window.closeSD = function() {
  document.getElementById('sdIf').src = '';
  document.getElementById('sdPanel').classList.remove('active');
  state.currentSeries = null;
};

// ─── PODCAST AUDIO PLAYER ─────────────────────────────
var au = null;

window.playEp = function(u, t) {
  if (!u) return;
  if (!au) au = document.getElementById('aEl');
  if (!au) return;
  au.src = u;
  au.play().catch(function() {});
  state.audioPlaying = true;
  document.getElementById('aNow').textContent = t;
  document.getElementById('aIcon').className = 'fas fa-pause';
  document.getElementById('abar').classList.add('active');
};

window.togA = function() {
  if (!au) au = document.getElementById('aEl');
  if (!au) return;
  if (state.audioPlaying) {
    au.pause();
    document.getElementById('aIcon').className = 'fas fa-play';
  } else {
    au.play().catch(function() {});
    document.getElementById('aIcon').className = 'fas fa-pause';
  }
  state.audioPlaying = !state.audioPlaying;
};

window.stopA = function() {
  if (!au) au = document.getElementById('aEl');
  if (!au) return;
  au.pause();
  au.src = '';
  state.audioPlaying = false;
  document.getElementById('abar').classList.remove('active');
};

// ─── BOOKS SHOW MORE TOGGLE ──────────────────────────
window.togB = function() {
  document.getElementById('bmore').classList.toggle('show');
  document.getElementById('btog').classList.toggle('open');
};

// ─── COMMAND PALETTE ──────────────────────────────────
function CommandPalette() {
  this.overlay = $('#cmd-overlay');
  this.input = $('#cmd-input');
  this.results = $('#cmd-results');
  this.selectedIdx = -1;
  this.commands = [
    { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Intelligence Feed', action: function() { var el = $('#mu-signals'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
    { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Series',            action: function() { var el = $('#mu-series'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
    { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Podcasts',          action: function() { var el = $('#mu-podcasts'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
    { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Library',           action: function() { var el = $('#mu-library'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
    { group: 'ACTIONS',  icon: '\u25cb', label: 'Fullscreen',              action: function() { if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen(); } },
    { group: 'ACTIONS',  icon: '\u25cb', label: 'Open mempool.space',      action: function() { window.open('https://mempool.space', '_blank'); } },
    { group: 'ACTIONS',  icon: '\u25cb', label: 'Copy share link',         action: function() { if (navigator.clipboard) navigator.clipboard.writeText(location.href); } }
  ];
  this._bind();
}

CommandPalette.prototype._bind = function() {
  var self = this;
  document.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); self.toggle(); }
    if (e.key === 'Escape' && self.overlay && self.overlay.classList.contains('active')) { e.preventDefault(); self.close(); }
  });

  if (this.input) {
    this.input.addEventListener('input', function() { self._render(); });
    this.input.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowDown') { self.selectedIdx++; self._render(); e.preventDefault(); }
      if (e.key === 'ArrowUp')   { self.selectedIdx--; self._render(); e.preventDefault(); }
      if (e.key === 'Enter')     { self._execute(); e.preventDefault(); }
    });
  }

  if (this.overlay) {
    this.overlay.addEventListener('click', function(e) { if (e.target === self.overlay) self.close(); });
  }
};

CommandPalette.prototype.toggle = function() {
  if (this.overlay && this.overlay.classList.contains('active')) this.close();
  else this.open();
};

CommandPalette.prototype.open = function() {
  if (this.overlay) this.overlay.classList.add('active');
  if (this.input) { this.input.focus(); this.input.value = ''; }
  this.selectedIdx = -1;
  this._render();
};

CommandPalette.prototype.close = function() {
  if (this.overlay) this.overlay.classList.remove('active');
};

CommandPalette.prototype._render = function() {
  if (!this.results) return;
  var q = (this.input && this.input.value || '').toLowerCase();
  var filtered = q ? this.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q) >= 0; }) : this.commands;
  this.selectedIdx = Math.max(-1, Math.min(this.selectedIdx, filtered.length - 1));

  var html = '';
  var lastGroup = '';
  var self = this;
  filtered.forEach(function(cmd, i) {
    if (cmd.group !== lastGroup) {
      html += '<div class="mu-cmd-group-label">' + cmd.group + '</div>';
      lastGroup = cmd.group;
    }
    html += '<div class="mu-cmd-item' + (i === self.selectedIdx ? ' selected' : '') + '" data-idx="' + i + '">' +
      '<span class="icon">' + cmd.icon + '</span>' +
      '<span class="label">' + cmd.label + '</span>' +
    '</div>';
  });
  this.results.innerHTML = html;

  this.results.querySelectorAll('.mu-cmd-item').forEach(function(el) {
    el.addEventListener('click', function() {
      var idx = parseInt(el.dataset.idx);
      var q2 = (self.input && self.input.value || '').toLowerCase();
      var f2 = q2 ? self.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q2) >= 0; }) : self.commands;
      if (f2[idx]) { f2[idx].action(); self.close(); }
    });
  });
};

CommandPalette.prototype._execute = function() {
  var q = (this.input && this.input.value || '').toLowerCase();
  var filtered = q ? this.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q) >= 0; }) : this.commands;
  var cmd = filtered[Math.max(0, this.selectedIdx)];
  if (cmd) { cmd.action(); this.close(); }
};

// ─── FEED FILTER CHIPS ────────────────────────────────
function initFeedFilters(combinedFeed) {
  var chips = $$('.intel-chip[data-filter]');
  chips.forEach(function(chip) {
    chip.addEventListener('click', function() {
      chips.forEach(function(c) { c.classList.remove('active'); });
      chip.classList.add('active');
      combinedFeed.activeFilter = chip.dataset.filter;
      if (combinedFeed.items.length > 0) {
        combinedFeed._firstLoad = true;
        combinedFeed.render(combinedFeed.items);
      }
    });
  });
}

// ─── SCROLL REVEAL (IntersectionObserver) ─────────────
function initScrollReveal() {
  if (!('IntersectionObserver' in window)) {
    $$('.mu-reveal').forEach(function(el) { el.classList.add('visible'); });
    return;
  }

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });

  $$('.mu-reveal').forEach(function(el) { observer.observe(el); });
}

// ─── TIMESTAMP UPDATER ────────────────────────────────
function initTimeUpdater() {
  setInterval(function() {
    $$('.intel-card-time').forEach(function(el) {
      var ts = parseInt(el.dataset.ts);
      if (ts) el.textContent = formatTimeAgo(ts);
    });
  }, 30000);
}

// ─── KEYBOARD: Escape closes series panel ─────────────
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var sdPanel = document.getElementById('sdPanel');
    if (sdPanel && sdPanel.classList.contains('active')) window.closeSD();
  }
});

// ─── INIT ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  // Core engines
  var nostrFeed    = new NostrFeed();
  var telemetry    = new TelemetryEngine();
  var combinedFeed = new CombinedFeed();
  var voiceIntel   = new VoiceIntel();
  var cmdPalette   = new CommandPalette();

  // Start data flows
  nostrFeed.init();
  telemetry.start();
  combinedFeed.start();
  voiceIntel.start();

  // Signal strength
  setInterval(updateSignalStrength, POLL_INTERVALS.signal);
  setTimeout(updateSignalStrength, 5000);

  // UI modules
  initFeedFilters(combinedFeed);
  initScrollReveal();
  initTimeUpdater();

  // Cmd+K hint
  var cmdHint = $('#cmd-k-hint');
  if (cmdHint) cmdHint.addEventListener('click', function() { cmdPalette.open(); });

  // Loading skeletons safety net
  ['#nostr-feed', '#combined-feed'].forEach(function(sel) {
    var el = $(sel);
    if (el && !el.children.length) {
      el.innerHTML = '<div class="mu-skeleton mu-skel-block"></div><div class="mu-skeleton mu-skel-block"></div><div class="mu-skeleton mu-skel-block"></div>';
    }
  });

  console.log('[Media Unified v3.0] Phase 3: The Network online. Relays:', NOSTR_RELAYS.length);
});

})();
