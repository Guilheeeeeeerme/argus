# Repository boundaries

The monorepo mirrors the intended future split:

- `apps/core-admin/`: Admin Dashboard and administrative API ownership.
- `apps/platform/`: ingestion, workers, WebSocket, and notification services.
- `apps/mfes/`: independently runnable operator micro-frontends.
- `packages/`: reserved for generated contracts and shared clients.
- `backend/`: temporary shared Python implementation during the transition.

Plain `docker compose up` starts Core Admin plus PostgreSQL, Redis, MinIO, and
the HTTPS gateway. Platform services and MFEs are opt-in profiles.
