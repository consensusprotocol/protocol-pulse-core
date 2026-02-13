# Articles Page, Drafting & Auto-Publish — Full Code & Instructions

This document contains **all code and instructions** for:
1. The `/articles` page (template, CSS, route)
2. Article drafting (ContentGenerator + ContentEngine prompts and flow)
3. Auto-publish mechanisms (AI review, Substack, automation pipeline)

---

## 1. ARTICLES PAGE — ROUTE (routes.py)

Location: `routes.py` — `articles()`, `article_detail()`, helpers, `fetch_mempool_data()`.

```python
# ========== ARTICLES LIST ==========
@app.route('/articles')
def articles():
    """Intelligence Terminal: Bento layout with hero, grid, Network Health sidebar. Paginated."""
    now = datetime.utcnow()
    per_page = 40
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    base_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(
        models.Article.created_at.desc()
    )
    total_count = base_q.count()
    if total_count == 0:
        logging.info("No published articles; falling back to all articles.")
        base_q = models.Article.query.order_by(models.Article.created_at.desc())
        total_count = base_q.count()

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page
    recent = base_q.offset(offset).limit(per_page).all()

    ticker_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(
        models.Article.created_at.desc()
    ).limit(5)
    if total_count == 0:
        ticker_q = models.Article.query.order_by(models.Article.created_at.desc()).limit(5)
    ticker_titles = [a.title for a in ticker_q.all()]

    latest_article = recent[0] if (page == 1 and recent) else None
    grid_articles = recent[1:] if (page == 1 and len(recent) > 1) else recent

    today_articles = recent[:10]
    yesterday_articles = recent[10:20] if len(recent) > 10 else []
    archive_articles = recent[20:40] if len(recent) > 20 else []
    for article in today_articles:
        time_diff = (now - article.created_at).total_seconds() / 3600
        article.is_pressing = time_diff < 1

    categories = [cat[0] for cat in db.session.query(models.Article.category).distinct().all() if cat[0]]
    use_published = total_count > 0
    category_counts = {}
    for c in categories:
        q = models.Article.query.filter(models.Article.category == c)
        if use_published:
            q = q.filter(models.Article.published.is_(True))
        category_counts[c] = q.count()
    active_ads = models.Advertisement.query.filter_by(is_active=True).all()
    prices = price_service.get_prices()
    network_stats = None
    mempool_data = {}
    try:
        network_stats = NodeService.get_network_stats()
    except Exception:
        pass
    try:
        mempool_data = fetch_mempool_data()
    except Exception:
        pass
    default_header_url = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"

    return render_template('articles.html',
                         today_articles=today_articles,
                         yesterday_articles=yesterday_articles,
                         archive_articles=archive_articles,
                         latest_article=latest_article,
                         grid_articles=grid_articles,
                         ticker_titles=ticker_titles,
                         categories=categories,
                         category_counts=category_counts,
                         active_ads=active_ads,
                         prices=prices,
                         price_service=price_service,
                         network_stats=network_stats,
                         mempool_data=mempool_data,
                         last_updated=now,
                         page=page,
                         total_pages=total_pages,
                         total_count=total_count,
                         per_page=per_page,
                         default_header_url=default_header_url)


def _article_body_without_tldr(content):
    """Strip first <div class=\"tldr-section\">...</div> so TL;DR is never shown twice."""
    if not content:
        return ""
    tldr_pattern = re.compile(
        r'<div\s+class="tldr-section"[^>]*>.*?</div>',
        re.DOTALL | re.IGNORECASE
    )
    stripped = tldr_pattern.sub("", content, count=1).strip()
    return stripped if stripped else content


def _article_key_takeaways(article):
    """Extract key takeaways: summary, or TL;DR from content, or first 400 chars."""
    summary = (article.summary or "").strip()
    content = (article.content or "")
    if summary:
        return summary
    tldr_match = re.search(
        r'<div\s+class="tldr-section"[^>]*>\s*(?:<[^>]+>)*\s*TL;DR:\s*([^<]+)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if tldr_match:
        text = re.sub(r"<[^>]+>", "", tldr_match.group(1)).strip()
        return text[:500] + ("…" if len(text) > 500 else "")
    plain = re.sub(r"<[^>]+>", "", content).strip()
    return plain[:400] + ("…" if len(plain) > 400 else "") if plain else ""


@app.route('/articles/<int:article_id>')
def article_detail(article_id):
    """Individual article. Key Takeaways and body never duplicated."""
    article = models.Article.query.get_or_404(article_id)
    try:
        related_articles = models.Article.query.filter(
            models.Article.id != article_id,
            models.Article.published == True,
            models.Article.category == article.category
        ).limit(3).all()
    except Exception:
        related_articles = []
    _log_engagement_event(
        event_type="article_view",
        content_type="article",
        content_id=article.id,
        source_url=request.path,
    )
    key_takeaways_text = _article_key_takeaways(article)
    key_takeaways_bullets = []
    if key_takeaways_text:
        for part in re.split(r"\.\s+", key_takeaways_text):
            part = part.strip().strip(".")
            if part and len(part) > 10:
                key_takeaways_bullets.append(part + ("." if not part.endswith(".") else ""))
    if not key_takeaways_bullets and key_takeaways_text:
        key_takeaways_bullets = [key_takeaways_text]
    body_html = _article_body_without_tldr(article.content or "")
    header_image_url = article.header_image_url or "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"
    return render_template(
        "article_detail.html",
        article=article,
        related_articles=related_articles,
        key_takeaways_text=key_takeaways_text,
        key_takeaways_bullets=key_takeaways_bullets,
        body_html=body_html,
        header_image_url=header_image_url,
    )


def fetch_mempool_data():
    """Fetch real-time data from Mempool.space API (used by /articles sidebar)."""
    try:
        mempool_stats = {}
        response = requests.get('https://mempool.space/api/mempool', timeout=10)
        if response.status_code == 200:
            data = response.json()
            mempool_stats['count'] = data.get('count', 0)
            mempool_stats['vsize'] = data.get('vsize', 0)
            mempool_stats['total_fee'] = data.get('total_fee', 0)
        response = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10)
        if response.status_code == 200:
            fees = response.json()
            mempool_stats['fees'] = {
                'fastest': fees.get('fastestFee', 0),
                'half_hour': fees.get('halfHourFee', 0),
                'hour': fees.get('hourFee', 0),
                'economy': fees.get('economyFee', 0),
                'minimum': fees.get('minimumFee', 0)
            }
        response = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10)
        if response.status_code == 200:
            hashrate_data = response.json()
            mempool_stats['current_hashrate'] = hashrate_data.get('currentHashrate', 0)
            mempool_stats['current_difficulty'] = hashrate_data.get('currentDifficulty', 0)
        return mempool_stats
    except Exception as e:
        logging.error(f"Error fetching mempool data: {e}")
        return {}
```

