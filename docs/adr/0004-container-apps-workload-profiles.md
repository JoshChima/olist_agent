# 4. Azure Container Apps in a workload-profiles environment

Date: 2026-10-18 · Status: Accepted

## Context
- The target spend is about $30–50/month, so idle cost should be near zero.
- Agent sign-in needs to be cheap to add.
- P5 adds a self-hosted model on a serverless GPU, and serverless GPU profiles exist only in workload-profiles environments.
- A Container Apps environment cannot be converted between types after it is created.

## Decision
Run on Azure Container Apps in a **workload-profiles environment from P0**, using the Consumption profile.
- One container app runs FastAPI and serves the React SPA.
- Container Apps Jobs handle the data loader, batch backfills, evals and scheduled anomaly scans.
- Images live in ACR Basic.
- Easy Auth (GitHub) gates live runs. The app also checks the signed-in user against an allowlist.
- In P5, add a T4 GPU workload profile running Ollama with gpt-oss-20b. It uses a non-root image, `min_replicas = 0` and internal ingress.

## Consequences
- Idle cost is close to zero.
- The GPU app costs about $1.50/hour, and only while it is serving requests. Each cold start takes 60–90 s.
- App Service was rejected because it always bills at least one instance. AKS was rejected because it would mean operating a whole platform.
- Choosing the environment type in P0 constrains P5. That is exactly why it is recorded here.
