# MVP demo

The MVP uses administrator-created accounts; public signup is disabled. A user
may have no company memberships or several. After login, the company selector
shows only assigned companies. A user without assignments sees an empty state.
Platform administrators manage assignments; changing company clears the selected
establishment. Tenant access is checked server-side.

Run the reviewed demo seed through infra's **Migrate app** workflow with
`seed_demo=true`, using the deployed release. It creates:

- **Argus Public Camera Demo**: three camera sites, one prompt set per camera,
  and two enabled prompts per set.
- **Demo Sandbox**: an empty company for trying camera and prompt management.
- **manager@demo.local**: manager assigned to both demo companies.
- **guest@demo.local**: operator assigned only to the public-camera company.

New accounts use the protected `DEMO_PASSWORD` setting. Existing passwords and
operator-edited streams/prompts are preserved. The seed never prints credentials.
Local development falls back to the existing local-only demo password.

## Cameras and analysis

The feeds are official Caltrans US-101 cameras at Broad Street, Monterey Street,
and Madonna Road in San Luis Obispo. Sources are advertised in the
[Caltrans CCTV integration dataset](https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json).
Use is subject to [Caltrans conditions](https://dot.ca.gov/conditions-of-use).
Caltrans provides no availability or accuracy guarantee; cameras may go offline.

Gateway sources use stable HLS master URLs through FFmpeg video-copy mode.
Private go2rtc snapshots feed stream-prep, Edge CV, and prompt-eval. The first
prompt on each camera records ordinary visible vehicle activity so the demo can
produce real observations; the second checks a specific queue/obstruction case.
Prompts avoid inferring speed, identity, or duration from a single image.

Select the public-camera company and an establishment to manage its camera,
prompt set, and prompts. Open triage to inspect real positive detections and
their retained evidence; observations are not proof of an incident. No fake
detections are inserted by the seed. Existing provider quotas still apply.
Night glare, HLS latency, camera outages, and the vehicle-detection gate affect
how often a candidate reaches the language model.

The gateway has no public control port. Source pages remain the operator's
public viewing option; retained analysis evidence is available through Argus.
