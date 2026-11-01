import { StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { useClock } from "./clock";
import { Explore } from "./Explore";
import { Orders } from "./Orders";
import { Funnel } from "./Funnel";
import { Shell } from "./Shell";
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
  const orders: [string, ReactNode] = ["Orders", <Orders clock={clock} />];
  const routes: Record<string, [string, ReactNode]> = {
    "/": orders,
    "/explore": ["Explorer", <Explore clock={clock} />],
    "/orders": orders,
    "/funnel": ["Funnel", <Funnel clock={clock} />],
  };
  const [title, page] = routes[location.pathname] ?? [];

  return (
    <Shell clock={clock} onClock={setClock} loaded={loaded} title={title}>
      {page}
    </Shell>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