---

## 2. ARTICLES PAGE — FULL TEMPLATE (templates/articles.html)

```html
{% extends "base.html" %}
{% block title %}Intelligence Terminal — Protocol Pulse{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/articles-terminal.css') }}?v=terminal2">
<style>
  body { background: #0A0A0A !important; }
  .intel-category-bar { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem 1rem; border-bottom: 1px solid rgba(220,38,38,0.2); margin-bottom: 0.5rem; }
  .intel-category-pill { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.65); text-decoration: none; padding: 0.4rem 0.85rem; border: 1px solid rgba(220,38,38,0.2); border-radius: 4px; }
  .intel-category-pill:hover { border-color: #DC2626; color: #DC2626; }
  .intel-category-pill.active { background: #DC2626; border-color: #DC2626; color: #fff; }
  .intel-grid-section-title { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.2em; color: #DC2626; margin-bottom: 0.75rem; padding-bottom: 0.35rem; border-bottom: 1px solid rgba(220,38,38,0.2); }
  .intel-terminal-wrap { display: grid; grid-template-columns: 1fr 320px; gap: 1.25rem; max-width: 1400px; margin: 0 auto; padding: 1rem; }
  @media (max-width: 992px) { .intel-terminal-wrap { grid-template-columns: 1fr; } }
  @media (max-width: 768px) { .intel-bento-grid { grid-template-columns: 1fr; } }
</style>
{% endblock %}

{% block content %}
{% set articles = (today_articles or []) + (yesterday_articles or []) + (archive_articles or []) %}
{% set default_img = default_header_url|default('https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200') %}
{% set categories = categories|default([]) %}
{% set grid_articles = grid_articles|default([]) %}
{% set ticker_titles = ticker_titles|default([]) %}
{% set total_count = total_count|default(0) %}
{% set total_pages = total_pages|default(1) %}
{% set page = page|default(1) %}

<section class="intel-ticker-wrap">
  <div class="container-fluid d-flex align-items-center">
    <span class="intel-ticker-label">Breaking Intelligence</span>
    <div class="intel-ticker">
      {% for title in (ticker_titles or []) %}<span>{{ title }}</span>{% endfor %}
      {% for title in (ticker_titles or []) %}<span>{{ title }}</span>{% endfor %}
    </div>
  </div>
</section>

<nav class="intel-category-bar intel-zones" role="tablist" aria-label="Intelligence Zones">
  <button type="button" class="intel-category-pill intel-zone-tab active" data-zone="all" aria-selected="true">All</button>
  <button type="button" class="intel-category-pill intel-zone-tab" data-zone="bitcoin">Bitcoin</button>
  <button type="button" class="intel-category-pill intel-zone-tab" data-zone="macro">Macro</button>
  <button type="button" class="intel-category-pill intel-zone-tab" data-zone="privacy">Privacy</button>
  <button type="button" class="intel-category-pill intel-zone-tab" data-zone="mining">Mining</button>
  {% for cat in (categories or []) %}
  {% if cat not in ['Bitcoin', 'Macro', 'Privacy', 'Mining'] %}
  <a href="{{ url_for('category_articles', category=cat) }}" class="intel-category-pill">{{ cat }}</a>
  {% endif %}
  {% endfor %}
</nav>

<div class="intel-terminal-wrap">
  <div class="intel-bento-main">
    {% if latest_article %}
    <section class="intel-hero-zone" data-intel-zone="{{ ((latest_article.category or '')|lower|replace(' ', '-')) or 'all' }}">
      <div class="intel-hero-card">
        <div class="intel-hero-bg" style="background-image: url({{ latest_article.header_image_url or default_img }});"></div>
        <div class="intel-hero-content">
          <span class="intel-hero-tag intel-hero-tag-breaking">Breaking</span>
          <a href="{{ url_for('article_detail', article_id=latest_article.id) }}" class="intel-hero-link">
            <h2 class="intel-hero-title">{{ latest_article.title }}</h2>
          </a>
          <div class="intel-hero-meta">
            <span class="intel-hero-cat">{{ latest_article.category or 'Intel' }}</span>
            <span>{{ (((latest_article.content or '')|striptags).split()|length / 200)|int or 1 }} min read</span>
            {% if latest_article.created_at %}<span>{{ latest_article.created_at.strftime('%b %d, %Y') }}</span>{% endif %}
          </div>
        </div>
      </div>
    </section>
    {% endif %}

    <h2 class="intel-grid-section-title">Intelligence Feed</h2>
    <div class="intel-bento-grid">
      {% for article in (grid_articles or []) %}
      {% set word_count = ((article.content or '')|striptags).split()|length %}
      {% set read_mins = ((word_count / 200)|int) if (word_count / 200)|int >= 1 else 1 %}
      {% set signal_pct = (100 - loop.index0 * 2) if (100 - loop.index0 * 2) >= 40 else 40 %}
      <article class="intel-card" data-intel-zone="{{ ((article.category or '')|lower|replace(' ', '-')) or 'all' }}">
        <div class="intel-card-signal">
          <div class="intel-card-signal-bar" style="--signal-pct: {{ signal_pct }}%;"></div>
        </div>
        <span class="intel-card-time">{{ read_mins }} min read</span>
        <h3 class="intel-card-title">
          <a href="{{ url_for('article_detail', article_id=article.id) }}">{{ article.title }}</a>
        </h3>
        <p class="intel-card-preview">{{ article.content|striptags|truncate(120) }}</p>
        <a href="{{ url_for('article_detail', article_id=article.id) }}" class="intel-card-link">Read intel →</a>
      </article>
      {% endfor %}
    </div>
    {% if not (grid_articles or []) and (total_count or 0) == 0 %}
    <p class="text-muted">No articles yet.</p>
    {% endif %}

    {% if (total_pages or 1) > 1 %}
    <nav class="intel-pagination" aria-label="Articles pages">
      <div class="intel-pagination-inner">
        {% if page and page > 1 %}
        <a href="{{ url_for('articles', page=page - 1) }}" class="intel-pagination-btn">← Prev</a>
        {% endif %}
        <span class="intel-pagination-info">Page {{ page or 1 }} of {{ total_pages or 1 }} ({{ total_count or 0 }} intel)</span>
        {% if page and total_pages and page < total_pages %}
        <a href="{{ url_for('articles', page=page + 1) }}" class="intel-pagination-btn">Next →</a>
        {% endif %}
      </div>
      <div class="intel-pagination-jump">
        <a href="{{ url_for('articles', page=1) }}" class="intel-pagination-num {% if (page or 1) == 1 %}active{% endif %}">1</a>
        {% if (page or 1) > 3 %}<span class="intel-pagination-ellipsis">…</span>{% endif %}
        {% for p in range([2, (page or 1) - 2]|max, [(total_pages or 1) - 1, (page or 1) + 2]|min + 1) %}
        <a href="{{ url_for('articles', page=p) }}" class="intel-pagination-num {% if p == (page or 1) %}active{% endif %}">{{ p }}</a>
        {% endfor %}
        {% if total_pages and (page or 1) < (total_pages or 1) - 2 %}<span class="intel-pagination-ellipsis">…</span>{% endif %}
        {% if (total_pages or 1) > 1 %}
        <a href="{{ url_for('articles', page=total_pages or 1) }}" class="intel-pagination-num {% if (page or 1) == (total_pages or 1) %}active{% endif %}">{{ total_pages or 1 }}</a>
        {% endif %}
      </div>
    </nav>
    {% endif %}
  </div>

  <aside class="intel-sidebar">
    <h2 class="intel-sidebar-title">Live HUD</h2>
    <div class="intel-sidebar-row">
      <span class="intel-sidebar-label">BTC</span>
      <span class="intel-sidebar-value">
        {% if prices and (prices.get('bitcoin') or {}).get('price') %}
        ${{ "{:,.0f}".format((prices.get('bitcoin') or {}).get('price', 0)) }}
        {% else %}—{% endif %}
      </span>
    </div>
    <div class="intel-sidebar-row">
      <span class="intel-sidebar-label">Hashrate</span>
      <span class="intel-sidebar-value">{{ (network_stats or {}).get('hashrate', (mempool_data or {}).get('current_hashrate')) or '—' }}</span>
    </div>
    <div class="intel-sidebar-row">
      <span class="intel-sidebar-label">Mempool</span>
      <span class="intel-sidebar-value">{{ (mempool_data or {}).get('count', '—') }} tx</span>
    </div>
    {% if mempool_data and mempool_data.get('fees') %}
    <div class="intel-sidebar-row">
      <span class="intel-sidebar-label">Fee (fast)</span>
      <span class="intel-sidebar-value">{{ mempool_data.fees.get('fastest', mempool_data.fees.get('fastestFee', '—')) }} sat/vB</span>
    </div>
    {% endif %}
    {% if network_stats and network_stats.get('difficulty') %}
    <div class="intel-sidebar-row">
      <span class="intel-sidebar-label">Difficulty</span>
      <span class="intel-sidebar-value">{{ network_stats.difficulty }}</span>
    </div>
    {% endif %}
  </aside>
</div>

<script>
(function() {
  var zoneMap = { bitcoin: ['bitcoin'], macro: ['macro', 'regulation', 'economy', 'defi'], privacy: ['privacy', 'cypherpunk'], mining: ['mining'] };
  var tabs = document.querySelectorAll('.intel-zone-tab');
  var cards = document.querySelectorAll('.intel-card, .intel-hero-zone');
  function filterZone(zone) {
    var match = zone === 'all';
    var keys = match ? [] : (zoneMap[zone] || [zone]);
    cards.forEach(function(el) {
      var z = (el.getAttribute('data-intel-zone') || '').toLowerCase().replace(/\s+/g, '-');
      var show = match || keys.some(function(k) { return z.indexOf(k) !== -1; });
      el.style.display = show ? '' : 'none';
    });
    tabs.forEach(function(t) {
      t.classList.toggle('active', t.getAttribute('data-zone') === zone);
      t.setAttribute('aria-selected', t.getAttribute('data-zone') === zone ? 'true' : 'false');
    });
  }
  tabs.forEach(function(t) {
    t.addEventListener('click', function() { filterZone(t.getAttribute('data-zone')); });
  });
})();
</script>
{% endblock %}
```

