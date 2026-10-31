import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FIRST_DAY } from "./clock";
import { dataQualityAreas } from "./dataQuality";
import { useJson } from "./useJson";

type Stage = { stage: string; count: number; conversion: number | null };
type Funnel = { stages: Stage[]; monthly_mqls: { month: string; origin: string; mqls: number }[] };

const LABELS: Record<string, string> = {
  mql: "MQLs",
  closed_deal: "Closed deals",
  active_seller: "Active sellers",
};
// Color follows the origin, in a fixed order; the source's rarer origins fold into "other".
const ORIGINS = ["organic_search", "paid_search", "social", "unknown", "direct_traffic", "email", "referral", "other"];
const COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];

/** Every month from the dataset's first day to the clock, so gaps and windows show. */
function months(clock: string): string[] {
  const out: string[] = [];
  for (let d = new Date(`${FIRST_DAY.slice(0, 7)}-01`); ; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const month = d.toISOString().slice(0, 7);
    if (month > clock.slice(0, 7)) return out;
    out.push(month);
  }
}

/** MQL -> closed deal -> active seller at the clock, and MQLs a month by origin. */
export function Funnel({ clock }: { clock: string }) {
  const { data, error } = useJson<Funnel>(`/api/funnel?clock=${clock}`);

  if (error) return <p role="alert">Couldn't load the funnel: {error}</p>;
  if (!data) return <p>Loading…</p>;

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
    <section>
      <h2 className="h2">Funnel as of {clock}</h2>
      <ol style={{ display: "flex", flexWrap: "wrap", gap: "1rem", listStyle: "none", padding: 0, alignItems: "center" }}>
        {data.stages.map((s) => (
          <li key={s.stage} style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            {s.stage !== "mql" && (
              <span>→ {s.conversion === null ? "–" : `${(s.conversion * 100).toFixed(1)}%`} →</span>
            )}
            <div style={{ border: "1px solid #ddd", borderRadius: 4, padding: "0.5rem 1rem" }}>
              <div style={{ fontSize: 13, color: "#555" }}>{LABELS[s.stage] ?? s.stage}</div>
              <strong style={{ fontSize: 24 }}>{s.count.toLocaleString()}</strong>
            </div>
          </li>
        ))}
      </ol>
      <h3 className="h3">MQLs a month, by origin</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={rows}>
          <CartesianGrid vertical={false} stroke="#eee" />
          {dataQualityAreas(axis[0], last)}
          <XAxis dataKey="month" fontSize={12} />
          <YAxis allowDecimals={false} fontSize={12} />
          <Tooltip />
          <Legend />
          {ORIGINS.map((o, i) => (
            <Bar key={o} dataKey={o} stackId="mqls" fill={COLORS[i]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <p style={{ fontSize: 13, color: "#555" }}>
        Shaded months are data-quality windows: changes there are data artifacts, not business change.
      </p>
    </section>
  );
}
