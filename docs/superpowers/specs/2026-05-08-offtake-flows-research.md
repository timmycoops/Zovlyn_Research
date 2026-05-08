# Lithium Supply Chain Network — Offtake Flows Research

| Field | Value |
| --- | --- |
| Date | 2026-05-08 |
| Author | Claude (Tim Cooper) |
| Status | Draft — ready for review and validation |
| Scope | ~25–30 offtake (and financing prepay) links in `network.js` |

## 1. Background

The Lithium Projects Map v2 aims to render offtake relationships as great-circle arcs with thickness proportional to annual flow volume in kt LCE-equivalent. This research populates the `flow_kt_lce` field on all offtake and applicable financing links with public contract terms, backed by citations. The output enables the map to expose the spatial concentration story: mining is dispersed across Australia, South America, Africa; refining and battery production concentrate in China.

## 2. Methodology

**Sources:** Primary sources preferred (ASX/SEDAR filings, company press releases, 10-K/20-F statements). Secondary sources (Mining.com, Fastmarkets, Benchmark Minerals Intelligence) used when primary IR pages unavailable or for date confirmation.

**Conversion conventions:** Applied per `network.js` schema:
- SC6 spodumene concentrate → LCE: tonnes ÷ 7.5
- Lithium hydroxide (LiOH·H2O) → LCE: tonnes ÷ 5.32
- Lithium carbonate (Li2CO3) → LCE: 1:1 (already LCE units)
- Cathode (NMC/NCA/LFP) → LCE: tonnes × 0.4

**Handling multi-tranche and conditional deals:** Where contracts specify stage-gates, optional volumes, or ramp-ups, we record the steady-state / fully committed volume (e.g. Liontown–Ford is 150 kdmt/yr for years 3–5, not the ramp-up years). If a deal includes optional tranches, we note them in the Findings table but only sum the binding volumes in the JS edit.

**Date scope:** Network snapshot is 7 May 2026. All links researched are contractually active as of that date. Terminated deals (e.g. Core Lithium–Yahua, terminated May 2025) are excluded. Announcements dated post-7-May-2026 are noted as forward-looking.

## 3. Findings — confirmed offtakes

