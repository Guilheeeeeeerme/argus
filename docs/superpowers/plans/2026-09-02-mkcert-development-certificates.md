# mkcert Development Certificates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Caddy's internal CA with mkcert to fix Chrome certificate warnings for `*.development.argus.com`

**Architecture:** Use mkcert to generate locally-trusted certificates, mount them into Caddy container, add auto-renewal script, update setup.sh to handle mkcert installation and cert generation.

**Tech Stack:** mkcert, Caddy, Docker Compose, Bash

**Spec:** `docs/superpowers/specs/2026-09-02-mkcert-development-certificates-design.md`

## Global Constraints

- Changes limited to argus-core infrastructure only
- Must work on Linux (primary target)
- Requires sudo for first-time mkcert CA installation (same as existing /etc/hosts setup)
- Certs stored in `argus-core/infra/caddy/certs/` (gitignored)
- Backwards compatible: existing setup.sh flags (ARGUS_SKIP_CORE_START, ARGUS_SKIP_CERT_TRUST) still work

## File Structure

| File | Change |
|------|--------|
| `argus-core/infra/caddy/Caddyfile` | `tls internal` → `tls /certs/cert.pem /certs/key.pem` |
| `argus-core/backend/docker/docker-compose.yml` | Add cert volume mount to dev-gateway |
| `setup.sh` | Add mkcert installation and cert generation |
| New: `argus-core/infra/caddy/renew-certs.sh` | Auto-renewal script |
| New: `argus-core/infra/caddy/certs/.gitkeep` | Cert storage directory |
| `.gitignore` | Add `argus-core/infra/caddy/certs/*.pem` |

---

### Task 1: Create worktree and branch

**Files:**
- Create: worktree at `/home/ferre/Code/argus-worktrees/mkcert-certs`

**Interfaces:**
- Consumes: main branch of argus repository
- Produces: isolated worktree for implementation

- [ ] **Step 1: Create worktree directory**

```bash
mkdir -p /home/ferre/Code/argus-worktrees
```

- [ ] **Step 2: Create git worktree with new branch**

```bash
cd /home/ferre/Code/argus
git worktree add -b feat/mkcert-development-certificates /home/ferre/Code/argus-worktrees/mkcert-certs main
```

- [ ] **Step 3: Verify worktree created**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git status
```

Expected: On branch feat/mkcert-development-certificates, nothing to commit

---

### Task 2: Update Caddyfile to use cert files

**Files:**
- Modify: `argus-core/infra/caddy/Caddyfile`

**Interfaces:**
- Consumes: none
- Produces: Caddyfile that reads certs from /certs/ mount

- [ ] **Step 1: Read current Caddyfile**

```bash
cat argus-core/infra/caddy/Caddyfile
```

Verify it contains `tls internal` directives.

- [ ] **Step 2: Replace all `tls internal` with cert file paths**

Edit `argus-core/infra/caddy/Caddyfile` and replace every occurrence of `tls internal` with `tls /certs/cert.pem /certs/key.pem`.

There are 5 occurrences:
- Line 3: `app.development.argus.com` block
- Line 6: `development.argus.com:3000` block
- Line 9: `development.argus.com:3001` block
- Line 12: `development.argus.com:3002` block
- Line 15: `api.development.argus.com` block

- [ ] **Step 3: Verify the changes**

```bash
grep -n "tls" argus-core/infra/caddy/Caddyfile
```

Expected: All 5 lines show `tls /certs/cert.pem /certs/key.pem`

- [ ] **Step 4: Commit**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git add argus-core/infra/caddy/Caddyfile
git commit -m "fix(caddy): use mkcert certificates instead of internal CA

Replace tls internal with tls /certs/cert.pem /certs/key.pem to use
mkcert-generated certificates that Chrome trusts automatically."
```

---

### Task 3: Update Docker Compose to mount certs

**Files:**
- Modify: `argus-core/backend/docker/docker-compose.yml` (dev-gateway service)

**Interfaces:**
- Consumes: certs directory from Task 2
- Produces: dev-gateway service with cert volume mount

- [ ] **Step 1: Read docker-compose.yml dev-gateway section**

```bash
grep -A 20 "dev-gateway:" argus-core/backend/docker/docker-compose.yml
```

- [ ] **Step 2: Add cert volume mount to dev-gateway**

In the `volumes:` section of the `dev-gateway` service, add:
```yaml
      - ../../infra/caddy/certs:/certs:ro
```