---

## 3. ARTICLE DETAIL — FULL TEMPLATE (templates/article_detail.html)

```html
{% extends "base.html" %}
{% block title %}{{ article.title }} — Protocol Pulse{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/articles-terminal.css') }}?v=terminal3">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style> body { background: #0A0A0A !important; } </style>
{% endblock %}

{% block content %}
<article class="article-detail-terminal">
  <header class="article-detail-header">
    <div class="article-detail-header-bg" style="background-image: url({{ header_image_url or article.header_image_url or 'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200' }});"></div>
    <div class="article-detail-header-overlay"></div>
    <div class="article-detail-header-content">
      <h1 class="article-detail-title">{{ article.title }}</h1>
      <p class="article-detail-meta">
        {{ article.created_at.strftime('%B %d, %Y') if article.created_at else '—' }}
        {% if article.author %} · {{ article.author }}{% endif %}
        {% if article.category %} · <span class="article-detail-category">{{ article.category }}</span>{% endif %}
      </p>
    </div>
  </header>

  <div class="key-takeaways">
    <h3>Key Takeaways</h3>
    {% if key_takeaways_bullets and key_takeaways_bullets|length > 0 %}
    <ul>
      {% for point in key_takeaways_bullets %}
      <li>{{ point }}</li>
      {% endfor %}
    </ul>
    {% else %}
    <p>{{ key_takeaways_text or 'Key points from this analysis.' }}</p>
    {% endif %}
  </div>

  <div class="article-body-serif">
    {% if body_html %}
    {{ body_html|safe }}
    {% else %}
    <p class="text-muted" style="font-size: 0.95rem;">Full analysis is summarized in Key Takeaways above.</p>
    {% endif %}
  </div>

  <div class="mt-5 pt-4 article-detail-share">
    <p class="share-intel-label">Share Intelligence</p>
    <a href="https://twitter.com/intent/tweet?text={{ (article.title + ' ' + request.url)|urlencode }}" target="_blank" rel="noopener" class="share-intel-btn">$ share x</a>
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ request.url|urlencode }}" target="_blank" rel="noopener" class="share-intel-btn">$ share linkedin</a>
    <button type="button" class="share-intel-btn" onclick="navigator.clipboard.writeText('{{ request.url }}'); this.textContent='$ copied'; setTimeout(() => { this.textContent='$ copy link'; }, 1500);">$ copy link</button>
  </div>

  <div class="mt-4">
    <a href="{{ url_for('articles') }}" class="share-intel-btn" style="text-decoration: none;">← Back to Terminal</a>
  </div>
</article>
{% endblock %}
```

