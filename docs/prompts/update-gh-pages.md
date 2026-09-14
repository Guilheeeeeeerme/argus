# Prompt: update GitHub Pages (ecosystem docs) — Argus

Use this when Argus architecture, vision pipeline, RAG/session defaults,
prompt-eval, or guardrails change and the shared ecosystem docs may be stale.

**Ecosystem docs live only in ferredemo-docs** — never recreate a multi-product
VitePress site (or Pages deploy) inside this repository.

| | |
| --- | --- |
| **Docs repo** | https://github.com/Guilheeeeeeerme/ferredemo-docs |
| **Live URL** | https://guilheeeeeeerme.github.io/ferredemo-docs/ |
| **Full SoT prompt** | https://github.com/Guilheeeeeeerme/ferredemo-docs/blob/main/prompts/update-gh-pages.md |

Product branding, icons, and README links in **this** repo may point at that
URL. Edits and deploys happen in **ferredemo-docs** only.

## 1. Identify relevant commits / diffs (this repo)

Collect commits since the last docs update that touch Argus paths such as:

| Area | Typical paths |
| --- | --- |
| Vision pipeline | `services/stream-gateway/**`, `services/stream-prep/**`, `services/prompt-eval/**` |
| API / triage | `apps/api/**`, `apps/admin/**`, `apps/triage/**` |
| Auth / session | `apps/shared/auth/**`, Redis SSO / session TTL env |
| Guardrails / LLM | `docs/ai-engineering.md`, `apps/api/docs/guardrails.md`, VLM registries |
| Defaults | SAMPLE_FPS, WINDOW, POLL, confidence, RAG_LIMIT, LOOKBACK, VLM timeout |

Record **SHA range** (or single SHAs) and a one-line summary per commit.
Cross-check sibling repos (`infra`, shared standards) only when those diffs
affect Argus claims.

**Do not invent** Agents, token streaming, full semantic RAG, or other
capabilities without code evidence.

## 2. Diff against documented claims

In a checkout of **ferredemo-docs**, open matching Pages under `docs/en/**`
(and `pt/**` if translated) and check:

- Defaults tables (intervals, TTLs, budgets, thresholds)
- Mermaid diagrams (new/removed services or edges)
- Status tags: `VERIFIED` / `PARTIAL` / `UNUSED` / `NOT FOUND`
- Comparison matrix + defaults cheatsheet + known-gaps

Upgrade/downgrade tags **only** with code evidence. Prefer citing
`path:symbol` in the PR body.

## 3. Update only affected sections (in ferredemo-docs)

Edit the smallest set of markdown under `docs/` in **ferredemo-docs**, not here.

Argus checklist (paths relative to ferredemo-docs `docs/`):

- [ ] `en/argus/architecture.md` / `vision-pipeline.md` / `prompt-eval-and-vlm.md`
- [ ] `en/argus/hitl-triage.md` / `rag-and-feedback.md` / `known-gaps.md`
- [ ] Defaults (SAMPLE_FPS, WINDOW, POLL, confidence, RAG_LIMIT, LOOKBACK, VLM timeout, session)
- [ ] `en/standards/guardrails.md` / `en/reference/defaults-cheatsheet.md` / `comparison-matrix.md` if shared claims moved
- [ ] `en/reference/not-in-scope.md` if a capability was wrongly implied
- [ ] PT mirrors for any page you substantially changed

Preserve status-tag HTML (`<span class="status …">`). Keep EN canonical.
Never document unused code as live behavior.

## 4. Rebuild and deploy (ferredemo-docs)

```bash
# from ferredemo-docs checkout
npm ci
npm run build
```

Push/merge to `main` in **ferredemo-docs**. Workflow
`.github/workflows/deploy-pages.yml` builds and deploys Pages.

Confirm Actions green and
`https://guilheeeeeeerme.github.io/ferredemo-docs/` serves updated `/en/` content.

## Done criteria

1. SHAs + claim deltas listed in the ferredemo-docs PR
2. `npm run build` succeeds in ferredemo-docs
3. Pages workflow green on ferredemo-docs only
4. No new undocumented “Agents / streaming / full RAG” claims
5. This product repo was **not** given a VitePress tree or Pages workflow
