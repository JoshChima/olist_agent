# Glossary

**Clock** — The simulated "today" for one browser session: a calendar day, between 2016-09-04 and 2018-10-17. A clock of D means all of day D has happened. Each session has its own clock. Avoid: "current date", "sim time", "now".

**Time-warp** — Any move of the clock. A **step** is a time-warp by one day, week or month; a **rewind** is a time-warp backwards. Avoid: "seek", "jump".

**as_of** — The rule that every read of Olist data shows only what existed at the clock: rows whose governing timestamp falls on or before the clock's day, with any later lifecycle field (approval, shipping, delivery, review answer) left empty and status derived at the clock. See ADR-0001 and ADR-0008.

**Governing timestamp** — The column that decides when a row becomes visible: `order_purchase_timestamp` for orders and their items/payments, `review_creation_date` for reviews, `first_contact_date` for qualified leads, `won_date` for closed deals, an order's purchase for its customer, and the earlier of first order and `won_date` for sellers.

**Derived status** — An order's status as of the clock, computed from its lifecycle timestamps (purchased → approved → shipped → delivered), not the dataset's final `order_status`. A canceled or unavailable order shows its lifecycle stage until its estimated delivery date, and only then its final status, since the dataset records no cancellation time.

**Repaired timestamps** — An order whose source lifecycle timestamps were out of order (about 1.4%), clamped so no stage is earlier than the stage before it, and flagged as repaired. Avoid: "fixed", "cleaned".

**Person** — A real customer, identified by `customer_unique_id`. One person has a different `customer_id` on every order, so customer counts are counts of people. Avoid: "user", "customer" when the human is meant.

**Static table** — A table with no time dimension, always fully visible: products, geolocation, product category translation.

**Future leakage** — Any query or agent input that reveals a row or field later than the clock. Always a bug; guarded by a property test.

**Data-quality window** — A stretch of simulated time whose data can't support business conclusions: 2016-09-04 → 2016-12-31 (sparse) and 2018-09-01 → 2018-10-17 (collection artifact). Agents flag changes inside it as data quality, not business change. Avoid: "outage", "gap".

**Clock window** — A half-open interval `[t0, t1)` of simulated time. The unit agents process and the cache key for agent output.

**Delta event** — Counts of what appeared or changed in a clock window ("412 new orders, 38 delivered, 2 deals closed"). Produced only by a forward time-warp; a rewind produces none. Triggers reactive agents.

**Funnel stage** — Position of a marketing lead: MQL (first contact) → closed deal (won) → active seller.

**Active seller** — A seller with at least one order at the clock. The last funnel stage. Avoid: "live seller".

**Finding** — An agent's persisted output for a clock window, e.g. an anomaly investigation or a product review summary.

**Issue taxonomy** — The frozen, versioned list of review issue categories (late delivery, damaged, wrong item…) that Jev tags against.

**Golden set** — A labeled evaluation dataset (reviews with issue tags and sentiment; anomaly windows with known causes) used to score models in CI.

**Cost ledger** — One Postgres row per model call (agent, model, tokens, cost, latency, clock window). Source of truth for spend caps and cost dashboards.

**Toolbox** — The `olist-tf-*` Docker container, one per checkout (`tools/tf-toolbox/`), that runs Terraform and `az` against real Azure from a dev machine, driven only through `scripts/tf-toolbox.sh`. See ADR-0007.

**Risk tier** — `scripts/tf_risk.py`'s verdict on a plan: SAFE, REVIEW (identity/auth or bootstrap changes), DANGER (any delete or replace), BLOCK (delete or replace of a protected stateful resource). Shared by the terraform-operator subagent and CI.

**Approved plan hash** — The sha256 of a saved plan file that the user approved. A bootstrap apply only runs that exact file.

**Drift** — Azure and Terraform state disagree: something changed outside Terraform, or an apply only partly landed. Found with `plan -refresh-only`.

**Live run** — An agent execution that calls models and spends money. Only allowlisted signed-in users trigger live runs; everyone else reads cached findings.
