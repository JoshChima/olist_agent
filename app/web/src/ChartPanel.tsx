import { cloneElement, type ReactElement } from "react";
import { ResponsiveContainer, Tooltip, type TooltipContentProps } from "recharts";
import { count } from "./format";
import { CARD, LINE, MUTED, SECTION_TITLE, SMALL } from "./tokens";

// The design system's chart tokens as Skeleton light-dark pairings (ADR-0011), read by Recharts
// through CSS: Recharts writes its colours as SVG attributes, which any stylesheet rule beats, so the
// panel below colours every grid line, axis, tick label and data-quality window inside it and a
// chart names only its series. A chart outside a panel keeps Recharts' defaults.
const pair = (light: string, dark: string) => `light-dark(var(--color-${light}),var(--color-${dark}))`;

/**
 * `series-1` to `series-4`, in order: indigo, blue, pink, grey. Pass as a Bar or Line `fill`/`stroke`.
 * Then `series-5` to `series-8`, the same four families' tints, for a chart with more series than four
 * (the Funnel's eight origins): further from the card, darker in light mode and lighter in dark, so no
 * two stack alike. Every one is at least 3:1 on `card` in both modes (AIE-55's accessibility review).
 */
export const SERIES = [
  pair("primary-500", "primary-400"),
  pair("tertiary-700", "tertiary-400"),
  pair("secondary-600", "secondary-300"),
  pair("surface-500", "surface-300"),
  pair("primary-800", "primary-200"),
  pair("tertiary-900", "tertiary-200"),
  pair("secondary-800", "secondary-100"),
  pair("surface-700", "surface-200"),
];

// Written out in full: Tailwind only emits a class it can read whole from the source, and only
// the single shades, not Skeleton's `--color-surface-200-700` pairing variables, reach the build.
const CHART = [
  // tick labels: `small` `ink-muted`
  "[&_.recharts-cartesian-axis-tick-value]:fill-[light-dark(var(--color-surface-600),var(--color-surface-200))]",
  "[&_.recharts-cartesian-axis-tick-value]:text-[13px]",
  // grid lines, axis lines, tick marks and the tooltip's hover band: `line`
  "[&_.recharts-cartesian-grid_line]:stroke-[light-dark(var(--color-surface-200),var(--color-surface-700))]",
  "[&_.recharts-cartesian-axis-line]:stroke-[light-dark(var(--color-surface-200),var(--color-surface-700))]",
  "[&_.recharts-cartesian-axis-tick-line]:stroke-[light-dark(var(--color-surface-200),var(--color-surface-700))]",
  "[&_.recharts-tooltip-cursor]:fill-[light-dark(var(--color-surface-200),var(--color-surface-700))]",
  "[&_.recharts-tooltip-cursor]:[fill-opacity:0.4]",
  // data-quality windows (dataQuality.tsx): `quality-shade`, the reason in `small` `ink-muted`
  "[&_.recharts-reference-area-rect]:fill-[light-dark(var(--color-surface-400),var(--color-surface-300))]",
  "[&_.recharts-reference-area-rect]:[fill-opacity:0.18]",
  "[&_.recharts-label]:fill-[light-dark(var(--color-surface-600),var(--color-surface-200))]",
  "[&_.recharts-label]:text-[13px]",
  // legend labels: `small` `ink-muted`; Recharts writes them in the series colour as an inline style,
  // which only an !important rule beats, and the swatch beside each still carries the colour
  "[&_.recharts-legend-item-text]:text-[light-dark(var(--color-surface-600),var(--color-surface-200))]!",
  "[&_.recharts-legend-item-text]:text-[13px]",
  // the chart surface takes keyboard focus (Recharts' accessibility layer): the `focus` ring
  "[&_.recharts-surface:focus-visible]:outline-2",
  "[&_.recharts-surface:focus-visible]:outline-offset-2",
  "[&_.recharts-surface:focus-visible]:outline-[light-dark(var(--color-primary-500),var(--color-primary-300))]",
].join(" ");

/**
 * A card with a section title and one Recharts chart (design system ChartPanel), full width of
 * its column. Panels stack `gap-6` apart; the Orders dashboard puts two in a `grid-cols-2` row.
 * The chart is named after the panel: Recharts passes `aria-label` to its focusable SVG surface, so a
 * screen reader names the chart it lands on (an SVG `title` would also pop a native hover tooltip).
 */
export function ChartPanel({ title, height, children }: { title: string; height: number; children: ReactElement<{ "aria-label"?: string }> }) {
  return (
    <section className={`${CARD} ${LINE} ${CHART} flex min-w-0 flex-col gap-2 rounded-container border p-4`}>
      <h2 className={SECTION_TITLE}>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>
        {cloneElement(children, { "aria-label": title })}
      </ResponsiveContainer>
    </section>
  );
}

function TooltipContent({ active, payload, label }: TooltipContentProps) {
  if (!active || payload.length === 0) return null;
  return (
    <div className={`${CARD} ${LINE} rounded-base border px-3 py-2 tabular-nums ${SMALL}`}>
      <div className={MUTED}>{label}</div>
      {payload.map((p) => (
        <div key={p.name}>
          {p.name}: {count(Number(p.value))}
        </div>
      ))}
    </div>
  );
}

/** Recharts' tooltip restyled onto the card ground: `line` edge, `small` text, counts formatted as everywhere else. */
export const chartTooltip = <Tooltip content={TooltipContent} />;
