# olist_agent — Showcase plan (agreed via grilling session, 2026-10-18)

## Context
A public showcase project, also run as a learning course for the developer. It demonstrates:
- building a multi-agent AI app with LangGraph, the Claude API and TypeSafe Jev;
- RAG, and picking the right model for each job, backed by measured evals;
- Azure deployment with Terraform and CI/CD for both the app and the infrastructure;
- later, model-agnostic agents running on OpenRouter or a self-hosted open model.

The base app is a **time-travel simulator** over the Olist Kaggle dataset (orders plus the marketing lead funnel). Agents treat the simulator's data as if it were arriving live. The repo is currently empty apart from the agent-skills config: it has no git remote, no GLOSSARY.md and no ADRs. Linear project `olist_agent` belongs to the AIE team.

## Settled decisions
**Simulator**
- **Hybrid design.** The full dataset sits in Postgres as the source of truth. Every read goes through `as_of(clock)` views. Advancing the clock from t₀ to t₁ produces delta **events**, which trigger the agents.
- **Status is derived from timestamps at clock time.** An order moves from purchased to approved, shipped and delivered as its timestamps pass. Reviews appear on their creation date. Customers and sellers appear with their first activity. Products, geolocation and category translations are static.
- **No future leakage**, enforced by a property test in CI.
- **One clock per browser session.** Agent output is a memoized function of a **clock window**: the first signed-in user to reach a window pays for it, and everyone else reads the cache.
- **Data quirks to handle:**
  - 2016 is sparse.
  - Sep–Oct 2018 is a collection artifact; agents should flag it as data quality, not as a business change.
  - About 1.4% of orders have their timestamps in the wrong order.
  - `review_id` is not unique.
  - `customer_unique_id` identifies the actual person.

**AI**

*Agents (v1):*
- **Anomaly Investigator** (reactive):
  - A median/MAD z-score runs in code over daily metrics by category and state, with weekday seasonality removed.
  - Only a flagged spike or dip gets a Sonnet investigation.
- **Review Analyst:** issue tagging, sentiment, RAG and summaries.
- **Analyst Chat supervisor:** routes requests to the other two, and has a SQL tool over the as_of views.
- A leads-funnel agent is optional (P6).

*Models:*
- **Jev:**
  - issue tagging with a `choice` question, using a frozen taxonomy that Claude proposes and the user edits;
  - per-aspect sentiment and star/text mismatch with `score`;
  - RAG reranking with `noul`;
  - supervisor routing with `choice`.
  - Jev only produces typed judgments: no generated text, no embeddings. It is weak at arithmetic and dates, and only moderately good in Portuguese, so the evals test it on the Portuguese originals and on the English translations.
- **Haiku:** Portuguese→English translation, cached incrementally by `review_id`, plus a Batch API backfill as a lesson; also per-product summaries.
- **Sonnet:** anomaly investigation and the supervisor.
- **Azure OpenAI `text-embedding-3-small`:** embeds the Portuguese originals, stored in pgvector.

*Framework:* LangGraph in Python, with a Postgres checkpointer. The first AI lesson hand-writes the raw Claude tool-use loop.

