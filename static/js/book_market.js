/* /books/market: Book Market map, map/table toggle and sortable table. Illustrative data only.
   No libraries, no CDN.

   BookMarketLayout (pure, no DOM; tests/books runs it under node):
     coverSize(s, aspect, aMin, aMax)  cover AREA = aMin + (aMax - aMin) * s, s in [0, 1];
                                        width = sqrt(area * aspect), height = sqrt(area / aspect)
                                        so the area follows s and the cover keeps its shape.
     separate(nodes, opt)              pushes overlapping covers apart, then clamps every cover to
                                        at most opt.maxDx / opt.maxDy from its data point (a hard
                                        cap, e.g. 6% of each axis span). Deterministic.
     geometry(W, H, compact)           plot box, paddings and the cover area range for a map size.
     recency(year, asOfYear)           horizontal scale input: -log(1 + age in years), so recent
                                        years get more room and one old title cannot squeeze the
                                        rest into a corner. Monotonic: left is always older.
     yearTicks(years, X, minGap)       the plotted books' own years as axis labels, newest first,
                                        dropping any label closer than minGap px to a kept one. */
(function (root) {
  'use strict';

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function coverSize(s, aspect, aMin, aMax) {
    var area = aMin + (aMax - aMin) * clamp(s, 0, 1);
    return { w: Math.sqrt(area * aspect), h: Math.sqrt(area / aspect), area: area };
  }

  function overlap(a, b, pad) {
    var ox = (a.w + b.w) / 2 + pad - Math.abs(a.px - b.px);
    var oy = (a.h + b.h) / 2 + pad - Math.abs(a.py - b.py);
    return ox > 0 && oy > 0 ? { x: ox, y: oy } : null;
  }

  function separate(nodes, opt) {
    var pad = opt.pad || 0;
    var maxIter = opt.iterations || 160;
    var ns = nodes.map(function (n) { return { x: n.x, y: n.y, w: n.w, h: n.h, px: n.x, py: n.y }; });
    var iterations = 0, converged = false;
    for (var it = 0; it < maxIter; it += 1) {
      var moved = false;
      var before = ns.map(function (n) { return [n.px, n.py]; });
      for (var i = 0; i < ns.length; i += 1) {
        for (var j = i + 1; j < ns.length; j += 1) {
          var a = ns[i], b = ns[j], o = overlap(a, b, pad);
          if (!o) continue;
          moved = true;
          // Move along the axis whose push costs less of that axis's displacement budget.
          if (o.x / opt.maxDx <= o.y / opt.maxDy) {
            var sx = a.px < b.px || (a.px === b.px && a.x <= b.x) ? -1 : 1;
            a.px += sx * o.x / 2;
            b.px -= sx * o.x / 2;
          } else {
            var sy = a.py < b.py || (a.py === b.py && a.y <= b.y) ? -1 : 1;
            a.py += sy * o.y / 2;
            b.py -= sy * o.y / 2;
          }
        }
      }
      for (var k = 0; k < ns.length; k += 1) {
        var n = ns[k];
        if (opt.bounds) {
          n.px = clamp(n.px, opt.bounds.x0 + n.w / 2, opt.bounds.x1 - n.w / 2);
          n.py = clamp(n.py, opt.bounds.y0 + n.h / 2, opt.bounds.y1 - n.h / 2);
        }
        // The hard cap comes last, so it always holds.
        n.px = clamp(n.px, n.x - opt.maxDx, n.x + opt.maxDx);
        n.py = clamp(n.py, n.y - opt.maxDy, n.y + opt.maxDy);
      }
      iterations = it + 1;
      // Done when nothing overlaps, or when the caps stop every remaining push (no cover moved).
      var shift = 0;
      ns.forEach(function (n, idx) { shift = Math.max(shift, Math.abs(n.px - before[idx][0]), Math.abs(n.py - before[idx][1])); });
      if (!moved || shift < 0.01) { converged = true; break; }
    }
    var maxDx = 0, maxDy = 0, left = 0;
    ns.forEach(function (n) {
      n.dx = n.px - n.x;
      n.dy = n.py - n.y;
      maxDx = Math.max(maxDx, Math.abs(n.dx));
      maxDy = Math.max(maxDy, Math.abs(n.dy));
    });
    for (var p = 0; p < ns.length; p += 1) {
      for (var q = p + 1; q < ns.length; q += 1) { if (overlap(ns[p], ns[q], 0)) left += 1; }
    }
    return { nodes: ns, maxDx: maxDx, maxDy: maxDy, overlaps: left, iterations: iterations, converged: converged };
  }

  function geometry(W, H, compact) {
    var m = compact ? { l: 44, r: 10, t: 22, b: 40 } : { l: 64, r: 20, t: 26, b: 50 };
    var plotW = Math.max(W - m.l - m.r, 40), plotH = Math.max(H - m.t - m.b, 40);
    var wMax = clamp(plotW * (compact ? 0.12 : 0.085), 28, 96);
    var aMax = wMax * wMax * 1.5;
    var aMin = aMax * 0.3;
    // Room for the widest (aspect 0.8) and the tallest (aspect 0.55) cover at full size.
    var padX = Math.sqrt(aMax * 0.8) / 2 + 4;
    var padY = Math.sqrt(aMax / 0.55) / 2 + 4;
    return {
      W: W, H: H, m: m, plotW: plotW, plotH: plotH, aMin: aMin, aMax: aMax,
      x0: m.l + padX, x1: m.l + plotW - padX, y0: m.t + padY, y1: m.t + plotH - padY,
      bounds: { x0: m.l, x1: m.l + plotW, y0: m.t, y1: m.t + plotH }
    };
  }

  function recency(year, asOfYear) { return -Math.log(1 + Math.max(asOfYear - year, 0)); }

  function yearTicks(years, X, minGap) {
    var kept = [];
    years.slice().sort(function (a, b) { return b - a; }).forEach(function (y) {
      if (kept.indexOf(y) !== -1) return;
      if (kept.every(function (k) { return Math.abs(X(k) - X(y)) >= minGap; })) kept.push(y);
    });
    return kept;
  }

  var api = { coverSize: coverSize, overlap: overlap, separate: separate, geometry: geometry, recency: recency,
              yearTicks: yearTicks, clamp: clamp };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.BookMarketLayout = api;
}(typeof window !== 'undefined' ? window : this));

