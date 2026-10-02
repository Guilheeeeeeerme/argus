# Skill: argus-ui-workflow

Use this skill when discussing UI changes or generating frontend code for the ARGUS platform
(`apps/admin`, `apps/triage`, `packages/ui`).

## When to Use

- User wants to add, modify, or discuss UI features
- User asks about styling, theming, or component choices
- Generating new React components for admin or triage apps
- Refactoring existing UI code

## Two Modes

### 1. UI Feature Discussion

1. **Understand the context** — which app (admin or triage), which role (root/admin/manager/operator)
2. **Identify affected components** — reuse `@argus/design-system` before adding anything to `packages/ui`
3. **Propose design** — describe the change using existing tokens and components
4. **Confirm before implementing** — present design, wait for approval

### 2. Code Generation

1. **Import from `@argus/design-system`** — never raw HTML for interactive controls
2. **Tokens only** — `var(--bg-surface)`, never hex; app CSS holds page layout only
3. **Every control has a label** — `Input`/`Select`/`Textarea` `label` prop, `Switch` `label`
4. **Async states are explicit** — see table below; no list may show `EmptyState` while loading
5. **Mutations never double-submit** — `Button loading`, `Form busy`, `AlertDialog busy`
6. **Copy is pt-BR through `useT()`** — keys are the Portuguese text; add the `en` entry in `packages/i18n/src/dictionary.ts`
7. **Domain labels** — say *Conta* / *Unidade* in UI copy even where code identifiers still read `account` / `unit`
8. **Reference `STYLE_GUIDE.md`** at the repo root for the full rule list

## Component Reference

```tsx
import {
  ThemeProvider, ThemeToggle, LocaleToggle, UserMenu,
  AppShell, Sidenav, PageHeader, Tabs, TabPanel, Status,
  Button, Spinner, Input, Select, Textarea, Switch,
  Form, FormField, FormActions, FormError,
  Card, Badge, badgeVariantForTriageState, ListRow, Message,
  EmptyState, Skeleton, ListSkeleton, GridSkeleton, FormSkeleton,
  AlertDialog, Dialog, Drawer, ToastProvider, useToast,
} from '@argus/design-system';
```

Shared app helpers:

- `@shared/auth` — `apiFetch<T>()`, `ApiError` (`status`, `detail`, `fieldErrors`), token helpers, `Session`
- `@shared/hooks` — `useAsync(fn, deps)` → `{ data, loading, error, reload }`; `useMutation(fn)` → `{ run, pending, error }`
- `@argus/i18n` — `useT()`, `localizeApiError(error, t)`, `roleLabel`, `triageStateLabel`

## Async state table

| Situation | Render |
|-----------|--------|
| List fetching | `<ListSkeleton rows={4} />` |
| Grid fetching | `<GridSkeleton />` |
| Edit form loading its record | `<FormSkeleton />` |
| Empty result | `<EmptyState title description action>` |
| Submit pending | `<Button type="submit" loading={m.pending}>` inside `<Form busy={m.pending}>` |
| Toggle pending | `<Switch loading>` |
| Delete pending | `<AlertDialog busy={m.pending}>` — close only after the promise settles |
| Success / failure | `useToast().success(t('…'))` / `.error(localizeApiError(err, t))` |
| Field validation | `error` prop on the control (from `ApiError.fieldErrors` or local checks) |

## Token Reference

- Surface: `--bg-page`, `--bg-surface`, `--bg-overlay`, `--bg-input`, `--hover-secondary`
- Text: `--text-primary`, `--text-secondary`, `--text-muted`, `--text-accent`
- Triage: `--color-open`, `--color-confirmed`, `--color-dismissed`, `--color-false-positive`
- Action: `--color-primary`, `--color-danger`, `--color-focus`
- Spacing: `--space-1` (4px) … `--space-8`; default gap `--gap` (5px)
- Radius: `--radius-sm` / `--radius-md` (6px), `--radius-lg` (8px)

## App Layouts

### Admin (router + shell)

```tsx
<AppShell brand="ARGUS" meta={t('Administração')} actions={<ThemeToggle /> /* + UserMenu */}
  sidebar={<Sidenav subtitle={t('Administração')}>{/* Conta/Unidade Selects + nav */}</Sidenav>}>
  <Outlet />   {/* react-router pages: PageHeader + Card/ListRow + Drawer forms */}
</AppShell>
```

Pages live in `apps/admin/src/routes/*`, forms in `apps/admin/src/components/forms/*`,
typed API in `apps/admin/src/api/`. Create/edit are URL-addressable (`/units/new`, `/units/:id/edit`).

### Triage (grid + rail)

```tsx
<AppShell brand="ARGUS" meta={t('Triagem')} wide>
  <CameraGrid />   {/* tiles; alert ring on the camera that fired */}
  <CaseRail />     {/* sticky list; FOLLOW / PINNED per docs/realtime-page.md */}
  <Drawer>{/* TriageDetail */}</Drawer>
</AppShell>
```

## Common Patterns

### CRUD list page

```tsx
const units = useAsync(() => listUnits(accountId), [accountId]);
const remove = useMutation(deleteUnit);

<PageHeader title={t('Unidades')} actions={<Button onClick={() => navigate('new')}>{t('Nova unidade')}</Button>} />
<Card>
  {units.loading ? <ListSkeleton /> : units.error ? <FormError message={localizeApiError(units.error, t)} />
    : units.data.length === 0 ? <EmptyState title={t('Nenhuma unidade ainda')} action={…} />
    : units.data.map(unit => <ListRow key={unit.id} title={unit.name} meta={unit.timezone} actions={…} />)}
</Card>
<AlertDialog open={!!pending} busy={remove.pending} … onConfirm={async () => { await remove.run(pending.id); setPending(null); units.reload(); }} />
```

### Drawer form (create or edit)

```tsx
<Drawer open title={unit ? t('Editar unidade') : t('Nova unidade')} busy={save.pending} onClose={close}
  footer={<>
    <Button variant="ghost" onClick={close} disabled={save.pending}>{t('Cancelar')}</Button>
    <Button type="submit" form="unit-form" loading={save.pending}>{t('Salvar')}</Button>
  </>}>
  {loadingRecord ? <FormSkeleton /> : (
    <Form id="unit-form" busy={save.pending} onSubmit={submit}>
      <FormError message={formError} />
      <Input label={t('Nome')} value={name} error={fieldErrors.name} onChange={e => setName(e.target.value)} required />
      <Select label={t('Fuso horário')} value={tz} options={TIMEZONES} onChange={…} />
    </Form>
  )}
</Drawer>
```
