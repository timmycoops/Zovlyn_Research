# Lithium Projects Map v2 — Data-Consumption Design

| Field | Value |
| --- | --- |
| Date | 2026-05-08 |
| Author | Tim Cooper (with Claude) |
| Status | Approved — schema landed; rendering plan TBD |
| Scope | `lithium_projects_map_*.html` and `lithium-supply-chain-network/data/network.js` |

## 1. Background and intent

The current `lithium_projects_map_8.html` is a project locator — dots on a world map with stage / jurisdiction filters. It tells the reader *where* lithium is, not *where it goes* or *who controls it*. The Lithium Network (`lithium-supply-chain-network/index.html`) holds all of the equity / financing / offtake topology but has no geography. The two tools are parallel and don't talk to each other.

Map v2 fuses them. The Map becomes the spatial view of the same dataset the Network already renders relationally. The headline picture this should expose: **spatial concentration of refining vs distribution of mining** — the China-bottleneck story that a static project map hides.

This spec covers the **data layer only** — what `network.js` carries, how the Map resolves it, and how flow size becomes a visual. It does not cover layout, controls, or interactions. Those land in a follow-up spec once the dataset is rich enough to render meaningfully.

## 2. Goals

- One source of truth for entities and relationships: `lithium-supply-chain-network/data/network.js`. Both the Network and the Map read it directly. No duplication.
- The Map can plot the *physical* geography of any node, including refiners whose HQ country differs from where they actually process material.
- The Map can render arc thickness proportional to annual flow volume in kt LCE-equivalent on offtake links — when that data exists. When it doesn't, the arc still draws (thin, unlabelled) so the topology is preserved.
- All conversion conventions (SC6 → LCE, hydroxide → LCE, etc.) live in one place: the `network.js` schema docstring.

## 3. Non-goals

- No new dataset. No external API for project coordinates. No live commodity prices in v2.
- No facility-level granularity beyond country. A v3 may add `facility_lat / facility_lng` for plant-precise rendering; v2 uses country centroids.
- No automatic flow inference. If `flow_kt_lce` is absent on a link, the map shows the relationship but not its volume — it does not guess.
- No edits to the Network's rendering. The Network keeps using `country` and `stake`; the Map's new fields are additive and ignored by the Network.

## 4. Schema additions (landed in `network.js`)

### 4.1 Node — `facility_country?`

ISO-2 code where the entity's primary production / processing physically happens. Optional. Falls back to `country` when absent.

Set this only when HQ ≠ facility — when the spatial story the Map should show is the physical-flow geography, not the legal / listing geography.

| Entity | `country` (HQ) | `facility_country` |
| --- | --- | --- |
| Tianqi | CN | AU (Kwinana) |
| Albemarle | US | AU (Kemerton — primary lithium plant) |
| POSCO | KR | AR (Sal de Oro JV — when used as origin of brine flow) |
| Liontown | AU | (unset — `country` is correct) |
| CATL | CN | (unset — domestic) |

Mining project nodes (Liontown, Pilbara, Talison, etc.) generally do not need `facility_country` set: their `country` is already the location of the rock.

### 4.2 Link — `flow_kt_lce?`

Annual contracted or expected volume flowing FROM source TO target, expressed in kilotonnes LCE-equivalent. Optional.

Meaningful primarily for `type === 'offtake'`. Case-by-case for `'financing'` (prepay deals where the volume is contractually defined). Not used for `'equity'` — equity arcs use `stake` for thickness.

Conversion conventions when the source contract is denominated in another unit:

| From | To LCE (divide / multiply by) |
| --- | --- |
| SC6 spodumene concentrate | tonnes ÷ 7.5 |
| Lithium hydroxide (LiOH·H2O) | tonnes ÷ 5.32 |
| Lithium carbonate (Li2CO3) | tonnes × 1.0 |
| Cathode (NMC / NCA / LFP) | tonnes × ~0.4 |

