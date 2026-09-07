# `@argus/design-system`

Shared Argus design tokens, styles, and React components (`packages/ui`).

Consumed workspace-locally via vite aliases in both apps — no npm publishing:

```ts
// apps/*/vite.config.ts
{ find: /^@argus\/design-system$/, replacement: '<repo>/packages/ui/src/index.ts' }
{ find: '@argus/design-system/tokens.css', replacement: '<repo>/packages/ui/src/tokens.css' }
{ find: '@argus/design-system/global.css', replacement: '<repo>/packages/ui/src/global.css' }
```

Rules and token reference: see `STYLE_GUIDE.md` at the repo root.
