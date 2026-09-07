# Skill: argus-ui-workflow

Use this skill when discussing UI changes or generating frontend code for the ARGUS platform.

## When to Use

- User wants to add, modify, or discuss UI features
- User asks about styling, theming, or component choices
- Generating new React components for admin or triage apps
- Refactoring existing UI code

## Two Modes

### 1. UI Feature Discussion

When the user wants to discuss a UI change:

1. **Understand the context** — which app (admin or triage), which role (root/admin/manager/agent)
2. **Identify affected components** — check if existing `@argus/design-system` components can be reused
3. **Propose design** — describe the UI change using available tokens and components
4. **Confirm before implementing** — present design, wait for approval

### 2. Code Generation

When generating UI code:

1. **Always import from `@argus/design-system`** — never create raw HTML elements for interactive components
2. **Always use CSS custom properties** — never hardcode colors
3. **Always use accessible labels** — every `<Input>` and `<Select>` must have a `label` prop
4. **Always wrap app root in `<ThemeProvider>`** — theme toggle works automatically
5. **Follow the layout pattern** — max-width containers, responsive grid
6. **Reference the style guide** — see `STYLE_GUIDE.md` at the repo root for full rules

## Component Reference

Import all components from `@argus/design-system`:
```tsx
import {
  Button, Input, Select, Textarea,
  Card, Badge, Header, Sidenav,
  Message, ThemeToggle
} from '@argus/design-system';
```

## Token Reference

Use CSS custom properties for all styling:
- Surface: `--bg-page`, `--bg-surface`, `--bg-input`
- Text: `--text-primary`, `--text-secondary`, `--text-muted`, `--text-accent`
- State: `--color-normal`, `--color-weird`, `--color-warning`, `--color-resolved`
- Action: `--color-primary`, `--color-danger`
- Spacing: `--space-xs` (4px) to `--space-xl` (32px)
- Radius: `--radius-sm` (4px) to `--radius-lg` (8px)

## Decision State Colors

Always use `<Badge>` for decision states:
- Normal → `<Badge variant="normal">`
- Weird → `<Badge variant="weird">`
- Warning → `<Badge variant="warning">`
- Resolved → `<Badge variant="resolved">`

## App Layouts

### Admin App (max-width: 960px)
```tsx
<main className="argus-admin">
  <Header title="ARGUS" subtitle="Administration" actions={<ThemeToggle />} />
  <Sidenav>{/* navigation */}</Sidenav>
  <Card>{/* content */}</Card>
</main>
```

### Triage App (max-width: 1100px, responsive grid)
```tsx
<main className="argus-triage">
  <Header title="ARGUS Triage" subtitle="..." actions={<ThemeToggle />} />
  <div className="argus-triage__grid">
    <Card>{/* feed */}</Card>
    <Card>{/* detail */}</Card>
  </div>
</main>
```

## Common Patterns

### CRUD List
```tsx
<Card>
  <h2>Items</h2>
  {items.map(item => (
    <article key={item.id} className="argus-list-item">
      <b>{item.name}</b>
      <Button size="sm" variant="ghost" onClick={() => edit(item)}>Edit</Button>
      <Button size="sm" variant="danger" onClick={() => remove(item)}>Delete</Button>
    </article>
  ))}
  <div className="argus-inline-form">
    <Input label="New item" value={name} onChange={e => setName(e.target.value)} />
    <Button onClick={create}>Create</Button>
  </div>
</Card>
```

### Form
```tsx
<Card>
  <h2>Form Title</h2>
  <Input label="Field 1" value={v1} onChange={e => setV1(e.target.value)} />
  <Select label="Field 2" value={v2} onChange={e => setV2(e.target.value)} options={[...]} />
  <Textarea label="Field 3" value={v3} onChange={e => setV3(e.target.value)} />
  <Button onClick={submit}>Submit</Button>
</Card>
```
