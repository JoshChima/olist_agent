import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dataQualityAreas } from "./dataQuality";
import { count, currency } from "./format";
import { MUTED } from "./tokens";
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

const BAR = "#3b6fd4";
const none = "–";

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: "0.75rem 1rem", minWidth: 150 }}>
      <div style={{ fontSize: 13, color: "#555" }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function Panel({ title, height, children }: { title: string; height: number; children: ReactNode }) {
  return (
    <section style={{ marginTop: "1.5rem" }}>
      <h3 className="h3" style={{ margin: "0 0 0.5rem" }}>{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </section>
  );
}

/** The business as it looked on the clock's day: 30-day KPIs and the orders behind them. */
export function Orders({ clock }: { clock: string }) {
  const { data, error } = useJson<Dashboard>(`/api/orders?clock=${clock}`);

  if (error) return <p role="alert">Couldn't load the order dashboard: {error}</p>;
  if (!data) return <p className={MUTED}>Loading…</p>;
  const { kpis, daily_orders: daily } = data;

  return (
    <section>
      <h2 className="h2">Orders as of {clock}</h2>
      <h3 className="h3" style={{ margin: "0 0 0.5rem" }}>Last 30 days</h3>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <Kpi label="Orders" value={count(kpis.orders)} />
        <Kpi label="Customers (people)" value={count(kpis.people)} />
        <Kpi label="GMV" value={currency(kpis.gmv)} />
        <Kpi label="Avg review score" value={kpis.avg_review_score?.toFixed(2) ?? none} />
        <Kpi label="Delivered late" value={kpis.late_pct === null ? none : `${kpis.late_pct.toFixed(1)}%`} />
      </div>

      <Panel title="Daily orders, last 90 days" height={280}>
        <BarChart data={daily} margin={{ top: 20 }}>
          <CartesianGrid vertical={false} stroke="#eee" />
          {daily.length > 0 && dataQualityAreas(daily[0].day, daily[daily.length - 1].day)}
          <XAxis dataKey="day" minTickGap={24} fontSize={12} />
          <YAxis allowDecimals={false} fontSize={12} />
          <Tooltip />
          <Bar dataKey="orders" name="Orders" fill={BAR} radius={[2, 2, 0, 0]} />
        </BarChart>
      </Panel>

      <Panel title="Orders by status" height={40 + 32 * data.by_status.length}>
        <BarChart data={data.by_status} layout="vertical">
          <XAxis type="number" allowDecimals={false} fontSize={12} />
          <YAxis type="category" dataKey="status" width={100} fontSize={12} />
          <Tooltip />
          <Bar dataKey="orders" name="Orders" fill={BAR} radius={[0, 4, 4, 0]} />
        </BarChart>
      </Panel>

      <Panel title="Top 10 categories by orders" height={40 + 28 * data.top_categories.length}>
        <BarChart data={data.top_categories.map((c) => ({ ...c, category: c.category ?? "(none)" }))} layout="vertical">
          <XAxis type="number" allowDecimals={false} fontSize={12} />
          <YAxis type="category" dataKey="category" width={180} fontSize={12} />
          <Tooltip />
          <Bar dataKey="orders" name="Orders" fill={BAR} radius={[0, 4, 4, 0]} />
        </BarChart>
      </Panel>

      <Panel title="Orders by customer state" height={280}>
        <BarChart data={data.by_state.map((s) => ({ ...s, state: s.state ?? "(none)" }))}>
          <CartesianGrid vertical={false} stroke="#eee" />
          <XAxis dataKey="state" interval={0} fontSize={11} />
          <YAxis allowDecimals={false} fontSize={12} />
          <Tooltip />
          <Bar dataKey="orders" name="Orders" fill={BAR} radius={[2, 2, 0, 0]} />
          <Legend />
          <Bar dataKey="people" name="People" fill="#9bb5e8" radius={[2, 2, 0, 0]} />
        </BarChart>
      </Panel>
    </section>
  );
}
