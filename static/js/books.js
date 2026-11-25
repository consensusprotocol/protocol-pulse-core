/* /books (The Sovereign Library): search, category chips, grid/list toggle and three disclosures.
   Progressive enhancement. core/routes_books.py already rendered the page with ?q= and ?cat=
   applied, so it works without JavaScript; this applies the same rules in place, keeps the
   URL in step and leaves the server's markup as the single source of the book list.
   fold() mirrors routes_books.fold(): lowercase, accents removed. No libraries.

   Disclosures (buttons with aria-expanded; without JavaScript everything is simply shown):
     More            on narrow grid cards the description opens under the title (books.css hides it
                     only on .bt.has-js below 640 px)
     View all        on a phone the Original Series shelf previews SERIES_PREVIEW books; the rest
                     get .is-extra. A search or category filter shows every match instead.
     Why this order  a pathway's notes on why each book sits where it does */
(function () {
  'use strict';

  var root = document.getElementById('btLibrary');
  var form = document.getElementById('btTools');
  if (!root || !form) return;
  root.classList.add('has-js');

  var SERIES_PREVIEW = 2;
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
  var seriesShelf = document.getElementById('btSeriesShelf');
  var seriesBooks = seriesShelf ? Array.prototype.slice.call(seriesShelf.querySelectorAll('.bt-book')) : [];
  var viewAll = document.getElementById('btSeriesAll');
  var total = books.length;
  var state = {
    q: input.value,
    cat: hiddenCat.value,
    view: root.classList.contains('is-list') ? 'list' : 'grid',
    seriesOpen: false
  };

  function fold(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function filtering() { return !!(state.q.trim() || state.cat); }

  function updateSeries() {
    if (!viewAll) return;
    var shown = seriesBooks.filter(function (li) { return !li.hidden; });
    var preview = !filtering() && !state.seriesOpen;
    seriesBooks.forEach(function (li) {
      li.classList.toggle('is-extra', preview && shown.indexOf(li) >= SERIES_PREVIEW);
    });
    viewAll.hidden = filtering() || shown.length <= SERIES_PREVIEW;
    viewAll.setAttribute('aria-expanded', state.seriesOpen ? 'true' : 'false');
    viewAll.textContent = state.seriesOpen ? 'Show fewer' : 'View all ' + shown.length;
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
    updateSeries();
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

  // A link or hash that points at a book card: show the card first if a filter or the series
  // preview hides it.
  function reveal(slug) {
    var target = document.getElementById('book-' + slug);
    if (!target) return;
    if (target.hidden) reset();
    if (target.classList.contains('is-extra')) {
      state.seriesOpen = true;
      updateSeries();
    }
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

  if (viewAll) {
    viewAll.addEventListener('click', function () {
      state.seriesOpen = !state.seriesOpen;
      updateSeries();
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
    var more = e.target.closest('.bt-more-btn');
    if (more) {
      var open = more.getAttribute('aria-expanded') !== 'true';
      more.setAttribute('aria-expanded', open ? 'true' : 'false');
      more.querySelector('.bt-more-label').textContent = open ? 'Less' : 'More';
      more.closest('.bt-card').classList.toggle('is-open', open);
      return;
    }
    var why = e.target.closest('.bt-path-why');
    if (why) {
      var shown = why.getAttribute('aria-expanded') !== 'true';
      why.setAttribute('aria-expanded', shown ? 'true' : 'false');
      why.querySelector('.bt-path-why-label').textContent = shown ? 'Hide the notes' : 'Why this order';
      why.closest('.bt-path').classList.toggle('is-open', shown);
      return;
    }
    // A pathway step points at a book card.
    var step = e.target.closest('.bt-step-title');
    if (step) reveal(step.getAttribute('data-book'));
  });

  // The toolbar is sticky from 640 px up and covers the top of the viewport: keep jump targets
  // below it. On a phone it scrolls away with the page, so nothing needs to be reserved.
  function measureTools() {
    var sticky = getComputedStyle(form).position === 'sticky';
    root.style.setProperty('--bt-tools-h', (sticky ? form.getBoundingClientRect().height : 0) + 'px');
  }
  measureTools();
  window.addEventListener('resize', measureTools, { passive: true });

  updateSeries();
  if (location.hash.indexOf('#book-') === 0) reveal(location.hash.slice(6));

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
