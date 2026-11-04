import { Bar, BarChart, CartesianGrid, Legend, XAxis, YAxis } from "recharts";
import { ChartPanel, chartTooltip, SERIES } from "./ChartPanel";
import { FIRST_DAY } from "./clock";
import { dataQualityAreas } from "./dataQuality";
import { count } from "./format";
import { StatTile } from "./StatTile";
import { MUTED, SECTION_TITLE, SMALL } from "./tokens";
import { useJson } from "./useJson";

type Stage = { stage: string; count: number; conversion: number | null };
type Funnel = { stages: Stage[]; monthly_mqls: { month: string; origin: string; mqls: number }[] };

// GLOSSARY.md "Funnel stage".
const LABELS: Record<string, string> = {
  mql: "MQL",
  closed_deal: "Closed deal",
  active_seller: "Active seller",
};
// Color follows the origin, in a fixed order; the source's rarer origins fold into "other".
const ORIGINS = ["organic_search", "paid_search", "social", "unknown", "direct_traffic", "email", "referral", "other"];

/** Every month from the dataset's first day to the clock, so gaps and windows show. */
function months(clock: string): string[] {
  const out: string[] = [];
  for (let d = new Date(`${FIRST_DAY.slice(0, 7)}-01`); ; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const month = d.toISOString().slice(0, 7);
    if (month > clock.slice(0, 7)) return out;
    out.push(month);
  }
}

/**
 * MQL -> closed deal -> active seller at the clock, and MQLs a month by origin. The stages are stat
 * tiles joined by arrows carrying the conversion into each stage (design system FunnelStage); each
 * arrow sits in the list item of the stage it leads to, so the row wraps arrow and tile together. The items grow
 * to fill the row, as the Orders tiles do, which also keeps each tile at its 150px minimum.
 */
export function Funnel({ clock }: { clock: string }) {
  const { data, error } = useJson<Funnel>(`/api/funnel?clock=${clock}`);

  if (error) return <p role="alert">Couldn't load the funnel: {error}</p>;
  if (!data) return <p className={MUTED}>Loading…</p>;

  const axis = months(clock);
  const rows = axis.map((month) => {
    const row: Record<string, string | number> = { month };
    for (const o of ORIGINS) row[o] = 0;
    return row;
  });
  for (const { month, origin, mqls } of data.monthly_mqls) {
    const row = rows[axis.indexOf(month)];
    const key = ORIGINS.includes(origin) ? origin : "other";
    if (row) row[key] = (row[key] as number) + mqls;
  }
  const last = axis[axis.length - 1];

  return (
    <>
      <section className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className={SECTION_TITLE}>Funnel stages</h2>
          <p className={`${SMALL} ${MUTED}`}>as of {clock}</p>
        </div>
        <ol className="flex flex-wrap items-center gap-4">
          {data.stages.map((s) => (
            <li key={s.stage} className="flex flex-[1_1_auto] items-center gap-4">
              {s.stage !== "mql" && (
                <div className={`${SMALL} ${MUTED} flex flex-col items-center tabular-nums`}>
                  <span className="sr-only">Conversion from the previous stage:</span>
                  <span>{s.conversion === null ? "–" : `${(s.conversion * 100).toFixed(1)}%`}</span>
                  <span aria-hidden="true">→</span>
                </div>
              )}
              <StatTile label={LABELS[s.stage] ?? s.stage} value={count(s.count)} />
            </li>
          ))}
        </ol>
      </section>

      <ChartPanel title="MQLs a month, by origin" height={320}>
        <BarChart data={rows} margin={{ top: 20, right: 32 }}>
          <CartesianGrid vertical={false} />
          {dataQualityAreas(axis[0], last)}
          {/* Recharts thins the months by label width: the baselines' 18 months fit at 1280px with
              room to spare, so the platforms agree there, and a tablet's narrower plot drops some. */}
          <XAxis dataKey="month" />
          <YAxis allowDecimals={false} width={56} />
          {chartTooltip}
          <Legend iconType="square" iconSize={10} />
          {ORIGINS.map((o, i) => (
            <Bar key={o} dataKey={o} stackId="mqls" fill={SERIES[i]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ChartPanel>
      <p className={`${SMALL} ${MUTED}`}>
        Shaded months are data-quality windows: changes there are data artifacts, not business change.
      </p>
    </>
  );
}
