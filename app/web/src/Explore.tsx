import { useEffect, useState } from "react";

type Page = { columns: string[]; rows: unknown[][]; total: number; page: number; page_size: number };
type Sort = { column?: string; desc: boolean };

/** A sim view at the clock: 50 rows a page, sortable columns, total row count. */
export function Explore({ clock }: { clock: string }) {
  const [views, setViews] = useState<string[]>([]);
  const [view, setView] = useState("orders");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<Sort>({ desc: false });
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/explore")
      .then((r) => r.json())
      .then((d: { views: string[] }) => setViews(d.views))
      .catch(() => setViews([]));
  }, []);

  useEffect(() => setPage(1), [clock]); // a rewind can leave fewer pages than before

  const pick = (v: string) => {
    setView(v);
    setPage(1);
    setSort({ desc: false });
    setData(null);
    setError(null);
  };

  useEffect(() => {
    const q = new URLSearchParams({ clock, page: String(page), desc: String(sort.desc) });
    if (sort.column) q.set("sort", sort.column);
    let current = true;
    fetch(`/api/explore/${encodeURIComponent(view)}?${q}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then((d: Page) => {
        if (current) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [view, clock, page, sort]);

  const picker = (
    <label>
      View{" "}
      <select value={view} onChange={(e) => pick(e.target.value)}>
        {(views.length ? views : [view]).map((v) => (
          <option key={v}>{v}</option>
        ))}
      </select>
    </label>
  );
  if (error)
    return (
      <section>
        {picker}
        <p role="alert">
          Couldn't load {view}: {error}
        </p>
      </section>
    );
  if (!data)
    return (
      <section>
        {picker}
        <p>Loading…</p>
      </section>
    );
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const sortBy = (column: string) =>
    setSort((s) => ({ column, desc: s.column === column ? !s.desc : false }));

  return (
    <section>
      {picker}
      <p>
        <strong>{data.total.toLocaleString()}</strong> rows as of {clock}
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              {data.columns.map((c) => (
                <th key={c} style={{ textAlign: "left", padding: "4px 8px" }}>
                  <button onClick={() => sortBy(c)} style={{ all: "unset", cursor: "pointer" }}>
                    {c} {sort.column === c ? (sort.desc ? "▼" : "▲") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} style={{ borderTop: "1px solid #ddd" }}>
                {row.map((v, j) => (
                  <td key={j} style={{ padding: "4px 8px", whiteSpace: "nowrap" }}>
                    {v === null ? "" : String(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </button>{" "}
        Page {page} of {pages}{" "}
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>
          Next
        </button>
      </p>
    </section>
  );
}
