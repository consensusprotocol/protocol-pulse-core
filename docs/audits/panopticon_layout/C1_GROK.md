### PANOPTICON DESKTOP LAYOUT AUDIT

I have conducted a thorough visual design audit of the PANOPTICON dashboard layout for desktop screens (1920x1080+), focusing on the provided CSS and HTML structure. Below are detailed analyses and recommendations for each of the six critical questions, with specific line number citations, severity ratings, and actionable fixes using exact CSS values.

---

### Q1 — GRID + PANEL RHYTHM

**Detailed Analysis:**
- **Gap Tightness (Line 327):** The `.pn-grid` uses a `gap: 1px`, which is excessively tight for a 1920px viewport. At this resolution, a 1px gap is visually imperceptible and fails to provide adequate separation between columns, making the layout feel cramped and cluttered.
- **Panel Padding (Line 346):** The `.pn-panel` padding of `20px 16px` is insufficient for breathing room at desktop widths. At 1920px, this results in content feeling too close to the edges, diminishing the premium feel expected of a high-end dashboard.
- **Max-Width Bottleneck (Line 321):** The `.pn-main` max-width of 1800px is a bottleneck for ultrawide monitors (2560px+). This constraint leaves significant unused space on larger screens, reducing the dashboard's ability to scale gracefully and utilize available real estate.
- **Vertical Rhythm (Lines 325-329):** The three-column grid (`1fr 1.1fr 1fr`) shows inconsistent vertical rhythm due to varying content lengths in each `.pn-panel`. Without a mechanism to balance heights or enforce consistent scrolling behavior, columns visually drift, disrupting the overall harmony.

**Severity:** HIGH
- The tight gap and insufficient padding significantly impact readability and perceived quality on desktop.
- The max-width limitation is a notable issue for ultrawide users, a key demographic for premium dashboards.

**Specific Fix:**
- Update `.pn-grid` gap to `gap: clamp(16px, 1.5vw, 28px);` (Line 327) to ensure visible separation that scales with viewport width.
- Increase `.pn-panel` padding to `padding: clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px);` (Line 346) for better breathing room at desktop resolutions.
- Adjust `.pn-main` max-width to `max-width: clamp(1600px, 90vw, 2400px);` (Line 321) to accommodate ultrawide monitors while maintaining a focused layout.
- Add `display: flex; flex-direction: column; height: calc(100vh - 420px);` to `.pn-panel` (Line 343) and ensure content containers within panels use `flex: 1; overflow-y: auto;` to enforce consistent vertical rhythm by aligning panel heights.

---

### Q2 — TYPOGRAPHY SCALING

**Detailed Analysis:**
- **Hardcoded Small Font Sizes (Multiple Lines):** Numerous elements use sub-10px font sizes, which are below the threshold for comfortable readability on a 1920px desktop display. Examples include:
  - `.pn-hero-stat-label` at 9px (Line 192)
  - `.pn-ticker-tag` at 8px (Line 288)
  - `.pn-panel-head` at 10px (Line 353)
  - `.pn-section-label` at 9px (Line 386)
  - `#ss2-verdict` at 9px (Line 1722)
  - `.ss2-wf-label` at 7px (Line 1992)
  - `.ss2-wf-contrib` at 6.5px (Line 1997)
  - `.ss2-si-label` at 7.5px (Line 1936)
  - `#ss2-dc-insight` at 8.5px (Line 1859)
- These sizes fail to meet the minimum recommended thresholds of ≥10px for labels, ≥12px for values, and ≥14px for headers on a premium product at desktop resolutions. Small text appears pixelated or strained on high-DPI displays, reducing accessibility and perceived quality.
- **Letter-Spacing Readability (Lines 159, 167, 223, 1681, etc.):** JetBrains Mono letter-spacing values range from `.12em` to `.25em` (e.g., `.pn-hero-title` at 12px letter-spacing on Line 159, `.ss2-overline` at .25em on Line 1681). At small font sizes (below 12px), these wide spacings can fragment text, making it harder to read quickly, especially for labels and tickers.

**Severity:** CRITICAL
- Typography is a foundational element of UI design. Sub-10px text at 1920px is a severe accessibility and aesthetic issue, directly impacting user experience on a premium dashboard.

