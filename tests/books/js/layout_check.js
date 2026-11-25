// Exercises BookMarketLayout from static/js/book_market.js under node and prints JSON for
// tests/books/test_library_market.py to assert on. Usage: node layout_check.js <book_market.js>
'use strict';
const L = require(process.argv[2]);
const out = {};

// Cover area follows s; the cover keeps its aspect ratio.
out.coverSize = [];
for (const aspect of [0.5, 0.62, 2 / 3, 0.8, 1]) {
  for (const s of [0, 0.25, 0.5, 1]) {
    const c = L.coverSize(s, aspect, 1000, 9000);
    out.coverSize.push({ aspect, s, area: c.area, w: c.w, h: c.h });
  }
}
out.coverClamp = [L.coverSize(-1, 2 / 3, 1000, 9000).area, L.coverSize(2, 2 / 3, 1000, 9000).area];

// Seeded random layouts: the displacement cap must hold for every one, and runs repeat exactly.
let seed = 1124;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
out.separate = [];
for (let t = 0; t < 80; t += 1) {
  const n = 3 + Math.floor(rnd() * 9);
  const W = 300 + rnd() * 900;
  const H = 250 + rnd() * 400;
  const nodes = [];
  for (let i = 0; i < n; i += 1) {
    const w = 20 + rnd() * 70;
    nodes.push({ x: rnd() * W, y: rnd() * H, w, h: w * (1.3 + rnd() * 0.5) });
  }
  const opt = { maxDx: 0.06 * W, maxDy: 0.06 * H, pad: 4, bounds: { x0: 0, x1: W, y0: 0, y1: H } };
  const a = L.separate(nodes, opt);
  const b = L.separate(nodes, opt);
  out.separate.push({
    maxDx: a.maxDx, maxDy: a.maxDy, capX: opt.maxDx, capY: opt.maxDy,
    every_node_within_cap: a.nodes.every((m) => Math.abs(m.px - m.x) <= opt.maxDx + 1e-9 && Math.abs(m.py - m.y) <= opt.maxDy + 1e-9),
    sizes_kept: a.nodes.every((m, i) => m.w === nodes[i].w && m.h === nodes[i].h),
    repeatable: JSON.stringify(a) === JSON.stringify(b),
    overlaps_before: (() => { let k = 0; const ns = nodes.map((m) => ({ ...m, px: m.x, py: m.y }));
      for (let i = 0; i < ns.length; i += 1) for (let j = i + 1; j < ns.length; j += 1) if (L.overlap(ns[i], ns[j], 0)) k += 1; return k; })(),
    overlaps_after: a.overlaps,
  });
}

// Covers that do not touch are not moved.
const apart = L.separate([{ x: 50, y: 50, w: 20, h: 30 }, { x: 200, y: 50, w: 20, h: 30 }], { maxDx: 30, maxDy: 30, pad: 4 });
out.apart = { maxDx: apart.maxDx, maxDy: apart.maxDy, iterations: apart.iterations, converged: apart.converged };

// Two overlapping covers with room to move are separated, symmetrically.
const pair = L.separate([{ x: 100, y: 100, w: 40, h: 60 }, { x: 110, y: 100, w: 40, h: 60 }], { maxDx: 60, maxDy: 60, pad: 4 });
out.pair = { overlaps: pair.overlaps, dx: pair.nodes.map((n) => n.dx), dy: pair.nodes.map((n) => n.dy) };

// A pair the cap cannot separate stays overlapping and still respects the cap.
const tight = L.separate([{ x: 100, y: 100, w: 80, h: 120 }, { x: 101, y: 101, w: 80, h: 120 }], { maxDx: 5, maxDy: 5, pad: 0 });
out.tight = { overlaps: tight.overlaps, maxDx: tight.maxDx, maxDy: tight.maxDy };

// Horizontal scale: older is always further left.
out.recency = [1990, 1999, 2010, 2019, 2020, 2025, 2026].map((y) => L.recency(y, 2026));

// Year marks: the candidates for a 1999-2025 map seen on 2026, thinned at two plot widths with the
// same X the covers use.
out.candidates = L.tickYears(2026, 1995, 2025);
out.ticks = {};
out.X = {};
for (const width of [300, 900]) {
  const X = (y) => (L.recency(y, 2026) - L.recency(1999, 2026)) / (L.recency(2025, 2026) - L.recency(1999, 2026)) * width;
  out.ticks[width] = L.yearTicks(out.candidates, X, 34).map((y) => [y, X(y)]);
  out.X[width] = Object.fromEntries(out.candidates.map((y) => [y, X(y)]));
}

process.stdout.write(JSON.stringify(out));
