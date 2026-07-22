# 首页方案 1：设计 QA

## 比较对象

- Source visual truth path: `C:\Users\dell\.codex\generated_images\019f87f5-69de-7911-8847-5c51e76ae825\exec-04141571-602b-4b22-a249-6a5b6c68be7d.png`
- Implementation screenshot path: `C:\Users\dell\Desktop\ARCHITECT\architecture-case-site\tmp\phase4-preview\cdp-home-1440.png`
- Side-by-side evidence: `C:\Users\dell\Desktop\ARCHITECT\architecture-case-site\tmp\phase4-preview\qa-option1-vs-home-1440.png`
- Source pixels: 1487 × 1058. Implementation: 1440 × 1024 CSS px at deviceScaleFactor 1.
- Normalization: source was proportionally resized into a 1440 × 1024 comparison canvas; implementation was captured at its native 1440 × 1024 viewport. Both show the default desktop homepage state with no active filters.

## Full-view and focused evidence

- Full view: the implementation preserves the selected direction's paper canvas, compact masthead, serif research headline, real architectural hero image, direct archive action, and archive-first reading order.
- Focused areas: hero typography/image composition; index heading and filter-entry boundary; mobile 390 × 844 capture at `tmp/phase4-preview/cdp-home-390.png`.
- Responsive checks: CDP verified no horizontal overflow at 1440, 1024, 768, and 390 CSS px. The respective `scrollWidth` equals `clientWidth` in every checked viewport.
- Primary interactions: desktop filter rail is visible with 29 filter controls; text search `museum` narrows the 17 real cases to 3 and updates the result count; at 390 px the filter drawer opens and closes correctly.
- Console: clean Chrome DevTools session reported no errors or warnings. `node --check src/app.js` and `python -m py_compile scripts/build_site.py` passed.

## Required fidelity surfaces

- Fonts and typography: serif is reserved for research heading, lead, and case names; sans-serif/mono are used for interface labels and evidence data. Small labels retain readable contrast and do not truncate at the tested breakpoints.
- Spacing and layout rhythm: desktop uses a 48px gutter, 4-column index, and 24px card gaps; 1024 uses 3 columns; 768 and 390 use 2 columns. The mobile hero becomes a single vertical sequence.
- Colors and visual tokens: paper, deep paper, ink, muted ink, line, field, and oxide are expressed as semantic CSS variables. Oxide is limited to action/focus emphasis.
- Image quality and asset fidelity: hero and case media use existing case-package images. Index images are 4:3; drawing-classified images use `object-fit: contain` with paper padding rather than a crop.
- Copy and content: all project titles, summaries, year/place/type/status fields, filters, and result counts are generated from the existing case data; no placeholder copy was introduced.

## Findings

- No actionable P0, P1, or P2 differences remain for the selected archive-first direction.

## Comparison history

1. P2 — old `#cases` title rule overrode the new section heading, rendering an outlined display style. Fixed with a final scoped `#cases`/`#featured` Token-layer override; post-fix desktop evidence is the implementation screenshot above.
2. P2 — a legacy mobile backdrop rule displayed the closed filter overlay. Fixed with an explicit `[hidden]` rule in the mobile layer; post-fix 390 px screenshot and drawer open/close test pass.
3. P2 — the first headless 390 px screenshot was window-size limited and appeared horizontally clipped. Rechecked with exact CDP device metrics: at 390 px, `scrollWidth` and `clientWidth` are both 375 after scrollbar allocation; the captured page has no horizontal overflow.

## Open questions

- The selected image is a visual direction rather than a strict pixel-specification. The implementation intentionally keeps the real 17-case archive, its existing route model, and its richer evidence fields instead of reproducing mock-only metrics or sample cards.

## Follow-up polish

- P3: a dedicated archive-list route would allow the filter rail and first case row to appear even earlier on the homepage while preserving the homepage's research introduction.
- P3: replace the local review/annotation control with a production review workflow before public release if end users should not see it.

final result: passed
