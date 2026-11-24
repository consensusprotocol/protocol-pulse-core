/* /books (The Sovereign Library): search, category chips, grid/list toggle.
   Progressive enhancement. core/routes_books.py already rendered the page with ?q= and ?cat=
   applied, so it works without JavaScript; this applies the same rules in place, keeps the
   URL in step and leaves the server's markup as the single source of the book list.
   fold() mirrors routes_books.fold(): lowercase, accents removed. No libraries. */
(function () {
  'use strict';

  var root = document.getElementById('btLibrary');
  var form = document.getElementById('btTools');
  if (!root || !form) return;

  var input = document.getElementById('btSearch');
  var hiddenCat = form.querySelector('input[type="hidden"][name="cat"]');
  var chips = Array.prototype.slice.call(form.querySelectorAll('.bt-chip'));
  var count = document.getElementById('btCount');
  var empty = document.getElementById('btEmpty');
  var toggle = form.querySelector('.bt-toggle');
  var books = Array.prototype.slice.call(root.querySelectorAll('.bt-book'));
  var sections = Array.prototype.slice.call(root.querySelectorAll('.bt-section')).filter(function (s) {
    return s.querySelector('.bt-shelf');
  });
  var total = books.length;
  var state = {
    q: input.value,
    cat: hiddenCat.value,
    view: root.classList.contains('is-list') ? 'list' : 'grid'
  };

  function fold(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function apply() {
    var terms = fold(state.q).split(/\s+/).filter(Boolean);
    var shown = 0;
    books.forEach(function (li) {
      var cats = (li.getAttribute('data-cats') || '').split('|');
      var hay = li.getAttribute('data-search') || '';
      var ok = (!state.cat || cats.indexOf(state.cat) !== -1) &&
        terms.every(function (t) { return hay.indexOf(t) !== -1; });
      li.hidden = !ok;
      if (ok) shown += 1;
    });
    sections.forEach(function (sec) { sec.hidden = !sec.querySelector('.bt-book:not([hidden])'); });
    count.textContent = 'Showing ' + shown + ' of ' + total + ' books';
    empty.hidden = shown !== 0;
    chips.forEach(function (c) { c.setAttribute('aria-pressed', c.value === state.cat ? 'true' : 'false'); });
    hiddenCat.value = state.cat;
  }

  function sync() {
    var params = new URLSearchParams();
    if (state.q.trim()) params.set('q', state.q.trim());
    if (state.cat) params.set('cat', state.cat);
    if (state.view === 'list') params.set('view', 'list');
    var qs = params.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
  }

  function reset() {
    state.q = '';
    state.cat = '';
    input.value = '';
    apply();
    sync();
  }

  var timer = null;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { state.q = input.value; apply(); sync(); }, 120);
  });

  // Enter in the search box: filter in place; on phones, close the keyboard.
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    clearTimeout(timer);
    state.q = input.value;
    apply();
    sync();
    input.blur();
  });

  chips.forEach(function (chip) {
    chip.addEventListener('click', function (e) {
      e.preventDefault();
      state.cat = chip.value;
      state.q = input.value;
      apply();
      sync();
    });
  });

  if (toggle) {
    toggle.hidden = false;
    toggle.addEventListener('click', function (e) {
      var btn = e.target.closest('.bt-toggle-btn');
      if (!btn) return;
      state.view = btn.getAttribute('data-view') === 'list' ? 'list' : 'grid';
      root.classList.toggle('is-list', state.view === 'list');
      Array.prototype.forEach.call(toggle.querySelectorAll('.bt-toggle-btn'), function (b) {
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      sync();
    });
  }

  root.addEventListener('click', function (e) {
    var resetLink = e.target.closest('[data-reset]');
    if (resetLink) {
      e.preventDefault();
      reset();
      input.focus();
      return;
    }
    // A pathway step points at a book card: show every book first if a filter hides it.
    var step = e.target.closest('.bt-step-title');
    if (step) {
      var target = document.getElementById('book-' + step.getAttribute('data-book'));
      if (target && target.hidden) reset();
    }
  });

  // The sticky toolbar covers the top of the viewport: keep jump targets below it.
  function measureTools() {
    root.style.setProperty('--bt-tools-h', form.getBoundingClientRect().height + 'px');
  }
  measureTools();
  window.addEventListener('resize', measureTools, { passive: true });

  // Covers: Open Library answers 404 for a missing cover (?default=false); Amazon answers a
  // 1x1 image. Either way show the typographic fallback instead of a broken image.
  function missing(img) {
    var slot = img.closest('.bt-cover');
    if (slot) slot.classList.add('is-missing');
    else img.style.visibility = 'hidden';
  }
  Array.prototype.forEach.call(root.querySelectorAll('.bt-cover img, .bt-step-cover, .bt-feature-cover img'), function (img) {
    function check() { if (img.naturalWidth < 10) missing(img); }
    if (img.complete) {
      check();
    } else {
      img.addEventListener('load', check);
      img.addEventListener('error', function () { missing(img); });
    }
  });
}());