---

## 4. ARTICLES TERMINAL CSS — FULL (static/css/articles-terminal.css)

See the file `static/css/articles-terminal.css` in the repo for the complete stylesheet (~360 lines). It defines:

- `:root` — `--terminal-red`, `--terminal-red-glow`, `--terminal-black`, `--terminal-glass`, `--terminal-glass-border`
- Ticker: `.intel-ticker-wrap`, `.intel-ticker`, `@keyframes ticker-scroll` (18s)
- Category/zone pills and `.intel-zone-tab.active`
- Hero: `.intel-hero-zone`, `.intel-hero-card`, `.intel-hero-bg::before` (red/black gradient), `.intel-hero-content`, `.intel-hero-tag-breaking`
- Bento: `.intel-terminal-wrap` (grid 1fr 320px), `.intel-bento-grid` (repeat(3,1fr), gap 1.5rem)
- Cards: `.intel-card`, `.intel-card-signal-bar`, glassmorphism, hover glow
- Sidebar: `.intel-sidebar` (sticky), `.intel-sidebar-row`
- Detail: `.article-detail-header-bg::before` (red/black overlay), `.key-takeaways` (red border), `.article-body-serif` (Crimson Pro 1.15rem), `.share-intel-btn`
- Pagination: `.intel-pagination`, `.intel-pagination-num.active`

