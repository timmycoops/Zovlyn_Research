# Zovlyn Research — project instructions

This project is a working research desk for an independent mining/lithium analyst. It is a collection of HTML tools — a tool index, long-form research reports, calculators, screeners, maps, primers — all sharing one design system.

## Design system

The system is documented in **`system.html`** (open it before designing anything new). It is the source of truth for tokens, type, components, voice, and templates. Read it.

Two files are the **canonical implementations** to copy-fork from:

- **`index.html`** — tool index / homepage. Use as the starting point for any landing/directory page.
- **`QTWO_Research_Report_v7.html`** — long-form research report. Use as the starting point for any deep-dive report, calculator, or data-heavy tool. Strip the QTWO content, keep the chrome and patterns.

Always inherit from these. Never start a new page from a blank file.

## Locked decisions — do not relitigate

- **Visual direction:** Terminal / Bloomberg-grade. Dense, monospaced, data-first, dark.
- **Light/dark:** Dark only. Do not propose a light mode.
- **Accent color:** Lithium green `#5dd3a8` (`--accent`). One signature color does the work of three. No multi-color decoration.
- **Wordmark:** Z badge (lithium green square, black "Z") + stacked "ZOVLYN / RESEARCH" in JetBrains Mono. Three sizes (S/M/L). Never separated, never recolored, never on white.
- **Type:** JetBrains Mono for everything UI, headers, numbers, labels. Inter for prose body copy only. No other families.
- **Corner radius:** Soft 4px (`--r`), system-wide. Single token.
- **Naming:** Tools named by what they do (`EV / t LCE Universe`), not codenames. Tickers always uppercase with exchange suffix (`QTWO.V`). The brand is a quiet badge in nav, never the page title.

## Tokens (canonical CSS variables)

```css
:root {
  --bg: #0c0d0a;       --bg-2: #131410;     --bg-3: #1a1c16;
  --line: #2a2c24;     --line-2: #3a3d33;
  --fg: #d8d4c2;       --fg-2: #8a8773;     --fg-3: #5d5b4d;
  --accent: #5dd3a8;   --accent-2: #3aa881; --accent-dim: rgba(93,211,168,0.10);
  --green: #5dd380;    --red: #ff5f56;      --amber: #e8b658;   --cyan: #6acfe0;
  --r: 4px;
  --mono: 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace;
  --sans: 'Inter', system-ui, sans-serif;
}
```

Semantic colors carry meaning: `--green` = positive/cash flow, `--red` = negative/risk, `--amber` = watch/exogenous, `--cyan` = peer/neutral comparison. Never use them decoratively.

## Voice & tone

- Independent, contrarian, technical, calm. Sharp without being loud.
- State the number, the comparison, the caveat. No exclamation marks, no emoji, no rocket ships, no superlatives that aren't earned.
- Numbers are sacred. Always include unit, source, and as-of date when context allows. `$2,000/t SC6`, not "around $2k".
- Audience is sophisticated investors who already know NI 43-101, JORC, LCE, SC6, EV/t LCE. Do not over-explain.
- Every page that discusses a position or company must include a "not investment advice" line in the footer.

## Page chrome (every page starts with this)

1. **Status bar** (`--bg-2`) — session timer · tool name · version · live clock right-aligned
2. **Nav bar** (`--bg`) — Z badge wordmark left · uppercase mono links right
3. *(Homepage only)* **Ticker tape** strip between them

## Components — the floor for any new tool

- KPI tiles (4-up or 6-up grid, mono numbers with `tnum`, `--accent` for the headline number)
- Cards (`--bg-2`, hairline border, accent uppercase header with `▸` prefix, dashed underline)
- Tables (small mono headers, 13px body, hairline rows, hover highlight, `.t-hl` for "winning" rows in accent green)
- Sparkline rows (ticker · 200×32 svg polyline · price + delta)
- Status pills (5 variants: primary, peer/cyan, exogenous/amber, risk/red, soon/dim)
- Buttons (primary green, secondary outline, ghost)

## Charts (Chart.js)

Set defaults at the top of every chart-using page:

```js
Chart.defaults.color = '#8a8773';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 10.5;
Chart.defaults.borderColor = 'rgba(58,61,51,0.5)';
```

Palette is semantic only: accent green = our subject, red = downside, amber = reference/caution, cyan = peers, fg-2 = generic background series. Do not invent chart colors.

## What's shipped vs. what's next

**Shipped templates:**
- Tool index (`index.html`)
- Research report (`QTWO_Research_Report_v7.html`)
- System reference (`system.html`)

**Roadmap — needs templating:**
- Calculator template (LCE converter, DCF) — *next*
- Screener / data table — *next*
- Map view, Primer/explainer, Investment thesis one-pager, Watchlist dashboard — later

When asked to build something matching one of these archetypes, design the **template** first (reusable patterns), then fill it with the specific content.

## Working defaults

- File naming: `snake_case.html` or `kebab-case.html`. Versioned files keep the old version until the new one is verified.
- Avoid creating loose variations as separate files — use the design canvas + tweaks pattern instead, so options live side-by-side.
- Do not add filler content. Every element earns its place. If a section feels empty, that's a layout problem, not a content problem.
- Do not add light mode, do not add emoji, do not add gradient hero backgrounds, do not add new font families, do not invent new accent colors.
