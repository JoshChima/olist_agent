import { StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { FIRST_DAY, LAST_DAY, useClock } from "./clock";
import { Explore } from "./Explore";
import { Orders } from "./Orders";

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
  };
  const page = routes[location.pathname] ?? null;

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 1100, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>olist_agent</h1>
      <nav style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <a href={`/explore?clock=${clock}`}>Explorer</a>
        <a href={`/orders?clock=${clock}`}>Orders</a>
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
      </nav>
      {!loaded && <p role="status">No data loaded yet.</p>}
      {page}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