**Specific Fix:**
- Replace hardcoded font sizes with `clamp()` for responsive scaling:
  - `.pn-hero-stat-label` (Line 192): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-ticker-tag` (Line 288): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-panel-head` (Line 353): `font-size: clamp(12px, 0.8vw, 16px);`
  - `.pn-section-label` (Line 386): `font-size: clamp(10px, 0.7vw, 14px);`
  - `#ss2-verdict` (Line 1722): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-label` (Line 1992): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-contrib` (Line 1997): `font-size: clamp(9px, 0.5vw, 11px);`
  - `.ss2-si-label` (Line 1936): `font-size: clamp(10px, 0.6vw, 12px);`
  - `#ss2-dc-insight` (Line 1859): `font-size: clamp(10px, 0.6vw, 12px);`
- Adjust letter-spacing for small text to improve readability: For all elements with font sizes potentially below 12px after clamping, set `letter-spacing: clamp(0.08em, 0.1vw, 0.12em);` (e.g., Lines 192, 288, 386). For larger text (headers like `.pn-hero-title`), retain current values as they are visually acceptable.

---

### Q3 — HERO STATS BAR

**Detailed Analysis:**
- **Height and Alignment (Lines 53, 174):** The `.pn-hero` height of 340px (Line 53) is adequate for 1920px but may feel constrained on ultrawide 2560px screens where vertical space perception shifts due to wider aspect ratios. The `.pn-hero-stats` flex row with `gap: 32px` (Line 175) is centered, but the min-height is not defined, risking overlap or misalignment if content scales.
- **Font Size Ratio (Lines 183, 191):** The `.pn-hero-stat-val` at 24px (Line 183) and `.pn-hero-stat-label` at 9px (Line 191) create a ratio of ~2.67:1, which is visually unbalanced for a premium feel. A ratio closer to 2:1 (e.g., 24px:12px) would provide better hierarchy and readability at desktop resolutions.
- **Radar Rings (Lines 67-85):** The `.pn-radar-rings` at 600px width/height (Line 76) are visually distracting at ultrawide resolutions (2560px+). They occupy a small central portion of the screen, leaving vast empty space on the sides, and their subtle opacity (e.g., `rgba(255,59,95,0.06)` on Line 79) makes them feel like background noise rather than an elegant design element.

**Severity:** MEDIUM
- The hero stats bar issues are noticeable but not critical to functionality. The radar rings’ distraction is more pronounced on ultrawide screens, affecting perceived polish.

**Specific Fix:**
- Increase `.pn-hero` height to `height: clamp(340px, 18vh, 400px);` (Line 53) to ensure proportional scaling on ultrawide screens.
- Define a `min-height: clamp(60px, 6vh, 80px);` for `.pn-hero-stats` (Line 174) to guarantee vertical space and maintain centered alignment.
- Adjust font sizes for better ratio: `.pn-hero-stat-val` to `font-size: clamp(20px, 1.5vw, 28px);` (Line 183) and `.pn-hero-stat-label` to `font-size: clamp(10px, 0.7vw, 14px);` (Line 191).
- Scale radar rings dynamically with `width: clamp(600px, 40vw, 800px); height: clamp(600px, 40vw, 800px);` (Line 76) and increase opacity to `rgba(255,59,95,0.12)` (Line 79) for elegance, or consider hiding them on ultrawide via media query if they remain distracting (`@media (min-width: 2400px) { .pn-radar-rings { display: none; } }`).

---

### Q4 — SOVEREIGN SIGNAL SECTION (ss2-root)

**Detailed Analysis:**
- **Alignment with Grid (Line 1656):** `#ss2-root` is full-bleed with no max-width constraint aligned to `.pn-main`’s 1800px (Line 321). This creates a visual disconnect as the section extends beyond the grid’s boundaries, disrupting layout coherence at 1920px and ultrawide.
- **Signal Board Column (Line 1867):** The `#ss2-middle` layout uses `grid-template-columns: 1fr 400px;` for the signal board (`#ss2-board-wrap`). At 1920px, 400px is too narrow, causing text truncation and cramped visuals in a section meant to be analytical and readable.
- **Waterfall Bars (Line 1970):** The `.ss2-wf-bar-wrap` height of 38px (Line 1970) is indeed cramped at desktop resolutions. Bars and labels overlap visually, reducing clarity in a data-heavy component.
- **Gauges Row Padding (Line 1731):** The `.ss2-gauge-cell` padding of `14px clamp(10px, 1.5vw, 18px) 10px` (Line 1731) is marginally sufficient at 1920px but feels tight on ultrawide screens where more horizontal space is available, risking a cluttered appearance.

**Severity:** HIGH
- Misalignment with the main grid and cramped components undermine the premium, data-driven aesthetic of the Sovereign Signal section, especially at desktop widths.

