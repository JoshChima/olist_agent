# AIE-55: accessibility review of the three pages

`design:accessibility-review` on Orders, Funnel and Explorer at the P1.5 milestone close, run on 2026-11-03 against the built app at 1280×1000 in both modes, with the e2e fixtures answering the API at clock 2018-02-17. Contrast ratios are computed from the rendered colours (every colour read back through a canvas, translucent fills composited over their ground). Standard: WCAG 2.1 AA. The shell was reviewed on AIE-51 (`docs/evidence/aie-51/accessibility-review.md`); this review covers the page bodies, with attention to what Skeleton doesn't cover: the Recharts panels and the Explorer's hand-rolled sort.

## Summary

Issues found: 6. Critical: 0. Major: 3 (2 fixed, 1 filed as [AIE-64](https://linear.app/gloph-software-factory/issue/AIE-64)). Minor: 3 (fixed).

## Findings

### Perceivable

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 1 | Recharts writes legend labels in the series colour, as an inline style. Four miss 4.5:1 on `card`: light `series-1` 4.2:1, `series-2` 3.0:1, `series-3` 4.0:1; dark `series-1` 3.4:1, `series-4` 2.9:1, `series-3` 4.4:1. Orders (customer states) and Funnel (origins). | 1.4.3 Contrast | 🟡 Major | **Fixed**: the chart panel colours legend labels `ink-muted` at `small` (7.1:1 light, 6.0:1 dark), as axis text is. The swatch keeps the series colour. |
| 2 | Two bar fills under 3:1 on `card`: light `series-2` (tertiary-600, 3.0:1: the Orders "People" bars, Funnel paid search) and dark `series-4` (surface-400, 2.9:1: Funnel unknown). | 1.4.11 Non-text contrast | 🟡 Major | **Fixed**: `series-2` light is tertiary-700 (3.7:1), `series-4` dark is surface-300 (4.2:1), and `series-6` light moves to tertiary-900 so it stays a step darker than the new `series-2`. All eight series are now 3.4:1 or more in both modes. |
| 3 | Charts have no text alternative: a screen reader gets the tick labels and nothing of the data. | 1.1.1 Non-text content | 🟡 Major | Filed as [AIE-64](https://linear.app/gloph-software-factory/issue/AIE-64): a data summary or hidden table is new content, outside a restyle milestone. |

### Operable

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 4 | Each chart surface is focusable (Recharts' accessibility layer, arrow keys move the tooltip) but showed the browser's default focus outline, not the theme's `focus` ring. | 2.4.7 Focus visible | 🟢 Minor | **Fixed**: the chart panel gives the surface the `focus` ring. |

Tab order on every page: date input → six step buttons → three rail tiles → page content (Orders: four chart surfaces; Funnel: one; Explorer: view picker, sort buttons left to right, pager). The sort buttons are native buttons (Enter and Space sort), show the `focus` ring, and sit inside the scrolling wrap, so arrow keys scroll the rows once one has focus. They are 18px tall, under WCAG 2.2's 24px target (2.5.8, not in 2.1 AA); the header row's 36px cell is the practical target.

### Understandable

No issues. Labels and headings are sentence case and in the glossary's words; each dashboard states its "as of" day once; the Funnel says what its shaded months mean in a caption under the chart.

### Robust

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 5 | Every chart surface is `role="application"` with no name: a screen reader announced four unnamed applications on Orders. | 4.1.2 Name, role, value | 🟢 Minor | **Fixed**: the chart panel passes its title to the chart as `aria-label` ("Daily orders, last 90 days"). Not an SVG `title`, which would also pop a native hover tooltip over Recharts' own. |
| 6 | The sort button's name included the arrow glyph ("order_status black up-pointing triangle") on top of the header's `aria-sort`. | 4.1.2 Name, role, value | 🟢 Minor | **Fixed**: the arrow is `aria-hidden`; `aria-sort` alone says the order. |

## Colour contrast

| Element | Light | Dark | Required | Pass |
|---|---|---|---|---|
| Section titles on card | 15.2:1 | 10.7:1 | 3:1 | ✅ |
| Stat label (`ink-muted`) on card | 7.1:1 | 6.0:1 | 4.5:1 | ✅ |
| "as of" line on page | 7.7:1 | 7.2:1 | 4.5:1 | ✅ |
| Axis tick labels on card | 7.1:1 | 6.0:1 | 4.5:1 | ✅ |
| Data-quality label on its shade | 5.8:1 | 4.5:1 | 4.5:1 | ✅ (dark at the floor) |
| Tooltip label / values on card | 7.1:1 / 15.2:1 | 6.0:1 / 10.7:1 | 4.5:1 | ✅ |
| Legend labels on card | 7.1:1 | 6.0:1 | 4.5:1 | ✅ after finding 1 |
| Lowest bar fill on card | 3.7:1 | 3.4:1 | 3:1 | ✅ after finding 2 |
| Explorer header (`ink-muted`) on page | 7.7:1 | 7.2:1 | 4.5:1 | ✅ |
| Sort button on hover (`preset-tonal`) | 13.6:1 | 9.5:1 | 4.5:1 | ✅ |
| Table cells on page | 16.6:1 | 12.9:1 | 4.5:1 | ✅ |
| Focus ring on card | 4.2:1 | 4.5:1 | 3:1 | ✅ |

## Screen reader

| Element | Announced as |
|---|---|
| Chart surface | "Daily orders, last 90 days, application" (after finding 5) |
| Funnel stages | list of 3; "Conversion from the previous stage: 3.6%", then "Closed deal 135"; the arrow is hidden |
| Explorer header | "order_status, button", column header sorted ascending |
| Pager | "Pages of rows" navigation; Previous, page buttons, Next |

## Shell findings carried from AIE-51 (AIE-59)

The AIE-51 shell review filed three minors as [AIE-59](https://linear.app/gloph-software-factory/issue/AIE-59) for a decision at milestone close. Decided 2026-11-05, all three closed:

| # | Issue | WCAG | Decision |
|---|---|---|---|
| 1 | The date input's edge is Concord's `surface-300-700` ring: 2.5:1 on `card` light, 1.2:1 dark. | 1.4.11 Non-text contrast | **Fixed**: a second override-block entry sets that pair to surface-400 light / surface-300 dark on `.input` only, so the edge is 3.7:1 on `card` light and 4.2:1 dark (6.0:1 on the input's own dark fill). Focus still turns it primary. The design system artifact carries it as `input-edge`. |
| 2 | The delta strip truncates at tablet width: a day step's nine counts need 1163px of text, a month step's 1311px; the column gives 896px at 1024 wide. | 1.4.10 Reflow (advisory) | **Fixed**: below Tailwind's `2xl` (1536px, where a month's counts still fit on one line) the strip wraps instead of truncating, two lines at 1024 and 1280 wide; from 1536px up it stays one line with the ellipsis. No wording change, no count dropped. |
| 3 | Duplicate page heading under the shell's h1. | 2.4.6 Headings and labels | **Gone**: Orders and Funnel open with a section heading and a `small` `ink-muted` "as of" line (AIE-52, AIE-54). |

Contrast measured from the design system's hex values (WCAG relative luminance): edge on `card` before 2.52:1 light, 1.23:1 dark; after 3.72:1 light, 4.23:1 dark. Widths measured in Chromium with the shipped Inter against the e2e delta fixture (a day) and a month's counts.

## Glyphs outside the typeface

Not accessibility findings, but found on the same pass: Inter's Fontsource subsets carry ↑ ↓ − – … but not → or ▲ ▼, which fell back to a system font that draws differently per platform. The Funnel's arrows are now an inline SVG stroked in the text colour, and the Explorer's sort arrows are ↑ and ↓. The delta strip's "from → to" still uses →; its wording is pinned by the e2e interaction and it is not in a screenshot, so it is left as is.
