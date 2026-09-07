# MFE sketch: sketch-editor (drawing canvas)

> Status: **NOT IMPLEMENTED — handoff spec.** Decision recorded: the drawing/
> sketch editor becomes its own MFE so heavy canvas dependencies stay out of
> the admin and triage apps, and it can be embedded elsewhere later.
> Related: `docs/services/stream-to-image.md` (camera stream config),
> `README.md` ("Adding another MFE"), `docs/SPEC.md`.

## Why a separate MFE

- Canvas libraries (tldraw / fabric.js / konva) are heavy — admin and triage
  stay simple CRUD/operations bundles.
- Independent release cadence for a fast-moving editor surface.
- Embeddable: admin Location plan today; customer portals or agent-side tools
  later via iframe + postMessage.

## Product behavior

- Open a Location's sketch: upload/import an image or SVG floor plan, or draw
  one on a blank canvas (shapes, walls, zones).
- Place + drag Cameras on the sketch; each camera keeps its `{placement_x,
  placement_y}` (0..1 normalized) — same contract as today's inline editor.
- Draw RegionOfInterest polygons per camera (the "drawing over snapshots"
  rule-authoring surface can reuse this canvas in a later iteration).
- Save: `PUT /v1/companies/{id}/locations/{id}/sketch` and
  `PATCH /v1/companies/{id}/cameras/{id}` (existing endpoints; no backend
  changes required for MVP).

## Integration contract

- Served as its own Vite app (suggest port `:8182`), registered in compose on
  `argus_dmz`, added to `SSO_RETURN_ORIGINS` / `VITE_SSO_RETURN_ORIGINS`.
- Bootstrap identical to triage: `consumeTokenFromUrl()` → else
  `redirectToLogin(MAIN_ORIGIN)`; then `loadSession()`; requires
  manager+ (platform or company manager) to save.
- Entry deep link: `/sketch?locationId=<uuid>`; reads query param, fetches the
  location + its cameras.
- **Embed protocol** (for future iframe embedding):
  - Host (admin Location page or external portal) embeds
    `<iframe src="{SKETCH_ORIGIN}/sketch?locationId=...">`.
  - Editor posts messages to `window.parent` on save:
    `{ type: 'sketch:saved', locationId, cameras: [{id, placement_x, placement_y}] }`.
  - Host may post `{ type: 'sketch:reload' }` to force a refetch.
  - Origin checks on both sides (postMessage target origin must be
    allowlisted — reuse the `SSO_RETURN_ORIGINS` list).

## Admin-side fallback (today)

The inline `LocationSketch` component in
`apps/admin/src/pages/Locations.tsx` remains the fallback editor until this
MFE lands. When the MFE is live, swap the "Plan" button to either a deep link
or an iframe embed (same token handoff). Keep the fallback for degraded
networking/embedding failures.

## Runbook (start / resume)

1. `apps/sketch` Vite app (React 19), port 8182, `@shared/auth` alias +
   `@argus/design-system` (tokens for chrome, canvas for the plan area).
2. Canvas library choice — recommend **tldraw** (JSON export maps well to
   `sketch` TEXT column; SVG/image export for `sketch` upload). Alternative:
   konva if bundle size is the priority.
3. Wire compose service + CORS origin + SSO origins.
4. Implement save via existing endpoints (above). No API changes.
5. Acceptance: place/drag a camera, save, reload — placements persist; embed
   the app in admin via iframe and receive `sketch:saved` postMessage.

## Open decisions

- Sketch storage: TEXT column (current) vs MinIO object + URL (better for big
  files; presigned URLs already exist) — decide before large floor plans.
- Whether RegionOfInterest authoring moves into this MFE (likely yes, phase 2).
- Multi-floor locations (one location, several sketches) — not modeled yet.