---

## 5. DRAFTING ARTICLES — CONTENT GENERATOR (services/content_generator.py)

**Entry point:** `ContentGenerator().generate_article(topic, prompt_id=None, content_type='news_article', source_type='ai_generated', headline_style=None)`.

**Flow:**
1. **Duplicate gatekeeper:** `is_topic_duplicate_via_gemini(proposed_topic)` — compares to last 10 published titles; returns DUPLICATE/UNIQUE.
2. **Optional context:** Reddit trends (if `source_type='reddit'`) or X feedback (if `source_type='x'`) appended to topic.
3. **Prompt:** `_get_prompt_template(prompt_id, content_type)` → default is `default_prompts['news_article']` (or `analysis_piece`, `breaking_news`). Placeholders: `{topic}`, `{headline_style}`.
4. **System prompt** includes:
   - `accuracy_mandate` — ground truth data lockdown, no “record high” unless verified, transactor-focused.
   - `headline_style_mandate` — Style A (question) vs B (statement); random choice if `headline_style` is None.
   - `locked_structure_mandate` — 6 sections: TL;DR, The Report, Exclusive Data Analysis, The Bitcoin Lens, Transactor Intelligence, Sources; 1200+ words; clean HTML only.
5. **Real-time metrics:** `NodeService.get_network_stats()` injected into system prompt when available.
6. **Generation:** OpenAI first, then Gemini, then Anthropic. Up to 2 retries if `_validate_article_structure(content)` fails (checks for tldr-section, The Report, Exclusive Data Analysis, The Bitcoin Lens, Transactor Intelligence, Sources, and word count ≥ 1200).
7. **Title:** `_extract_or_generate_title(content, topic)` then `_clean_title(title)` then `_enforce_headline_style(title, headline_style, topic)`.
8. **Fact-check:** `verify_article_before_publish(content)` (from `services.fact_checker`).
9. **Return:** `{ title, content, summary="", category, tags, seo_title, seo_description, header_image_url=None, fact_check, fact_check_warnings, fact_check_passed }`.

