import { StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { FIRST_DAY, LAST_DAY, step, useClock, type Step } from "./clock";
import { DeltaStrip } from "./Delta";
import { Explore } from "./Explore";
import { Orders } from "./Orders";
import { Funnel } from "./Funnel";

const STEPS: [Step, string][] = [
  ["month", "M"],
  ["week", "W"],
  ["day", "D"],
];

function App() {
  const [clock, setClock] = useClock();
  const [loaded, setLoaded] = useState(true);
  useEffect(() => {
    fetch("/api/data-status")
      .then((r) => r.json())
      .then((d: { loaded: boolean }) => setLoaded(d.loaded))
      .catch(() => setLoaded(false));
  }, []);

  // A pathname switch is all the routing needed (no router library).
  const routes: Record<string, ReactNode> = {
    "/explore": <Explore clock={clock} />,
    "/orders": <Orders clock={clock} />,
    "/funnel": <Funnel clock={clock} />,
  };
  const page = routes[location.pathname] ?? null;

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 1100, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>olist_agent</h1>
      <nav style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <a href={`/explore?clock=${clock}`}>Explorer</a>
        <a href={`/orders?clock=${clock}`}>Orders</a>
        <a href={`/funnel?clock=${clock}`}>Funnel</a>
        <label>
          Clock{" "}
          <input
            type="date"
            min={FIRST_DAY}
            max={LAST_DAY}
            value={clock}
            onChange={(e) => setClock(e.target.value)}
          />
        </label>
        <span style={{ display: "flex", gap: "0.25rem" }}>
          {STEPS.map(([unit, short]) => (
            <button
              key={unit}
              title={`Back one ${unit}`}
              disabled={clock <= FIRST_DAY}
              onClick={() => setClock(step(clock, unit, -1))}
            >
              −1{short}
            </button>
          ))}
          {[...STEPS].reverse().map(([unit, short]) => (
            <button
              key={unit}
              title={`Forward one ${unit}`}
              disabled={clock >= LAST_DAY}
              onClick={() => setClock(step(clock, unit, 1))}
            >
              +1{short}
            </button>
          ))}
        </span>
      </nav>
      {!loaded && <p role="status">No data loaded yet.</p>}
      <DeltaStrip clock={clock} />
      {page}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
