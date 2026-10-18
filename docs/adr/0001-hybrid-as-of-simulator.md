# 1. Hybrid as_of simulator with delta events

Date: 2026-10-18 · Status: Accepted

## Context
The app replays the Olist dataset (Sep 2016 – Oct 2018) as if it were arriving live, and users can time-warp in either direction. Agents need both *state* ("what exists now") and *triggers* ("what just arrived").

A write-time replayer (insert rows as the clock advances) is the most realistic, but rewinding the clock means rebuilding the database from scratch.

## Decision
- The full dataset is loaded once and treated as immutable source data.
- All reads go through `as_of(clock)` views. These filter on each table's governing timestamp and derive order status at that instant.
- Advancing the clock from t0 to t1 computes a **delta event** for that clock window.
- Each browser session has its own clock.
- Agent output is memoized per clock window, so a given window is only processed once.

## Consequences
- Time-warping is free in both directions, and per-session clocks cost nothing.
- Future leakage is the main risk. A CI property test asserts that no as_of query returns a row whose governing timestamp is later than the clock.
- Delta events are computed rather than stored. If the app later needs a real event bus (e.g. Service Bus), that is an additive change.
- Customers and sellers are derived to appear at their first activity, even though the source tables carry no time column.
