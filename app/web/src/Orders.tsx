import { Bar, BarChart, CartesianGrid, Legend, XAxis, YAxis } from "recharts";
import { ChartPanel, chartTooltip, SERIES } from "./ChartPanel";
import { dataQualityAreas } from "./dataQuality";
import { count, currency } from "./format";
import { StatTile } from "./StatTile";
import { MUTED, SECTION_TITLE, SMALL } from "./tokens";
import { useJson } from "./useJson";

type Dashboard = {
  kpis: {
    orders: number;
    people: number;
    gmv: number;
    avg_review_score: number | null;
    late_pct: number | null;
  };
  daily_orders: { day: string; orders: number }[];
  by_status: { status: string; orders: number }[];
  top_categories: { category: string | null; orders: number }[];
  by_state: { state: string | null; orders: number; people: number }[];
};

const none = "–";

// Every 14th day counted back from the clock, so the axis ends on the clock's day. Recharts' own
// thinning picks ticks by measured label width, which differs by a pixel between the platforms the
// screenshot baselines compare across (docs/agents/web-tests.md) and so picked different days.
const fortnightly = (days: { day: string }[]) => days.filter((_, i) => (days.length - 1 - i) % 14 === 0).map((d) => d.day);

/**
 * The business as it looked on the clock's day: 30-day KPIs as a row of stat tiles, then one chart
 * panel per chart. The layout AIE-50 chose: the daily orders first and full width, status and
 * categories side by side, the customer states full width (27 of them). The shell renders the page
 * title; the page states its "as of" day once, on the stat row's heading line.
 */
export function Orders({ clock }: { clock: string }) {
  const { data, error } = useJson<Dashboard>(`/api/orders?clock=${clock}`);

  if (error) return <p role="alert">Couldn't load the order dashboard: {error}</p>;
  if (!data) return <p className={MUTED}>Loading…</p>;
  const { kpis, daily_orders: daily } = data;

  return (
    <>
      <section className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className={SECTION_TITLE}>Last 30 days</h2>
          <p className={`${SMALL} ${MUTED}`}>as of {clock}</p>
        </div>
        <div className="flex flex-wrap gap-4">
          <StatTile label="Orders" value={count(kpis.orders)} />
          <StatTile label="Customers (people)" value={count(kpis.people)} />
          <StatTile label="GMV" value={currency(kpis.gmv)} />
          <StatTile label="Avg review score" value={kpis.avg_review_score?.toFixed(2) ?? none} />
          <StatTile label="Delivered late" value={kpis.late_pct === null ? none : `${kpis.late_pct.toFixed(1)}%`} />
        </div>
      </section>

      <ChartPanel title="Daily orders, last 90 days" height={360}>
        <BarChart data={daily} margin={{ top: 20, right: 32 }}>
          <CartesianGrid vertical={false} />
          {daily.length > 0 && dataQualityAreas(daily[0].day, daily[daily.length - 1].day)}
          <XAxis dataKey="day" ticks={fortnightly(daily)} interval={0} />
          <YAxis allowDecimals={false} width={56} />
          {chartTooltip}
          <Bar dataKey="orders" name="Orders" fill={SERIES[0]} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ChartPanel>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartPanel title="Orders by status" height={300}>
          <BarChart data={data.by_status} layout="vertical" margin={{ right: 32 }}>
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="status" width={100} />
            {chartTooltip}
            <Bar dataKey="orders" name="Orders" fill={SERIES[0]} radius={[0, 3, 3, 0]} isAnimationActive={false} />
          </BarChart>
        </ChartPanel>

        <ChartPanel title="Top 10 categories by orders" height={300}>
          <BarChart data={data.top_categories.map((c) => ({ ...c, category: c.category ?? "(none)" }))} layout="vertical" margin={{ right: 32 }}>
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="category" width={180} />
            {chartTooltip}
            <Bar dataKey="orders" name="Orders" fill={SERIES[0]} radius={[0, 3, 3, 0]} isAnimationActive={false} />
          </BarChart>
        </ChartPanel>
      </div>

      <ChartPanel title="Orders by customer state" height={280}>
        <BarChart data={data.by_state.map((s) => ({ ...s, state: s.state ?? "(none)" }))} margin={{ top: 8, right: 32 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="state" interval={0} />
          <YAxis allowDecimals={false} width={56} />
          {chartTooltip}
          <Legend iconType="square" iconSize={10} />
          <Bar dataKey="orders" name="Orders" fill={SERIES[0]} radius={[2, 2, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="people" name="People" fill={SERIES[1]} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ChartPanel>
    </>
  );
}
