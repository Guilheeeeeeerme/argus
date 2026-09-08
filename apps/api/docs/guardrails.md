# OWASP LLM guardrails (Top 10 for LLM Applications **2026**)

Promptdesk-derived guardrails standardize how ARGUS prompts are built and
screened. All components are strict: any registry, screening, or provider error
fails closed (the analysis is skipped/failed, never silently degraded).

## Components

- `python:apps/api/src/argus/guardrails/registry.yml` — versioned prompt and policy registry (validated on load; duplicate ids, missing keys, or malformed regex abort startup).
- `python:apps/api/src/argus/guardrails/screening.py` — deterministic regex screening of untrusted text (operator feedback) BEFORE any LLM call **and at feedback write**. Hits return policy ids only, never matched text.
- `python:apps/api/src/argus/guardrails/fencing.py` — wraps untrusted payload in `BEGIN_UNTRUSTED_VLM_CONTEXT`/`END_UNTRUSTED_VLM_CONTEXT` markers from the `context.fence` registry prompt.
- `python:apps/api/src/argus/integrations/llm_provider.py` — provider chain (`LLM_PROVIDER_ORDER`, default `gemini,openai`); keyless providers are skipped, and with no usable provider the worker fails closed unless `AUTH0_USE_MOCK` enables the mock client.
- `python:apps/api/src/argus/integrations/model_rank.py` — cheapest-first model ranking from **seed-priced allowlisted** models only (no `inf`-price unknown IDs).
- `python:apps/api/src/argus/services/llm_budget.py` — per-tenant Redis rate/budget plus global ceiling; optional token/cost halts.
- `python:apps/api/src/argus/integrations/gemini_vlm.py` — frames via `data:` / `s3://` / allowlisted HTTP only (SSRF-hardened).
- Notify HITL — WARNING queues deliveries as `awaiting_approval`; Twilio send requires triage approve.

## OWASP LLM Top-10 mapping (2026)

| OWASP risk | Control |
| --- | --- |
| LLM01 Prompt Injection | pre-LLM `screen()` + write-time screen + `fence()` around feedback/RAG + injection-resistance rules in `vlm.system` |
| LLM02 Sensitive Information Disclosure | keys never in prompts; **accepted residual**: frames/prompts leave to Gemini/OpenAI by design — require DPA + retention; prompt “don’t reveal secrets” is defense-in-depth only |
| LLM03 Excessive Agency | no tool use; JSON-only; **HITL** before external notify; severity Claim–Check–Act with confidence floor |
| LLM04 Supply Chain | seed-priced allowlisted model IDs only; pinned critical deps |
| LLM05 Data & Model Poisoning | screen feedback before embedding |
| LLM06 Unbounded Consumption | per-company + global call budgets; optional `LLM_DAILY_TOKEN_BUDGET` / `LLM_DAILY_COST_USD` halt |
| LLM07 Misinformation | sanitize VLM JSON; min confidence before hint-driven severity |
| LLM08 Hidden Context Exposure | no secrets in registry; assume prompts recoverable |
| LLM09 Vector & Embedding Weaknesses | tenant filters + RLS; write-time screen |
| LLM10 Improper Output Handling | React text sinks; deterministic SMS template; sanitized JSON into severity |

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `""` | Gemini provider key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Default Gemini model before rank override |
| `OPENAI_API_KEY` | `""` | OpenAI provider key |
| `OPENAI_BASE_URL` | `""` | Optional OpenAI-compatible base URL |
| `OPENAI_MODEL` | `gpt-4o` | Default OpenAI model before rank override |
| `LLM_PROVIDER_ORDER` | `gemini,openai` | Provider priority |
| `MODEL_RANK_REFRESH_MS` | `43200000` | Beat interval for `models.refresh_rank` |
| `MODEL_RANK_TOP_N` | `3` | Models kept in the cached cheapest-first rank |
| `LLM_RATE_LIMIT_PER_MINUTE` | `20` | Per-tenant LLM calls per minute |
| `LLM_DAILY_BUDGET` | `500` | Per-tenant daily LLM call budget |
| `LLM_GLOBAL_DAILY_BUDGET` | `5000` | Global daily call ceiling |
| `LLM_DAILY_TOKEN_BUDGET` | `0` | Optional token halt (0 = disabled) |
| `LLM_DAILY_COST_USD` | `0` | Optional USD halt (0 = disabled) |
| `VLM_MIN_CONFIDENCE_FOR_HINT` | `0.55` | Min confidence before suspicious hint raises severity |
| `FRAME_HTTP_ALLOWLIST` | `""` | Extra comma-separated hosts allowed for Gemini HTTP frames |
| `RATE_LIMIT_PER_MINUTE` | `30` | API per-IP requests per minute |

## Notes

- **Event-driven, not periodic.** VLM analysis is ingest-driven.
- **Embeddings stay OpenAI-only.** `text-embedding-3-small` with SHA-256 fallback.
- Budget/rate-limit skips write Evidence with `rate_limit` / `budget_exceeded` / `token_budget_exceeded` / `cost_budget_exceeded`.
- MinIO bucket is **private** (no anonymous download); workers use credentials / presigned URLs.
