# ARGUS UI Style Guide

Linear-inspired design system for Argus admin and triage frontends.
Dark mode is first-class. Import from `@argus/design-system` only.

## Mandatory Rules

1. **Import from `@argus/design-system`** — never inline hex colors or ad-hoc CSS variables
2. **Use CSS custom properties** — `var(--bg-surface)`, never `#172235`
3. **Use shared components** — `<Button>`, `<Card>`, `<Badge>`, `<AlertDialog>`, never raw destructive `window.confirm`
4. **Theme via tokens** — never hardcode dark/light colors
5. **All inputs must have labels** — use `<Input label="…"/>` or `<Select label="…"/>`
6. **Semantic HTML** — `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`
7. **State colors via Badge** — `<Badge variant={decision.state}>`
8. **Layout** — prefer `<AppShell>`; content max-width via `--content-max`
9. **Typography** — Inter only (`var(--font-family)`); `text-wrap: balance` on headings
10. **No inline styles** — except dynamic geometry (e.g. sketch marker placement)
11. **Focus** — never remove focus rings; use `2px` `#5E6AD2` outline + `2px` offset
12. **Destructive actions** — must use `<AlertDialog>`
13. **Icon-only buttons** — must have `aria-label`
14. **Viewport height** — use `100dvh`, never `100vh` for full-screen shells
15. **Motion** — respect `prefers-reduced-motion`; animate only `transform`/`opacity`

## Tokens

| Category | Token | Notes |
|----------|-------|-------|
| Surface | `--bg-page` | `#080A0A` dark base |
| Surface | `--bg-surface` | Cards / raised |
| Surface | `--bg-overlay` | Dialogs / menus |
| Surface | `--bg-input` / `--bg-hover` | Controls & hover |
| Border | `--border` / `--border-strong` | 1px separators |
| Text | `--text-primary` / `--text-secondary` / `--text-muted` / `--text-accent` | AA contrast |
| State | `--color-normal` / `--weird` / `--warning` / `--resolved` | Domain states |
| Action | `--color-primary` (`#5E6AD2`) / `--color-danger` | Linear accent |
| Focus | `--color-focus` | Focus ring |
| Spacing | `--space-1`…`--space-8` (4px grid) | Also `--space-xs`…`--space-xl` aliases |
| Radius | `--radius-sm/md` = 6px, `--radius-lg` = 8px | |
| Type | `--font-size-*`, `--font-weight-*` | Inter 400/500/700 |

## Components

```tsx
import {
  ThemeProvider, ThemeToggle, useTheme,
  AppShell, Header, Sidenav, Status,
  Button,      // primary|secondary|danger|ghost · sm|md
  Input, Select, Textarea,
  Card, Badge, ListRow, Message,
  EmptyState, Skeleton,
  AlertDialog, Dialog,
  LocaleToggle,
} from '@argus/design-system';
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
