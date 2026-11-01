import { useEffect, useState, type ComponentProps, type ReactNode } from "react";
import { Pagination } from "@skeletonlabs/skeleton-react";
import { count } from "./format";
import { FOCUS, LINE, MUTED, SMALL } from "./tokens";
import { useJson } from "./useJson";

type Page = { columns: string[]; rows: unknown[][]; total: number; page: number; page_size: number };
type Sort = { column?: string; desc: boolean };

/** A sim view at the clock: 50 rows a page, sortable columns, total row count. */
export function Explore({ clock }: { clock: string }) {
  const views = useJson<{ views: string[] }>("/api/explore").data?.views ?? [];
  const [view, setView] = useState("orders");

  const picker = (
    <label className={`flex items-center gap-2 ${SMALL}`}>
      <span className={MUTED}>View</span>
      <select className={`select w-auto py-1.5 ${SMALL} ${FOCUS}`} value={view} onChange={(e) => setView(e.target.value)}>
        {(views.length ? views : [view]).map((v) => (
          <option key={v}>{v}</option>
        ))}
      </select>
    </label>
  );

  // Keyed by view, so picking one starts again: page 1, unsorted, nothing shown yet.
  return <Rows key={view} view={view} clock={clock} picker={picker} />;
}

// Identifiers (the `_id` columns) are read in the mono family; numerals sit right-aligned.
const isId = (column: string) => column.endsWith("_id");
const isNumeric = (rows: unknown[][], j: number) => typeof rows.find((row) => row[j] !== null)?.[j] === "number";

function Rows({ view, clock, picker }: { view: string; clock: string; picker: ReactNode }) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<Sort>({ desc: false });

  useEffect(() => setPage(1), [clock]); // a rewind can leave fewer pages than before

  const q = new URLSearchParams({ clock, page: String(page), desc: String(sort.desc) });
  if (sort.column) q.set("sort", sort.column);
  const { data, error } = useJson<Page>(`/api/explore/${encodeURIComponent(view)}?${q}`);

  const sortBy = (column: string) =>
    setSort((s) => ({ column, desc: s.column === column ? !s.desc : false }));
  const align = (numeric: boolean) => (numeric ? "text-right" : "text-left");

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4">
        {picker}
        {data && (
          <p className={`${SMALL} ${MUTED} tabular-nums`}>
            {count(data.total)} rows as of {clock}
          </p>
        )}
      </div>
      {error ? (
        <p role="alert">
          Couldn't load {view}: {error}
        </p>
      ) : !data ? (
        <p className={MUTED}>Loading…</p>
      ) : (
        <>
          {/* The wrap's height is capped so the rows scroll inside it while the app bar and the page
              heading stay put. The cap is the viewport less the shell's bar and the page's own chrome
              (title, picker row, pager, paddings, and room for the delta strip). */}
          <div className="table-wrap max-h-[calc(100vh-21rem)]">
            <table className={`table w-auto min-w-full whitespace-nowrap tabular-nums ${SMALL}`}>
              <thead className={LINE}>
                <tr>
                  {data.columns.map((c, j) => (
                    <th
                      key={c}
                      className={`px-3 py-2 ${align(isNumeric(data.rows, j))}`}
                      aria-sort={sort.column === c ? (sort.desc ? "descending" : "ascending") : undefined}
                    >
                      <button
                        className={`-mx-1 rounded-base px-1 hover:preset-tonal ${MUTED} ${FOCUS}`}
                        onClick={() => sortBy(c)}
                      >
                        {c}
                        {sort.column === c && (sort.desc ? " ▼" : " ▲")}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row, i) => (
                  <tr key={i} className={`border-b ${LINE}`}>
                    {row.map((v, j) => (
                      <td
                        key={j}
                        className={`px-3 py-2 ${align(isNumeric(data.rows, j))} ${isId(data.columns[j]) ? "font-mono" : ""}`}
                      >
                        {v === null ? "" : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Skeleton's Pagination over the same 50-row pages the API serves; the items become buttons
              so they are reachable from the keyboard (Skeleton renders them as anchors without an href). */}
          <Pagination
            count={data.total}
            pageSize={data.page_size}
            page={page}
            onPageChange={(d) => setPage(d.page)}
            className={SMALL}
            aria-label="Pages of rows"
          >
            <Pagination.PrevTrigger className={FOCUS}>Previous</Pagination.PrevTrigger>
            <Pagination.Context>
              {(pagination) =>
                pagination.pages.map((p, index) =>
                  p.type === "page" ? (
                    <Pagination.Item
                      key={index}
                      {...p}
                      className={FOCUS}
                      element={(attrs) => <button {...(attrs as ComponentProps<"button">)}>{p.value}</button>}
                    />
                  ) : (
                    <Pagination.Ellipsis key={index} index={index}>
                      …
                    </Pagination.Ellipsis>
                  ),
                )
              }
            </Pagination.Context>
            <Pagination.NextTrigger className={FOCUS}>Next</Pagination.NextTrigger>
          </Pagination>
        </>
      )}
    </section>
  );
}
