<p align="center">
  <img src="branding/argus.svg" alt="Argus" width="72" height="72" />
</p>

# Argus

Multi-company vision platform (MVP): admin SSO host, near-realtime triage micro-frontend, and an AI pipeline that turns camera streams into operator-ready **TriageCases**.

## Live

| Application | URL |
| --- | --- |
| Admin (SSO host) | https://app.argus.ferredemo.dev |
| Triage MFE | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Storage (signed URLs) | https://api.storage.argus.ferredemo.dev |

## Technical docs (GitHub Pages)

**https://guilheeeeeeerme.github.io/ferredemo-docs/** — shared ecosystem docs (`/en/argus/…`). Hosted in dedicated repo [`ferredemo-docs`](https://github.com/Guilheeeeeeerme/ferredemo-docs).

## AI engineering (audit-honest)

| Capability | Status |
| --- | --- |
| Pipeline `stream-gateway → stream-prep → prompt-eval → API WS → triage` | **VERIFIED** |
| Live multimodal LLM in **prompt-eval**; SAMPLE_FPS=1, WINDOW=6, POLL=30s, confidence 0.5, VLM 60s | **VERIFIED** |
| Product i18n en + pt-BR; session 7d; opaque Redis SSO | **VERIFIED** |
| Agents framework / offline eval product | **NOT FOUND** |
| API LLM + Celery model rank | **UNUSED** on live triage path |
| RAG (`RAG_LIMIT=5`, lookback 900s) | **PARTIAL** — no `query_embedding` on live path |

Align with Promptdesk guardrails: [`apps/api/docs/guardrails.md`](apps/api/docs/guardrails.md), [`docs/ai-engineering.md`](docs/ai-engineering.md).

## Architecture snapshot

```
stream-gateway (go2rtc) → stream-prep → MinIO + Redis frames:ready
                                      → prompt-eval → Detection / TriageCase
                                      → api (WS) → admin / triage MFEs
```

Brand mark: [`branding/argus.svg`](branding/argus.svg) — geometric many-eyed watcher (original; Panoptes-inspired, not a Wikimedia copy).

## Quick start

```bash
cp .env.example .env.local.docker && cp .env.local.docker .env   # Compose Postgres
./scripts/up.sh -d
```

| Service | URL |
| --- | --- |
| Admin | http://localhost:8180 |
| Triage | http://localhost:8181 |
| API | http://localhost:8800 |

## Deeper docs

- Agent map: [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) · [`STYLE_GUIDE.md`](STYLE_GUIDE.md)
- Spec: [`docs/SPEC.md`](docs/SPEC.md)
- Production deploy: private **infra** repo (GitHub Actions → GHCR → VPS; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md))

## Deployment

Push to `main` → infra GitHub Actions builds to GHCR and deploys. Details: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