(function () {
  'use strict';
  if (typeof document === 'undefined') return;
  var L = window.BookMarketLayout;
  var page = document.getElementById('btMarket');
  if (!page) return;
  page.classList.add('has-js');

  var SVGNS = 'http://www.w3.org/2000/svg';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function el(tag, attrs, text) {
    var e = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function fmtRank(n) { return '#' + Number(n).toLocaleString('en-US'); }
  function fmtMom(v) {
    if (v == null) return 'no 7-day change';
    return (v > 0 ? '▲ ' : v < 0 ? '▼ ' : '') + Math.abs(v).toFixed(1) + '%' + (v > 0 ? ' improving' : v < 0 ? ' cooling' : '');
  }
  function fmtPct(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + '%'; }

  /* ── Map ── */
  var dataEl = document.getElementById('btMapData');
  var map = document.getElementById('btMap');
  var svg = document.getElementById('btMapSvg');
  var layer = document.getElementById('btMapNodes');
  var tip = document.getElementById('btTip');
  var debugBtn = document.getElementById('btDebugBtn');
  var debugOut = document.getElementById('btDebug');
  var data = dataEl ? JSON.parse(dataEl.textContent) : null;
  var nodes = [];
  var lastResult = null;

  function buildNodes() {
    data.books.forEach(function (b) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bt-node';
      btn.setAttribute('aria-label', b.title + ', published ' + b.pub_year + ', 7-day ' + fmtMom(b.momentum) +
        ', illustrative rank ' + fmtRank(b.rank));
      btn.setAttribute('data-slug', b.slug);
      var img = document.createElement('img');
      img.alt = '';
      img.decoding = 'async';
      img.src = b.cover_url;
      var fallback = document.createElement('span');
      fallback.className = 'bt-node-fallback';
      fallback.textContent = b.title;
      btn.appendChild(img);
      btn.appendChild(fallback);
      layer.appendChild(btn);
      nodes.push({ book: b, btn: btn, img: img, aspect: 2 / 3 });
    });
  }

  function whenLoaded(timeoutMs) {
    return Promise.race([
      Promise.all(nodes.map(function (n) {
        return new Promise(function (resolve) {
          function done() {
            // Natural aspect ratio of the actual cover; 2:3 if the image failed or is a placeholder.
            if (n.img.naturalWidth >= 10 && n.img.naturalHeight >= 10) n.aspect = n.img.naturalWidth / n.img.naturalHeight;
            else n.btn.classList.add('is-missing');
            resolve();
          }
          if (n.img.complete) done();
          else { n.img.addEventListener('load', done); n.img.addEventListener('error', done); }
        });
      })),
      new Promise(function (resolve) { setTimeout(resolve, timeoutMs); })
    ]);
  }

  function drawAxes(g) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute('viewBox', '0 0 ' + g.W + ' ' + g.H);
    svg.setAttribute('width', g.W);
    svg.setAttribute('height', g.H);
    var compact = g.W < 560;
    var frame = el('g', { 'class': 'bt-axes' });
    var rMin = L.recency(data.x.min, data.as_of_year), rMax = L.recency(data.x.max, data.as_of_year);
    var yMin = data.y.min, yMax = data.y.max;
    g.X = function (year) {
      if (rMax === rMin) return (g.x0 + g.x1) / 2;
      return g.x0 + (L.recency(year, data.as_of_year) - rMin) / (rMax - rMin) * (g.x1 - g.x0);
    };
    g.Y = function (mom) { return g.y0 + (yMax - mom) / (yMax - yMin) * (g.y1 - g.y0); };
    var bx0 = g.bounds.x0, bx1 = g.bounds.x1, by0 = g.bounds.y0, by1 = g.bounds.y1;
    [yMax, yMax / 2, 0, yMin / 2, yMin].forEach(function (v) {
      var y = g.Y(v);
      frame.appendChild(el('line', { x1: bx0, x2: bx1, y1: y, y2: y, 'class': v === 0 ? 'bt-grid-zero' : 'bt-grid' }));
      frame.appendChild(el('text', { x: bx0 - 8, y: y + 4, 'class': 'bt-tick', 'text-anchor': 'end' }, fmtPct(v)));
    });
    L.yearTicks(data.books.map(function (b) { return b.pub_year; }), g.X, compact ? 34 : 40).forEach(function (year) {
      var x = g.X(year);
      frame.appendChild(el('line', { x1: x, x2: x, y1: by0, y2: by1, 'class': 'bt-grid bt-grid-v' }));
      frame.appendChild(el('text', { x: x, y: by1 + 18, 'class': 'bt-tick', 'text-anchor': 'middle' }, String(year)));
    });
    frame.appendChild(el('line', { x1: bx0, x2: bx0, y1: by0, y2: by1, 'class': 'bt-axis' }));
    frame.appendChild(el('line', { x1: bx0, x2: bx1, y1: by1, y2: by1, 'class': 'bt-axis' }));
    frame.appendChild(el('text', { x: bx0, y: by1 + 36, 'class': 'bt-axis-label', 'text-anchor': 'start' }, '← Established'));
    frame.appendChild(el('text', { x: (bx0 + bx1) / 2, y: by1 + 36, 'class': 'bt-axis-label', 'text-anchor': 'middle' },
      compact ? 'Publication year' : 'Publication year · recent years spaced wider'));
    frame.appendChild(el('text', { x: bx1, y: by1 + 36, 'class': 'bt-axis-label', 'text-anchor': 'end' }, 'Newer →'));
    frame.appendChild(el('text', { x: bx0 + 6, y: by0 - 9, 'class': 'bt-axis-label', 'text-anchor': 'start' }, '↑ Improving'));
    frame.appendChild(el('text', { x: bx0 + 6, y: by1 - 6, 'class': 'bt-axis-label bt-axis-label-dim', 'text-anchor': 'start' }, '↓ Cooling'));
    var ylab = el('text', { 'class': 'bt-axis-label', 'text-anchor': 'middle',
      transform: 'translate(' + (compact ? 12 : 16) + ' ' + ((by0 + by1) / 2) + ') rotate(-90)' }, '7-day momentum');
    frame.appendChild(ylab);
    svg.appendChild(frame);
  }

  function layout(animate) {
    if (!map || !data || !nodes.length) return;
    var W = map.clientWidth, H = map.clientHeight;
    if (W < 40 || H < 40) return;
    var g = L.geometry(W, H, W < 560);
    drawAxes(g);
    var items = nodes.map(function (n) {
      var size = L.coverSize(n.book.strength, n.aspect, g.aMin, g.aMax);
      return { x: g.X(n.book.pub_year), y: g.Y(n.book.momentum), w: size.w, h: size.h };
    });
    var res = L.separate(items, { maxDx: data.cap_fraction * g.plotW, maxDy: data.cap_fraction * g.plotH, pad: 4, bounds: g.bounds });
    lastResult = { res: res, g: g };

    var leads = el('g', { 'class': 'bt-leads' + (animate && !reduceMotion ? '' : ' is-on') });
    var dbg = el('g', { 'class': 'bt-dbg' });
    res.nodes.forEach(function (r, i) {
      var n = nodes[i];
      var st = n.btn.style;
      st.width = r.w.toFixed(1) + 'px';
      st.height = r.h.toFixed(1) + 'px';
      st.left = (r.x - r.w / 2).toFixed(1) + 'px';
      st.top = (r.y - r.h / 2).toFixed(1) + 'px';
      n.final = 'translate(' + r.dx.toFixed(1) + 'px,' + r.dy.toFixed(1) + 'px)';
      if (Math.hypot(r.dx, r.dy) > 1.5) {
        leads.appendChild(el('line', { x1: r.x, y1: r.y, x2: r.px, y2: r.py, 'class': 'bt-lead' }));
        leads.appendChild(el('circle', { cx: r.x, cy: r.y, r: 3, 'class': 'bt-lead-dot' }));
      }
      dbg.appendChild(el('rect', { x: r.px - r.w / 2, y: r.py - r.h / 2, width: r.w, height: r.h, 'class': 'bt-dbg-box' }));
      dbg.appendChild(el('path', { d: 'M' + (r.x - 5) + ' ' + r.y + 'h10M' + r.x + ' ' + (r.y - 5) + 'v10', 'class': 'bt-dbg-pt' }));
    });
    svg.appendChild(leads);
    svg.appendChild(dbg);

    if (animate && !reduceMotion) {
      map.classList.add('is-settling');
      nodes.forEach(function (n) { n.btn.style.transform = 'translate(0px,0px)'; });
      void map.offsetWidth; // start from the data points, then settle (CSS transition, 600 ms)
      requestAnimationFrame(function () {
        nodes.forEach(function (n) { n.btn.style.transform = n.final; });
        setTimeout(function () { leads.classList.add('is-on'); map.classList.remove('is-settling'); }, 600);
      });
    } else {
      nodes.forEach(function (n) { n.btn.style.transform = n.final; });
    }
    map.classList.add('is-ready');
    writeDebug();
  }

  function writeDebug() {
    if (!lastResult || !debugOut) return;
    var r = lastResult.res, g = lastResult.g;
    debugOut.textContent = 'Max displacement: x ' + r.maxDx.toFixed(1) + ' px (' + (r.maxDx / g.plotW * 100).toFixed(1) +
      '% of the ' + Math.round(g.plotW) + ' px x span), y ' + r.maxDy.toFixed(1) + ' px (' + (r.maxDy / g.plotH * 100).toFixed(1) +
      '% of the ' + Math.round(g.plotH) + ' px y span). Cap ' + (data.cap_fraction * 100) + '% per axis. Overlaps left: ' +
      r.overlaps + '. Iterations: ' + r.iterations + (r.converged ? ' (settled).' : ' (limit reached).');
    map.setAttribute('data-max-dx-pct', (r.maxDx / g.plotW * 100).toFixed(2));
    map.setAttribute('data-max-dy-pct', (r.maxDy / g.plotH * 100).toFixed(2));
    map.setAttribute('data-overlaps', String(r.overlaps));
  }

  function showTip(n) {
    var b = n.book;
    tip.innerHTML = '';
    var t = document.createElement('strong'); t.textContent = b.title; tip.appendChild(t);
    var a = document.createElement('span'); a.textContent = b.author; tip.appendChild(a);
    var f = document.createElement('span');
    f.textContent = b.pub_year + ' · 7-day ' + fmtMom(b.momentum) + ' · ' + fmtRank(b.rank) + ' (illustrative)';
    tip.appendChild(f);
    tip.hidden = false;
    var mr = map.getBoundingClientRect(), nr = n.btn.getBoundingClientRect();
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var left = L.clamp(nr.left - mr.left + nr.width / 2 - tw / 2, 4, mr.width - tw - 4);
    var top = nr.top - mr.top - th - 8;
    if (top < 4) top = nr.bottom - mr.top + 8;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hideTip() { tip.hidden = true; }

  if (map && data && data.books.length) {
    buildNodes();
    nodes.forEach(function (n) {
      n.btn.addEventListener('mouseenter', function () { showTip(n); });
      n.btn.addEventListener('mouseleave', hideTip);
      n.btn.addEventListener('focus', function () { showTip(n); });
      n.btn.addEventListener('blur', hideTip);
      n.btn.addEventListener('click', function () { showTip(n); });
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideTip(); });
    whenLoaded(4000).then(function () { layout(true); });
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { hideTip(); layout(false); }, 150);
    }, { passive: true });
    if (debugBtn) {
      debugBtn.hidden = false;
      debugBtn.addEventListener('click', function () {
        var on = debugBtn.getAttribute('aria-pressed') !== 'true';
        debugBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        map.classList.toggle('is-debug', on);
        debugOut.hidden = !on;
        writeDebug();
      });
    }
  }

  /* ── Map | Table ── */
  var toggle = document.getElementById('btMapToggle');
  var panel = document.getElementById('btMapPanel');
  var mapTable = document.getElementById('btMapTable');
  if (toggle && panel && mapTable) {
    toggle.hidden = false;
    mapTable.hidden = true;
    toggle.addEventListener('click', function (e) {
      var btn = e.target.closest('.bt-toggle-btn');
      if (!btn) return;
      var showMap = btn.getAttribute('data-show') === 'map';
      panel.hidden = !showMap;
      mapTable.hidden = showMap;
      Array.prototype.forEach.call(toggle.querySelectorAll('.bt-toggle-btn'), function (b) {
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      if (showMap) layout(false);
    });
  }

  /* ── Sortable market table ── */
  var table = document.getElementById('btTable');
  if (table) {
    var tbody = table.tBodies[0];
    var status = document.createElement('p');
    status.className = 'bt-sr';
    status.setAttribute('role', 'status');
    table.parentNode.parentNode.insertBefore(status, table.parentNode.nextSibling);
    table.querySelector('thead').addEventListener('click', function (e) {
      var btn = e.target.closest('.bt-sort');
      if (!btn) return;
      var th = btn.closest('th');
      var key = btn.getAttribute('data-key');
      var numeric = btn.getAttribute('data-type') === 'num';
      var dir = th.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending';
      Array.prototype.forEach.call(table.querySelectorAll('thead th[aria-sort]'), function (h) { h.setAttribute('aria-sort', 'none'); });
      th.setAttribute('aria-sort', dir);
      var rows = Array.prototype.slice.call(tbody.rows);
      rows.sort(function (a, b) {
        var va = a.getAttribute('data-' + key), vb = b.getAttribute('data-' + key);
        if (va === '' || vb === '') return va === vb ? 0 : (va === '' ? 1 : -1); // no value: always last
        var c = numeric ? parseFloat(va) - parseFloat(vb) : va.localeCompare(vb);
        return dir === 'ascending' ? c : -c;
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
      status.textContent = 'Sorted by ' + btn.textContent.trim() + ', ' + dir + '.';
    });
  }
}());