**Instructions/mandates (excerpts):**
- **Editorial accuracy:** Use only verified Bitcoin metrics; never claim “all-time high” for difficulty unless current > 155.9 T; transactor lens, not tourist; “The Hardest Money” framing.
- **Headline style:** Vary question vs statement; no clickbait; &lt;15 words.
- **Locked structure:** 6 sections, clean HTML, TL;DR in `<div class="tldr-section"><em><strong>TL;DR: ...</strong></em></div>`, `<h2 class="article-header">`, `<p class="article-paragraph">`, Sources as `<ul class="sources-list">`.
- **Walter Cronkite tone:** Authoritative, factual, no first-person; Bitcoin-first, pro-decentralization; unique analysis and data.

---

## 6. DRAFTING & SAVING — CONTENT ENGINE (services/content_engine.py)

**Entry points:**
- `ContentEngine().generate_and_publish_article(topic, content_type="bitcoin_news", auto_publish=False)`
- `ContentEngine().approve_and_publish_article(article_id)`

**generate_and_publish_article flow:**
1. **Generate:** By `content_type` → `_generate_bitcoin_article(topic)` | `_generate_defi_article(topic)` | `_generate_market_article(topic)` | `_generate_general_article(topic, content_type)`. Each uses a Walter Cronkite–style prompt + ACCURACY_MANDATE + clean HTML (tldr-section, article-header, sources-list).
2. **Save:** `_save_article_to_db(article_data)` → creates `Article` with `published=False`, `header_image_url=default_header` if not provided.
3. **Optional:** Audio (ElevenLabs), video (HeyGen).
4. **If auto_publish and Substack available:**  
   - `review_article_with_gemini(title, content)` → JSON `{ decision: APPROVE|REJECT, reason, score }`.  
   - If APPROVE: `publish_to_substack(title, body_markdown, image_path=None)` → then set `article.published = True`, `article.substack_url = ...`, commit.  
   - If REJECT: leave `published=False`, commit.

