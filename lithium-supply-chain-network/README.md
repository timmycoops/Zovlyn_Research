# Lithium-Ion Battery Supply Chain Network

An interactive, force-directed network visualisation of equity and financing relationships across the lithium-ion battery supply chain — miners, refiners, cathode producers, cell makers, OEMs, traders, oil & gas majors, and recyclers.

Part of [Zovlyn Research](https://github.com/timmycoops/Zovlyn_Research).

## Data attribution

The underlying relationship dataset is adapted from work by **Daniel Jimenez / iLiMarkets**, specifically the *Lithium-Ion Battery Supply Chain: equity and large financing relationships* map (snapshot: 7 May 2026). All credit for the structural mapping of the industry belongs to him; this project is a re-rendering of that data into an interactive, navigable form. Any errors in transcription are mine, not his.

If you use or extend this work, please continue to credit Daniel Jimenez / iLiMarkets as the data source.

## What it does

- **Force-directed graph** of ~185 entities and ~190 relationships, clustered horizontally by supply-chain role (investor → miner → refiner → CAM → cell → OEM → recycler)
- **Three connection types**: equity stakes (solid), financing/debt (dashed), offtake/supply (dotted blue)
- **Filter** by role, country, and stage (production vs project)
- **Search** for any entity by name
- **Click any node** to lock-in detail view with grouped, directional connection list
- **Hover** to highlight the immediate ego-network
- **Drag, zoom, pan** the canvas
- Visual encoding: node size = degree centrality, dashed ring = project-stage, role-coloured fill

## Running it

It's a static site with one external dependency (D3.js from CDN). Two ways to view:

```bash
# Option 1 — open directly
open index.html        # macOS
xdg-open index.html    # Linux
start index.html       # Windows

# Option 2 — local server (recommended for dev)
python3 -m http.server 8000
# then visit http://localhost:8000
```

For GitHub Pages: enable Pages on the `main` branch from repo Settings → Pages. The site will serve directly from `/index.html`.

## Repo structure

```
.
├── index.html         # rendering, layout, interaction (single-file UI)
├── data/
│   └── network.js     # entity + relationship data (the editable layer)
├── README.md
├── LICENSE
└── .gitignore
```

The split is deliberate: `index.html` is presentation, `data/network.js` is the dataset. Update one without touching the other.

## Editing the data

Open `data/network.js`. The schema is documented at the top of the file. Briefly:

```js
// Add an entity:
{ id: 'newco', name: 'NewCo Lithium', role: 'miner',
  country: 'AU', stage: 'project', resource: 'hardrock' }

// Add a relationship:
{ source: 'newco', target: 'ganfeng', type: 'offtake' }
```

Valid `role` values: `miner`, `refiner`, `cam`, `cell`, `oem`, `investor`, `oilgas`, `recycler`.
Valid `type` values: `equity`, `financing`, `offtake`.

Refresh the page — node IDs that don't exist are filtered out at runtime, so partial edits won't break the rendering.

## Tech

- [D3.js v7](https://d3js.org/) — force simulation, zoom, drag
- Vanilla HTML/CSS/JS — no build step, no framework
- Self-contained except for the D3 CDN reference

## Roadmap

Things that would be nice to add:

- [ ] Stake percentages on edges (display on hover)
- [ ] Transaction dates / timeline filter
- [ ] Resource-type filter (hardrock / brine / clay)
- [ ] Sankey view alongside the force layout for upstream→downstream volume framing
- [ ] CSV/JSON export of filtered subgraph
- [ ] Mobile-friendly responsive layout
- [ ] Edge bundling for high-degree hub nodes (Ganfeng, CATL)

## License

Code: MIT — see [LICENSE](LICENSE).

Data: derivative of work by Daniel Jimenez / iLiMarkets. Re-use of the dataset should attribute the original source.
