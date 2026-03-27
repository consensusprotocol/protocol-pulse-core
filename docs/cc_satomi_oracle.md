Read ~/protocol_pulse/templates/stage.html — focus on the topbar ticker JS (around line 1000-1100) and the ticker HTML (lines 706-756).
Read ~/protocol_pulse/templates/oracle_live.html — lines 1-20 (title) and 760-800 (GREETING and S object).
Read ~/protocol_pulse/core/routes.py — search for "def.*btc.*price" and "api/btc-price".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5 SURGICAL FIXES — TICKER + ORACLE/SATOMI CLEANUP + BTC PRICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — STAGE TOPBAR TICKER: populate live data
The ticker shows BITCOIN "Loading…", SENTIMENT "—", NETWORK "—"
because there is no JS that fetches and fills these values.

In stage.html, after the DOMContentLoaded or in the init block,
add a function that fetches and updates ticker values every 30s:

function updateTopbarTicker() {
  // Bitcoin price
  fetch('/api/signal-cache')
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d) return;
      var price = d.btc_price || d.bitcoin_price || 0;
      var fng = d.fear_greed_value || d.fng || '';
      var fng_label = d.fear_greed_label || '';
      var hashrate = d.hashrate_eh || d.network_hashrate || '';
      
      var priceStr = price ? '$' + Number(price).toLocaleString('en-US', {maximumFractionDigits:0}) : '---';
      var sentStr = (fng && fng_label) ? fng + ' · ' + fng_label : '—';
      var netStr = hashrate ? hashrate + ' EH/s' : '—';
      
      // Update both copies of ticker (original + duplicate for loop)
      ['tickerPrice','tickerPrice2'].forEach(id => {
        var el = document.getElementById(id);
        if (el) el.textContent = priceStr;
      });
      ['tickerSentiment','tickerSentiment2'].forEach(id => {
        var el = document.getElementById(id);
        if (el) el.textContent = sentStr;
      });
      ['tickerTopics','tickerTopics2'].forEach(id => {
        var el = document.getElementById(id);
        if (el) el.textContent = netStr;
      });
    })
    .catch(function(){});
    
  // If signal-cache doesn't have it, try the intelligence API
  fetch('/api/btc-price')
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d) return;
      var price = d.price || (d.bitcoin && d.bitcoin.usd) || 0;
      if (!price) return;
      var priceStr = '$' + Number(price).toLocaleString('en-US', {maximumFractionDigits:0});
      ['tickerPrice','tickerPrice2'].forEach(id => {
        var el = document.getElementById(id);
        if (el) el.textContent = priceStr;
      });
    })
    .catch(function(){});
}

Call updateTopbarTicker() on load and setInterval(updateTopbarTicker, 30000).

FIX 2 — STAGE TOPBAR: rename "ORACLE" label to "SATOMI"
In stage.html find all instances of:
  <span class="ti-label">ORACLE</span>
Replace with:
  <span class="ti-label">SATOMI</span>
There are 2 instances (original + duplicate). Change both.

FIX 3 — ORACLE LIVE PAGE: full Satomi rename
In oracle_live.html:
  a) Line 1: <title>Oracle · Protocol Pulse</title>
     → <title>Satomi · Protocol Pulse</title>
  
  b) Line ~766: GREETING:"Hey. I'm the Oracle — tracking everything happening..."
     → GREETING:"Hey. I'm Satomi — your Protocol Pulse intelligence anchor. On-chain, macro, geopolitical. What can I help you with?"
  
  c) Find any other "Oracle" references in visible text (not in JS variable names
     or route paths like /oracle or oracle_live):
     grep -n "Oracle" ~/protocol_pulse/templates/oracle_live.html | grep -v "route\|url\|class\|id\|oracle_live\|oracle_widget\|/oracle" | head -20
     Change "Oracle" → "Satomi" in displayed text only.
  
  d) Remove the subtitle text display: the #subtitle div shows the greeting
     text on screen. Find where subtitle.textContent or subtitle.innerHTML
     is set with the greeting text and either:
     - Remove it entirely (just play audio, no on-screen text), OR
     - Show a cleaner status like "Speaking..." 
     The user wants the text removed from view.
     Find: sub.textContent = ... or subtitle.innerHTML = ...
     Comment it out or replace with empty string.

FIX 4 — ADD /api/btc-price ROUTE to core/routes.py
The route is called by both base.html and stage.html but doesn't exist.
The internal function _fetch_btc_price() exists at line ~8916.

Add this route near the other API routes:
  @app.route('/api/btc-price')
  def api_btc_price():
      """Live BTC price endpoint used by nav ticker and stage."""
      try:
          import requests as _req
          r = _req.get(
              'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true',
              timeout=5, headers={'User-Agent': 'ProtocolPulse/1.0'}
          )
          if r.ok:
              d = r.json()
              price = d.get('bitcoin', {}).get('usd', 0)
              change = d.get('bitcoin', {}).get('usd_24h_change', 0)
              from flask import jsonify
              return jsonify({'price': price, 'change_24h': round(change, 2)})
      except Exception:
          pass
      # Fallback: try internal cache
      try:
          cache_file = '/home/ultron/protocol_pulse/data/btc_price_cache.json'
          import json, os
          if os.path.exists(cache_file):
              data = json.loads(open(cache_file).read())
              from flask import jsonify
              return jsonify(data)
      except Exception:
          pass
      from flask import jsonify
      return jsonify({'price': 0, 'change_24h': 0}), 200

FIX 5 — MOBILE TICKER SPEED
The ticker spazzes on mobile because animation-duration is too fast
for the content width on small screens.
Find the CSS for .stage-topbar__ticker-inner:
  animation: ticker-scroll 40s linear infinite;
The mobile override currently sets 45s. Change mobile to 60s:
  @media (max-width: 768px) {
    .stage-topbar__ticker-inner { animation-duration: 60s; }
  }
Also add for very small screens (<480px):
  @media (max-width: 480px) {
    .stage-topbar__ticker-inner { animation-duration: 80s; }
  }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/api/btc-price
  # Expected: 200
  
  curl -s --max-time 5 http://localhost:5000/api/btc-price | python3 -m json.tool
  # Expected: {"price": 71000+, "change_24h": ...}
  
  grep -c "Oracle.*Protocol Pulse" ~/protocol_pulse/templates/oracle_live.html
  # Expected: 0 (title changed to Satomi)
  
  grep -c "ti-label.*ORACLE" ~/protocol_pulse/templates/stage.html
  # Expected: 0 (changed to SATOMI)
  
  kill -HUP $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1)
  sleep 6
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/oracle-live

COMMIT:
  git add templates/stage.html templates/oracle_live.html core/routes.py
  git commit -m "fix(satomi+ticker): live ticker data + Satomi rename oracle page + /api/btc-price route + mobile ticker speed"
  git push
