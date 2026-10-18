import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

function App() {
  const [message, setMessage] = useState("…");
  useEffect(() => {
    fetch("/api/hello")
      .then((r) => r.json())
      .then((d: { message: string }) => setMessage(d.message))
      .catch(() => setMessage("API unreachable"));
  }, []);
  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "4rem auto", padding: "0 1rem" }}>
      <h1>olist_agent</h1>
      <p>{message}</p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
