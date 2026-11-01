// PROTOTYPE (AIE-50). Throwaway code answering one question: what should the shell and the Orders
// dashboard look like on Concord? Three structurally different variants on the live Orders route,
// switchable via ?variant= (A|B|C) and the floating bar. Shell decisions fixed by the spec (AIE-47):
// AppBar with the product name and the clock controls, a left Navigation rail, the delta strip under
// the app bar. The variants differ in the content column, the stat tiles and the chart panels only.
import type { ReactNode } from "react";
import { AppBar, Navigation } from "@skeletonlabs/skeleton-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FIRST_DAY, LAST_DAY, step, type Step } from "../clock";
import { dataQualityAreas } from "../dataQuality";
import { DeltaStrip } from "../Delta";
import { useJson } from "../useJson";
import { PrototypeSwitcher, useVariant, type Variant } from "./PrototypeSwitcher";

// ---------- tokens as Skeleton classes (design system: page, card, line, ink-muted) ----------
// Concord's dark root is surface-900, so cards are surface-800: not a mirrored pairing, hence dark:.
const CARD = "card bg-surface-50 dark:bg-surface-800";
const LINE = "border-surface-200 dark:border-surface-700";
const MUTED = "text-surface-600 dark:text-surface-200";
const SMALL = "text-[13px] leading-[18px]";
// Recharts reads these as CSS variables; set per theme with Tailwind arbitrary properties.
const CHART_VARS =
  "[--ink-muted:var(--color-surface-600)] dark:[--ink-muted:var(--color-surface-200)] [--series-1:var(--color-primary-500)] dark:[--series-1:var(--color-primary-300)] [--series-2:var(--color-tertiary-500)] dark:[--series-2:var(--color-tertiary-300)]";

type Dashboard = {
  kpis: { orders: number; people: number; gmv: number; avg_review_score: number | null; late_pct: number | null };
  daily_orders: { day: string; orders: number }[];
  by_status: { status: string; orders: number }[];
  top_categories: { category: string | null; orders: number }[];
  by_state: { state: string | null; orders: number; people: number }[];
};

const none = "–";
const count = (n: number) => n.toLocaleString("en-US");
const brl = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "BRL" });
function kpiRows(k: Dashboard["kpis"]): [string, string][] {
  return [
    ["Orders", count(k.orders)],
    ["Customers (people)", count(k.people)],
    ["GMV", brl(k.gmv)],
    ["Avg review score", k.avg_review_score?.toFixed(2) ?? none],
    ["Delivered late", k.late_pct === null ? none : `${k.late_pct.toFixed(1)}%`],
  ];
}

// ---------- shell: fixed by the spec, shared by all variants ----------
const STEPS: [Step, string][] = [
  ["month", "M"],
  ["week", "W"],
  ["day", "D"],
];

function ClockControls({ clock, setClock }: { clock: string; setClock: (d: string) => void }) {
  const btn = (unit: Step, short: string, dir: -1 | 1) => (
    <button
      key={`${dir}${unit}`}
      className="btn btn-sm preset-tonal font-semibold"
      title={`${dir < 0 ? "Back" : "Forward"} one ${unit}`}
      disabled={dir < 0 ? clock <= FIRST_DAY : clock >= LAST_DAY}
      onClick={() => setClock(step(clock, unit, dir))}
    >
      {dir < 0 ? "−" : "+"}1{short}
    </button>
  );
  return (
    <div className={`flex items-center gap-2 ${SMALL}`}>
      <label htmlFor="clock" className={MUTED}>
        Clock
      </label>
      <input
        id="clock"
        type="date"
        className={`input w-auto px-2 py-1 ${SMALL}`}
        min={FIRST_DAY}
        max={LAST_DAY}
        value={clock}
        onChange={(e) => setClock(e.target.value)}
      />
      <div className="flex gap-1">{STEPS.map(([u, s]) => btn(u, s, -1))}</div>
      <div className="w-2" />
      <div className="flex gap-1">{[...STEPS].reverse().map(([u, s]) => btn(u, s, 1))}</div>
    </div>
  );
}

