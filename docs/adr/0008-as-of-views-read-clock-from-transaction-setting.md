# 8. as_of views read the clock from a transaction setting

Date: 2026-10-27 · Status: Accepted

## Context
ADR-0001 says every read goes through `as_of(clock)` views, but Postgres views take no parameters. The candidates were:
- **Set-returning functions** (`orders_as_of(clock)`): any caller, including P2's agent SQL tool, can pass a later clock.
- **`WHERE` clauses built in the app**: nothing in the database stops a query that forgets one.
- **Views that read the clock from a transaction-local setting**: callers query plain view names and never see the clock as an argument.

## Decision
- The loaded source data lives in a `raw` schema. The app's database role has no access to it.
- The `sim` schema holds one view per table. Time-dimensioned views filter on the governing timestamp and blank lifecycle fields later than the clock. Static tables are plain pass-through views.
- The views read the clock from a custom setting that the API sets with `SET LOCAL` at the start of each request's transaction. If the setting is missing, the views return no rows.
- Derived data that never changes (repaired timestamps, first-activity dates) is computed once by the loader, not per query.

## Consequences
- Agent SQL in P2 is plain `select … from sim.orders`, and it can't widen the clock by changing an argument.
- Agent SQL *can* call `set_config`/`SET`. The P2 SQL tool must reject those statements, and the leakage property test must cover that tool.
- Every request needs a transaction, because `SET LOCAL` only lasts until its transaction ends.
