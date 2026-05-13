# /img — image assets for Zovlyn Research reports

One folder per company / report. Reference images relatively from inside a report HTML file:

```
img/PMET/site-aerial-2025.jpg
img/ELV/nal-flowsheet.png
img/QTWO/cs25-044-section.jpg
```

## Figure pattern (canonical)

Every image in a report lives inside a `<figure class="report-fig">` with a JetBrains-Mono caption + source attribution. The CSS is defined locally in each report (mirrors the design system; see `system.html`).

### Live image

```html
<figure class="report-fig">
  <img src="img/PMET/cv5-pit-shell.jpg" alt="CV5 pit-shell plan view">
  <figcaption>
    <span class="lbl">▸ CV5 pit shell — 6 sub-pits</span>
    <span class="src">Source: PMET FS, Oct 2025</span>
  </figcaption>
</figure>
```

### Placeholder (use while waiting on the image)

```html
<figure class="report-fig is-placeholder">
  <div class="report-fig-slot">
    <span class="lbl">CV5 pit shell — 6 sub-pits</span>
    <span class="desc">Drop file at img/PMET/cv5-pit-shell.jpg</span>
  </div>
  <figcaption>
    <span class="lbl">▸ CV5 pit shell — 6 sub-pits</span>
    <span class="src">Source: PMET FS, Oct 2025</span>
  </figcaption>
</figure>
```

To swap a placeholder for a live image: delete the `<div class="report-fig-slot">…</div>` block, add an `<img>` tag, and remove the `is-placeholder` class.

## Filename conventions

- All lowercase, hyphens not underscores: `cv5-pit-shell.jpg`
- Include a version / date suffix when the underlying disclosure may be refreshed: `nal-flowsheet-2026-05.png`
- Prefer `.jpg` for photos, `.png` for diagrams / line art, `.svg` for vector charts

## Sizing

Aim for ~1200–1600px wide source images. The figure frame is full-content-width on desktop (~1100px max) so anything wider is wasted bytes.
