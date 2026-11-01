# AIE-50: design critique of the three shell and Orders dashboard variants

Prototype on the `prototype/shell-orders` branch (never merged). Run `docker compose up` and `pnpm dev` in `app/web`, then open `/orders?clock=2017-11-24&variant=A` (or `B`, `C`); the floating bar and the ← → keys switch variants. Captures here are 1280×1000, clock 2017-11-24 (the day of the Black Friday spike), light and dark, taken with the project's Playwright MCP server.

Mockups: Claude Design canvas "Shell and Orders variants" (https://claude.ai/artifact/8GCYV5A8CctXYCXAQDrXpo), three artboards built from the design system artifact linked on AIE-47.

| Variant | One line |
|---|---|
| **A · Ledger** | Stat tiles in a row, then every chart panel full width, stacked; the page reads top to bottom (the spec's text as written). |
| **B · Hero chart** | A stat column beside one large daily-orders panel; the three breakdowns share one row beneath. |
| **C · Console grid** | One stat bar across the top and four equal panels in a 2×2 grid; the whole page fits one screen. |

All three share the fixed shell: Skeleton `AppBar` (product name left, clock controls right), `Navigation layout="rail"` down the left with the active tile tonal brand, the delta strip under the app bar, the content column scrolling under a fixed bar and rail.

## Critique (design:design-critique)

### Overall impression

A is the safest and the dullest: a report, not a console. B is the only one with a point of view, and the hero chart is right for a time-travel console, but its bottom row starves the breakdowns. C is the one an analyst would keep open: everything on one screen, numerals in one scan line, every chart wide enough to read. C wins, with B's hero chart borrowed.

### Usability

| Finding | Variant | Severity | Recommendation |
|---|---|---|---|
| The page scrolls ~1700px at 1280×1000; the state chart is two screens below the stat tiles, so comparing a tile with a breakdown means scrolling back and forth. | A | 🟡 Moderate | Put more than one panel in a row (C). |
| Full-width horizontal bar charts with 6–10 rows: 1136px of width carries no information for a 6-bar status chart. | A | 🟡 Moderate | Half-width panels for the categorical charts (C). |
| Three breakdowns in one row at 349px each: the customer-state chart's 27 tick labels collide into one unreadable string, and Recharts drops half the category labels. | B | 🔴 Critical | Never put the state chart in a third of the column; it needs ≥500px. |
| The stat column stretches to the hero panel's height and leaves ~160px of empty card below the five rows. | B | 🟢 Minor | `self-start`, or move the as-of line into the card. |
| Daily orders at half width: 90 bars at ~5px each. The spike reads; a quiet week does not. | C | 🟡 Moderate | Give the daily chart the full column width (borrow B's hero). |
| Everything fits in 1000px with 170px to spare; no scrolling to reach any figure. | C | ✅ | Keep. |
| The native date input shows the locale's format (11/24/2017) while every other date on the page is ISO. | all | 🟢 Minor | Inherent to the native input the spec requires; accept, or show the ISO day in the as-of line (all three do). |

### Visual hierarchy

- **What draws the eye first**: A: the tile row, then the spike. B: the spike, immediately; the stat column reads second. C: the stat bar's numeral line, then the spike. B and C are both correct for "numbers first"; A's tiles are big boxes around small numbers.
- **Reading flow**: A: strictly down. B: left column, then the hero, then a weak bottom row. C: Z-pattern across the stat bar, then the four panels in reading order (daily, status, categories, state).
- **Emphasis**: B over-weights the hero against three cramped panels. C is even: four panels of equal weight, which fits a dashboard where no breakdown is primary, but under-weights the time series. The spec's clock is the primary affordance, so the daily chart deserves the top row (B's lesson applied to C).
- **Page title**: A's 28px title with the as-of beneath takes 70px for two words. C's 22px title with the as-of right-aligned on the same line costs 28px and reads fine; B's inline as-of beside a 28px title is the compromise.

### Consistency with the design system

| Element | Issue | Recommendation |
|---|---|---|
| Stat tile | C puts the number over the label; the StatTile card says label over number. Number-first makes a stronger scan line in a single bar, but it is a second tile style. | Keep C's one-card, five-cell bar; restore label over number (A) so the Funnel stages and later pages share one tile. |
| Card ground | The design system's StatTile card names `preset-filled-surface-50-800`, which Skeleton does not ship (only mirrored pairings exist: 50-950, 100-900, 200-800 …). | Use `bg-surface-50 dark:bg-surface-800` as the prototype does; fix the card's text when the artifact is regenerated. |
| Rail active tile | `preset-tonal-primary` is primary-50 on primary-950: a pale wash in light, a saturated fill in dark. The design system's `brand-tonal` is brand at 20% in both modes. | `bg-primary-500/20 text-surface-950-50` in the shell ticket, so both modes match the mockups. |
| Currency | `R$1,012,022.46` has no space after the symbol; the design system's sample is `R$ 1,203,118.44`. | Format as `"R$ " + n.toLocaleString("en-US", {minimumFractionDigits: 2})`. |
| Delta strip | Wraps to two lines at 1280 with the nine-count summary; the card says one line with an ellipsis. | `truncate` on the strip (delta-strip ticket). |
| Chart colours | Series, grid and ticks read from CSS variables set with Tailwind arbitrary properties (`[--series-1:var(--color-primary-500)]`), which works in both modes without hex literals. | Carry into the Orders dashboard ticket; the data-quality shading still uses the old hex greys. |

### Accessibility

- **Colour contrast**: ink on card and page passes in both modes; muted labels use surface-600 (light) and surface-200 (dark) on the card, both above 4.5:1. Chart tick text at 12px in the muted colour is at the floor; the state chart's 11px ticks are below it in B.
- **Targets**: step buttons are 28px tall (Skeleton `btn-sm`), rail tiles 63px; the date input 28px. Fine for desktop and tablet with a pointer; the step buttons are the smallest control on the page.
- **Semantics**: the active rail tile carries `aria-current="page"`; the delta strip is `role="status"`; C's stat bar is a labelled `section`. Keyboard focus shows Skeleton's ring on every control. The charts are SVG with no text alternative beyond the tooltip, which the milestone's accessibility review will have to take up.

### What works well

- The shell holds across all three: fixed app bar and rail, one hairline each, no shadows; Concord's light and dark both look deliberate.
- C's stat bar: five numerals in one tabular line, divided by hairlines, is the densest and quietest way to show the 30-day figures.
- B's hero: the Black Friday spike is unmistakable at 848px wide and 360px tall.
- Recharts coloured from theme variables needs no per-mode props.

### Priority recommendations

1. **Build C, with the daily chart spanning the content column as the first panel** (from B). The three categorical charts follow: status and categories share a row at half width; the customer-state chart gets a full-width row because of its 27 categories. Target: one screen at 1280×1000 with at most a short scroll.
2. **Keep the stat bar as one card, label over number** (from A and the design system), 26px tabular numerals, hairline dividers; the as-of day right-aligned on the title line (C).
3. **Fix the shell details before the Funnel and Explorer follow**: brand-tonal at 20% for the active tile in both modes, the delta strip truncating, the rail at 72px with 13px labels over Skeleton's 100px/10px defaults.

## Verdict

**C · Console grid**, borrowing B's hero daily chart (full-width top panel) and A's label-over-number tile order. Nothing from the prototype merges to main; AIE-51 builds the shell and AIE-52 the Orders dashboard from this verdict.

## Notes for the shell ticket (AIE-51), found while building

- Skeleton's base CSS (`@skeletonlabs/skeleton-common`) styles the components: `AppBar` root is a padded flex column and `AppBar.Toolbar` a grid; `Navigation` rail is 100px wide with centred tiles and 10px labels. The prototype's overrides are in `app/web/src/prototype/ShellOrdersPrototype.tsx`.
- After installing `@skeletonlabs/skeleton-react`, a stale Vite pre-bundle produced "Invalid hook call … reading 'use'" from `AppBarRoot` until `node_modules/.vite` was removed (or `vite --force`). It is a dev-server artifact, not a bug in the code.
- Recharts' entry animation leaves bars at zero height in screenshots taken within ~1.5s of render; the prototype sets `isAnimationActive={false}`. The Playwright screenshot run (AIE-49) will need the same.
