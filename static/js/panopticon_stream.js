// ── PANOPTICON REAL-TIME SSE CLIENT ──────────────────────────────────────────
// Replaces all setInterval polling with a single persistent SSE connection.
// Reconnects automatically on disconnect with exponential backoff.

(function() {
  var _es = null;
  var _reconnectDelay = 2000;
  var _maxDelay = 60000;
  var _reconnectTimer = null;
  var _lastBtcPrice = 0;

  // ── Connect ─────────────────────────────────────────────────────────────────
  function connectSSE() {
    if (_es) { try { _es.close(); } catch(e) {} }

    _es = new EventSource('/api/panopticon/stream');

    _es.onopen = function() {
      _reconnectDelay = 2000;
      setStreamStatus(true);
    };

    _es.onerror = function() {
      setStreamStatus(false);
      _es.close();
      scheduleReconnect();
    };

    _es.onmessage = function(e) {
      try {
        var d = JSON.parse(e.data);
        routeEvent(d);
      } catch(err) {}
    };
  }

  function scheduleReconnect() {
    if (_reconnectTimer) clearTimeout(_reconnectTimer);
    _reconnectTimer = setTimeout(function() { connectSSE(); }, _reconnectDelay);
    _reconnectDelay = Math.min(_reconnectDelay * 2, _maxDelay);
  }

  // ── Status indicator ─────────────────────────────────────────────────────────
  function setStreamStatus(live) {
    var dot = document.getElementById('pnStreamDot');
    var label = document.getElementById('pnStreamLabel');
    if (dot) { dot.style.background = live ? '#22c55e' : '#ef4444'; dot.style.animation = live ? 'pn-pulse 1s ease-in-out infinite' : 'none'; }
    if (label) label.textContent = live ? 'LIVE' : 'RECONNECTING';
  }

  // ── Event router ─────────────────────────────────────────────────────────────
  function routeEvent(d) {
    switch(d.type) {
      case 'orb_update':      handleOrb(d);       break;
      case 'whale_alert':
      case 'whale_update':    handleWhales(d);    break;
      case 'congress_update': handleCongress(d);  break;
      case 'geo_update':      handleGeo(d);       break;
      case 'heartbeat':       handleHeartbeat(d); break;
      case 'connected':       handleConnected(d); break;
    }
  }

  // ── Orb handler ──────────────────────────────────────────────────────────────
  function handleOrb(d) {
    // BTC price in header ticker
    var priceEl = document.querySelector('.pp-btc-price, #btcPrice, [data-btc-price]');
    if (priceEl && d.btc && d.btc.price) {
      var price = parseFloat(d.btc.price);
      var prev = _lastBtcPrice;
      if (prev && price !== prev) {
        priceEl.style.color = price > prev ? '#22c55e' : '#ef4444';
        setTimeout(function() { priceEl.style.color = ''; }, 2000);
      }
      priceEl.textContent = '$' + price.toLocaleString('en-US', {maximumFractionDigits: 0});
      _lastBtcPrice = price;
    }

    // Fear & Greed
    var fgEl = document.getElementById('pnFearGreed');
    if (fgEl && d.fear_greed) {
      var fgv = d.fear_greed.value || 0;
      var fgCol = fgv < 25 ? '#ef4444' : fgv < 45 ? '#f97316' : fgv < 55 ? '#f8c15c' : fgv < 75 ? '#22c55e' : '#16a34a';
      fgEl.innerHTML = '<span style="font-size:22px;font-weight:900;color:' + fgCol + ';">' + fgv + '</span>'
        + '<span style="font-size:9px;color:' + fgCol + ';margin-left:6px;letter-spacing:.1em;">' + (d.fear_greed.label || '').toUpperCase() + '</span>';
    }

    // Convergence state
    var convEl = document.getElementById('pnConvergenceState');
    if (convEl && d.convergence) {
      var stateColors = {IDLE:'#888', WATCH:'#f8c15c', ALERT:'#f97316', CRITICAL:'#ef4444'};
      var state = d.convergence.state || 'IDLE';
      convEl.innerHTML = '<span style="color:' + (stateColors[state]||'#888') + ';font-weight:700;">' + state + '</span>';
    }

    // Signal score
    var sigEl = document.getElementById('pnSignalScore');
    if (sigEl && d.signal_score) {
      var bull = d.signal_score.bull_count || 0;
      var bear = d.signal_score.bear_count || 0;
      sigEl.innerHTML = '<span style="color:#22c55e;">' + bull + ' bull</span> / <span style="color:#ef4444;">' + bear + ' bear</span>';
    }

    // Flash new-data indicator on hero
    var hero = document.querySelector('.pn-hero-ring');
    if (hero) {
      hero.style.boxShadow = '0 0 30px rgba(204,0,0,0.4)';
      setTimeout(function() { hero.style.boxShadow = ''; }, 800);
    }
  }

  // ── Whale handler ─────────────────────────────────────────────────────────────
  function handleWhales(d) {
    var el = document.getElementById('pnWhales');
    if (!el) return;
    var alerts = d.alerts || [];
    if (!alerts.length) return;

    // If it's a new alert, prepend with flash
    if (d.type === 'whale_alert' && d.new_count > 0) {
      flashElement(el);
      // Prepend new alerts to existing list
      var newHtml = '';
      (d.alerts || []).forEach(function(a) {
        newHtml += renderWhaleItem(a, true);
      });
      el.innerHTML = newHtml + el.innerHTML;
      // Trim to 12 items
      var items = el.querySelectorAll('.pn-whale-item');
      for (var i = 12; i < items.length; i++) items[i].remove();
    } else {
      // Full refresh
      var html = '';
      alerts.slice(0, 12).forEach(function(a) { html += renderWhaleItem(a, false); });
      el.innerHTML = html || '<div class="pn-empty">Monitoring whale wallets...</div>';
    }
  }

  function renderWhaleItem(a, isNew) {
    var amt = parseFloat(a.amount_btc || 0).toFixed(1);
    var col = parseFloat(amt) > 500 ? '#ef4444' : parseFloat(amt) > 100 ? '#f97316' : '#f8c15c';
    var flash = isNew ? ' style="animation:pn-flash-in .6s ease;"' : '';
    return '<div class="pn-whale-item"' + flash + '>'
      + '<div style="display:flex;justify-content:space-between;align-items:center;">'
      + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.7);">'
      + (a.wallet_label || 'Unknown Wallet').substring(0,28) + '</span>'
      + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:' + col + ';font-weight:700;">'
      + amt + ' BTC</span></div>'
      + '<div style="font-size:8px;color:rgba(255,255,255,0.3);margin-top:3px;">'
      + (a.tx_type || 'transfer').toUpperCase() + ' · ' + (a.timestamp || '').substring(0,10) + '</div>'
      + '</div>';
  }

  // ── Congress handler ──────────────────────────────────────────────────────────
  function handleCongress(d) {
    // Update IHX
    var ihxEl = document.getElementById('pnIHX');
    if (ihxEl && d.ihx) {
      var s = d.ihx.score || 50;
      var col = s > 65 ? '#22c55e' : s < 35 ? '#ef4444' : '#f8c15c';
      ihxEl.innerHTML = '<div style="display:flex;align-items:center;gap:12px;">'
        + '<div style="font-size:28px;font-weight:900;color:' + col + ';">' + s + '</div>'
        + '<div><div style="font-size:10px;font-weight:700;color:' + col + ';">' + (d.ihx.signal||'neutral').toUpperCase() + '</div>'
        + '<div style="font-size:8px;color:rgba(255,255,255,0.4);margin-top:2px;">' + (d.ihx.interpretation||'') + '</div></div></div>'
        + '<div style="height:3px;background:rgba(255,255,255,0.04);border-radius:2px;margin-top:8px;">'
        + '<div style="height:100%;width:' + s + '%;background:' + col + ';border-radius:2px;transition:width .6s ease;"></div></div>';
    }
    if (d.score_changed) flashElement(ihxEl);

    // Update trades table
    var trEl = document.getElementById('pnCongress');
    if (trEl && d.trades && d.trades.length) {
      var html = '<div style="display:flex;flex-direction:column;gap:6px;">';
      d.trades.slice(0,8).forEach(function(t) {
        var isBuy = (t.transaction||'').toLowerCase().includes('purchase');
        var col2 = isBuy ? '#22c55e' : '#ef4444';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
          + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">'
          + (t.member||t.entity||'').substring(0,22) + '</div>'
          + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:2px;">'
          + (t.ticker||'???') + ' · ' + (t.date||'').substring(0,10) + '</div></div>'
          + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:' + col2 + ';font-weight:700;">'
          + (isBuy?'BUY':'SELL') + '</span></div>';
      });
      html += '</div>';
      trEl.innerHTML = html;
    }
  }

  // ── Geo handler ──────────────────────────────────────────────────────────────
  function handleGeo(d) {
    var el = document.getElementById('pnGeo');
    if (!el || !d.signals) return;
    // Only update if we have new signals
    var html = '';
    d.signals.slice(0,4).forEach(function(g) {
      var sigTag = g.btc_signal === 'bullish' ? '#22c55e' : g.btc_signal === 'bearish' ? '#ef4444' : '#888';
      html += '<div class="pn-geo-item" style="animation:pn-flash-in .4s ease;">'
        + '<div class="pn-geo-headline">' + (g.headline||'') + '</div>'
        + '<span style="color:' + sigTag + ';font-size:8px;font-family:\'JetBrains Mono\',monospace;font-weight:700;letter-spacing:.1em;">BTC ' + (g.btc_signal||'neutral').toUpperCase() + '</span>'
        + '<div class="pn-geo-rationale">' + (g.btc_rationale||'') + '</div>'
        + '</div>';
    });
    if (html) el.innerHTML = html;
  }

  // ── Heartbeat ─────────────────────────────────────────────────────────────────
  function handleHeartbeat(d) {
    var el = document.getElementById('pnLastUpdate');
    if (el) {
      var now = new Date();
      el.textContent = 'Updated ' + now.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    }
  }

  function handleConnected(d) {
    setStreamStatus(true);
    var el = document.getElementById('pnStreamMode');
    if (el) el.textContent = d.commander ? 'COMMANDER FEED' : 'LIVE FEED';
  }

  // ── Utility ──────────────────────────────────────────────────────────────────
  function flashElement(el) {
    if (!el) return;
    el.style.transition = 'background .15s';
    el.style.background = 'rgba(204,0,0,0.08)';
    setTimeout(function() { el.style.background = ''; }, 600);
  }

  // ── CSS animation injection ───────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = '@keyframes pn-flash-in { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }';
  document.head.appendChild(style);

  // ── Boot ──────────────────────────────────────────────────────────────────────
  if (window.EventSource) {
    connectSSE();
  } else {
    // Fallback: keep existing polling for old browsers
    console.warn('EventSource not supported — falling back to polling');
  }

  // Reconnect on tab visibility change (mobile/background tabs)
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden && (!_es || _es.readyState === EventSource.CLOSED)) {
      connectSSE();
    }
  });
})();
