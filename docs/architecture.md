# SPECTRA Architecture

## Investigation flow

QUESTION -> PLANNER -> SEARCH TASKS -> ROUTER -> SERPAPI -> NORMALIZED EVIDENCE -> SIGNALS -> DIVERGENCE -> BLIND SPOTS -> RESULT

## Phase 3 boundary

The planner converts a user question into a provider-neutral `InvestigationPlan` containing `SearchTask` objects. The router executes those tasks through the SerpApi service. The planner owns *why* a surface is needed; SerpApi owns *how* the search is retrieved.

The planner is deterministic for the first implementation so engine selection is inspectable and reproducible. An LLM may later enrich intent/topic extraction, but deterministic guardrails remain responsible for the final evidence requirements.
