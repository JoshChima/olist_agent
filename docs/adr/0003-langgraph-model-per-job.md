# 3. LangGraph orchestration, model chosen per job

Date: 2026-10-18 · Status: Accepted

## Context
There are three v1 agents: the Anomaly Investigator, the Review Analyst and the Analyst Chat supervisor. The project must show that each job runs on the cheapest model that is good enough. In P5 it must also swap in OpenRouter and a self-hosted open model.

TypeSafe Jev returns only typed judgments (`noul`, `choice`, `score`). It produces no generated text and no embeddings, and it is weak at arithmetic and date comparison.

## Decision
- LangGraph (Python) orchestrates the agents, with a Postgres checkpointer. The first AI lesson hand-writes a raw Claude tool-use loop before switching to LangGraph.
- Each job is assigned a model:

  | Model | Jobs |
  |---|---|
  | Jev | issue tagging, aspect sentiment, RAG reranking, supervisor routing |
  | Haiku | Portuguese→English translation (cached by `review_id`), product summaries |
  | Sonnet | anomaly investigation, supervisor chat |
  | Azure OpenAI `text-embedding-3-small` | embeddings |

- Statistics in code decide *whether* something is anomalous. LLMs only investigate what the statistics flag.
- Every model choice is justified by an eval in CI against a golden set, with a published model comparison table.

## Consequences
- Switching providers comes down to configuration through LangGraph's chat-model interface. OpenRouter and Ollama are both OpenAI-compatible base URLs.
- Jev's documented weak spots shape how it is used. Arithmetic and dates stay in code. The text Jev reads is untrusted input. `choice` options are ordered so that Jev's first-option bias doesn't skew the results.