**Specific Fix:**
- Constrain `#ss2-root` to align with grid: `max-width: clamp(1600px, 90vw, 2400px); margin: 0 auto;` (Line 1656) to match `.pn-main`’s responsive width.
- Adjust `#ss2-middle` signal board column to `grid-template-columns: 1fr clamp(400px, 22vw, 500px);` (Line 1867) for better readability at 1920px and beyond.
- Increase `.ss2-wf-bar-wrap` height to `height: clamp(50px, 3.5vh, 70px);` (Line 1970) to give bars and labels more breathing room.
- Update `.ss2-gauge-cell` padding to `padding: clamp(16px, 1.2vw, 24px) clamp(12px, 1.8vw, 24px) clamp(12px, 1vw, 16px);` (Line 1731) to ensure adequate spacing across desktop resolutions.

---

### Q5 — CARD COMPONENTS

**Detailed Analysis:**
- **Padding (Lines 400, 699, 625, 789):** Card components have inconsistent and often inadequate padding for desktop:
  - `.pn-disc-card` padding is `14px` (Line 400), below the target `clamp(12px, 1.5vw, 20px)`.
  - `.pn-poly-item` padding is `12px 14px` (Line 699), slightly below target on larger screens.
  - `.pn-whale-item` padding is `12px 14px` (Line 625), similarly constrained.
  - `.pn-geo-item` padding is `12px 14px` (Line 789), same issue.
- **Line-Height (Lines 426, 705, 651, 797):** Line heights are often below the target 1.5–1.6 for readability:
  - `.pn-disc-entity` has no explicit line-height, defaults to ~1.2 (Line 426).
  - `.pn-poly-question` is `1.3` (Line 705), too tight.
  - `.pn-whale-entity` has no explicit value (Line 649), defaults low.
  - `.pn-geo-headline` is `1.3` (Line 797), insufficient.
- **Border-Left Accent (Lines 401, 700, 641, 790):** Border-left accents vary in thickness and consistency:
  - `.pn-disc-card` uses `3px` (Line 401), consistent.
  - `.pn-poly-item` uses `1px` (Line 700), too thin for visibility.
  - `.pn-whale-item.inflow/outflow` uses `3px` (Line 641), consistent with disclosure cards.
  - `.pn-geo-item` uses `1px` (Line 790), too subtle.
- **Max-Width Constraints (Various Lines):** Cards lack explicit max-width or line-length constraints, risking awkward text wraps on ultrawide screens (e.g., `.pn-disc-entity` on Line 426 can overflow without `text-overflow` fully preventing long unbroken strings).

**Severity:** MEDIUM
- While functional, these inconsistencies and tight spacings reduce the premium feel and readability on desktop, especially for data-heavy cards.

**Specific Fix:**
- Standardize padding to `padding: clamp(12px, 1.5vw, 20px) clamp(14px, 1.8vw, 22px);` for `.pn-disc-card` (Line 400), `.pn-poly-item` (Line 699), `.pn-whale-item` (Line 625), and `.pn-geo-item` (Line 789).
- Set line-height to `line-height: clamp(1.4, 0.1vw, 1.6);` for `.pn-disc-entity` (Line 426), `.pn-poly-question` (Line 705), `.pn-whale-entity` (Line 649), and `.pn-geo-headline` (Line 797).
- Standardize border-left to `border-left: 3px solid var(--pn-red);` for `.pn-poly-item` (Line 700) and `.pn-geo-item` (Line 790) to match `.pn-disc-card` and `.pn-whale-item`.
- Add `max-width: 100%; overflow: hidden; text-overflow: ellipsis;` to text containers like `.pn-disc-entity` (Line 426), `.pn-poly-question` (Line 703), `.pn-whale-entity` (Line 649), and `.pn-geo-headline` (Line 795) to prevent awkward wraps.

---

### Q6 — COMMANDER LOCK ON CORRELATION MAP

