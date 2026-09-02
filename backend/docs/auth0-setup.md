# Auth0 setup for ARGUS SaaS MVP

## Overview

ARGUS uses Auth0 as the sole identity provider. All human users (Root Admin, Tenant Admin, Watcher) authenticate via Auth0 Universal Login (OIDC Authorization Code + PKCE). Edge devices use Auth0 Machine-to-Machine (M2M) client credentials.

## 1. Create Auth0 tenant resources

1. **API (Resource Server)**
   - Name: `ARGUS API`
   - Identifier (audience): `https://api.argus.example.com` (must match `AUTH0_API_AUDIENCE`)
   - Signing algorithm: RS256

2. **SPA applications** (Admin Dashboard, Triage UI)
   - Application type: Single Page Application
   - Allowed callback URLs: `http://localhost:5173/callback`, production URLs
   - Allowed logout URLs: matching origins
   - Enable OIDC conformant mode

3. **M2M application** (edge ingestion)
   - Application type: Machine to Machine
   - Authorize against the ARGUS API
   - Used by edge agents calling `POST /v1/ingest/sequences`

## 2. Custom claims Action

Create a **Login / Post Login** Action with this logic:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const ns = 'https://argus.local';
  const meta = event.user.app_metadata || {};
  api.accessToken.setCustomClaim(`${ns}/tenant_id`, meta.tenant_id || null);
  api.accessToken.setCustomClaim(`${ns}/role`, meta.role || 'watcher');
  if (meta.camera_id) {
    api.accessToken.setCustomClaim(`${ns}/camera_id`, meta.camera_id);
  }
};
```

Set `AUTH0_CLAIMS_NAMESPACE=https://argus.local` in `.env` (or use flat `tenant_id` / `role` claims in mock mode).

Map users in Auth0 `app_metadata`:

| Role | `app_metadata.role` | `app_metadata.tenant_id` |
|------|---------------------|--------------------------|
| Root Admin | `root_admin` | omit or null |
| Tenant Admin | `tenant_admin` | tenant UUID |
| Watcher | `watcher` | tenant UUID |

Seed script creates `auth0|seed-root-admin` and `auth0|seed-tenant-admin` rows in `tenant_users` for local correlation.

## 3. Test users

| User | Role | Auth0 `sub` (example) |
|------|------|------------------------|
| Root Admin | `root_admin` | `auth0|seed-root-admin` |
| Tenant Admin | `tenant_admin` | `auth0|seed-tenant-admin` |
| Watcher | `watcher` | create in Auth0 dashboard |

## 4. Local mock IdP (development)

When Auth0 is unavailable, enable mock JWT validation:

```bash
AUTH0_USE_MOCK=true
AUTH0_DOMAIN=dev.argus.local
AUTH0_API_AUDIENCE=https://api.argus.example.com
DEV_JWT_SECRET=local-dev-secret-change-me
```

Generate tokens with `python scripts/verify_pr3.py` or `integrations.auth0.create_mock_token`.

## 5. M2M edge flow

1. Edge agent requests token from `https://{AUTH0_DOMAIN}/oauth/token` with client credentials.
2. Auth0 Action adds `tenant_id`, `camera_id` claims for the edge device.
3. Ingest API validates token and rejects body fields that disagree with claims.

## 6. Backend validation

The backend validates:

- JWT signature (JWKS or mock HS256)
- `iss`, `aud`, `exp`
- Custom claims: `tenant_id`, `role` (and `camera_id` for M2M)

Validated claims populate `AuthContext` and PostgreSQL session variables via `set_config('app.current_tenant_id', ...)` and `set_config('app.current_role', ...)` for RLS enforcement.
