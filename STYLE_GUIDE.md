# ARGUS UI Style Guide

Linear-inspired design system for Argus admin and triage frontends.
Dark mode is first-class (`#080A0A` page base, Inter, 4px grid).
Import from `@argus/design-system` only.

## Mandatory Rules

1. **Import from `@argus/design-system`** — never inline hex colors or ad-hoc CSS variables
2. **Use CSS custom properties** — `var(--bg-page)`, `var(--surface-base)`, never raw `#172235`
3. **Use shared components** — `<Button>`, `<Card>`, `<Badge>`, `<AlertDialog>`; never `window.confirm`
4. **Theme via tokens** — never hardcode dark/light colors in apps
5. **All inputs must have labels** — use `<Input label="…"/>` or `<Select label="…"/>`
6. **Semantic HTML** — `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`
7. **State colors via Badge** — `<Badge variant={badgeVariantForTriageState(state)}>`
8. **Layout** — prefer `<AppShell>`; content max-width via `--content-max`
9. **Typography** — Inter only (`var(--font-family)`); `text-wrap: balance` on headings, `pretty` on body
10. **No inline styles** — except dynamic geometry (width/height for skeletons)
11. **Focus** — never remove focus rings; `2px` `#5E6AD2` outline + `2px` offset (`--outline-*`)
12. **Destructive actions** — must use `<AlertDialog>`
13. **Icon-only buttons** — must have `aria-label`
14. **Viewport height** — use `100dvh`, never `100vh` / `h-screen`
15. **Motion** — respect `prefers-reduced-motion`; animate only `transform`/`opacity`; ≤200ms feedback
16. **App CSS** — page layouts only (`apps/*/src/style.css`); primitives stay in `packages/ui`

## Tokens

| Category | Token | Notes |
|----------|-------|-------|
| Surface | `--bg-page` / `--surface-base` | `#080A0A` dark base |
| Surface | `--bg-surface` / `--surface-raised` | Cards / raised |
| Surface | `--bg-overlay` / `--surface-overlay` | Dialogs / menus |
| Surface | `--bg-input` / `--bg-hover` | Controls & hover (light hover `#D2D2D3`) |
| Border | `--border` / `--border-default` | 1px separators |
| Text | `--text-primary` (`#E2E4E3`) / `--text-secondary` / `--text-muted` | AA contrast |
| Triage | `--color-open` / `--confirmed` / `--dismissed` / `--false-positive` | Case states |
| Action | `--color-primary` (`#5E6AD2`) / `--color-danger` | Linear accent |
| Focus | `--color-focus`, `--outline-width/offset` (2px) | Focus ring |
| Spacing | `--space-1`…`--space-8` (4px grid) | Default gap `--space-1` (4px) / `--space-2` (8px) |
| Radius | `--radius-sm/md` = 6px, `--radius-lg` = 8px | |
| Type | Inter 400/500/700; display 60px; body ~15–17px | |

## Components

```tsx
import {
  ThemeProvider, ThemeToggle, useTheme,
  AppShell, Header, Sidenav, Status,
  Button,      // primary|secondary|danger|ghost · sm|md
  Input, Select, Textarea,
  Card, Badge, badgeVariantForTriageState, ListRow, Message,
  EmptyState, Skeleton,
  AlertDialog, Dialog,
  LocaleToggle,
} from '@argus/design-system';
```

### Badge variants (MVP)

| Variant | Use |
|---------|-----|
| `open` | TriageCase open |
| `confirmed` | TriageCase confirmed |
| `dismissed` / `neutral` | Dismissed / inactive |
| `false_positive` | FP disposition |
| `normal` | Enabled / healthy |
| `warning` | Legacy / alerts |

```tsx
<Badge variant={badgeVariantForTriageState(case.state)}>{case.state}</Badge>
```

## Patterns

```tsx
<AppShell brand="ARGUS" meta={t('Administration')} actions={<ThemeToggle />}>
  <Sidenav>{/* context switchers */}</Sidenav>
  <Card>
    <h2>{t('Companies')}</h2>
    <ListRow title={…} meta={…} actions={…} />
    <EmptyState title={…} description={…} />
  </Card>
</AppShell>

<AlertDialog
  open={open}
  title={t('Delete company')}
  description={t('Delete {name}? This cannot be undone.', { name })}
  confirmLabel={t('Delete')}
  cancelLabel={t('Cancel')}
  onConfirm={…}
  onCancel={…}
/>
```

## Do / Don't

| Do | Don't |
|----|-------|
| `<Button variant="primary">` | Inline `#5E6AD2` backgrounds |
| `color: var(--text-primary)` | Hardcoded slate palette leftovers |
| `<AlertDialog>` for delete | `window.confirm` |
| `<Dialog>` + `<Input>` for rename | `window.prompt` |
| `min-height: 100dvh` | `100vh` / `h-screen` |
| Inter via design tokens | system-ui / emoji theme toggles |
| `var(--border-width)` | Raw `1px` in app CSS |
| `badgeVariantForTriageState` | Local switch mapping Decision states |
