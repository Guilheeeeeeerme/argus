# Argus Workspace

This private repository is the workspace for the Argus platform. Runtime infrastructure lives in `core`; independently deployable domain projects live in `services`; reusable contracts and libraries live in `libs`.

## Get started

```bash
git clone git@github.com:Guilheeeeeeerme/argus.git
cd argus
./setup.sh
```

Start the shared platform dependencies and edge services:

```bash
cd core
docker compose up --build
```

Run an individual domain project from the services repository. Each project owns its own compose file and can use its own port above 3000:

```bash
cd services/triage
docker compose up --build
```

## Repository layout

- `core` — shared platform runtime: TLS/edge routing, database, Redis, broker, and core APIs.
- `services/capture` — capture and ingestion.
- `services/triage` — triage workspace and operator experience.
- `services/realtime` — realtime updates.
- `services/analysis` — analysis workflows.
- `services/notifications` — notification delivery.
- `libs` — shared contracts and libraries.

The local development hostname is `development.argus.com`. Core owns the shared infrastructure and service projects remain independently runnable under their own ports while integration conventions are established.