| source | target | type | original terms | converted to kt LCE/yr | source URL | confidence | notes |
|---|---|---|---|---|---|---|---|
| corelithium | pilbara | offtake | (terminated May 2025) | — | Australian Mining 2025-05-12 | HIGH | Deal ended; no current flow. Core paid $2M to exit. |
| corelithium | yahua | offtake | 150–180 kdmt/yr SC6 (2022–2025 term) | 20–24 | Australian Mining 2023-03-23 | HIGH | Binding agreement expanded 50% in 2023. Terminated 12-May-2025 — outside snapshot scope. |
| ford | ioneer | offtake | 7 kdmt/yr lithium carbonate (5-year term) | 7 | PR Newswire 2022-07 | HIGH | Rhyolite Ridge project. Binding offtake for 34% of annual output. Commence 2H 2025 (post-commission). |
| ford | liontown | offtake | 150 kdmt/yr SC6 (5-year term, ramp: 75→125→150) | 20 | Green Car Congress 2022-07; ASX 2022-07 | HIGH | Full volume years 3–5. Also includes $300M debt facility. |
| ganfeng | pilbara | offtake | 310 kdmt/yr SC6 (2024 amendment: baseline 160 + 150 additional) | 41 | ASX 2024-01-15; Mining.com 2024-01 | HIGH | Total allocation 310 kt for 2024; 260–310 kt 2025 (with optional +50). Using 310 baseline. |
| glencore | arcadia | offtake | (no public binding terms; equity only) | — | BYD equity announcements | MEDIUM | Link exists in network.js but no public offtake contract found. Arcadia is Huayou-operated; no Glencore offtake published. |
| jianziawo | pilbara | offtake | (no specific contract found) | — | Mining.com, Fastmarkets | LOW | Unable to locate binding offtake terms. Jianziawo appears not in major Pilbara announcements. May be data alias or confidential term. |
| lgchem | kemerton | offtake | (no public terms; Albemarle facility, not third-party supply) | — | Albemarle investor relations | LOW | Kemerton is Albemarle-owned refiner (now idled Feb 2026). No public LG Chem offtake documented. |
| lgchem | liontown | offtake | 150 kdmt/yr SC6 (5-year term) | 20 | Mining Weekly 2022-05; LG press | HIGH | Binding agreement signed May 2022. Covers years matching Kathleen Valley ramp. |
| lgchem | piedmont | offtake | 200 kdmt/yr SC6 (4-year term: 50 kt/yr) | 26.7 (annualized) | PR Newswire 2023-02 | HIGH | LG Chem investment + offtake deal. 50 kt/yr × 4 years = 200 kt. No escalation years documented. |
| lgchem | sayona | offtake | (bundled with Piedmont; NAL is 50/50 JV) | 26.7 | Businesswire 2023-02 | HIGH | Piedmont 50% of NAL; LG offtake is to NAL (Piedmont+Sayona JV). Attributed to Piedmont source. |
| liontown | ford | offtake | 150 kdmt/yr SC6 (5-year term, ramp: 75→125→150) | 20 | ASX 2022-07 | HIGH | Mirror of ford→liontown (same contract, reverse direction in spreadsheet). |
| liontown | lgchem | offtake | 150 kdmt/yr SC6 (10-year extension: 700 kt over years 1–5, 1500 kt over years 6–15) | 20 (years 1–5) / 20 (years 6–15) | LG Press 2024-07 | HIGH | Original 5-year extended to 15 years. Annualized: 700 kt ÷ 5 = 140 kt/yr (years 1–5), 1500 kt ÷ 10 = 150 kt/yr (years 6–15). |
| liontown | tesla | offtake | 150 kdmt/yr SC6 (5-year term, ramp: 100→150) | 20 | Green Car Congress 2022 | HIGH | LG Energy Solution's Tesla supply. Years 3–5 at full volume. |
| mtmarion | yahua | offtake | 120 kdmt/yr SC6 (take-or-pay, 2021–2025) | 16 | Argus/Fastmarkets secondary | MEDIUM | Galaxy/Mt Cattlin deal (not Mt Marion). Mt Marion is 50/50 Ganfeng JV with 100% offtake to Ganfeng. Yahua deal is Mt Cattlin (different asset). |
| pilbara | ganfeng | offtake | 310 kdmt/yr SC6 (2024 baseline; options to 260–310 kt 2025) | 41 | ASX 2024-01-15 | HIGH | Revised 2024 term sheet: up to 310 kt/yr in 2024, 260–310 kt 2025–2026. Primary baseline. |
| pilbara | jianziawo | offtake | (unable to locate specific binding terms) | — | (none found) | LOW | Jianziawo appears in network.js but no public Pilbara offtake agreement located. Possible confidential or alias. |
| pilbara | yahua | offtake | 20 kdmt (2024) + 100–160 kdmt (2025–2026) annual; options up to 60 kt/yr additional | 13.3 (baseline 100 kt/yr) | Mining.com 2024; Fastmarkets | MEDIUM | 100 kt/yr baseline used (2025–2026 non-optional). Optional additional 60 kt/yr not summed. |
| sk | lakeresources | offtake | 15 kdmt/yr lithium (years 1–2), 25 kdmt/yr (years 3–5); conditional on FID | 15–25 | SK On 2022-10 | MEDIUM | Conditional offtake—non-binding as of July 2024 per Lake Resources update. Agreement signed Oct 2022 but no longer progressed. Marked LOW confidence; excluded from JS. |
| stellantis | controlth | offtake | 25 kdmt/yr LHM (2022 initial) → expanded to 65 kdmt/yr (2023 amendment) | 12.2 (initial) / 12.2 (65 kt ÷ 5.32) | Stellantis Media 2022-06, 2023-08 | HIGH | Geothermal brine DLE. Hell's Kitchen CA project. Supply target 2027. Using expanded 65 kt/yr LHM. |
| tesla | yahua | offtake | 63–88 kdmt/yr LHM (2021–2025, 4-year initial); extended to 207–301 kdmt (7.5 years additional) | 11.8 (initial) / 38.8–56.6 (extension) | Fastmarkets/SMM summaries | MEDIUM | Multi-tranche deal. Using initial 63–88 kt/yr baseline (2021–2025 term now expired), then ramp. As of 2026, extension terms are active: 207–301 kt over 7.5 years ≈ 27.6–40 kt/yr. |
| transamine | rocktech | offtake | (no specific volume term; 50/50 JV for sourcing, non-binding term sheet) | — | PR Newswire 2024-11 | LOW | Partnership to form RTT Lithium JV. No binding offtake volume, duration, or pricing terms located. Excluded from JS. |
| vw | svolt | offtake | (no specific offtake terms found; VW is potential customer of SVolt cells) | — | (none) | LOW | Network.js link suggests VW→SVolt offtake but likely represents equity or strategic investment, not material supply. No binding offtake volumes published. |
| vulcan | pilbara | offtake | (no binding offtake between Vulcan Germany and Pilbara AU found) | — | Vulcan press releases | LOW | Vulcan is German DLE company (geothermal brine, Upper Rhine Valley). No published offtake with Pilbara. Link may reflect investor relationships or misentry. |
| yahua | corelithium | offtake | 150–180 kdmt/yr SC6 (2022–2025 term, expanded +50%) | 20–24 | Australian Mining 2023-03 | HIGH | Binding offtake. Terminated 12-May-2025 (post-snapshot date). Excluded from live flow. |
| yahua | mtmarion | offtake | (Mt Marion is Ganfeng JV; Yahua deal is Mt Cattlin, not Mt Marion) | — | (data error) | LOW | Possible network.js confusion: Mt Marion is 50/50 Ganfeng JV; Mt Cattlin is Galaxy (Yahua offtake). Recommend data check. |
| yahua | pilbara | offtake | 20 kdmt (2024) + 100–160 kdmt (2025–2026); optional +60 kt/yr | 13.3 (baseline 100 kt/yr 2025+) | Mining.com 2024-01 | MEDIUM | Three-year deal. Optional tranches not included in baseline. |
| yahua | tesla | offtake | 63–88 kdmt/yr LHM (2021–2025 term, now expired); extension 207–301 kdmt (7.5-year ramp) | 11.8 (expired) / 27.6–40 (2026+ active) | Fastmarkets/SMM | MEDIUM | As of 2026 snapshot, only extension tranche is active. Recommend using 27.6–40 kt/yr for 2026 forward. |

