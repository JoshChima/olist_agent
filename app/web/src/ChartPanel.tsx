import type { ReactNode } from "react";
import { ResponsiveContainer, Tooltip, type TooltipContentProps } from "recharts";
import { count } from "./format";
import { CARD, LINE, MUTED, SECTION_TITLE, SMALL } from "./tokens";

// The design system's chart tokens as Skeleton light-dark pairings (ADR-0011), read by Recharts
// through CSS: Recharts writes its colours as SVG attributes, which any stylesheet rule beats, so the
// panel below colours every grid line, axis, tick label and data-quality window inside it and a
// chart names only its series. A chart outside a panel keeps Recharts' defaults.
const pair = (light: string, dark: string) => `light-dark(var(--color-${light}),var(--color-${dark}))`;

/** `series-1` to `series-4`, in order: indigo, blue, pink, grey. Pass as a Bar or Line `fill`/`stroke`. */
export const SERIES = [
  pair("primary-500", "primary-400"),
  pair("tertiary-600", "tertiary-400"),
  pair("secondary-600", "secondary-300"),
  pair("surface-500", "surface-400"),
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
  "[&_.recharts-label]:fill-[light-dark(var(--color-surface-600),var(--color-surface-200))]",
  "[&_.recharts-label]:text-[13px]",
].join(" ");

/**
 * A card with a section title and one Recharts chart (design system ChartPanel), full width of
 * its column. Panels stack `gap-6` apart; the Orders dashboard puts two in a `grid-cols-2` row.
 */
export function ChartPanel({ title, height, children }: { title: string; height: number; children: ReactNode }) {
  return (
    <section className={`${CARD} ${LINE} ${CHART} flex min-w-0 flex-col gap-2 rounded-container border p-4`}>
      <h2 className={SECTION_TITLE}>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>
        {children}
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
