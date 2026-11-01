import { StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { useClock } from "./clock";
import { ClockControls } from "./ClockControls";
import { DeltaStrip } from "./Delta";
import { Explore } from "./Explore";
import { Orders } from "./Orders";
import { Funnel } from "./Funnel";
import "./app.css";

function App() {
  const [clock, setClock] = useClock();
  const [loaded, setLoaded] = useState(true);
  useEffect(() => {
    fetch("/api/data-status")
      .then((r) => r.json())
      .then((d: { loaded: boolean }) => setLoaded(d.loaded))
      .catch(() => setLoaded(false));
  }, []);

  // A pathname switch is all the routing needed (no router library). / is the order dashboard.
  const orders = <Orders clock={clock} />;
  const routes: Record<string, ReactNode> = {
    "/": orders,
    "/explore": <Explore clock={clock} />,
    "/orders": orders,
    "/funnel": <Funnel clock={clock} />,
  };
  const page = routes[location.pathname] ?? null;

  return (
    <main style={{ maxWidth: 1100, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 className="h1">olist_agent</h1>
      <nav style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <a className="anchor" href={`/explore?clock=${clock}`}>Explorer</a>
        <a className="anchor" href={`/orders?clock=${clock}`}>Orders</a>
        <a className="anchor" href={`/funnel?clock=${clock}`}>Funnel</a>
        <ClockControls clock={clock} onChange={setClock} />
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
