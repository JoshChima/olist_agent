import { CARD, LINE, MUTED, SMALL } from "./tokens";

/**
 * One figure as of the clock (design system StatTile): a `small` `ink-muted` label over a `stat-value`
 * number, on `card` with the container radius. Tiles sit in a `flex flex-wrap gap-4` row, grow to fill
 * it and wrap below 150px. The consumer formats the value (`count`, `currency`).
 */
export function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className={`${CARD} ${LINE} flex-[1_1_150px] rounded-container border p-4`}>
      <div className={`${SMALL} ${MUTED}`}>{label}</div>
      <div className="text-[26px] leading-8 font-semibold tabular-nums">{value}</div>
    </div>
  );
}