const PAGES = [
  ["Explorer", "/explore"],
  ["Orders", "/orders"],
  ["Funnel", "/funnel"],
] as const;

function Shell({
  clock,
  setClock,
  loaded,
  children,
}: {
  clock: string;
  setClock: (d: string) => void;
  loaded: boolean;
  children: ReactNode;
}) {
  const here = location.pathname === "/" ? "/orders" : location.pathname;
  return (
    <div className="grid h-screen grid-cols-[72px_1fr] grid-rows-[56px_1fr]">
      {/* Skeleton's base CSS makes the AppBar root a padded column and the Toolbar a grid; the rail 100px
          wide with 10px labels and centred tiles. The classes below are the overrides the design system asks for. */}
      <AppBar className={`col-span-2 h-14 justify-center gap-0 border-b px-4 py-0 ${CARD} ${LINE} rounded-none`}>
        <AppBar.Toolbar className="grid-cols-[auto_auto]">
          <AppBar.Lead>
            <span className="h3 text-[17px]">olist_agent</span>
          </AppBar.Lead>
          <AppBar.Trail>
            <ClockControls clock={clock} setClock={setClock} />
          </AppBar.Trail>
        </AppBar.Toolbar>
      </AppBar>
      <Navigation layout="rail" className={`w-[72px] gap-1 border-r p-1 ${CARD} ${LINE} rounded-none`}>
        <Navigation.Content>
          <Navigation.Menu className="justify-start gap-1">
            {PAGES.map(([label, path]) => (
              <Navigation.TriggerAnchor
                key={path}
                href={`${path}?clock=${clock}`}
                aria-current={path === here ? "page" : undefined}
                className={`justify-center font-semibold ${path === here ? "preset-tonal-primary" : MUTED}`}
              >
                <Navigation.TriggerText className={SMALL}>{label}</Navigation.TriggerText>
              </Navigation.TriggerAnchor>
            ))}
          </Navigation.Menu>
        </Navigation.Content>
      </Navigation>
      <div className="flex min-w-0 flex-col">
        <div className="px-4 pt-2 empty:hidden">
          {!loaded && <p role="status">No data loaded yet.</p>}
          <DeltaStrip clock={clock} />
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

// ---------- chart panels, shared drawing, variant-chosen sizes ----------
function Panel({ title, height, small, children }: { title: string; height: number; small?: boolean; children: ReactNode }) {
  return (
    <section className={`${CARD} ${CHART_VARS} flex min-w-0 flex-col gap-2 ${small ? "px-4 py-3" : "p-4"}`}>
      <h3 className={`h3 ${small ? "text-[15px]" : "text-[17px]"}`}>{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </section>
  );
}

const tick = { fontSize: 12, fill: "var(--ink-muted)" };
const grid = <CartesianGrid vertical={false} stroke="var(--color-surface-300-700)" />;
const tooltip = (
  <Tooltip
    cursor={{ fill: "var(--color-surface-300-700)", fillOpacity: 0.4 }}
    contentStyle={{
      background: "var(--color-surface-50-950)",
      border: "1px solid var(--color-surface-300-700)",
      borderRadius: "var(--radius-base)",
      fontSize: 13,
    }}
  />
);

function DailyChart({ d }: { d: Dashboard }) {
  const daily = d.daily_orders;
  return (
    <BarChart data={daily} margin={{ top: 20, right: 8 }}>
      {grid}
      {daily.length > 0 && dataQualityAreas(daily[0].day, daily[daily.length - 1].day)}
      <XAxis dataKey="day" minTickGap={24} tick={tick} tickLine={false} axisLine={{ stroke: "var(--color-surface-300-700)" }} />
      <YAxis allowDecimals={false} tick={tick} tickLine={false} axisLine={false} width={44} />
      {tooltip}
      <Bar isAnimationActive={false} dataKey="orders" name="Orders" fill="var(--series-1)" radius={[2, 2, 0, 0]} />
    </BarChart>
  );
}

function HBars({ rows, dataKey, labelWidth }: { rows: object[]; dataKey: string; labelWidth: number }) {
  return (
    <BarChart data={rows} layout="vertical" margin={{ right: 8 }}>
      <XAxis type="number" allowDecimals={false} tick={tick} tickLine={false} axisLine={false} />
      <YAxis type="category" dataKey={dataKey} width={labelWidth} tick={tick} tickLine={false} axisLine={false} />
      {tooltip}
      <Bar isAnimationActive={false} dataKey="orders" name="Orders" fill="var(--series-1)" radius={[0, 3, 3, 0]} />
    </BarChart>
  );
}

function StateChart({ d }: { d: Dashboard }) {
  return (
    <BarChart data={d.by_state.map((s) => ({ ...s, state: s.state ?? "(none)" }))} margin={{ top: 8, right: 8 }}>
      {grid}
      <XAxis dataKey="state" interval={0} tick={{ ...tick, fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--color-surface-300-700)" }} />
      <YAxis allowDecimals={false} tick={tick} tickLine={false} axisLine={false} width={44} />
      {tooltip}
      <Legend iconType="square" iconSize={10} wrapperStyle={{ fontSize: 12 }} />
      <Bar isAnimationActive={false} dataKey="orders" name="Orders" fill="var(--series-1)" radius={[2, 2, 0, 0]} />
      <Bar isAnimationActive={false} dataKey="people" name="People" fill="var(--series-2)" radius={[2, 2, 0, 0]} />
    </BarChart>
  );
}

const statusRows = (d: Dashboard) => d.by_status;
const categoryRows = (d: Dashboard) => d.top_categories.map((c) => ({ ...c, category: c.category ?? "(none)" }));

// ---------- Variant A: Ledger ----------
// Tiles in a row, then every chart panel full width, stacked; the page reads top to bottom (the spec's text).
function VariantA({ d, clock }: { d: Dashboard; clock: string }) {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-4 py-8">
      <div className="flex flex-col gap-1">
        <h1 className="h1 text-[28px]">Orders</h1>
        <p className={`${SMALL} ${MUTED}`}>as of {clock}</p>
      </div>
      <section className="flex flex-col gap-2">
        <h2 className="h3 text-[17px]">Last 30 days</h2>
        <div className="flex flex-wrap gap-4">
          {kpiRows(d.kpis).map(([label, value]) => (
            <div key={label} className={`${CARD} min-w-[150px] flex-1 p-4`}>
              <div className={`${SMALL} ${MUTED}`}>{label}</div>
              <div className="text-[26px] font-semibold leading-8 tabular-nums">{value}</div>
            </div>
          ))}
        </div>
      </section>
      <Panel title="Daily orders, last 90 days" height={280}>
        <DailyChart d={d} />
      </Panel>
      <Panel title="Orders by status" height={40 + 32 * d.by_status.length}>
        <HBars rows={statusRows(d)} dataKey="status" labelWidth={100} />
      </Panel>
      <Panel title="Top 10 categories by orders" height={40 + 28 * d.top_categories.length}>
        <HBars rows={categoryRows(d)} dataKey="category" labelWidth={180} />
      </Panel>
      <Panel title="Orders by customer state" height={280}>
        <StateChart d={d} />
      </Panel>
    </main>
  );
}

// ---------- Variant B: Hero chart ----------
// A stat column beside one large daily-orders panel; the three breakdowns share one row beneath.
function VariantB({ d, clock }: { d: Dashboard; clock: string }) {
  const rows = kpiRows(d.kpis);
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-4 px-4 py-6">
      <div className="flex items-baseline gap-3">
        <h1 className="h1 text-[28px]">Orders</h1>
        <p className={`${SMALL} ${MUTED}`}>as of {clock}</p>
      </div>
      <div className="grid grid-cols-[280px_minmax(0,1fr)] gap-4">
        <section className={`${CARD} flex flex-col p-4`}>
          <h2 className="h3 mb-2 text-[17px]">Last 30 days</h2>
          {rows.map(([label, value], i) => (
            <div
              key={label}
              className={`flex items-baseline justify-between gap-2 py-2.5 ${i < rows.length - 1 ? `border-b ${LINE}` : ""}`}
            >
              <span className={`${SMALL} ${MUTED}`}>{label}</span>
              <span className="text-[20px] font-semibold leading-6 tabular-nums">{value}</span>
            </div>
          ))}
        </section>
        <Panel title="Daily orders, last 90 days" height={360}>
          <DailyChart d={d} />
        </Panel>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Panel title="Orders by status" height={232}>
          <HBars rows={statusRows(d)} dataKey="status" labelWidth={86} />
        </Panel>
        <Panel title="Top 10 categories" height={232}>
          <HBars rows={categoryRows(d)} dataKey="category" labelWidth={150} />
        </Panel>
        <Panel title="Orders by customer state" height={232}>
          <StateChart d={d} />
        </Panel>
      </div>
    </main>
  );
}

// ---------- Variant C: Console grid ----------
// One stat bar across the top and four equal panels in a 2x2 grid; the whole page fits one screen.
function VariantC({ d, clock }: { d: Dashboard; clock: string }) {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-4 py-4">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="h1 text-[22px]">Orders</h1>
        <p className={`${SMALL} ${MUTED}`}>last 30 days, as of {clock}</p>
      </div>
      <section aria-label="Last 30 days" className={`${CARD} grid grid-cols-[repeat(5,auto)] divide-x px-4 ${LINE} divide-surface-200 dark:divide-surface-700`}>
        {kpiRows(d.kpis).map(([label, value]) => (
          <div key={label} className="px-4 py-3 first:pl-0 last:pr-0">
            <div className="text-[26px] font-semibold leading-8 tabular-nums">{value}</div>
            <div className={`${SMALL} ${MUTED}`}>{label}</div>
          </div>
        ))}
      </section>
      <div className="grid grid-cols-2 gap-3">
        <Panel small title="Daily orders, last 90 days" height={260}>
          <DailyChart d={d} />
        </Panel>
        <Panel small title="Orders by status" height={260}>
          <HBars rows={statusRows(d)} dataKey="status" labelWidth={100} />
        </Panel>
        <Panel small title="Top 10 categories by orders" height={260}>
          <HBars rows={categoryRows(d)} dataKey="category" labelWidth={170} />
        </Panel>
        <Panel small title="Orders by customer state" height={260}>
          <StateChart d={d} />
        </Panel>
      </div>
    </main>
  );
}

const VARIANTS: Variant[] = [
  { key: "A", name: "Ledger", description: "stat tiles in a row, then every chart panel full width, stacked" },
  { key: "B", name: "Hero chart", description: "a stat column beside a large daily-orders panel, three breakdowns in one row beneath" },
  { key: "C", name: "Console grid", description: "one stat bar across the top and four equal panels in a 2×2 grid, no scrolling" },
];
const RENDER: Record<string, typeof VariantA> = { A: VariantA, B: VariantB, C: VariantC };

/** The Orders route with the prototype shell and the variant from ?variant=. Data fetching stays above the switch. */
export function ShellOrdersPrototype({ clock, setClock, loaded }: { clock: string; setClock: (d: string) => void; loaded: boolean }) {
  const [variant, setVariant] = useVariant(VARIANTS);
  const { data, error } = useJson<Dashboard>(`/api/orders?clock=${clock}`);
  const Page = RENDER[variant.key];
  return (
    <Shell clock={clock} setClock={setClock} loaded={loaded}>
      {error ? (
        <p role="alert" className="px-4 py-8 text-error-700 dark:text-error-300">
          Couldn't load the order dashboard: {error}
        </p>
      ) : !data ? (
        <p className={`px-4 py-8 ${MUTED}`}>Loading…</p>
      ) : (
        <Page d={data} clock={clock} />
      )}
      <PrototypeSwitcher variants={VARIANTS} current={variant} onChange={setVariant} />
    </Shell>
  );
}
