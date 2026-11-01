# AIE-51: accessibility review of the shell

`design:accessibility-review` on the shell built for AIE-51 (app bar, clock controls, navigation rail, delta strip), run on 2026-11-01 against the built app at 1280×1000 and 1024×768 in both modes, with Chromium driven by the Playwright MCP server and the e2e fixtures answering the API. Contrast ratios are computed from the rendered colours (translucent fills composited over their ground). Standard: WCAG 2.1 AA. The page bodies (charts, table) are out of scope here; the milestone-close review covers them.

## Summary

Issues found: 4. Critical: 0. Major: 1 (fixed). Minor: 3 (filed).

## Findings

### Perceivable

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 1 | The date input's edge (Concord's `surface-300-700` ring on the card) is 2.5:1 in light and 1.2:1 in dark, under the 3:1 floor for component boundaries. The input stays identifiable by its text and calendar icon, and its focus state is 4.2:1 / 4.5:1. | 1.4.11 Non-text contrast | 🟢 Minor | Filed. Concord's input ring; a theme override is a design-system decision (AIE-47 Implementation Decisions), not a shell one. |
| 2 | The delta strip truncates with an ellipsis at tablet width (the nine-count summary needs ~1180px; the column has ~920px at 1024). The full text is in the DOM, so screen readers get it, and it is in the `title`; a sighted keyboard user has no way to read the tail. | 1.4.10 Reflow (advisory) | 🟢 Minor | Filed. The design system asks for one line with an ellipsis; a wrap on narrow widths is the delta-strip ticket's call. |

### Operable

No issues. Tab order is date input → six step buttons → three rail tiles → page. Every control shows the theme's focus ring (solid 2px `primary-500`, 4.2:1 on the card in light; `primary-300`, 4.5:1 in dark; 2px offset). Step buttons disable with the native attribute at the dataset's edges. Targets: step buttons 47×31, date input 115×30, rail tiles 63×63 (all above WCAG 2.2's 24×24; the step buttons are under the 44×44 AAA advisory, as the AIE-50 critique noted).

### Understandable

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 3 | The content column opens with the shell's page title ("Orders") and then the page body's own heading ("Orders as of 2018-02-17"), a redundant heading one level down. | 2.4.6 Headings and labels | 🟢 Minor | Filed against the page tickets: AIE-52 (Orders) and AIE-54 (Funnel) fold the as-of day into a line under the title. Not a shell change. |

### Robust

| # | Issue | WCAG | Severity | Outcome |
|---|---|---|---|---|
| 4 | Skeleton renders `AppBar.Lead` and `AppBar.Trail` as `<nav>` elements, so a screen reader announced three navigation landmarks: one holding only the product name, one holding the clock controls, and the rail. | 1.3.1 Info and relationships, 4.1.2 | 🟡 Major | **Fixed**: both render as `div` via Skeleton's `element` prop; the rail is the page's one `nav`, labelled "Pages", and its active tile carries `aria-current="page"`. |

## Colour contrast

| Element | Light | Dark | Required | Pass |
|---|---|---|---|---|
| App title on card | 15.2:1 | 10.7:1 | 4.5:1 | ✅ |
| "Clock" label (`ink-muted`) on card | 7.1:1 | 6.0:1 | 4.5:1 | ✅ |
| Date input text | 15.2:1 | 15.2:1 | 4.5:1 | ✅ |
| Step button label on `preset-tonal` | 12.5:1 | 8.0:1 | 4.5:1 | ✅ |
| Rail tile, inactive (`ink-muted`) | 7.1:1 | 6.0:1 | 4.5:1 | ✅ |
| Rail tile, active (ink on `preset-tonal-brand`) | 11.1:1 | 8.6:1 | 4.5:1 | ✅ |
| Delta strip text on `preset-tonal-tertiary` | 6.2:1 | 6.2:1 | 4.5:1 | ✅ |
| Page title on page | 16.6:1 | 12.9:1 | 3:1 | ✅ |
| Focus ring on card | 4.2:1 | 4.5:1 | 3:1 | ✅ |
| Date input edge on card | 2.5:1 | 1.2:1 | 3:1 | ❌ finding 1 |
| Hairlines on card | 1.8:1 | 1.2:1 | decorative | n/a |

## Screen reader

| Element | Announced as |
|---|---|
| App bar | banner; "olist_agent" as text, not a heading (the page title is the h1) |
| Rail | navigation "Pages"; "Explorer, link", "Orders, link, current page", "Funnel, link" |
| Date input | "Clock, date field" with the native date parts |
| Step button | "−1W, button" with the description "Back one week" from its title |
| Delta strip | status region; read in full when it changes |
| "No data loaded yet." | status region, before the delta strip |
