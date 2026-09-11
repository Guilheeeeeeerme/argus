# Realtime page (triage) — UX + implementation spec

Near-realtime operator screen for **TriageCase** rows backed by positive
**Detection** records. Related: `docs/SPEC.md`, `docs/services/api.md`,
`docs/services/prompt-eval.md`.

> WS event names for MVP: `detection.created`, `triage.updated` (plus
> `ready` / `heartbeat`). Older `decision.state_changed` naming is retired
> with the Decision / RuleSet model.

## Goal

An always-on operator screen: the **main area** shows the focused triage case
(evidence clip / frame snapshots, prompt hits, confidence, summary, disposition
controls); the **far right** has a narrow rail listing open/recent cases as
they arrive.

## Layout

```
┌─────────────────────────────────────────────┬──────────────┐
│  Header (ARGUS Triage · company · site)     │  Case rail   │
│                                             │  (narrow)    │
│   Main focus area:                          ├──────────────┤
│   - evidence clip / snapshots               │  ⚠ 14:02:11  │
│   - prompt_hits + confidence + summary      │  open · cam  │
│   - disposition controls                    │──────────────│
│     (confirm / dismiss / false_positive)    │  ● 14:01:40  │
│                                             │  confirmed   │
│                                             │──────────────│
│                                             │  ○ 13:58:02  │
│                                             │  dismissed   │
└─────────────────────────────────────────────┴──────────────┘
```

## Case rail (right side, narrow column)

Each row (newest first):

1. **Timestamp** — `HH:mm:ss` of detection / case creation (or last update).
2. **State indicator** — maps `TriageCase` state:
   - `open` → accent / warning treatment
   - `confirmed` → strong positive / attention retained
   - `dismissed` → muted
   - `false_positive` → muted distinct variant
   Use design-system `<Badge variant=...>` colors; icons are token-colored
   dots/glyphs (not emoji in code).
3. **Short label** — camera name or truncated `summary` / primary prompt hit.

Row behavior:

- Active row highlighted (token `--border-strong` / accent text).
- Click a row → sets it as the focused case in the main area.
- Rail updates in place: WS `detection.created` inserts/bumps a row;
  `triage.updated` patches state without a full feed refetch when possible.

## Auto-follow ("stick to the most recent")

State machine for the focused case (`focus`):

- **FOLLOW** (default): focus = newest open (or newest overall) case. On every
  `detection.created`, main area switches to it.
- **PINNED**: operator clicked a specific row → focus stays on it. New cases
  arrive in the rail only. An "N new" pill appears at the rail top.
- **Return to FOLLOW**: after **IDLE_TIMEOUT without interaction** (default
  **2 minutes**, env `VITE_TRIAGE_IDLE_MS`), focus snaps back to the newest
  case and the pill clears.

Interactions that count as "interaction": clicking a rail row, changing
disposition, hovering the main area (resets the idle timer), keyboard nav.

Implementation sketch:

- `apps/triage/src/pages/TriageWorkspace.tsx` (or successor):
  - list of triage cases + `selected` / `pinnedId` / `lastActivityAt`;
  - WS `onmessage`: `detection.created` → prepend/patch; if `!pinnedId` →
    select newest; `triage.updated` → patch matching row;
  - idle timer: clear pin after `VITE_TRIAGE_IDLE_MS`.
- Detail pane: disposition controls write TriageCase state + optional
  Feedback; treat resolve as interaction (reset idle timer).

## Data needs

- Feed: company-scoped triage cases (state, camera, summary, confidence,
  timestamps) — e.g. `GET /v1/companies/{company_id}/triage-cases`.
- Detail: case + linked Detection (`prompt_hits`, clip / snapshot URLs,
  summary).
- Live updates: `WS /v1/ws?token=<session>` — `ready`, `heartbeat`,
  `detection.created`, `triage.updated`; company-scoped rooms; role gate
  manager/operator.

Detection creation is owned by prompt-eval (positive only); the API exposes
reads and fan-out. See Redis `detections:positive` in `docs/SPEC.md`.

## Styling rules

- Follow `STYLE_GUIDE.md`: tokens only, badges for TriageCase states,
  max-width 1100px main grid, rail fixed-width ~200px on the right
  (`position: sticky; top: 0; height: 100vh; overflow-y: auto`).
- Prefer classes such as `.argus-triage__rail`, `.argus-rail-row`,
  `.argus-rail-row--active`, `.argus-rail-new-pill` with design tokens.

## Acceptance checks

1. New detection arrives while FOLLOW → main area switches; rail row appears
   at top as `open`.
2. Click an older row → PINNED: subsequent `detection.created` events do not
   steal focus; "N new" pill counts them.
3. Wait 2 minutes without interaction → focus returns to newest, pill clears.
4. Confirm / dismiss / mark false_positive from the main area → rail row
   updates via `triage.updated`, stays in rail.
5. WS disconnect → rail shows reconnecting hint.

## Open decisions

- Rail capacity (render last N=50, drop older silently?).
- Sound/haptic on new `open` cases (operator request — later).
- Multi-establishment operator view: rail grouping per establishment (needs
  session establishment interplay).