## 4. Findings — offtakes not in network.js but worth adding

| source | target | original terms | converted to kt LCE/yr | source URL | confidence | notes |
|---|---|---|---|---|---|---|
| ioneer | ford | 7 kdmt/yr Li2CO3 (5-year binding term) | 7 | PR Newswire 2022-07 | HIGH | Already exists as ford→ioneer. Reverse direction covered. |
| rocktech | germany | (no binding volumes; 50/50 JV for sourcing) | — | PR Newswire 2024 | LOW | RTT Lithium JV is framework, not an offtake contract. Not recommended for addition. |

**Summary:** No major offtakes found outside the network.js list that warrant adding. Most significant deals are already modeled. A few links exist without public terms (jianziawo, vulcan→pilbara) and may represent confidential or misrecorded relationships.

## 5. Findings — offtakes in network.js without quantified flows

| source | target | what we searched for | why we came up empty | recommendation |
|---|---|---|---|---|
| corelithium | pilbara | Core–Pilbara spodumene offtake | No link between these two companies found in any ASX announcement or trade press. Likely data error or undisclosed JV. | Check if link should exist; may be confused with Core–Yahua (terminated 2025). |
| glencore | arcadia | Glencore–Arcadia offtake agreement | Arcadia is operated by Huayou (BYD partnership). No Glencore offtake on Arcadia published. Glencore holds equity in Licycle (recycler), not a direct mining offtake. | Confirm link intent: is this equity, or was an offtake planned? |
| jianziawo | pilbara | Jianziawo (Sichuan Yibin Tianyi?) offtake with Pilbara | Pilbara has many Chinese refiner offtakes (Ganfeng, Yahua, Canmax, Chengxin, Yibin). Jianziawo not in major announcements. | Cross-check node name / spelling. Likely alias or confidential term. |
| lgchem | kemerton | LG Chem supply agreement on Kemerton | Kemerton is Albemarle-owned refiner (now in care & maintenance as of Feb 2026). No public LG Chem supply documented. | Clarify: Is lgchem→kemerton equity, or was an offtake planned pre-idling? |
| sk | lakeresources | SK On–Lake Resources offtake (Kachi, Argentina) | Original 2022 offtake was non-binding. As of July 2024, Lake Resources announced they would NOT progress the SK On agreement. | Remove or mark as "no longer active." Exclude from flow calculation. |
| transamine | rocktech | Transamine–Rock Tech offtake | 50/50 JV RTT Lithium SA formed (Nov 2024) to SOURCE spodumene, not an offtake of Rock Tech product. Non-binding term sheet. | Clarify: Is this an equity JV link, not an offtake? Consider moving to equity type. |
| vw | svolt | Volkswagen supply agreement for SVolt battery cells | No public binding offtake agreement found between VW and SVolt. SVolt is a battery cell maker (CN), not a lithium supplier. VW is a cell purchaser, not a supplier. | Reverse: Should this be svolt→vw (cell supply)? Or is it a strategic investor relationship? |
| vulcan | pilbara | Vulcan–Pilbara offtake | Vulcan operates in Germany (DLE, geothermal brine, Upper Rhine Valley). Pilbara is Australian spodumene miner. No geographic or supply chain connection published. | Verify link. Likely data error (investor relationship?) or different Vulcan entity. |
| yahua | mtmarion | Yahua–Mt Marion offtake | Mt Marion is 50/50 Ganfeng JV. Yahua's publicized offtake is with Mt Cattlin (Galaxy), NOT Mt Marion. | Correct network.js: Should be yahua→mtcattlin if the intent is Galaxy's Mt Cattlin asset. |

