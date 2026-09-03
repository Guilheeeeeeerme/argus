# Design: mkcert Development Certificates

## Problem

Chrome shows "insecure" warning for `*.development.argus.com` because Caddy's internal CA (`tls internal`) generates self-signed certificates that Chrome doesn't trust, even after extracting and installing the root CA in the OS trust store.

## Solution

Replace Caddy's internal CA with **mkcert** — a zero-config tool that creates a local CA Chrome trusts automatically.

## Architecture

### Certificate Generation

```bash
# One-time setup per developer machine
mkcert -install  # Creates local CA, installs in OS + NSS (Chrome/Firefox)

# Generate wildcard cert for Argus
mkcert "*.development.argus.com" development.argus.com localhost 127.0.0.1
```

Output files:
- `*.development.argus.com+2.pem` (certificate chain)
- `*.development.argus.com+2-key.pem` (private key)

### Caddy Integration

**Before:**
```caddyfile
api.development.argus.com {
    tls internal
    # ...
}
```

**After:**
```caddyfile
api.development.argus.com {
    tls /certs/cert.pem /certs/key.pem
    # ...
}
```

### Docker Compose Changes

Add volume mount to `dev-gateway` service:
```yaml
volumes:
  - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
  - ./infra/caddy/certs:/certs:ro
  - caddy_data:/data
  - caddy_config:/config
```

### Auto-Renewal

mkcert certs last ~2 years by default. Create a renewal script:

```bash
#!/usr/bin/env bash
# argus-core/infra/caddy/renew-certs.sh
set -euo pipefail

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

mkcert -cert-file "$CERT_DIR/cert.pem" \
        -key-file "$CERT_DIR/key.pem" \
        "*.development.argus.com" development.argus.com localhost 127.0.0.1

echo "Certificates renewed. Restart Caddy: docker compose restart dev-gateway"
```

Schedule via systemd timer or cron (every 6 months).

### setup.sh Integration

Add to existing setup script:
1. Check if mkcert is installed, install if not
2. Run `mkcert -install` (requires sudo on first run)
3. Generate certificates into `argus-core/infra/caddy/certs/`
4. Continue with existing docker compose up flow

## Files to Modify

| File | Change |
|------|--------|
| `argus-core/infra/caddy/Caddyfile` | `tls internal` → `tls /certs/cert.pem /certs/key.pem` |
| `argus-core/backend/docker/docker-compose.yml` | Add cert volume mount to dev-gateway |
| `setup.sh` | Add mkcert installation and cert generation |
| New: `argus-core/infra/caddy/renew-certs.sh` | Auto-renewal script |
| New: `argus-core/infra/caddy/certs/` | Cert storage directory (gitignored) |
| `.gitignore` | Add `argus-core/infra/caddy/certs/*.pem` |

## Scope

Changes limited to **argus-core** infrastructure. Services don't need modification — they communicate over HTTP internally, TLS is only at the Caddy edge.

## Testing

1. Run `setup.sh` — should install mkcert, generate certs, start stack
2. Visit `https://app.development.argus.com` — Chrome should show lock icon
3. Visit `https://api.development.argus.com` — same
4. Verify cert details show "mkcert` as issuer
5. Test renewal script regenerates certs

## Risks

- mkcert requires `sudo` for first-time CA installation (already required for `/etc/hosts`)
- Certs are per-developer (not shared) — acceptable for local dev
- If Caddy container is recreated without certs directory, TLS fails (graceful degradation)