**approve_and_publish_article flow:**
1. Load article by id.
2. `review_article_with_gemini(article.title, article.content)`.
3. If APPROVE: set `article.published = True`, call `publish_to_substack(title, body_markdown, image_path=None)`, set `article.substack_url`, commit.
4. If REJECT: set `article.published = False`, commit.

**publish_to_substack(title, body_markdown, image_path=None):**  
Uses `substack` package (`Api`, `Post`). Logs in with `SUBSTACK_EMAIL`, `SUBSTACK_PASSWORD`, `SUBSTACK_PUBLICATION_URL`; creates draft, prepublishes, publishes; returns `canonical_url`. No header image if `image_path` is None.

**Instructions (ContentEngine):**
- **ACCURACY_MANDATE:** Verify metrics via real-time fetch only; never “all-time high” unless verified; no hallucinated hashrate; difficulty can decrease; no “surge”/“soaring” without verification.
- **Walter Cronkite style:** Authoritative, no first-person, pro-Bitcoin/decentralization, strong closing without naming cypherpunk.

---

## 7. AUTO-PUBLISH & TRIGGERS

**A. Admin “Approve & Publish” (one article)**  
- **Route:** `POST /api/publish-article/<article_id>` (and admin UI that calls it).  
- **Code:** `content_engine.approve_and_publish_article(article_id)` then set `article.published = True` and commit.  
- **Effect:** AI review (Gemini) → if APPROVE, publish to Substack and set `substack_url`.

**B. Generate + optional auto-publish (one shot)**  
- **Route:** `POST /admin/generate-content` with JSON `{ topic, content_type, auto_publish }`.  
- **Code:** `content_engine.generate_and_publish_article(topic, content_type, auto_publish)`.  
- **Effect:** Generate → save as draft → if `auto_publish` True and Substack available, run AI review and publish to Substack if approved.

**C. Test endpoint (no auth)**  
- **Route:** `POST /test/generate-article` with JSON `{ topic, content_type, auto_publish }`.  
- **Code:** Same `content_engine.generate_and_publish_article(...)`.

**D. Automation pipeline (daily/scheduled)**  
- **Service:** `services.automation.generate_article_with_tracking(force=False)`.  
- **Flow:**  
  1. Try `ContentEngine().generate_and_publish_article(topic, "bitcoin_news", auto_publish=False)`; if success, set `article.published = True` and return.  
  2. Fallback: `ContentGenerator().generate_article(topic, content_type="news_article", source_type="ai_generated")` → create `Article` and set `published=True`.  
  3. Fallback: Reddit trending → `ContentGenerator().generate_article(..., source_type="reddit")` → create `Article` and set `published=True`.  
  4. If all fail and no published articles exist: create stub placeholder article so site has something.  
- **Trigger (manual):** `python -m core.scripts.draft_articles_now` (or `scripts/draft_articles_now.py`) which calls `generate_article_with_tracking(force=True)`.

**E. Scheduler**  
- If `ENABLE_APSCHEDULER=true`, the app may register jobs that call the automation or content engine; see `services/scheduler.py` and any cron-like triggers for “daily article” or “draft articles.”

**F. Substack-only (existing article)**  
- **Route:** `POST /admin/publish-to-substack/<article_id>`.  
- **Code:** Load article, format content for newsletter, call `substack_service.publish_to_substack(title, newsletter_content, header_image_url)` (or equivalent), set `article.substack_url`, commit.

---

## 8. INSTRUCTIONS SUMMARY

