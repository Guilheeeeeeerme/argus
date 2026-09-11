# stream-gateway

go2rtc restream sidecar plus a lightweight config-sync loop.

- `go2rtc.yaml` — base go2rtc config (API :1984, RTSP :8554)
- `sync.py` — polls `GET /v1/internal/stream-configs` and registers streams

Compose services: `stream-gateway`, `stream-gateway-sync`.
