# Edge Fusion Implementation Plan

> Execution: dispatching-parallel-agents; independent file ownership, followed by integration review.

**Goal:** Implement the supplied Edge Fusion design in an isolated worktree and open a PR.

**Architecture:** Keep go2rtc, stream-prep, Redis Streams, and existing product entities. Add an opt-in CPU edge cascade and a sensor-aware consensus gate inside prompt-eval. Rollback selects frames:ready using EDGE_CV_ENABLED=false.

**Tech stack:** Python, OpenCV, YOLOv8n, Redis Streams, MinIO, existing Gemini provider adapter.

**Spec:** docs/edge-fusion-architecture.md (based on the supplied architectural brief).

## Constraints

- Local Compose only; production deployment remains infra-owned.
- Tenant and camera isolation; no raw prompts or frames in logs.
- No Agent entity, MQTT, on-prem fleet, continuous embedding bank, or production Auth0.
- Targeted mocked tests; no GPU/provider credentials needed for unit validation.

## Tasks and ownership

- [x] Sensor contracts: extend API webhook schema and published fields; add dependency-free argus.services.sensor_fusion.SensorFusionBuffer; register stream groups. Tests cover compatibility, validation, tenant/camera scope, ±5-second matching and bounded storage.
- [x] Edge worker: services/edge-cv only. Consume existing frames:ready windows and context:events; motion, allowed-class tracking, novelty selection; emit candidates:ready. Test synthetic frames with injected detector, malformed input and worker delivery behavior.
- [x] Prompt consensus: services/prompt-eval only. Add ConsensusEngine; flag-select candidates stream; select one frame and fence structural context; retain negative discard and legacy path. Test veto, thresholds, malformed output and stream routing.
- [x] Integration: local Compose and .env.example; per-frame captured_at in preproc_meta for accurate fusion; architecture and SPEC contracts. Add Compose and capture-time contract tests before edits.
- [x] Review: inspect all diffs and resolve producer/consumer mismatches. Run affected Python tests and Compose configuration validation; inspect dependency/build feasibility. Commit, push and create PR with evidence and limitations.

## Shared contracts

SensorFusionBuffer(window_seconds=5).add(event: dict); match(company_id=..., establishment_id=..., camera_id=..., timestamp=...) returns scoped sensor dictionaries.

Candidates preserve company_id, establishment_id, camera_id, sequence_id, captured_at, frame_uris and preproc_meta. JSON fields add tracks, sensors, sensor_ids; scalar fields add edge_score, motion_score and temporal_span_seconds. frame_uris contains at most three ranked keyframes; prompt-eval sends one.

## Validation commands

Use the existing API Python environment with PYTHONPATH including the worktree API and relevant service src directories. Run each agent's focused tests, apps/api/tests/test_compose_contract.py, and the prompt-eval regression tests. Run docker compose --env-file .env.example config --quiet. No production rollout is part of this PR.

## Verification evidence

- Focused host suite: 101 passed, 3 runtime skips, 4 subtests passed.
- CPU Docker image built with host networking after default build-network DNS failed.
- Offline image tests: 20 passed, no skips; actual ByteTrack and ResNet interfaces exercised without pretrained downloads.
- Targeted Ruff, Compose configuration and whitespace checks passed.
- Independent review resolved timestamp alignment, chronological evidence, historical replay sampling/tracking and expired-object handling. Live provider/camera accuracy and a full DB-backed deployment are not validated here.