| Mechanism | Where | What it does |
|-----------|--------|--------------|
| **Articles page** | `routes.articles()`, `templates/articles.html`, `static/css/articles-terminal.css` | Bento terminal: ticker, zones, hero, grid, Live HUD sidebar, pagination. |
| **Article detail** | `routes.article_detail()`, `templates/article_detail.html` | One Key Takeaways box (bullets), body without duplicate TL;DR, Crimson Pro, header overlay. |
| **Draft article (full quality)** | `ContentGenerator.generate_article()` | 6-section locked structure, 1200+ words, accuracy mandate, headline style, fact-check. |
| **Draft + save (simpler)** | `ContentEngine.generate_and_publish_article(..., auto_publish=False)` | Shorter prompts per type (bitcoin/defi/market); saves to DB as draft. |
| **Approve & publish one** | `ContentEngine.approve_and_publish_article(article_id)` | Gemini review → if APPROVE, publish to Substack and set `published=True`. |
| **Auto-publish on generate** | `generate_and_publish_article(..., auto_publish=True)` | After save, run Gemini review and publish to Substack if approved. |
| **Daily/on-demand draft** | `automation.generate_article_with_tracking(force=True)` | ContentEngine → ContentGenerator → Reddit fallback → stub if nothing exists. |
| **Run draft now** | `python -m core.scripts.draft_articles_now` | Calls `generate_article_with_tracking(force=True)` once. |

---

## 9. FILES TO EDIT FOR ARTICLES UI / DRAFTING / PUBLISH

- **Articles list UI:** `templates/articles.html`, `static/css/articles-terminal.css`, `routes.py` (articles view).  
- **Article detail UI:** `templates/article_detail.html`, same CSS, `routes.py` (article_detail view + helpers).  
- **Drafting prompts & structure:** `services/content_generator.py` (mandates, default_prompts, generate_article, validation).  
- **Drafting + DB + Substack:** `services/content_engine.py` (generate_and_publish_article, approve_and_publish_article, _generate_*_article, _save_article_to_db, publish_to_substack).  
- **Auto-draft pipeline:** `services/automation.py` (`generate_article_with_tracking`).  
- **One-shot draft script:** `scripts/draft_articles_now.py` or `core/scripts/draft_articles_now.py`.  
- **Publish API / admin:** `routes.py` (`api_publish_article`, `publish_to_substack`, `generate_content`).

---

## 10. DRAFTING & AUTO-PUBLISH — CODE SNIPPETS

**ContentGenerator:** `is_topic_duplicate_via_gemini(proposed_topic)` — last 10 titles to Gemini, reply DUPLICATE or UNIQUE. **ContentEngine:** `approve_and_publish_article(article_id)` → review_article_with_gemini → if APPROVE: publish_to_substack, set published=True. **review_article_with_gemini:** Editor-in-Chief prompt, JSON decision/reason/score, APPROVE if score >= 7. **publish_to_substack:** Api(SUBSTACK_EMAIL etc), Post, post_draft, prepublish, publish, return canonical_url. **Generate by type:** _generate_bitcoin/defi/market/general_article each use ACCURACY_MANDATE + Walter Cronkite + tldr-section, article-header, sources-list. **Automation:** `generate_article_with_tracking(force)` — (1) ContentEngine then published=True (2) ContentGenerator fallback (3) Reddit + ContentGenerator (4) stub article if no published. **Routes:** POST /api/publish-article/<id>, /admin/generate-content, /test/generate-article, /admin/publish-to-substack/<id>.

## 11. HOW TO USE

**Draft one (full quality):** `ContentGenerator().generate_article(topic)`. **Draft and save as draft:** `ContentEngine().generate_and_publish_article(topic, auto_publish=False)`. **Approve one:** `approve_and_publish_article(article_id)` or POST /api/publish-article/<id>. **Auto-publish on generate:** `generate_and_publish_article(..., auto_publish=True)`. **Run pipeline now:** `python -m core.scripts.draft_articles_now` or `scripts/draft_articles_now.py`.

Use this doc as the single reference for “all the code and instructions” for the articles page, drafting, and auto-publish.
