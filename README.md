<p align="center">
  <img src="branding/argus.svg" alt="Argus" width="72" height="72" />
</p>

# Argus

Multi-account vision platform (MVP): admin SSO host, near-realtime triage micro-frontend, and an AI pipeline that turns camera streams into operator-ready **TriageCases**.

## Live

| Application | URL |
| --- | --- |
| Admin (SSO host) | https://app.argus.ferredemo.dev |
| Triage MFE | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Camera frames | Authenticated API `latest-frame` route backed by private R2 storage |

## Technical docs (GitHub Pages)

**https://guilheeeeeeerme.github.io/ferredemo-docs/** — shared ecosystem docs (`/en/argus/…`). Hosted in dedicated repo [`ferredemo-docs`](https://github.com/Guilheeeeeeerme/ferredemo-docs).

## AI engineering (audit-honest)

| Capability | Status |
| --- | --- |
| Pipeline `stream-gateway → stream-prep → prompt-eval → API WS → triage` | **IMPLEMENTED** — live end-to-end processing requires running pipeline consumers and camera/provider evidence |
| Multimodal LLM in **prompt-eval**; sampling/window settings | **IMPLEMENTED** — source defaults do not prove live provider execution |
| Product i18n pt-BR first (+ en opt-in); opaque Redis SSO | **IMPLEMENTED** — session/UI configuration must be checked separately from worker activity |
| Agents framework / offline eval product | **NOT FOUND** |
| API LLM + Celery model rank | **UNUSED** on live triage path |
| RAG (`RAG_LIMIT=5`, lookback 900s) | **PARTIAL** — no `query_embedding` on live path |

Align with Promptdesk guardrails: [`apps/api/docs/guardrails.md`](apps/api/docs/guardrails.md), [`docs/ai-engineering.md`](docs/ai-engineering.md).

## Architecture snapshot

```
stream-gateway (go2rtc) → stream-prep → R2 + Redis frames:ready
                                      → prompt-eval → Detection / TriageCase
                                      → api (WS) → admin / triage MFEs
```

Production frames stay in private Cloudflare R2 storage; the authenticated API proxies camera frames to the UI. Local development uses MinIO. The retired storage hostname is not a required public endpoint.

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
- Production deploy: app-owned GitHub Actions → GHCR → Dokploy; SPAs on Cloudflare Pages (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md))

## Deployment

Push to `main` → **Deploy (Dokploy)** builds GHCR images and deploys the API/workers; **Pages (SPA)** publishes admin/triage independently. Production database remains Supabase Postgres, schema `argus`. Details: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
