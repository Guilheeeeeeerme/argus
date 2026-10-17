# Intelligence routing (Argus)

Canonical cross-app contract: infra [`docs/intelligence-routing.md`](../../infra/docs/intelligence-routing.md).
Concept map: [ai-engineering.md](./ai-engineering.md).

| Need | Owner |
| --- | --- |
| Multimodal PromptSet eval (frames → structured hits) | **Gemini VLM** (`gemini-3.1-flash-lite` via Headroom) |
| Post-VLM publish / discard / review | **JEV Choice** on compact text state (`JEV_VERIFY_MODE=active`) |
| Feedback embeddings | Gemini `gemini-embedding-001` |
| Edge motion / YOLO / consensus weights | Code (classical CV) |

## Cascade

```
Gemini VLM once (frames inlined)
  → optional edge consensus
  → JEV Choice {publish, discard, review} on {summary, prompt_hits, scores}
  → low JEV confidence → passthrough (keep Gemini/code path)
  → discard → negative_discard (no TriageCase)
```

Never dual-bill vision. JEV images / Box stay lab-only until TypeSafe marks them production-ready.

## Modes

`JEV_VERIFY_MODE` ∈ `off | shadow | active`. Unset → `active` with `JEV_API_KEY`, else `off`.
`shadow` logs compare only (double spend) — holdout only; never leave prod on `shadow`.

Panel secret: `ARGUS_JEV_API_KEY` → `JEV_API_KEY` (never reuse Quizzeira/PromptDesk keys).
Code: `services/prompt-eval/.../jev_client.py`, `jev_verify.py`.