*Evals are a CI stage:*
- golden set of about 300 reviews, pre-labeled by Opus with about 100 corrected by the user;
- real anomaly events (Black Friday on 2017-11-24, the truckers' strike in May 2018) plus injected ones;
- a model comparison table (accuracy, cost per 1k, latency) published as a CI artifact.

*Observability:*
- a Postgres **cost ledger** (one row per model call; it is also the source of the spend cap);
- `azure-monitor-opentelemetry` for app and infrastructure telemetry in App Insights;
- the LangSmith free tier for agent traces only.
- OTel GenAI is skipped because its semantic conventions are still "Development" and have moved to a new repo.

**Access and cost**
- Public, read-only browsing with cached agent results.
- Live agents need a GitHub sign-in through Easy Auth, and the GitHub user must be on an allowlist.
- Spend caps:
  - a daily token budget in the app (from the ledger);
  - an Anthropic Console workspace spend limit;
  - an Azure budget alert.
- Target: about $30–50 a month. Region: **East US**, on a pay-as-you-go subscription.

**Infrastructure and CI/CD**
- Terraform, deployed from a walking skeleton in P0 onward; each phase adds its own infrastructure diff.
- Runtime: Azure Container Apps, one app plus jobs, in a **workload-profiles environment from P0**. GPU profiles need that environment type and an environment cannot be converted later.
- ACR Basic, and Postgres Flexible Server (smallest burstable tier) with pgvector.
- Blob storage for the raw SQLite file, uploaded once with `make upload-data` and never committed to git. An idempotent loader job reads it.
- Key Vault with managed identity.
- Public GitHub repo. GitHub Actions authenticates with OIDC. Terraform remote state lives in Azure Storage, created by a `bootstrap/` configuration.
- One Azure environment. Pull requests run lint, tests, evals, `terraform plan` (posted as a PR comment) and trivy. Merging to `main` runs apply, deploy and a smoke test.
- **P5 GPU:**
  - Ollama in a non-root custom image, serving gpt-oss-20b on a T4.
  - Kept provisioned by Terraform with `min_replicas=0` and internal ingress only.
  - Gated so that only eval jobs and allowlisted users can call it.
  - It takes over Haiku's jobs, and the eval table compares the two.
  - OpenRouter is the same code path with a different OpenAI-compatible base URL.

**Stack and tooling**
- FastAPI, plus a React + Vite single-page app served by FastAPI in one container; agent progress streams over SSE.
- docker-compose with Postgres for local development.
- uv, ruff, pyright, pnpm, tflint and trivy.
- pytest, with testcontainers for Postgres.

**Licensing**
- Code is MIT.
- The dataset is effectively CC BY-NC-SA 4.0. Derived data that contains review text (golden sets, fixtures) goes in `data/` under its own CC BY-NC-SA license. The README credits Olist.

**Course format**
- Each phase is a Linear **milestone** containing issues, with one PR per issue.
- When a milestone closes, write one **lesson as a Linear document**: why we built it, how the parts interact, and what to watch for on the infrastructure side.
- ADRs go in `docs/adr/` and domain terms in `GLOSSARY.md`, both in the repo as AGENTS.md requires.

## Phases (each one ends in a deployed state)
| Phase | App | AI | Infrastructure added |
|---|---|---|---|
| P0 Walking skeleton | FastAPI "hello" + React shell | — | bootstrap state, resource group, ACR, Log Analytics + App Insights, workload-profiles ACA environment + app, budget alert, OIDC pipelines |
| P1 Simulator | loader, as_of views, per-session clock, delta events, clock controls, order/funnel dashboards, table explorer | — | Postgres Flexible Server, Blob storage, ACA loader job |
| P2 First agent | Analyst Chat over SQL tool | raw tool-use loop lesson → LangGraph; cost ledger + spend cap | Key Vault, managed identity, Easy Auth + allowlist, LangSmith |
| P3 Review intelligence | product page (issues, summaries, translations, RAG search) | taxonomy discovery, Jev tagging/sentiment/rerank, Haiku translation/summaries, eval harness + model comparison | Azure OpenAI embeddings, pgvector, eval job |
| P4 Anomaly Investigator | findings feed with evidence charts | statistical detector → Sonnet investigation, memoized by window | scheduled job |
| P5 Model-agnostic | per-agent model selector | OpenRouter + self-hosted gpt-oss; Claude vs open-model evals | GPU workload profile + Ollama app |
| P6 (optional) | leads funnel agent | — | — |

## First steps (on approval)
1. Write ADRs for the load-bearing decisions: the hybrid as_of simulator, Postgres + pgvector, LangGraph, Container Apps with a workload-profiles environment, Terraform + OIDC, the observability split. Start `GLOSSARY.md` with as_of, clock, clock window, delta event, funnel stage, golden set, cost ledger.
2. Seed Linear: create milestones P0–P6, P0 issues in detail, and later phases at epic level.
3. Build P0. Prerequisites the user must do: create the GitHub repo, `az login`, and the one-time bootstrap apply. Explain each part as it is built.

## Verification
- **P0:** a PR shows a `terraform plan` comment. Merging deploys, and the public ACA URL serves the React shell and `/health`. The budget alert exists in the portal.
- **P1:** the leakage property test passes. Moving the clock to 2017-11-24 shows the Black Friday spike, and moving it backwards shows fewer rows.
- **P2+:** the eval job publishes the comparison table. Cost ledger totals match the Anthropic Console. Anonymous users see only cached results.