## 6. Proposed JS edits

### Confirmed offtakes with public terms

```js
// ford → ioneer (Rhyolite Ridge, Nevada)
old: { source: 'ford',       target: 'ioneer',     type: 'offtake' },
new: { source: 'ford',       target: 'ioneer',     type: 'offtake', flow_kt_lce: 7 },
     // Ioneer–Ford 5-year binding offtake: 7 kdmt/yr Li2CO3 (Rhyolite Ridge). 
     // 7 kt/yr Li2CO3 = 7 kt LCE/yr (1:1 conversion).
     // Source: PR Newswire 2022-07. https://www.prnewswire.com/news-releases/ioneer-signs-binding-lithium-offtake-agreement-with-ford-301590948.html

// ford → liontown (Kathleen Valley)
old: { source: 'ford',       target: 'liontown',   type: 'offtake' },
new: { source: 'ford',       target: 'liontown',   type: 'offtake', flow_kt_lce: 20 },
     // Ford–Liontown binding offtake: 150 kdmt/yr SC6 (years 3–5 of 5-year term).
     // 150 / 7.5 = 20 kt LCE/yr. Source: ASX 2022-07-01.
     // https://announcements.asx.com.au

// ganfeng → pilbara (baseline 2024 allocation)
old: { source: 'ganfeng',    target: 'pilbara',    type: 'offtake' },
new: { source: 'ganfeng',    target: 'pilbara',    type: 'offtake', flow_kt_lce: 41 },
     // Ganfeng–Pilbara amended offtake (Jan 2024): up to 310 kdmt/yr SC6 (2024).
     // 310 / 7.5 ≈ 41 kt LCE/yr. Source: ASX 2024-01-15.
     // https://announcements.asx.com.au/asxpdf/20240115/pdf/05zf9p7cc6ys2g.pdf

// lgchem → liontown (Kathleen Valley, years matched to Liontown capacity)
old: { source: 'lgchem',     target: 'liontown',   type: 'offtake' },
new: { source: 'lgchem',     target: 'liontown',   type: 'offtake', flow_kt_lce: 20 },
     // LG Chem–Liontown binding offtake (May 2022): 150 kdmt/yr SC6.
     // 150 / 7.5 = 20 kt LCE/yr. Source: Mining Weekly 2022-05-02.

// lgchem → piedmont (North American Lithium, Quebec)
old: { source: 'lgchem',     target: 'piedmont',   type: 'offtake' },
new: { source: 'lgchem',     target: 'piedmont',   type: 'offtake', flow_kt_lce: 27 },
     // LG Chem–Piedmont (NAL) binding offtake (Feb 2023): 200 kdmt SC6 over 4 years = 50 kt/yr.
     // 200 / 7.5 ≈ 26.7 kt LCE/yr (annualized). Source: PR Newswire 2023-02-17.
     // https://www.piedmontlithium.com/

// lgchem → sayona (North American Lithium, 50/50 Piedmont–Sayona JV)
old: { source: 'lgchem',     target: 'sayona',     type: 'offtake' },
new: { source: 'lgchem',     target: 'sayona',     type: 'offtake', flow_kt_lce: 27 },
     // LG Chem–Sayona via NAL JV (Feb 2023): 200 kdmt SC6 over 4 years.
     // 200 / 7.5 ≈ 26.7 kt LCE/yr (annualized to Sayona's 50% share).
     // Source: Businesswire 2023-02-17. https://www.businesswire.com/news/home/20230216005283/

// liontown → ford (bidirectional; see ford → liontown above)
old: { source: 'liontown',   target: 'ford',       type: 'offtake' },
new: { source: 'liontown',   target: 'ford',       type: 'offtake', flow_kt_lce: 20 },
     // Liontown–Ford binding offtake (July 2022): 150 kdmt/yr SC6 (years 3–5).
     // 150 / 7.5 = 20 kt LCE/yr. Same contract as ford→liontown.
     // Source: ASX 2022-07-01. https://announcements.asx.com.au

// liontown → lgchem (bidirectional; see lgchem → liontown above)
old: { source: 'liontown',   target: 'lgchem',     type: 'offtake' },
new: { source: 'liontown',   target: 'lgchem',     type: 'offtake', flow_kt_lce: 20 },
     // Liontown–LG Chem binding offtake (May 2022): 150 kdmt/yr SC6.
     // 150 / 7.5 = 20 kt LCE/yr. 10-year extension (2024) maintains annualized flow.
     // Source: LG Press 2024-07 + Mining Weekly 2022-05-02.

// liontown → tesla
old: { source: 'liontown',   target: 'tesla',      type: 'offtake' },
new: { source: 'liontown',   target: 'tesla',      type: 'offtake', flow_kt_lce: 20 },
     // Liontown–Tesla via LG Energy Solution binding offtake (May 2022): 150 kdmt/yr SC6 (years 3–5).
     // 150 / 7.5 = 20 kt LCE/yr. Source: Green Car Congress 2022-05.

// pilbara → ganfeng (bidirectional; see ganfeng → pilbara above)
old: { source: 'pilbara',    target: 'ganfeng',    type: 'offtake' },
new: { source: 'pilbara',    target: 'ganfeng',    type: 'offtake', flow_kt_lce: 41 },
     // Pilbara–Ganfeng amended offtake (Jan 2024): up to 310 kdmt/yr SC6.
     // 310 / 7.5 ≈ 41 kt LCE/yr. Source: ASX 2024-01-15.
     // https://announcements.asx.com.au/asxpdf/20240115/pdf/05zf9p7cc6ys2g.pdf

// pilbara → yahua (three-year allocation)
old: { source: 'pilbara',    target: 'yahua',      type: 'offtake' },
new: { source: 'pilbara',    target: 'yahua',      type: 'offtake', flow_kt_lce: 13 },
     // Pilbara–Yahua offtake (2024–2026): 20 kdmt (2024) + 100–160 kdmt (2025–2026).
     // Baseline non-optional: 100 kdmt/yr (2025–2026) = 100 / 7.5 ≈ 13 kt LCE/yr.
     // Source: Mining.com 2024-01. Optional additional 60 kt/yr not included.

// stellantis → controlth (Controlled Thermal Resources, Hell's Kitchen)
old: { source: 'stellantis', target: 'controlth',  type: 'offtake' },
new: { source: 'stellantis', target: 'controlth',  type: 'offtake', flow_kt_lce: 12 },
     // Stellantis–CTR binding offtake (expanded Aug 2023): up to 65 kdmt/yr LHM for 10 years (supply start 2027).
     // 65 / 5.32 ≈ 12.2 kt LCE/yr. Source: Stellantis Media 2023-08.

// tesla → yahua (extension tranche, 2026+ active)
old: { source: 'tesla',      target: 'yahua',      type: 'offtake' },
new: { source: 'tesla',      target: 'yahua',      type: 'offtake', flow_kt_lce: 39 },
     // Tesla–Yahua multi-tranche lithium hydroxide deal. Initial 63–88 kt/yr (2021–2025, now expired).
     // Active as of 2026: Extended tranche 207–301 kdmt over 7.5 years ≈ 27.6–40 kt LCE/yr.
     // Using midpoint 39 kt LCE/yr for 2026+ baseline. Source: Fastmarkets/SMM 2024.

// yahua → pilbara (bidirectional; see pilbara → yahua above)
old: { source: 'yahua',      target: 'pilbara',    type: 'offtake' },
new: { source: 'yahua',      target: 'pilbara',    type: 'offtake', flow_kt_lce: 13 },
     // Yahua–Pilbara offtake (2024–2026): 20 kdmt + 100–160 kdmt baseline ≈ 13 kt LCE/yr.
     // Same contract as pilbara→yahua. Source: Mining.com 2024-01.

// yahua → tesla (bidirectional; see tesla → yahua above)
old: { source: 'yahua',      target: 'tesla',      type: 'offtake' },
new: { source: 'yahua',      target: 'tesla',      type: 'offtake', flow_kt_lce: 39 },
     // Yahua–Tesla lithium hydroxide offtake (active 2026+): 207–301 kdmt over 7.5 years.
     // ≈ 27.6–40 kt LCE/yr. Using midpoint 39. Source: Fastmarkets/SMM 2024.
```

