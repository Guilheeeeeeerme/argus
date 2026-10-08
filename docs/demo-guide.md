# MVP demo

The MVP uses administrator-created accounts; public signup is disabled. A user
may have no account memberships or several. After login, the account selector
shows only assigned accounts. A user without assignments sees an empty state.
Platform administrators manage assignments; changing account clears the selected
unit. Tenant access is checked server-side.

Run the reviewed demo seed through infra's **Migrate app** workflow with
`seed_demo=true`, using the deployed release. It creates:

- **Argus Public Camera Demo**: seven camera sites across traffic, beach, and zoo
  topics (three Caltrans + two Beach TV + two San Diego Zoo), one prompt set per
  camera, and two enabled prompts per set.
- **Demo Sandbox**: an empty account for trying camera and prompt management.
- **manager@demo.local**: manager assigned to both demo accounts.
- **guest@demo.local**: operator assigned only to the public-camera account.

New accounts use the protected `DEMO_PASSWORD` setting. Existing passwords and
operator-edited streams/prompts are preserved. The seed never prints credentials.
Local development falls back to the existing local-only demo password.

## Cameras and analysis

Feeds are grouped so detections can be compared within a topic:

| Topic | Cameras | Source |
| --- | --- | --- |
| Traffic | US-101 Broad Street, Monterey Street, Madonna Road (San Luis Obispo) | [Caltrans D5 CCTV](https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json) — [conditions](https://dot.ca.gov/conditions-of-use) |
| Beach | Beach TV Key West & Florida Keys; Beach TV Myrtle Beach | [Beach TV](https://www.beachtv.net/) (TripSmarter HLS) |
| Zoo | San Diego Zoo Platypus Cam; San Diego Zoo Koala Cam | [San Diego Zoo Live Cams](https://zoo.sandiegozoo.org/live-cameras) |

Providers give no availability guarantee; cameras and tourism channels may go
offline, show nighttime loops, or (for Beach TV) interleave studio segments with
coastal footage. Prompts fail closed when the scene is not clearly visible.

Gateway sources use stable HLS master URLs through FFmpeg video-copy mode.
Private go2rtc snapshots feed stream-prep, Edge CV, and prompt-eval. Each camera
has two assertive prompts scoped to that scene type (vehicles/queues; people and
shoreline; target animals and people near the habitat). Prompts avoid inferring
speed, identity, intent, or duration from a single image.

Select the public-camera account and a unit to manage its camera, prompt set,
and prompts. Open triage to inspect real positive detections and their retained
evidence; observations are not proof of an incident. No fake detections are
inserted by the seed. Existing provider quotas still apply. Night glare, HLS
latency, camera outages, and the vehicle-detection gate affect how often a
candidate reaches the language model.

The gateway has no public control port. Source pages remain the operator's
public viewing option; retained analysis evidence is available through Argus.

Evidence clips are fetched through the authenticated, account-scoped API; browser playback does not require a public object-storage host.
