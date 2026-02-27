# Bitcoin News Network - Latest News Page Design Guidelines

## Design Approach
**Reference-Based:** Drawing from CoinDesk, Bloomberg, and Reuters professional news platforms. Dark theme with premium cryptocurrency market aesthetics.

## Typography System

**Primary Font:** Inter or SF Pro Display (Google Fonts CDN)
**Secondary Font:** IBM Plex Mono (for timestamps, market data)

**Hierarchy:**
- Page Title: text-4xl font-bold (48px)
- Featured Article Headline: text-3xl font-bold (36px)
- Standard Article Headline: text-xl font-semibold (20px)
- Article Excerpt: text-base font-normal (16px)
- Metadata (author, date): text-sm font-medium (14px)
- Category Tags: text-xs font-semibold uppercase tracking-wide (12px)

## Layout System

**Container Structure:**
- Max width: max-w-7xl (1280px)
- Consistent spacing units: 4, 6, 8, 12, 16, 24 (Tailwind units)
- Section vertical padding: py-12 desktop, py-8 mobile
- Card spacing: gap-6 for article grids

**Grid System:**
- Desktop: 3-column article grid (grid-cols-3)
- Tablet: 2-column (md:grid-cols-2)
- Mobile: Single column

## Page Structure & Components

### 1. Header Navigation (Fixed/Sticky)
- Full-width with subtle backdrop blur
- Logo + Primary navigation (Latest, Markets, Analysis, Opinion, Regulation)
- Search icon, Market ticker strip (BTC, ETH, top coins with live prices)
- User account/menu icon
- Height: h-16
- Padding: px-6

### 2. Hero Featured Article Section
**Layout:** Full-width banner style (not 100vh - natural height ~500-600px)
- Large background image with gradient overlay for text readability
- Positioned left-aligned content over image
- Elements: Category badge, headline, excerpt (2 lines), author metadata, "Read More" button with blurred background
- Padding: py-24 px-6

### 3. Breaking News Ticker (Optional Strip)
- Horizontal scrolling banner between hero and main content
- Height: h-12
- Red accent indicator for "BREAKING"

### 4. Main Article Grid
**3-Column Grid Layout:**

Each Article Card Contains:
- Thumbnail image (16:9 aspect ratio, ~400x225px)
- Category badge (top-left overlay on image or above)
- Headline (2-3 line limit with ellipsis)
- Excerpt text (2 lines)
- Bottom metadata row: Author photo (small circular) + Name, timestamp, read time
- Card padding: p-6
- Card hover state: subtle lift/glow effect

**Grid Spacing:**
- Gap between cards: gap-6
- Cards per row: 3 (desktop), 2 (tablet), 1 (mobile)

### 5. Secondary Featured Row (Every 9 articles)
**2-Column Wide Cards:**
- Larger thumbnails (landscape 2:1 ratio)
- Extended excerpts (3-4 lines)
- Breaks up standard grid rhythm
- Spans 2 columns in desktop view

### 6. Sidebar Components (Right Column - Desktop Only)
**Trending Topics:**
- Numbered list (1-5) with article titles
- Compact spacing: space-y-4
- Small thumbnails (80x80px)

**Market Overview Widget:**
- Top 5 cryptocurrencies
- Price + 24h change indicators
- Compact table format

**Newsletter Signup:**
- Headline, input field, subscribe button
- Contained card: p-6

### 7. Pagination/Load More
- Centered below article grid
- Button style: "Load More Articles" or numbered pagination
- Padding: py-16

### 8. Footer
**Multi-Column Layout (4 columns desktop, stack mobile):**
- About/Company links
- Editorial sections
- Social media icons
- Newsletter signup (if not in sidebar)
- Legal/Privacy links bottom row
- Padding: py-16

## Images

**Hero Section:** 
Large feature article background image (1920x600px suggested) - high-quality Bitcoin/crypto market imagery, trading floors, or abstract digital asset visuals with dark overlay gradient for text contrast.

**Article Cards:**
Each card requires thumbnail image (400x225px) - mix of:
- Bitcoin/cryptocurrency charts and graphs
- Market scenes, trading imagery
- Technology/blockchain visuals
- Portrait photos for opinion pieces
- Event photography for news coverage

**Sidebar Trending:**
Small square thumbnails (80x80px) for trending articles

**Author Photos:**
Circular avatars (32x32px) in article metadata

## Spacing & Rhythm

**Vertical Rhythm:**
- Section separation: space-y-12
- Card internal spacing: space-y-4
- Text block spacing: space-y-2
- Metadata elements: space-x-2

**Horizontal Spacing:**
- Page margins: px-6
- Grid gaps: gap-6
- Card padding: p-6
- Sidebar spacing: space-y-6

## Component Patterns

**Category Badges:**
- Small pill shape with colored accent (Bitcoin=orange, Ethereum=purple, Regulation=red, etc.)
- Padding: px-3 py-1
- Font: text-xs uppercase tracking-wide

**Buttons:**
- Primary CTA: Blurred background when over images, medium size (px-6 py-3)
- Secondary: Outline style for non-critical actions
- Rounded corners: rounded-lg

**Article Cards:**
- Subtle border treatment
- Hover: transform scale-[1.02] transition
- Shadow elevation on hover

**Icons:**
Use Heroicons (CDN) for: Search, menu, user account, share, bookmark, external link, trending arrows

## Professional News Aesthetics

- Clean, scannable layouts - never cramped
- Generous whitespace between articles
- Consistent image aspect ratios
- Clear visual hierarchy: featured > standard articles
- Sophisticated use of typography weight and size
- Professional metadata presentation (author, time, category always visible)
- Market data integration throughout (tickers, widgets)