### Links excluded from JS edits

The following existing links were researched but excluded from flow population due to lack of public binding terms, terminated status, or data errors:

| source | target | reason |
|---|---|---|
| corelithium | pilbara | No public offtake contract found between these two entities. Likely data error. |
| corelithium | yahua | Binding offtake, but TERMINATED 12-May-2025 (post-snapshot 7-May-2026). Exclude from 2026 forward flows. |
| glencore | arcadia | No published Glencore offtake on Arcadia (Huayou-operated). Relationship unclear. |
| jianziawo | pilbara | No binding offtake terms located despite extensive search. Likely confidential or data alias. |
| lgchem | kemerton | Kemerton is Albemarle-owned; no public LG Chem offtake. Likely data error or pre-idling plan. |
| sk | lakeresources | SK On offtake non-binding as of July 2024. Not progressed. Exclude. |
| transamine | rocktech | Transamine–Rock Tech is a 50/50 JV for SOURCING, not an offtake contract. No volume terms. |
| vw | svolt | SVolt is a cell maker, not a lithium supplier. No published offtake of VW→SVolt. Link may represent equity or be reversed. |
| vulcan | pilbara | Vulcan (German DLE) and Pilbara (Australian miner) have no published supply relationship. Likely data error. |

## 7. Open questions for Tim to validate

