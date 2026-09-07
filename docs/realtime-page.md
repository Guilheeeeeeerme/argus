# Realtime page (triage) — UX + implementation spec

> Status: **UI spec, not implemented.** The current triage workspace already
> streams `decision.state_changed` over WS and refetches the feed; this
> document specifies the realtime page upgrade. Any agent can implement from
> this. Related: `decision-engine.md`, `docs/SPEC.md`.

## Goal

An always-on operator screen: the **main area** shows the currently focused
event (evidence snapshots, detections, rules matched, resolve controls); the
**far right** has a narrow rail listing flagged events as they arrive.

## Layout

```
┌─────────────────────────────────────────────┬──────────────┐
│  Header (ARGUS Triage · company · location) │  Event rail  │
│                                             │  (narrow)    │
│   Main focus area:                          ├──────────────┤
│   - evidence snapshot(s)                    │  ⚠ 14:02:11  │
│   - detection class + confidence            │  🔴 x3 shop  │
│   - matched rule(s) + regions highlighted   │──────────────│
│   - resolve controls (disposition, reason)  │  🟡 14:01:40 │
│                                             │  🟡 x1 exit  │
│                                             │──────────────│
│                                             │  🔵 13:58:02 │
│                                             │  🔵 x2 shelf │
└─────────────────────────────────────────────┴──────────────┘
```

## Event rail (right side, narrow column)

Each row (newest first):

1. **Timestamp** — `HH:mm:ss` of the latest evidence (`last_evidence_at`).
2. **Severity icon** — maps `decision.state` (+ cumulative severity):
   - `normal` → 🔵 (or grey dot)
   - `weird` → 🟡
   - `warning` → 🔴
   - `resolved_*` → ✅ (muted)
   Use the design-system `<Badge variant=...>` colors; icons are
   representative glyphs, not emojis in code (SVG or token-colored dots).
3. **Trigger count** — number of evidences merged into the decision
   (`evidence_count`), e.g. `×3`.
4. **Short label** — camera name or detection_class of the latest evidence.

Row behavior:

- Active row highlighted (token `--border-strong` / accent text).
- Click a row → sets it as the focused event in the main area.
- Rail updates in place: WS `decision.state_changed` → bump/reorder row,
  update icon + count without full refetch (the current code refetches the
  whole feed on every WS message — replace with per-decision patch).

## Auto-follow ("stick to the most recent")

State machine for the focused event (`focus`):

- **FOLLOW** (default): focus = newest decision. On every new decision/evidence
  event, main area switches to it.
- **PINNED**: operator clicked a specific row → focus stays on it. New events
  arrive in the rail only. An "N new" pill appears at the rail top.
- **Return to FOLLOW**: after **IDLE_TIMEOUT without interaction** (default
  **2 minutes**, env `VITE_TRIAGE_IDLE_MS`), focus snaps back to the newest
  decision and the pill clears.

Interactions that count as "interaction": clicking a rail row, resolving a
decision, hovering the main area (resets the idle timer), keyboard nav.

Implementation sketch (existing files):

- `apps/triage/src/pages/TriageWorkspace.tsx`:
  - keep `decisions` list + `selected` state;
  - add `pinnedId: string | null` and `lastActivityAt: number`;
  - WS `onmessage`: on `decision.state_changed` → update the matching row
    in place; if `!pinnedId` → `selected = newest`;
  - idle timer: `useEffect` interval checks `Date.now() - lastActivityAt >
    VITE_TRIAGE_IDLE_MS` → `setPinnedId(null)`.
- `apps/triage/src/pages/DecisionDetail.tsx`: unchanged controls; resolving
  should treat as interaction (reset idle timer).

## Data needs (already available)

- Feed: `GET /v1/companies/{company_id}/decisions` (state, evidence_count,
  cumulative_severity, timestamps).
- Detail: `GET .../decisions/{id}` (evidences incl. `detection_class`,
  `confidence`, `vlm_result.description`, presigned snapshot URLs).
- Live updates: `WS /v1/ws?token=<session>` (`ready`, `heartbeat`,
  `decision.state_changed`), company-scoped rooms; role gate
  manager/operator.

## Styling rules

- Follow `STYLE_GUIDE.md`: tokens only, `<Badge variant={state}>` for states,
  max-width 1100px main grid, rail fixed-width ~200px on the right
  (`position: sticky; top: 0; height: 100vh; overflow-y: auto`).
- New CSS classes: `.argus-triage__rail`, `.argus-rail-row`, `.argus-rail-row--active`,
  `.argus-rail-new-pill` — added to `apps/triage/src/style.css` with tokens.

## Acceptance checks

1. New decision arrives while FOLLOW → main area switches, rail row appears at
   top with icon + count.
2. Click an older row → PINNED: subsequent events do NOT steal focus; "N new"
   pill counts them.
3. Wait 2 minutes without interaction → focus returns to newest, pill clears.
4. Resolve from the main area → row turns resolved icon, stays in rail.
5. WS disconnect → rail shows "reconnecting" hint (existing onclose message).

## Open decisions

- Rail capacity (render last N=50, drop older silently?).
- Sound/haptic on WARNING rows (operator request — later).
- Multi-location operator view: rail grouping per location (needs location
  selector interplay with the active session location).