Numbers are sacred per Zovlyn voice. Every populated `flow_kt_lce` should have a sibling JS comment naming the source contract document and its date — e.g.
```js
{ source: 'pilbara', target: 'ganfeng', type: 'offtake', flow_kt_lce: 18 },
// Pilbara–Ganfeng SC6 long-term offtake, ~135 kdmt/yr SC6 (2024 reaffirmation).
// 135 / 7.5 ≈ 18 kt LCE/yr.
```

## 5. Resolution rules (Map consumes, Network ignores)

### 5.1 Node coordinate

```
node.lat, node.lng = centroid_of(node.facility_country || node.country)
```

The Map ships with a static ISO-2 → centroid lookup table. Centroids are population-weighted where one is published, geographic centroid otherwise. The lookup table is part of the Map page, not `network.js`, since it's rendering data and never hand-edited.

### 5.2 Arc origin / destination

```
arc.origin      = coordinate(source)
arc.destination = coordinate(target)
```

Arcs are great-circle paths rendered as SVG quadratic Béziers. When origin and destination resolve to the same country (intra-country relationship) the arc is drawn as a small offset loop, not a zero-length line.

### 5.3 Arc thickness

| Link state | Thickness | Why |
| --- | --- | --- |
| `flow_kt_lce` set | linear scale, clamped 1.5–6 px against the dataset's max | makes the China-bottleneck arcs visibly heavier |
| `type === 'equity'` and `stake` set, no flow | scale by stake (0.5–3 px) — same encoding as Network | consistent with the existing graph view |
| Anything else | 1 px default | preserves topology without overstating |

Stroke style stays consistent with the Network: equity solid, offtake dotted, financing dashed. Stroke colour stays neutral fg-2 by default; selection / ego-network highlighting uses accent green per CLAUDE.md.

### 5.4 Hover / selection labels

- Default: no labels rendered (would clutter at the world-map zoom).
- Hover an arc: tooltip with `source.name → target.name`, type, and either `flow_kt_lce` (when present) or `stake` (when present), with units.
- Click a node: lock the ego-network — only arcs touching that node remain at full opacity, the rest dim. Same interaction as the Network's `index.html` already implements.

## 6. Backwards compatibility

- The Network (`lithium-supply-chain-network/index.html`) does not read `facility_country` or `flow_kt_lce` and will continue to behave identically.
- The current Map (`lithium_projects_map_8.html`) does not read any of `network.js` and is unaffected. Map v2 is a new file or a full rewrite of the existing one — TBD when the rendering spec lands.
- All new fields are optional. The dataset is valid at every stage of population. No bulk-edit migration is required.

## 7. Open questions for the rendering spec (next doc)

- Which projection? Robinson is the default for static world maps; Equal-Earth reads more honestly for a refining-concentration story. Pick one and stick.
- Where do filters live — left rail (mirror Network) or top of canvas (mirror current map)? Lean: left rail, for symmetry with Network.
- Time slider 2026 → 2040 driven by the Supply Model's `lithium_supply_model.html` forecasts: in v2 or v3? Lean: v3 — locks scope.
- Centroid table source — manually populated for the ~25 countries currently in the dataset, or pulled from a published list (e.g. Natural Earth)? Lean: hand-rolled JS object for the v2 country set; revisit if coverage grows.

## 8. Implementation status

- [x] Schema documented in `network.js` JSDoc header.
- [ ] Populate `facility_country` for the ~5 known HQ ≠ facility entities (Tianqi, Albemarle, POSCO, plus any cell makers with announced overseas plants).
- [ ] Populate `flow_kt_lce` on the well-attested offtake links (Liontown's Ford / LG Chem / Tesla deals; Pilbara → Ganfeng; Albemarle → Kemerton; etc.) with sibling comments citing the contract.
- [ ] Centroid lookup table (~25 ISO-2 codes covering current dataset).
- [ ] Map v2 rendering spec (next doc — covers projection, layout, controls, interactions).
- [ ] Map v2 build on canonical Zovlyn tokens, replacing `lithium_projects_map_8.html`.