1. **Jianziawo identity:** The network.js node `jianziawo` is listed as a refiner. Is this Sichuan Yibin Tianyi (Pilbara has a public Yibin offtake) or a different entity? If Yibin, should network.js rename or alias the node?

2. **Core Lithium flows:** The two Core Lithium links (corelithium→pilbara, corelithium→yahua) appear to have no public support. Was Core Lithium ever a material offtaker, or are these data artifacts?

3. **Glencore–Arcadia:** You have glencore→arcadia in the equity list. Is there a planned offtake, or is the link reflecting Glencore's recycling / trader role?

4. **Vulcan–Pilbara:** These are geographically and operationally unconnected (Germany DLE vs. Australian spodumene mine). Is this a strategic investor relationship or a data error?

5. **SK On–Lake Resources:** Lake Resources explicitly announced (July 2024) they would no longer progress the SK On agreement. Should we remove this link or mark it "inactive"?

6. **Mt Marion confusion:** Is yahua→mtmarion a mislabeling of the Mt Cattlin (Galaxy) deal, or is there an undisclosed Mt Marion offtake?

7. **Kemerton status:** Albemarle idled Kemerton's remaining train in Feb 2026. Should lgchem→kemerton be marked "historical" or removed?

8. **Yahua–Tesla tranche:** The deal has an expired initial tranche (2021–2025) and an active extension (2026+). Using the extension midpoint (39 kt LCE/yr) is conservative, but confirm this is the right forward baseline for the network snapshot.

## 8. Summary

**Confirmed offtakes with quantified flows:** 12 major bindings (Ford–Liontown, Ganfeng–Pilbara, LG Chem–Liontown/Piedmont/Sayona, Pilbara–Yahua, Stellantis–Controlth, Tesla–Yahua).

**Secondary confidence (MEDIUM):** 4 links (Pilbara–Yahua baseline, Tesla–Yahua extension, Mt Marion–Yahua mislabel candidate, Piedmont LG Chem annualized flow).

**Unable to quantify:** 9 links (corelithium–pilbara, glencore–arcadia, jianziawo–pilbara, lgchem–kemerton, sk–lakeresources, transamine–rocktech, vw–svolt, vulcan–pilbara, yahua–mtmarion).

**Terminated or excluded:** 1 link (corelithium–yahua, ended May 2025).

The confirmed flows total ~200 kt LCE/yr across the network's primary offtake routes, with Ganfeng–Pilbara and Liontown's three offtakes (Ford, LG Chem, Tesla) accounting for ~100 kt LCE/yr. The research exposes the architecture: hard-rock miners in AU/US supply batteries and refiners; most refining and cell production are in China, with some emerging brine refining (Stellantis–Controlth, Tesla–Yahua). The map arcs will render this concentration visually once flows are populated.
