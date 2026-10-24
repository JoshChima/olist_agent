# Glossary

**Clock** — The simulated "now" for one browser session. Each session has its own clock; moving it forward or backward is a time-warp. Avoid: "current date", "sim time".

**as_of** — The rule that every read of Olist data is filtered to what existed at the clock: `as_of(clock)` views return only rows whose governing timestamp ≤ clock, with status derived at that instant. See ADR-0001.

**Governing timestamp** — The column that decides when a row becomes visible: `order_purchase_timestamp` for orders and their items/payments, `review_creation_date` for reviews, `first_contact_date` for qualified leads, `won_date` for closed deals, first activity for customers and sellers.

**Derived status** — An order's status as of the clock, computed from its lifecycle timestamps (purchased → approved → shipped → delivered), not the dataset's final `order_status`.

**Static table** — A table with no time dimension, always fully visible: products, geolocation, product category translation.

**Future leakage** — Any query or agent input that reveals a row or field later than the clock. Always a bug; guarded by a property test.

**Clock window** — A half-open interval `[t0, t1)` of simulated time. The unit agents process and the cache key for agent output.

**Delta event** — What appeared or changed in a clock window ("412 new orders, 38 new reviews, 2 deals closed"). Triggers reactive agents.

**Funnel stage** — Position of a marketing lead: qualified lead (MQL) → closed deal → active seller (has orders).

**Finding** — An agent's persisted output for a clock window, e.g. an anomaly investigation or a product review summary.

**Issue taxonomy** — The frozen, versioned list of review issue categories (late delivery, damaged, wrong item…) that Jev tags against.

**Golden set** — A labeled evaluation dataset (reviews with issue tags and sentiment; anomaly windows with known causes) used to score models in CI.

**Cost ledger** — One Postgres row per model call (agent, model, tokens, cost, latency, clock window). Source of truth for spend caps and cost dashboards.

**Toolbox** — The `olist-tf` Docker container (`tools/tf-toolbox/`) that runs Terraform and `az` against real Azure from a dev machine, driven only through `scripts/tf-toolbox.sh`. See ADR-0007.

**Risk tier** — `scripts/tf_risk.py`'s verdict on a plan: SAFE, REVIEW (identity/auth or bootstrap changes), DANGER (any delete or replace), BLOCK (delete or replace of a protected stateful resource). Shared by the terraform-operator subagent and CI.

**Approved plan hash** — The sha256 of a saved plan file that the user approved. A bootstrap apply only runs that exact file.

**Drift** — Azure and Terraform state disagree: something changed outside Terraform, or an apply only partly landed. Found with `plan -refresh-only`.

**Live run** — An agent execution that calls models and spends money. Only allowlisted signed-in users trigger live runs; everyone else reads cached findings.
