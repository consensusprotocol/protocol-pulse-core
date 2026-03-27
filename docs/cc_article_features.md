Read frontend/src/app/articles/[slug]/page.tsx fully.
Read frontend/src/components/ArticleCard.tsx.
Read templates/media_hub.html lines 170-195.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARTICLE FEATURES + MEDIA FIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK 1 - Fix HTML showing in article card excerpts
ArticleCard.tsx shows raw HTML like <h2 class="article-header">... in excerpt.
Add stripHtml() function at top of ArticleCard.tsx:
  function stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
  }
Use it on the excerpt/summary field before rendering.

TASK 2 - Add Bitcoin Lightning tip widget to article detail page
In frontend/src/app/articles/[slug]/page.tsx, after the article content div, add:
  <div className="mt-12 p-6 bg-white/[0.03] backdrop-blur-md border border-[#F8C15C]/20 rounded-2xl text-center">
    <p className="text-[#EDEDED] font-semibold text-lg mb-1">Value this Intelligence Brief?</p>
    <p className="text-[#888888] text-sm mb-5">Support freedom tech journalism. Every sat funds the signal.</p>
    <div className="flex gap-3 justify-center flex-wrap">
      {[{label:'1K sats', amount: 1000}, {label:'5K sats', amount: 5000}, {label:'21K sats', amount: 21000}].map(t => (
        <a key={t.label}
           href={`lightning:bitcoin@protocolpulse.io?amount=${t.amount}`}
           className={`flex items-center gap-2 px-5 py-2.5 rounded-full border text-sm font-medium transition-all duration-300 ${t.amount===21000 ? 'bg-[#F8C15C] text-black border-[#F8C15C] shadow-[0_0_20px_rgba(248,193,92,0.4)]' : 'bg-white/[0.05] text-[#F8C15C] border-[#F8C15C]/30 hover:bg-[#F8C15C]/10'}`}>
          ⚡ {t.label}
        </a>
      ))}
    </div>
  </div>

TASK 3 - Add Satomi AI summary widget to article detail page
In frontend/src/app/articles/[slug]/page.tsx, right after the article hero image section and before the article body, add:
  {(article.summary || article.content) && (
    <div className="mb-8 p-5 bg-white/[0.03] backdrop-blur-md border border-white/[0.06] rounded-xl border-l-4 border-l-[#CC0000]">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[#CC0000] font-bold text-xs uppercase tracking-widest">⚡ Satomi Summary</span>
      </div>
      <p className="text-[#EDEDED]/80 text-sm leading-relaxed italic">
        {article.summary ? article.summary.replace(/<[^>]*>/g, '').slice(0, 300) : article.content.replace(/<[^>]*>/g, '').slice(0, 300)}...
      </p>
    </div>
  )}

TASK 4 - Fix article categories filter (tabs not working)
Test: curl "http://localhost:5000/api/v2/articles?category=Bitcoin&limit=2" - should return filtered articles.
Check frontend/src/lib/api.ts fetchArticles function - ensure category param is passed in query string.
Check the category filter link hrefs in articles/page.tsx - they should be /articles?category=Bitcoin etc.
If the issue is that the frontend doesn't see the filtered results, add console.log to debug.
The most likely fix: in api.ts, ensure the fetch URL includes category correctly:
  if (category) params.append('category', category);

TASK 5 - Media hub book series fix
In templates/media_hub.html, find the book series cards (they use <a href="{{ b.amazon_url }}">).
Replace with a div that shows a modal panel instead of navigating away.
Add onclick="showSeriesPanel(this)" data-title="{{ b.title }}" data-episodes="{{ b.episode_count|default(0) }}"
Add a modal div at bottom of page that slides in showing:
  - Series cover and title
  - Description
  - Episode list (if available) or "Episodes coming soon"
  - Close button
  - Link to Amazon as "Get the Full Series"
Style: glassmorphic dark overlay, red accent, matches PP aesthetic.

AFTER ALL FIXES:
  git add -A
  git commit -m "feat(articles+media): Lightning tips, Satomi summary, HTML strip, book series modal"
  git push
  
  cd /home/ultron/protocol_pulse/frontend
  npm run build > /tmp/nb_features.log 2>&1
  echo "Build: $?"
  /home/ultron/.nvm/versions/node/v24.13.1/bin/pm2 restart pp-frontend
  echo "PM2 restarted"
