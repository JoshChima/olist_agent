import { useEffect, useState, type ComponentProps } from "react";
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

  // A two-column grid: the picker, then the row count beside it; the table and the pager span both.
  // The picker stays mounted across views (so a keyboard user keeps focus in it); Rows is keyed by
  // view, so picking one starts again: page 1, unsorted, nothing shown yet.
  return (
    <section className="grid grid-cols-[auto_1fr] items-center gap-4">
      <label className={`flex items-center gap-2 ${SMALL}`}>
        <span className={MUTED}>View</span>
        <select className={`select w-auto py-1.5 ${SMALL} ${FOCUS}`} value={view} onChange={(e) => setView(e.target.value)}>
          {(views.length ? views : [view]).map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <Rows key={view} view={view} clock={clock} />
    </section>
  );
}

// Identifiers (the `_id` columns) are read in the mono family; numerals sit right-aligned.
// ponytail: a column's kind is read off the current page's first non-null value, so a page where
// a numeric column is all null aligns it left; the API would have to describe its columns to do better.
const isId = (column: string) => column.endsWith("_id");
const isNumeric = (rows: unknown[][], j: number) => typeof rows.find((row) => row[j] !== null)?.[j] === "number";

function Rows({ view, clock }: { view: string; clock: string }) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<Sort>({ desc: false });

  useEffect(() => setPage(1), [clock]); // a rewind can leave fewer pages than before

  const q = new URLSearchParams({ clock, page: String(page), desc: String(sort.desc) });
  if (sort.column) q.set("sort", sort.column);
  const { data, error } = useJson<Page>(`/api/explore/${encodeURIComponent(view)}?${q}`);

  if (error)
    return (
      <p role="alert" className="col-span-2">
        Couldn't load {view}: {error}
      </p>
    );
  if (!data) return <p className={MUTED}>Loading…</p>;

  const sortBy = (column: string) =>
    setSort((s) => ({ column, desc: s.column === column ? !s.desc : false }));
  const align = data.columns.map((_, j) => (isNumeric(data.rows, j) ? "text-right" : "text-left"));

  return (
    <>
      <p className={`${SMALL} ${MUTED} tabular-nums`}>
        {count(data.total)} rows as of {clock}
      </p>
      {/* The wrap's height is capped so the rows scroll inside it while the app bar and the page
          heading stay put. The cap is the viewport less the shell's bar and the page's own chrome
          (title, picker row, pager, paddings, and room for the delta strip). */}
      <div className="table-wrap col-span-2 min-w-0 max-h-[max(16rem,calc(100vh-21rem))]">
        {/* Borders sit on the cells, not the rows, so the header cells can stick to the top of the wrap
            as the rows scroll under them, on the page ground (Concord's root background). */}
        <table className={`table w-auto min-w-full border-separate border-spacing-0 whitespace-nowrap tabular-nums ${SMALL}`}>
          <thead>
            <tr>
              {data.columns.map((c, j) => (
                <th
                  key={c}
                  className={`sticky top-0 border-b bg-(--color-root-bg-light) px-3 py-2 dark:bg-(--color-root-bg-dark) ${LINE} ${align[j]}`}
                  aria-sort={sort.column === c ? (sort.desc ? "descending" : "ascending") : undefined}
                >
                  <button className={`-mx-1 rounded-base px-1 hover:preset-tonal ${MUTED} ${FOCUS}`} onClick={() => sortBy(c)}>
                    {c}
                    {sort.column === c && (sort.desc ? " ▼" : " ▲")}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i}>
                {row.map((v, j) => (
                  <td key={j} className={`border-b px-3 py-2 ${LINE} ${align[j]} ${isId(data.columns[j]) ? "font-mono" : ""}`}>
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
        count={Math.max(data.total, 1)} // an empty view is one page, with Next disabled, as before
        pageSize={data.page_size}
        page={page}
        onPageChange={(details) => setPage(details.page)}
        className={`col-span-2 ${SMALL}`}
        aria-label="Pages of rows"
      >
        <Pagination.PrevTrigger className={FOCUS}>Previous</Pagination.PrevTrigger>
        <Pagination.Context>
          {(pagination) =>
            pagination.pages.map((item, index) =>
              item.type === "page" ? (
                <Pagination.Item
                  key={index}
                  {...item}
                  className={FOCUS}
                  element={(attrs) => <button {...(attrs as ComponentProps<"button">)}>{item.value}</button>}
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
  );
}
