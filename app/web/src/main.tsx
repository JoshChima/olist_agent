import { StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { useClock } from "./clock";
import { Explore } from "./Explore";
import { Orders } from "./Orders";
import { Funnel } from "./Funnel";
import { activePath, Shell } from "./Shell";
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

  const pages: Record<string, ReactNode> = {
    "/explore": <Explore clock={clock} />,
    "/orders": <Orders clock={clock} />,
    "/funnel": <Funnel clock={clock} />,
  };

  return (
    <Shell clock={clock} onClock={setClock} loaded={loaded}>
      {pages[activePath()]}
    </Shell>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
