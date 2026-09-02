# ARGUS

**Continuous vigilance. Simultaneous attention.**

> *Surveillance that never looks away.*

## About

ARGUS is a project built around the idea of **watching many things at once** — detecting change and threat without abandoning what is already under protection.

Named after **Argos Panoptes** (Ἄργος Πανόπτης), the many-eyed sentinel of Greek mythology: some of his eyes always remained open while others rested. ARGUS carries that spirit into software — persistent, layered observation that does not blink when attention is needed elsewhere.

## Concept

At its core, ARGUS represents the ability to:

- **Observe multiple points simultaneously**
- **Detect changes and threats** as they emerge
- **Stay committed to what is already protected** while scanning the horizon

It is, in mythological terms, the principle of *one eye on the fish, one on the cat*: protection is not only about guarding what you hold — it is also about keeping watch on what might threaten it.

## Status

Development MVP in progress. The backend MVP slices, local mock event/notification
flow, hot-reload React surfaces, shared `.env`, and HTTPS development gateway are
present in the working tree. Run the development instructions in
`docs/development-network.md` and `specs/001-saas-mvp/quickstart.md`.

The monorepo mirrors the future Core Admin, platform-services, and MFE
repository boundaries. Plain `docker compose up --build` starts Core Admin;
use `docker compose --profile platform --profile mfe up --build` for the full
pipeline.

## Project handoff

Start each development interaction with [START_HERE.md](START_HERE.md). The
evidence-based documentation and delivery audit is in
[DOCUMENTATION_AUDIT.md](DOCUMENTATION_AUDIT.md).

## License

TBD
