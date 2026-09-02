# Argus Workspace

This private repository is the workspace for the Argus platform. Runtime infrastructure lives in `argus-core`; independently deployable domain projects live in `argus-services`; reusable contracts and libraries live in `argus-libs`.

## Get started

```bash
git clone git@github.com:Guilheeeeeeerme/argus.git
cd argus
./setup.sh
```

Start the shared platform dependencies and edge services:

```bash
cd argus-core
docker compose up --build
```

Run an individual domain project from the argus-services repository. Each project owns its own compose file and can use its own port above 3000:

```bash
cd argus-services/triage
docker compose up --build
```

## Repository layout

- `argus-core` — shared platform runtime: TLS/edge routing, database, Redis, broker, and core APIs.
- `argus-services/capture` — capture and ingestion.
- `argus-services/triage` — triage workspace and operator experience.
- `argus-services/realtime` — realtime updates.
- `argus-services/analysis` — analysis workflows.
- `argus-services/notifications` — notification delivery.
- `argus-libs` — shared contracts and libraries.

The local development hostname is `development.argus.com`. Core owns the shared infrastructure and service projects remain independently runnable under their own ports while integration conventions are established.
