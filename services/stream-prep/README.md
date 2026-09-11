# stream-prep

Samples frames from **stream-gateway** (go2rtc), preprocesses them, stores
ephemeral JPEGs in MinIO, and publishes sequences on Redis `frames:ready`.

See [`docs/services/stream-prep.md`](../../docs/services/stream-prep.md) for
the handoff spec and AI engineering module map.
