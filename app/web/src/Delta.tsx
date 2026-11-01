import { useEffect, useRef, useState } from "react";
import { count } from "./format";
import { STATUS } from "./tokens";
import { useJson } from "./useJson";

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

/**
 * After a forward time-warp from day `from` to day `to`, the delta event for the clock window
 * [from+1 00:00, to+1 00:00). A rewind fetches nothing.
 */
export function DeltaStrip({ clock }: { clock: string }) {
  const prev = useRef(clock);
  const [warp, setWarp] = useState<{ from: string; to: string } | null>(null);

  useEffect(() => {
    if (clock === prev.current) return;
    setWarp({ from: prev.current, to: clock });
    prev.current = clock;
  }, [clock]);

  const url = warp && warp.to > warp.from ? `/api/delta?from=${warp.from}&to=${warp.to}` : null;
  const { data, error, loading } = useJson<{ counts: Record<string, number> }>(url);

  if (!warp) return null;
  const at = `${warp.from} → ${warp.to}`;
  const text = !url
    ? "rewound"
    : loading
      ? `${at}: loading…`
      : error
        ? `${at}: couldn't load the delta event: ${error}`
        : `${at}: ${Object.entries(LABELS)
            .map(([k, label]) => `${count(data!.counts[k])} ${label}`)
            .join(", ")}`;
  return (
    <p role="status" className={STATUS} title={text}>
      {text}
    </p>
  );
}
