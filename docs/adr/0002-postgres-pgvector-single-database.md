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
Use Azure Database for PostgreSQL Flexible Server, smallest burstable tier, in East US, with the `vector` extension enabled.
- The SQLite file is only a load source. It is uploaded once to Blob storage and imported by an idempotent Container Apps Job.
- Local development runs the same Postgres in docker-compose.

## Consequences
- One database to provision, back up and secure.
- RAG retrieval is plain SQL: pgvector similarity search, then Jev reranking.
- At this scale a dedicated vector database would be overhead. Revisit only if retrieval latency or volume demands it.
- The database costs about $15/month and is the largest fixed cost.
