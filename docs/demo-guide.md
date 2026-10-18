# MVP demo

The MVP uses administrator-created accounts; public signup is disabled. A user
may have no account memberships or several. After login, the account selector
shows only assigned accounts. A user without assignments sees an empty state.
Platform administrators manage assignments; changing account clears the selected
unit. Tenant access is checked server-side.

Run the reviewed demo seed through infra's **Migrate app** workflow with
`seed_demo=true`, using the deployed release. It creates:

- **Argus Demo Brasil**: one account, two estabelecimentos, three cameras each
  under a **monitoramento municipal** story — Distrito Vias (tráfego) and
  Distrito Orla (costa). Streams are verified public HLS feeds named honestly
  after their real scenes (not Brazilian street names on foreign highways).
  One PromptSet per camera with two enabled Portuguese prompts.
- **manager@demo.local**: manager on the demo account.
- **guest@demo.local**: operator on the demo account.

The previous **Demo Sandbox** account and one-camera-per-site layout are removed
on re-seed.

New accounts use the protected `DEMO_PASSWORD` setting. Existing passwords and
operator-edited streams/prompts are preserved unless `DEMO_PASSWORD_SYNC=1` is
set for a one-shot seed (rotates `manager@demo.local` / `guest@demo.local` to
match `DEMO_PASSWORD`). The seed never prints credentials. Local development
falls back to the existing local-only demo password.

## Cameras and analysis

| Estabelecimento | Câmeras | Source |
| --- | --- | --- |
| Distrito Vias — Trânsito | Via 101 Broad / Monterey / Madonna | [Caltrans D5 CCTV](https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json) — [conditions](https://dot.ca.gov/conditions-of-use) |
| Distrito Orla — Costa | Praia Key West, Praia Myrtle Beach, Orla Ballina | [Beach TV](https://www.beachtv.net/) · [CoastalCOMs](https://www.coastalcoms.com/) |

Providers give no availability guarantee; cameras and tourism channels may go
offline, show nighttime loops, or (for Beach TV) interleave studio segments with
coastal footage. Prompts fail closed when the scene is not clearly visible.

Gateway sources use stable HLS master URLs through FFmpeg video-copy mode.
Private go2rtc snapshots feed stream-prep, Edge CV, and prompt-eval. Each camera
has two assertive Portuguese prompts scoped to that scene type. Prompts avoid
inferring speed, identity, intent, or duration from a single image.

Select the demo account and an estabelecimento to manage its cameras, PromptSets,
and prompts. Open triage to inspect real positive detections and their retained
evidence; observations are not proof of an incident. No fake detections are
inserted by the seed. Existing provider quotas still apply. Night glare, HLS
latency, camera outages, and the vehicle-detection gate affect how often a
candidate reaches the language model.

The gateway has no public control port. Source pages remain the operator's
public viewing option; retained analysis evidence is available through Argus.

Evidence clips are fetched through the authenticated, account-scoped API; browser playback does not require a public object-storage host.
