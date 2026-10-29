import { useEffect, useRef, useState } from "react";

// The API's count keys, in display order (GLOSSARY.md "Delta event").
const LABELS: Record<string, string> = {
  new_orders: "new orders",
  approved: "approved",
  shipped: "shipped",
  delivered: "delivered",
  canceled_or_unavailable: "canceled or unavailable",
  new_reviews: "new reviews",
  new_mqls: "new MQLs",
  deals_closed: "deals closed",
  new_active_sellers: "new active sellers",
};

/** After a forward time-warp, what happened in (previous clock, clock]. A rewind fetches nothing. */
export function DeltaStrip({ clock }: { clock: string }) {
  const prev = useRef(clock);
  const [text, setText] = useState<string | null>(null);

  useEffect(() => {
    const from = prev.current;
    if (clock === from) return;
    prev.current = clock;
    if (clock < from) {
      setText("rewound");
      return;
    }
    let current = true;
    setText(`${from} → ${clock}: loading…`);
    fetch(`/api/delta?from=${from}&to=${clock}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then((d: { counts: Record<string, number> }) => {
        const parts = Object.entries(LABELS).map(([k, label]) => `${d.counts[k].toLocaleString()} ${label}`);
        if (current) setText(`${from} → ${clock}: ${parts.join(", ")}`);
      })
      .catch((e: Error) => {
        if (current) setText(`${from} → ${clock}: couldn't load the delta event: ${e.message}`);
      });
    return () => {
      current = false;
    };
  }, [clock]);

  if (!text) return null;
  return (
    <p
      role="status"
      style={{ background: "#f3f6fc", border: "1px solid #d5def0", borderRadius: 6, padding: "0.5rem 0.75rem" }}
    >
      {text}
    </p>
  );
}
