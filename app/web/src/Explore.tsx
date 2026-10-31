import { useEffect, useState } from "react";
import { useJson } from "./useJson";

type Page = { columns: string[]; rows: unknown[][]; total: number; page: number; page_size: number };
type Sort = { column?: string; desc: boolean };

/** A sim view at the clock: 50 rows a page, sortable columns, total row count. */
export function Explore({ clock }: { clock: string }) {
  const views = useJson<{ views: string[] }>("/api/explore").data?.views ?? [];
  const [view, setView] = useState("orders");

  return (
    <section>
      <label>
        View{" "}
        <select value={view} onChange={(e) => setView(e.target.value)}>
          {(views.length ? views : [view]).map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      {/* Keyed by view, so picking one starts again: page 1, unsorted, nothing shown yet. */}
      <Rows key={view} view={view} clock={clock} />
    </section>
  );
}

function Rows({ view, clock }: { view: string; clock: string }) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<Sort>({ desc: false });

  useEffect(() => setPage(1), [clock]); // a rewind can leave fewer pages than before

  const q = new URLSearchParams({ clock, page: String(page), desc: String(sort.desc) });
  if (sort.column) q.set("sort", sort.column);
  const { data, error } = useJson<Page>(`/api/explore/${encodeURIComponent(view)}?${q}`);

  if (error)
    return (
      <p role="alert">
        Couldn't load {view}: {error}
      </p>
    );
  if (!data) return <p>Loading…</p>;
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const sortBy = (column: string) =>
    setSort((s) => ({ column, desc: s.column === column ? !s.desc : false }));

  return (
    <>
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
        <button className="btn btn-sm preset-tonal" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </button>{" "}
        Page {page} of {pages}{" "}
        <button className="btn btn-sm preset-tonal" disabled={page >= pages} onClick={() => setPage(page + 1)}>
          Next
        </button>
      </p>
    </>
  );
}
