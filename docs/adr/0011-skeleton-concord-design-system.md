# 11. Skeleton v5 with the Concord theme is the design system

Date: 2026-10-31 · Status: Accepted

## Context
P0 and P1 shipped the web app with inline styles, no stylesheet and no component library. The next milestone reworks the UI and uses Claude Design for mockups, which works from a design system: tokens, components and guidelines that agents read. Every later phase adds a data-dense surface (chat over SQL, a product page, a findings feed, a model comparison), so the look is an analyst console.

## Decision
- Tailwind v4 with Skeleton v5 (`@skeletonlabs/skeleton` and `@skeletonlabs/skeleton-react`) and Skeleton's preset theme **Concord**, used verbatim. Theme overrides, if any, live in one block of the global stylesheet and are chosen only after seeing Concord on real pages.
- The repo's global stylesheet (Skeleton import, Concord import, override block) is the source of truth. The Design System artifact that Claude Design reads is generated from it and regenerated when the override block changes; it is never edited by hand.
- A Skeleton React component is used wherever one exists. Tables are native HTML with Skeleton's table classes. Charts stay on Recharts, coloured from Skeleton's CSS variables. Anything Skeleton lacks is built from Tailwind utilities and Skeleton presets. No second component library.
- Both light and dark mode ship, following the operating system; no in-app toggle.
- Desktop and tablet widths only. Routing stays the pathname switch, and the clock stays in the URL (ADR-0009).

Alternatives: shadcn/ui copies component source into the repo and is what most agents emit by default, but it ships no theme, so the tokens would have to be designed from nothing. Plain CSS with custom properties is smallest but every component is hand-built. Boxed libraries (MUI, Mantine) bring a look that fights any custom theme and that agents translate into badly.

## Consequences
- Claude Design prompts and tickets use Skeleton's vocabulary: colour families (primary, secondary, tertiary, success, warning, error, surface), light-dark pairings such as `bg-surface-200-800`, preset classes and Skeleton component names.
- Skeleton has no data grid or chart component, so the Explorer keeps its own column sort and Recharts stays.
- Swapping the theme later is one import and one attribute; swapping Skeleton itself means rewriting every component.
