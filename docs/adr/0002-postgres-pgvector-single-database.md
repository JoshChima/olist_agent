# 2. One Postgres (with pgvector) for everything

Date: 2026-10-18 · Status: Accepted

## Context
The app needs to store several kinds of data:
- the Olist source data and its as_of views
- agent findings and cached model outputs
- the cost ledger
- LangGraph checkpoints
- review embeddings, about 41k review texts

The dataset ships as SQLite, but SQLite on an Azure file share corrupts under concurrent access because file locking over SMB is unreliable. Azure AI Search would add about $75/month.

## Decision
Use Azure Database for PostgreSQL Flexible Server, smallest burstable tier, in South Central US, with the `vector` extension enabled.
- Amended 2026-10-29: the first P1 deploys could not create the server in East US or East US 2.
  - East US: provisioning is restricted for this subscription (`list-skus` says so).
  - East US 2: the create failed with `SkuNotAvailable`.

  South Central US works, and this subscription already runs a B1ms server there. The rest of the app stays in East US.
- Amended 2026-10-31: CI's plan job now fails a PR that creates a server in a restricted region, or where the SKU or version isn't offered (`scripts/check_capacity.py`, which reads `list-skus`). Nothing could have predicted East US 2. Its quota (40 Burstable cores), capabilities and `list-skus` all matched South Central US, in every API version tried. Only the Azure MCP `quota_usage_check` reported "No SKU available" there, and its source couldn't be traced. Treat the first create in a new region as unproven until CD succeeds.
- The SQLite file is only a load source. It is uploaded once to Blob storage and imported by an idempotent Container Apps Job.
- Local development runs the same Postgres in docker-compose.

## Consequences
- One database to provision, back up and secure.
- RAG retrieval is plain SQL: pgvector similarity search, then Jev reranking.
- At this scale a dedicated vector database would be overhead. Revisit only if retrieval latency or volume demands it.
- The database costs about $15/month and is the largest fixed cost.
