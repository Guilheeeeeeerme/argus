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
17. **Loading lists** — a list that is fetching renders `<ListSkeleton>` (grid: `<GridSkeleton>`, edit form: `<FormSkeleton>`); never `<EmptyState>` while loading
18. **Mutations** — every create/update/delete button uses `<Button loading>`; `<AlertDialog busy>` keeps the dialog open until the request resolves; no double submit
19. **Feedback** — success and transient errors go through `useToast()`; field errors go to the control's `error` prop; form-level errors to `<FormError>`. `<Message>` is for persistent inline notices only
20. **Create vs edit** — forms open in `<Drawer>` with an explicit title (`Nova unidade` / `Editar unidade`), submit via `<Form onSubmit>` (Enter works), and are addressable by URL

## Tokens

| Category | Token | Notes |
|----------|-------|-------|
| Surface | `--bg-page` / `--surface-base` | `#080A0A` dark base |
| Surface | `--bg-surface` / `--surface-raised` | Cards / raised |
| Surface | `--bg-overlay` / `--surface-overlay` | Dialogs / menus |
| Surface | `--bg-input` / `--hover-secondary` | Controls; list/secondary hover `#D2D2D3` |
| Border | `--border` / `--border-default` | 1px separators |
| Text | `--text-primary` (`#E2E4E3` dark) / `--text-secondary` / `--text-muted` | AA contrast |
| Triage | `--color-open` / `--confirmed` / `--dismissed` / `--false-positive` | Case states |
| Action | `--color-primary` (`#5E6AD2`) / `--color-danger` | Linear accent |
| Focus | `--color-focus`, `--outline-width/offset` (2px) | Focus ring |
| Spacing | `--space-*` (4px grid) + `--gap` (5px default) | Prefer 5/11/12/13/14/16/19/20 |
| Radius | `--radius-sm/md` = 6px, `--radius-lg` = 8px | |
| Type | Inter 400/500/700; heading-1 60px; body 17px | |

## Components

```tsx
import {
  ThemeProvider, ThemeToggle, useTheme,
  AppShell, Header, Sidenav, PageHeader, Tabs, TabPanel, Status,
  Button, Spinner,          // Button: primary|secondary|danger|ghost · sm|md · loading
  Input, Select, Textarea, Switch,
  Form, FormField, FormActions, FormError,
  Card, Badge, badgeVariantForTriageState, ListRow, Message,
  EmptyState, Skeleton, ListSkeleton, GridSkeleton, FormSkeleton,
  AlertDialog, Dialog, Drawer,
  ToastProvider, useToast,
  LocaleToggle, UserMenu,
} from '@argus/design-system';
```

### Async states

| State | Component |
|-------|-----------|
| List / grid / form loading | `ListSkeleton` / `GridSkeleton` / `FormSkeleton` |
| Button mutation pending | `<Button loading>` (disabled + `aria-busy` + spinner) |
| Toggle pending | `<Switch loading>` |
| Delete pending | `<AlertDialog busy>` (confirm spins, cancel/Escape locked) |
| Drawer form pending | `<Form busy>` + `<Drawer busy>` |
| Outcome | `useToast().success(…)` / `.error(…)`; field error → `error` prop |

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
  busy={remove.pending}
  title={t('Excluir unidade')}
  description={t('Excluir {name}? Essa ação não pode ser desfeita.', { name })}
  confirmLabel={t('Excluir')}
  cancelLabel={t('Cancelar')}
  onConfirm={() => remove.run(id)}      // dialog closes only after the response
  onCancel={…}
/>

// List page: skeleton → empty → rows
{units.loading ? <ListSkeleton /> : units.data.length === 0
  ? <EmptyState title={…} action={<Button onClick={openCreate}>{t('Nova unidade')}</Button>} />
  : units.data.map(u => <ListRow key={u.id} title={u.name} actions={…} />)}

// Create / edit in a Drawer
<Drawer open title={editing ? t('Editar unidade') : t('Nova unidade')} busy={save.pending} onClose={close}
  footer={<><Button variant="ghost" form="unit-form" onClick={close}>{t('Cancelar')}</Button>
           <Button type="submit" form="unit-form" loading={save.pending}>{t('Salvar')}</Button></>}>
  <Form id="unit-form" busy={save.pending} onSubmit={submit}>
    <Input label={t('Nome')} value={name} error={errors.name} onChange={…} required />
  </Form>
</Drawer>
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
| `<ListSkeleton>` while fetching | `<EmptyState>` before data arrives |
| `<Button loading>` on submit | `disabled={submitting}` with no feedback |
| `useToast().success()` | Persistent `<Message>` per card |
| `<Drawer>` with `Nova…`/`Editar…` title | Always-visible inline create form |