**Detailed Analysis:**
- **Approach Feasibility (Not in Code Yet):** The proposed Jinja `{% if not is_commander %}` conditional blur overlay for `#ss2-map-wrap` is sound as it leverages server-side rendering to apply the lock, ensuring no client-side data leakage if implemented correctly. It should wrap the canvas (Line 1621) with a conditional div.
- **Data Leakage Risk (Lines 1621-1629, 2330-2437):** Currently, the canvas (`#ss2-map-canvas`) and its rendering logic in JavaScript (Lines 2330-2437) expose data points (e.g., `mapData` with scores and positions) in the DOM and client-side code. Without server-side gating, free users can inspect the DOM or disable CSS to access Commander data. The Jinja approach mitigates this by not rendering sensitive data for free users if implemented with a fallback or redacted dataset.
- **Teaser Design (Conceptual):** A blurred canvas with a centered lock box and “UNLOCK COMMANDER →” button aligns with the brand’s premium, surveillance-tech aesthetic (e.g., `.pn-classified-overlay` on Line 917). It maintains the red (#CC2222) and dark (#0A0A0F) palette from LAW 1, ensuring on-brand consistency.
- **Axis Labels Visibility (Lines 1626-1628):** The axis labels and section header (Lines 1619-1620) are outside the `#ss2-map-wrap` canvas container. They will remain visible for free users unless explicitly hidden, which is desirable for context while teasing premium content.

**Severity:** HIGH
- Potential data leakage via client-side code is a critical security concern for a premium feature. The visual design is sound, but implementation must prevent DOM exposure.

**Specific Fix:**
- Implement Jinja conditional around `#ss2-map-wrap` content (Line 1621): `{% if not is_commander %}<div style="position:relative;"><canvas id="ss2-map-canvas"></canvas><div style="position:absolute;inset:0;backdrop-filter:blur(12px);background:rgba(0,0,0,0.6);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;"><div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;letter-spacing:8px;color:var(--pn-red);text-transform:uppercase;transform:rotate(-8deg);border:3px solid var(--pn-red);padding:8px 24px;opacity:0.85;">CLASSIFIED</div><a href="/join" style="display:inline-block;padding:10px 24px;background:var(--pn-red);color:var(--pn-white);font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;text-decoration:none;transition:all 0.2s;">Unlock Commander &rarr;</a></div></div>{% else %}<canvas id="ss2-map-canvas"></canvas>{% endif %}`
- Prevent data rendering for free users by gating `mapData` in JavaScript (Line 2371): Add a server-injected flag `<script>var isCommander = {{ 'true' if is_commander else 'false' }};</script>` and wrap rendering logic with `if (isCommander) { /* render mapData */ } else { /* render placeholder or nothing */ }`.
- Ensure axis labels and header remain outside the conditional block (Lines 1619-1620, 1626-1628) to maintain teaser context for free users.

---

### FINAL VERDICT

**Top 5 CSS Changes for World-Class Desktop Layout:**
1. **Grid Gap and Panel Padding (Q1):** Update `.pn-grid` gap to `clamp(16px, 1.5vw, 28px)` (Line 327) and `.pn-panel` padding to `clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px)` (Line 346) for breathing room and visual separation at 1920px+.
2. **Typography Scaling (Q2):** Replace sub-10px font sizes with `clamp()` values (e.g., `.pn-hero-stat-label` to `clamp(10px, 0.6vw, 12px)` on Line 192) to ensure readability across desktop resolutions.
3. **Hero Stats Bar Height (Q3):** Set `.pn-hero` height to `clamp(340px, 18vh, 400px)` (Line 53) and `.pn-hero-stats` min-height to `clamp(60px, 6vh, 80px)` (Line 174) for proportional scaling on ultrawide screens.
4. **Sovereign Signal Alignment (Q4):** Constrain `#ss2-root` with `max-width: clamp(1600px, 90vw, 2400px); margin: 0 auto;` (Line 1656) to align with the main grid, and widen signal board to `1fr clamp(400px, 22vw, 500px)` (Line 1867).
5. **Card Padding and Line-Height (Q5):** Standardize card padding to `clamp(12px, 1.5vw, 20px) clamp(14px, 1.8vw, 22px)` (Lines 400, 699, 625, 789) and line-height to `clamp(1.4, 0.1vw, 1.6)` (Lines 426, 705, 649, 797) for readability.

**What Stays As-Is (Already Excellent):**
- The color palette (Lines 16-29) adheres to LAW 1 (Brand Palette) with `#CC2222` red, `#0A0A0F` background, and `#F8C15C` gold, providing a cohesive, premium aesthetic.
- Animation effects like `.pn-radar-sweep` (Lines 114-135) and card entrance animations (Lines 406-415) add polish without overwhelming the design, aligning with LAW 5 (Animation).
- The historical timeline design (Lines 1013-1229) with glassmorphic cards and glowing red line is visually striking and on-brand for desktop.

**Overall Verdict:** PASS WITH FIXES
- The current layout has a strong foundation with thematic consistency and premium elements but falls short on desktop scalability, typography readability, and spacing. Implementing the above fixes will elevate it to a world-class standard for 1920px+ screens, addressing critical accessibility and aesthetic concerns while maintaining the brand’s surveillance-tech identity.