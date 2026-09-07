# Argus Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `argus` as a single clean local monorepo that preserves the Argus business code while removing umbrella/HTTPS leftovers and matching the Promptdesk-style repo shape as closely as the stack allows.

**Architecture:** Start by snapshotting the current dirty Argus tree, then rebuild the root from the Promptdesk scaffold. Transplant Argus backend, frontend, shared UI, docs, and tests into the new layout, then rewrite config so dev runs over HTTP only and no file hardcodes browser-local origins or TLS assumptions.

**Tech Stack:** Bash, Docker Compose, Python/FastAPI/Alembic, React/Vite, TypeScript, Node package manifests, Git.

**Spec:** `/home/ferre/Code/promptdesk/README.md`, `/home/ferre/Code/promptdesk/docker-compose.yml`, `/home/ferre/Code/promptdesk/.env.example`, `/home/ferre/Code/promptdesk/scripts/up.sh`, `/home/ferre/Code/argus/README.md`

## Global Constraints

- Keep local development on HTTP only.
- Preserve the Argus business logic, API surface, frontends, tests, and design system.
- Remove umbrella-layer assumptions and certificate/TLS artifacts.
- Ensure the final repository root is `/home/ferre/Code/argus`.
- Leave only one Argus repository tree at the end.

---

### Task 1: Snapshot and scaffold

**Files:**
- Create: `/tmp/argus-backup` copy of current repo
- Replace: `/home/ferre/Code/argus/*`

**Interfaces:**
- Consumes: current dirty Argus tree, Promptdesk scaffold tree
- Produces: clean Promptdesk-shaped Argus root ready for code transplant

- [ ] **Step 1: Back up the current tree**

```bash
rsync -a /home/ferre/Code/argus/ /tmp/argus-backup/
```

- [ ] **Step 2: Recreate the root from Promptdesk**

```bash
rm -rf /home/ferre/Code/argus
mkdir -p /home/ferre/Code/argus
rsync -a --exclude='.git' --exclude='node_modules' /home/ferre/Code/promptdesk/ /home/ferre/Code/argus/
```

- [ ] **Step 3: Preserve the Argus Git history only as backup**

```bash
git -C /home/ferre/Code/argus init
```

### Task 2: Transplant Argus code into the scaffold

**Files:**
- Create/modify: `/home/ferre/Code/argus/apps/api/**`
- Create/modify: `/home/ferre/Code/argus/apps/web/**`
- Create/modify: `/home/ferre/Code/argus/apps/support/**`
- Create/modify: `/home/ferre/Code/argus/apps/shared/auth/**`
- Create/modify: `/home/ferre/Code/argus/packages/ui/**`
- Create/modify: `/home/ferre/Code/argus/docs/**`
- Create/modify: `/home/ferre/Code/argus/scripts/**`
- Create/modify: `/home/ferre/Code/argus/tests/**`

**Interfaces:**
- Consumes: current Argus app code under `apps/admin`, `apps/triage`, `apps/api`, `apps/shared/auth`, `packages/ui`
- Produces: Promptdesk-shaped Argus monorepo with the same business code

- [ ] **Step 1: Move the backend**

```bash
rsync -a /tmp/argus-backup/apps/api/ /home/ferre/Code/argus/apps/api/
```

- [ ] **Step 2: Move the frontends and shared package**

```bash
rsync -a /tmp/argus-backup/apps/admin/ /home/ferre/Code/argus/apps/web/
rsync -a /tmp/argus-backup/apps/triage/ /home/ferre/Code/argus/apps/support/
rsync -a /tmp/argus-backup/apps/shared/auth/ /home/ferre/Code/argus/apps/shared/auth/
rsync -a /tmp/argus-backup/packages/ui/ /home/ferre/Code/argus/packages/ui/
```

- [ ] **Step 3: Move docs and tests**

```bash
rsync -a /tmp/argus-backup/docs/ /home/ferre/Code/argus/docs/
rsync -a /tmp/argus-backup/tests/ /home/ferre/Code/argus/tests/
rsync -a /tmp/argus-backup/scripts/ /home/ferre/Code/argus/scripts/
```

### Task 3: Remove TLS, umbrella, and browser-origin hardcoding

**Files:**
- Modify: `/home/ferre/Code/argus/docker-compose.yml`
- Modify: `/home/ferre/Code/argus/.env.example`
- Modify: `/home/ferre/Code/argus/apps/shared/auth/index.ts`
- Modify: `/home/ferre/Code/argus/apps/api/alembic.ini`
- Modify: `/home/ferre/Code/argus/apps/api/src/argus/config.py`
- Modify: `/home/ferre/Code/argus/apps/api/scripts/migrate.sh`
- Modify: `/home/ferre/Code/argus/apps/api/scripts/validate_rls.py`
- Modify: `/home/ferre/Code/argus/apps/api/tests/test_http_cors.py`
- Modify: `/home/ferre/Code/argus/apps/api/src/argus/workers/notifier.py`
- Modify: `/home/ferre/Code/argus/README.md`

**Interfaces:**
- Consumes: transplanted Argus source
- Produces: HTTP-only local dev config with env-driven origins

- [ ] **Step 1: Search for leftover literals**

```bash
rg -n --hidden --glob '!**/.git/**' 'https://|umbrella|cert|certificate|ssl|tls' /home/ferre/Code/argus
```

- [ ] **Step 2: Replace literals with env-driven HTTP defaults**

```python
MAIN_ORIGIN = os.getenv("MAIN_ORIGIN", "http://admin.argus.test:8180")
TRIAGE_ORIGIN = os.getenv("TRIAGE_ORIGIN", "http://triage.argus.test:8181")
```

- [ ] **Step 3: Re-run the search until it is clean**

```bash
rg -n --hidden --glob '!**/.git/**' 'https://|umbrella|cert|certificate|ssl|tls' /home/ferre/Code/argus
```

### Task 4: Rebuild repo metadata and workspace commands

**Files:**
- Modify: `/home/ferre/Code/argus/README.md`
- Modify: `/home/ferre/Code/argus/.gitignore`
- Modify: `/home/ferre/Code/argus/scripts/up.sh`
- Modify: `/home/ferre/Code/argus/docker-compose.yml`

**Interfaces:**
- Consumes: Promptdesk-style root layout
- Produces: Root docs and scripts that match the new monorepo

- [ ] **Step 1: Align start commands and docs**
- [ ] **Step 2: Keep only the necessary root files**
- [ ] **Step 3: Remove any duplicated or stale deployment files**

### Task 5: Delete legacy leftovers and reinitialize Git

**Files:**
- Delete: `/home/ferre/Code/argus-old-local`
- Delete: any remaining `Argus*` or `argus-*` directories outside the final root
- Replace: `/home/ferre/Code/argus/.git` if starting from a clean history

**Interfaces:**
- Consumes: verified clean consolidated repo
- Produces: one Argus repo with clean history and no leftovers

- [ ] **Step 1: Remove old Argus directories only after validation**

```bash
find /home/ferre/Code -maxdepth 1 -type d \( -iname 'argus*' -o -iname 'Argus*' \) | sort
```

- [ ] **Step 2: Reinitialize Git if desired**

```bash
rm -rf /home/ferre/Code/argus/.git
git -C /home/ferre/Code/argus init
git -C /home/ferre/Code/argus add .
git -C /home/ferre/Code/argus commit -m "chore: rebuild argus monorepo"
```

- [ ] **Step 3: Push to the single GitHub repo named `argus`**

```bash
gh repo create argus --source /home/ferre/Code/argus --private --push
```
