# OWASP LLM guardrails

Promptdesk-derived guardrails standardize how ARGUS prompts are built and
screened. All components are strict: any registry, screening, or provider error
fails closed (the analysis is skipped/failed, never silently degraded).

## Components

- `python:apps/api/src/argus/guardrails/registry.yml` — versioned prompt and policy registry (validated on load; duplicate ids, missing keys, or malformed regex abort startup).
- `python:apps/api/src/argus/guardrails/screening.py` — deterministic regex screening of untrusted text (operator feedback) BEFORE any LLM call. Hits return policy ids only, never matched text.
- `python:apps/api/src/argus/guardrails/fencing.py` — wraps untrusted payload in `BEGIN_UNTRUSTED_VLM_CONTEXT`/`END_UNTRUSTED_VLM_CONTEXT` markers from the `context.fence` registry prompt.
- `python:apps/api/src/argus/integrations/llm_provider.py` — provider chain (`LLM_PROVIDER_ORDER`, default `gemini,openai`); keyless providers are skipped, and with no usable provider the worker fails closed unless `AUTH0_USE_MOCK` enables the mock client.
- `python:apps/api/src/argus/integrations/model_rank.py` — cheapest-first model ranking (seeds for gemini/openai, best-effort `models.list` enrichment), cached in Redis (`models:rank:{provider}`, `models:rank:updatedAt`) and refreshed by the `models.refresh_rank` beat task.
- `python:apps/api/src/argus/services/llm_budget.py` — worker-side Redis fixed-window rate limit (`llm:rate:{minute_bucket}`) and daily budget (`llm:budget:{yyyymmdd}`).

## OWASP LLM Top-10 mapping

| OWASP risk | Control |
| --- | --- |
| LLM01 Prompt Injection | pre-LLM `screen()` policy blocks + `fence()` markers around all feedback/RAG text + injection-resistance rules in `vlm.system` |
| LLM02 Sensitive Disclosure | system prompt forbids revealing prompts/secrets; screening blocks secret-looking input before it reaches the model |
| LLM06 Excessive Agency | no tool use, no shell, no network actions allowed in any VLM prompt; JSON-output-only contract |
| LLM10 Unbounded Consumption | worker `LLM_RATE_LIMIT_PER_MINUTE` (20/min) + `LLM_DAILY_BUDGET` (500/day) fail closed to `budget_exceeded`/`rate_limit` evidence; API-wide per-IP `RATE_LIMIT_PER_MINUTE` (30/min) via slowapi |

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `""` | Gemini provider key (required for gemini in the chain) |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Default Gemini model before rank override |
| `OPENAI_API_KEY` | `""` | OpenAI provider key |
| `OPENAI_BASE_URL` | `""` | Optional OpenAI-compatible base URL (now consumed by the client) |
| `OPENAI_MODEL` | `gpt-4o` | Default OpenAI model before rank override |
| `LLM_PROVIDER_ORDER` | `gemini,openai` | Provider priority; unknown names ignored |
| `MODEL_RANK_REFRESH_MS` | `43200000` | Beat interval for `models.refresh_rank` (12h) |
| `MODEL_RANK_TOP_N` | `3` | Models kept in the cached cheapest-first rank |
| `LLM_RATE_LIMIT_PER_MINUTE` | `20` | Worker fixed-window LLM calls per minute |
| `LLM_DAILY_BUDGET` | `500` | Worker daily LLM call budget |
| `RATE_LIMIT_PER_MINUTE` | `30` | Admin/triage API per-IP requests per minute (slowapi, exempt `/health` and docs) |

## Notes

- **Event-driven, not periodic.** VLM analysis is ingest-driven (frame arrivals
  trigger analysis immediately) and cannot be reduced to twice daily. The only
  periodic LLM-adjacent task is `models.refresh_rank`, default 2x/day.
- **Embeddings stay OpenAI-only.** `text-embedding-3-small` with a
  deterministic SHA-256 fallback; Gemini is not used for embeddings.
- Budget/rate-limit skips write Evidence rows with `status` `policy_block`,
  `rate_limit`, or `budget_exceeded` for observability. Offending user text is
  never logged or persisted.
