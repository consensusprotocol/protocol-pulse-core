// Runs the real #books script from templates/media_hub.html against a stub DOM, with a given
// /api/books/metrics payload, and prints what it rendered as JSON.
// Usage: node media_books_harness.js <media_hub.html> <payload.json>
'use strict';
const fs = require('fs');
const vm = require('vm');

const [, , templatePath, payloadPath] = process.argv;
const src = fs.readFileSync(templatePath, 'utf8');
const marker = '/* ═══════════ SOVEREIGN BOOK LIBRARY ═══════════ */';
const start = src.indexOf(marker);
const endMark = '\n})();\n';
const end = src.indexOf(endMark, start);
if (start < 0 || end < 0) throw new Error('#books script not found in ' + templatePath);
const code = src.slice(start, end + endMark.length);
const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));

const els = {};
const ids = ['books', 'bookMetricsDot', 'bookMetricsUpdated', 'featuredBookBanner', 'bookChartCard', 'bookBubbleChart',
  'bookChartNote', 'risingStarsSection', 'risingStarsGrid', 'libraryCount', 'libraryGrid'];
for (const id of ids) {
  els[id] = { id, innerHTML: '', textContent: '', hidden: id === 'featuredBookBanner' || id === 'risingStarsSection', style: {}, addEventListener() {} };
}
// The page defines _esc() in an earlier script: textContent -> innerHTML escapes &, < and >.
const esc = (s) => (s == null || s === '' ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
const status = payload.__http_status || 200;
const sandbox = {
  window: {}, console, Promise, Date, Math, Number, String, Array, Object, JSON, isNaN,
  document: { getElementById: (id) => els[id] || null },
  fetch: () => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(payload) }),
  setInterval: () => 0,
  _esc: esc,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
setTimeout(() => {
  process.stdout.write(JSON.stringify({
    libraryGrid: els.libraryGrid.innerHTML,
    libraryCount: els.libraryCount.textContent,
    featured: els.featuredBookBanner.innerHTML,
    featuredHidden: els.featuredBookBanner.hidden,
    rising: els.risingStarsGrid.innerHTML,
    risingHidden: els.risingStarsSection.hidden,
    chartCardDisplay: els.bookChartCard.style.display,
    status: els.bookMetricsUpdated.textContent,
  }));
}, 30);
