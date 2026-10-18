# 6. Observability: cost ledger + App Insights + LangSmith, not OTel GenAI (yet)

Date: 2026-10-18 · Status: Accepted

## Context
The project's headline claim is that the cheap-model strategy saves money, so it needs reliable per-agent cost and token numbers. As of Oct 2026:
- Every OpenTelemetry GenAI semantic convention (`gen_ai.*`) is still at "Development" status, and the conventions moved to a new repo (`semantic-conventions-genai`) with no tagged release.
- The instrumentations are split across OpenLLMetry, OpenInference and the official beta packages, and their attribute shapes differ.
- Microsoft's OTel distro has no Anthropic integration.

## Decision
- **Cost ledger:** one Postgres row per model call (agent, model, tokens, cost, latency, clock window). It is the source of truth for cost dashboards and for the daily spend cap.
- **App and infrastructure telemetry:** `azure-monitor-opentelemetry` sends it to Application Insights.
- **Agent trace debugging:** the LangSmith free tier (5k traces/month), enabled by environment variable for agent runs only. Per-review Jev calls are never traced there.

## Consequences
- No long-lived dashboard depends on an unstable attribute name.
- The cost-ledger write has to wrap *every* model client. Calls that bypass it go uncounted and unenforced.
- Revisit OTel GenAI once `semantic-conventions-genai` publishes a stable release.