The volumes section should become:
```yaml
    volumes:
      - ../../infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - ../../infra/caddy/certs:/certs:ro
      - caddy_data:/data
      - caddy_config:/config
```

- [ ] **Step 3: Verify the change**

```bash
grep -A 10 "volumes:" argus-core/backend/docker/docker-compose.yml | head -15
```

Expected: Shows the new cert volume mount line.

- [ ] **Step 4: Commit**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git add argus-core/backend/docker/docker-compose.yml
git commit -m "fix(docker): mount mkcert certificates into Caddy container

Add read-only bind mount for argus-core/infra/caddy/certs/ to /certs/
in the dev-gateway service."
```

---

### Task 4: Create certs directory and .gitkeep

**Files:**
- Create: `argus-core/infra/caddy/certs/.gitkeep`

**Interfaces:**
- Consumes: none
- Produces: certs directory ready for certificate files

- [ ] **Step 1: Create certs directory**

```bash
mkdir -p argus-core/infra/caddy/certs
```

- [ ] **Step 2: Create .gitkeep**

```bash
touch argus-core/infra/caddy/certs/.gitkeep
```

- [ ] **Step 3: Update .gitignore**

Add to `/home/ferre/Code/argus-worktrees/mkcert-certs/.gitignore`:
```
argus-core/infra/caddy/certs/*.pem
argus-core/infra/caddy/certs/*.key
```

- [ ] **Step 4: Commit**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git add argus-core/infra/caddy/certs/.gitkeep .gitignore
git commit -m "chore: add certs directory and gitignore for mkcert certificates"
```

---

### Task 5: Create auto-renewal script

**Files:**
- Create: `argus-core/infra/caddy/renew-certs.sh`

**Interfaces:**
- Consumes: mkcert installed on host
- Produces: renewed certificates in argus-core/infra/caddy/certs/

- [ ] **Step 1: Create renewal script**

Create `argus-core/infra/caddy/renew-certs.sh` with the following content:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/certs"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "Error: mkcert is not installed." >&2
  echo "Install: https://github.com/FiloSottile/mkcert#installation" >&2
  exit 1
fi

mkdir -p "$CERT_DIR"

echo "Generating certificates for *.development.argus.com..."
mkcert -cert-file "$CERT_DIR/cert.pem" \
        -key-file "$CERT_DIR/key.pem" \
        "*.development.argus.com" development.argus.com localhost 127.0.0.1

echo "Certificates renewed successfully."
echo "Certificate: $CERT_DIR/cert.pem"
echo "Private key: $CERT_DIR/key.pem"
echo ""
echo "To apply, restart Caddy:"
echo "  cd $SCRIPT_DIR/../.. && docker compose restart dev-gateway"
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x argus-core/infra/caddy/renew-certs.sh
```

- [ ] **Step 3: Test script runs without errors (will fail if mkcert not installed, that's ok)**

```bash
./argus-core/infra/caddy/renew-certs.sh 2>&1 || true
```

If mkcert is not installed, should show "Error: mkcert is not installed."

- [ ] **Step 4: Commit**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git add argus-core/infra/caddy/renew-certs.sh
git commit -m "feat(caddy): add certificate renewal script

Script regenerates mkcert certificates for *.development.argus.com.
Run manually or schedule via cron/systemd timer every 6 months."
```

---

### Task 6: Update setup.sh to use mkcert

**Files:**
- Modify: `setup.sh`

**Interfaces:**
- Consumes: mkcert installed on host
- Produces: certificates generated during setup, mkcert CA trusted

- [ ] **Step 1: Read current setup.sh**

```bash
cat setup.sh
```

- [ ] **Step 2: Add mkcert to required commands check**

Change the first check block from:
```bash
for command_name in git docker openssl; do
```
to:
```bash
for command_name in git docker openssl; do
```

We'll add mkcert check separately since it needs installation.

- [ ] **Step 3: Add mkcert installation function**

After the initial checks, add:

```bash
# Install mkcert if not present
if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found. Installing..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq mkcert libnss3-tools
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y mkcert
  elif command -v brew >/dev/null 2>&1; then
    brew install mkcert
  else
    echo "Cannot install mkcert automatically." >&2
    echo "Install manually: https://github.com/FiloSottile/mkcert#installation" >&2
    exit 1
  fi
  echo "mkcert installed."
fi

# Initialize mkcert CA (requires sudo on first run)
mkcert -install 2>/dev/null || true
```

- [ ] **Step 4: Add certificate generation before docker compose up**

Before the `docker compose up` section, add:

```bash
# Generate development certificates
cert_dir="$repo_root/argus-core/infra/caddy/certs"
mkdir -p "$cert_dir"
if [[ ! -f "$cert_dir/cert.pem" ]] || [[ ! -f "$cert_dir/key.pem" ]]; then
  echo "Generating development certificates..."
  mkcert -cert-file "$cert_dir/cert.pem" \
          -key-file "$cert_dir/key.pem" \
          "*.development.argus.com" development.argus.com localhost 127.0.0.1
  echo "Certificates generated at $cert_dir/"
fi
```

- [ ] **Step 5: Remove old Caddy cert trust section**

The old section that extracts Caddy's internal CA is no longer needed. Remove or comment out the entire block starting with:
```bash
if [[ "${ARGUS_SKIP_CERT_TRUST:-0}" != 1 ]]; then
```
through its matching `fi`.

Replace with:
```bash
# mkcert CA is trusted during mkcert -install step above
# No separate cert trust extraction needed
```

- [ ] **Step 6: Verify the changes**

```bash
grep -n "mkcert" setup.sh
```

Expected: Shows mkcert installation, -install, and cert generation lines.

- [ ] **Step 7: Commit**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git add setup.sh
git commit -m "feat(setup): integrate mkcert for development certificates

- Auto-install mkcert if not present
- Initialize mkcert CA
- Generate wildcard certificates for *.development.argus.com
- Remove old Caddy internal CA trust extraction"
```

---

### Task 7: Verify all changes work together

**Files:**
- All modified files

**Interfaces:**
- Consumes: all previous tasks completed
- Produces: verified implementation ready for PR

- [ ] **Step 1: Check git status**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git status
```

Expected: Clean working tree, on branch feat/mkcert-development-certificates

- [ ] **Step 2: Review commit history**

```bash
git log --oneline main..HEAD
```

Expected: 5-6 commits showing the progression of changes.

- [ ] **Step 3: Verify Caddyfile syntax**

```bash
cat argus-core/infra/caddy/Caddyfile | grep -c "tls /certs/cert.pem /certs/key.pem"
```

Expected: 5 (all site blocks updated)

- [ ] **Step 4: Verify docker-compose has cert mount**

```bash
grep "certs:/certs:ro" argus-core/backend/docker/docker-compose.yml
```

Expected: One match showing the volume mount.

- [ ] **Step 5: Verify renewal script is executable**

```bash
ls -la argus-core/infra/caddy/renew-certs.sh
```

Expected: File exists with execute permissions.

- [ ] **Step 6: Verify .gitignore excludes cert files**

```bash
grep "certs/\*.pem" .gitignore
```

Expected: Match found.

---

### Task 8: Create Pull Request

**Files:**
- None (PR creation)

**Interfaces:**
- Consumes: all previous tasks completed and verified
- Produces: PR on GitHub

- [ ] **Step 1: Push branch to remote**

```bash
cd /home/ferre/Code/argus-worktrees/mkcert-certs
git push -u origin feat/mkcert-development-certificates
```

- [ ] **Step 2: Create PR using gh**

```bash
gh pr create \
  --title "fix: use mkcert for trusted development certificates" \
  --body "## Problem

Chrome shows 'insecure' warning for \`*.development.argus.com\` because Caddy's internal CA generates self-signed certificates that Chrome doesn't trust.

## Solution

Replace Caddy's internal CA with [mkcert](https://github.com/FiloSottile/mkcert) — a zero-config tool that creates a local CA Chrome trusts automatically.

## Changes

- **Caddyfile**: Replace \`tls internal\` with \`tls /certs/cert.pem /certs/key.pem\`
- **Docker Compose**: Mount \`argus-core/infra/caddy/certs/\` into Caddy container
- **setup.sh**: Auto-install mkcert, generate wildcard certificates
- **renew-certs.sh**: New script to regenerate certificates (run every 6 months)
- **.gitignore**: Exclude certificate files from version control

## Testing

1. Run \`./setup.sh\` — should install mkcert, generate certs, start stack
2. Visit \`https://app.development.argus.com\` — Chrome should show lock icon
3. Visit \`https://api.development.argus.com\` — same
4. Verify cert details show 'mkcert' as issuer" \
  --base main
```

- [ ] **Step 3: Verify PR created**

```bash
gh pr view
```

Expected: Shows the PR with title and description.

- [ ] **Step 4: Return to main worktree**

```bash
cd /home/ferre/Code/argus
```
