# Realtime page (triage) — UX + implementation spec

Near-realtime operator screen for **TriageCase** rows backed by positive
**Detection** records. Related: `docs/SPEC.md`, `docs/services/api.md`,
`docs/services/prompt-eval.md`.

> WS event names for MVP: `detection.created`, `triage.updated` (plus
> `ready` / `heartbeat`). Older `decision.state_changed` naming is retired
> with the Decision / RuleSet model.

## Goal

An always-on operator screen for one **Unidade**: the **main area** is a grid
with every camera of the unit (latest frame, refreshed ~2 s); the camera that
produced the newest open detection is highlighted. The **right rail** lists
open/recent cases as they arrive. Clicking a tile or a rail row opens the case
in a **Drawer** (evidence clip, prompt hits, confidence, summary, disposition
controls); the grid stays mounted behind it.

## Layout

```
┌─────────────────────────────────────────────┬──────────────┐
│  Header (ARGUS · Triagem · Conta · Unidade) │  Case rail   │
│  [Unidade ▾]                                │  ● Ao vivo   │
│  ┌────────┐ ┌────────┐ ┌────────┐           │  [3 novos]   │
│  │ cam 1  │ │ cam 2 ⚠│ │ cam 3  │           ├──────────────┤
│  │ Ao vivo│ │ Ao vivo│ │Sem sinal│          │  14:02:11    │
│  └────────┘ └────────┘ └────────┘           │  open · cam 2│
│  ┌────────┐ ┌────────┐                      │──────────────│
│  │ cam 4  │ │ cam 5  │                      │  14:01:40    │
│  └────────┘ └────────┘                      │  confirmed   │
└─────────────────────────────────────────────┴──────────────┘
          ⚠ = ring in --color-open on the camera of the newest open case
```

## Camera grid

- `GET /v1/accounts/{c}/units/{e}/cameras/overview` → tiles
  (`name`, `is_active`, `last_frame_at`, `open_case_count`).
- Each tile polls `GET /v1/accounts/{c}/cameras/{cam}/latest-frame` every
  `VITE_LATEST_FRAME_MS` (2000) with `If-None-Match`; `304` keeps the current
  blob, `404`/stale (`VITE_LATEST_FRAME_TTL_MS`, 30 000) shows **Sem sinal**.
  Polling pauses while the tab is hidden. Both paths are exempt from the API
  rate limit. The browser never talks to MinIO or go2rtc.
- Tile = `<button>`: image/placeholder, name, `Status` Ao vivo/Sem sinal,
  `Badge` with open cases. `--alert` modifier (ring in `--color-open`, pulse
  ≤200 ms, off under `prefers-reduced-motion`) marks the camera of the newest
  open case; `--focused` marks the camera of the case open in the drawer.
- Clicking a tile pins the newest open case of that camera (or the newest
  case of any state); with none, a toast says so.

## Case rail (right side, narrow column)

Each row (newest first, capacity 50):

1. **Timestamp** — `HH:mm:ss` of `detection.created_at` (fallback `updated_at`).
2. **State** — `<Badge variant={badgeVariantForTriageState(state)}>`.
3. **Label** — `camera_name` (from the API or the overview map), else summary.

The rail head shows the WebSocket `Status` (Conectando… / Ao vivo /
Reconectando… / Desconectado) and, in PINNED mode, an "N novos" pill that
returns to FOLLOW when clicked.

## Auto-follow ("stick to the most recent")

Pure reducer in `apps/triage/src/feed.ts` (`caseFeedReducer`, tested with
vitest):

- **FOLLOW** (default): focus = newest open case; every `detection.created`
  for this unit opens it in the drawer.
- **PINNED**: the operator clicked a row/tile (or closed the drawer). New
  cases only increment `newCount`; duplicates (at-least-once stream) do not.
- **idle** → FOLLOW after `VITE_TRIAGE_IDLE_MS` (120 000) without interaction
  (pin, drawer close, pointer/keyboard inside the detail, disposition).
- `triage.updated` patches the row in place; in FOLLOW a resolved focus moves
  to the next open case.

Hooks: `useCaseFeed` (initial `GET /triage-cases?unit_id=&limit=50`,
WS events filtered by `unit_id`, idle timer), `useTriageSocket`
(exponential backoff 1→30 s, stops on close codes 4001/4003),
`useLatestFrame` (ETag poll, blob URL revocation, visibility pause).

## Data needs

- Units: `GET /v1/accounts/{account_id}/units` (operator+);
  `PATCH /v1/auth/context {unitId}` selects the unit.
- Feed: `GET /v1/accounts/{account_id}/triage-cases?unit_id=&camera_id=&limit=`
  (state, camera_name, unit_name, summary, confidence, timestamps).
- Detail: case + linked Detection (`prompt_hits`, clip / snapshot URLs,
  summary).
- Live updates: `WS /v1/ws?token=<session>` — `ready`, `heartbeat`,
  `detection.created` (payload carries `unit_id`, `camera_id`,
  `sequence_id`, `state`, `created_at`, `summary`, `confidence`,
  `prompt_hits`), `triage.updated`; account-scoped rooms, filtered per unit
  on the client; role gate manager/operator.

Detection creation is owned by prompt-eval (positive only); the API exposes
reads and fan-out. See Redis `detections:positive` in `docs/SPEC.md`.

## Styling rules

- Follow `STYLE_GUIDE.md`: tokens only, badges for TriageCase states, grid
  `repeat(auto-fill, minmax(16rem, 1fr))`, rail 17rem sticky on the right
  (`max-height: calc(100dvh - …); overflow-y: auto`), single column below 64rem.
- Classes: `.argus-cam-grid`, `.argus-cam-tile[--alert|--focused]`,
  `.argus-rail`, `.argus-rail-row[--active]`, `.argus-rail__pill`.

## Acceptance checks

1. 12 tiles refresh every ~2 s without a 429; stopping stream-prep turns
   tiles into "Sem sinal" after the TTL.
2. New detection arrives while FOLLOW → its camera gets the ring, a rail row
   appears at top as `open`, the drawer opens on it.
3. Click an older row → PINNED: subsequent `detection.created` events do not
   steal focus; "N novos" pill counts them; clicking the pill returns to FOLLOW.
4. Wait 2 minutes without interaction → focus returns to newest, pill clears.
5. Confirm / dismiss / false_positive from the drawer → toast, rail row updates,
   drawer closes, tile count drops.
6. Restart the API → rail shows "Reconectando…" then "Ao vivo".

## Open decisions

- Sound/haptic on new `open` cases (operator request — later).
- Per-frame evidence (`frame_uris`) is no longer exposed to the client; an
  authenticated per-frame proxy is a follow-up.
