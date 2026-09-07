# ARGUS UI Style Guide

## For Agents Generating UI Code

### Mandatory Rules

1. **Import from `@argus/design-system`** — never inline colors, never create ad-hoc CSS variables
2. **Use CSS custom properties** — `var(--bg-surface)`, never `#172235`
3. **Use shared components** — `<Button>`, `<Card>`, `<Badge>`, never raw `<button>` with inline styles
4. **Dark mode is automatic** — never hardcode dark/light colors, always use tokens
5. **All inputs must have labels** — use `<Input label="..."/>` or `<Select label="..."/>`
6. **Use semantic HTML** — `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`
7. **State colors via Badge** — `<Badge variant={decision.state}>` for decision states
8. **Layout** — max-width containers (960px admin, 1100px triage), `var(--space-xl)` padding
9. **Typography** — never override font family, use `var(--font)` sizing
10. **No inline styles** — all styling through CSS classes using tokens

### Available Tokens

| Category | Token | Description |
|----------|-------|-------------|
| Surface | `--bg-page` | Page background |
| Surface | `--bg-surface` | Card/section background |
| Surface | `--bg-input` | Input background |
| Border | `--border` | Standard border |
| Border | `--border-strong` | Emphasized border |
| Text | `--text-primary` | Main text |
| Text | `--text-secondary` | Secondary text |
| Text | `--text-muted` | Muted text |
| Text | `--text-accent` | Accent/brand text |
| State | `--color-normal` | Normal state (green) |
| State | `--color-weird` | Weird state (yellow) |
| State | `--color-warning` | Warning state (red) |
| State | `--color-resolved` | Resolved state (purple) |
| Action | `--color-primary` | Primary button/action |
| Action | `--color-danger` | Danger/destructive action |
| Spacing | `--space-xs` through `--space-xl` | 4px to 32px |
| Radius | `--radius-sm/md/lg` | 4px to 8px |

### Available Components

```tsx
import {
  Button,      // variant: primary|danger|ghost, size: sm|md
  Input,       // label: string, standard input props
  Select,      // label: string, options: {value, label}[]
  Textarea,    // label?: string, standard textarea props
  Card,        // children wrapper
  Badge,       // variant: normal|weird|warning|resolved
  Header,      // title, subtitle?, actions?
  Sidenav,     // children wrapper
  Message,     // text, variant: info|error
  ThemeToggle, // no props, sun/moon toggle
  ThemeProvider, // wraps app root
} from '@argus/design-system';
```

### Component Examples

```tsx
// Button
<Button variant="primary" onClick={handleSave}>Save</Button>
<Button variant="danger" onClick={handleDelete}>Delete</Button>
<Button variant="ghost" onClick={handleCancel}>Cancel</Button>

// Input with label
<Input label="Email" value={email} onChange={e => setEmail(e.target.value)} />

// Select with options
<Select
  label="Disposition"
  value={state}
  onChange={e => setState(e.target.value)}
  options={[
    { value: 'tp', label: 'True Positive' },
    { value: 'fp', label: 'False Positive' },
  ]}
/>

// Badge for states
<Badge variant={decision.state}>{decision.state}</Badge>

// Card wrapper
<Card>
  <h2>Section title</h2>
  {/* content */}
</Card>
```

### CSS Pattern

```css
/* App-specific styles only — never duplicate token values */
.my-page {
  max-width: 960px;
  margin: auto;
  padding: var(--space-xl);
}

.my-list-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  border-bottom: 1px solid var(--border);
  padding: var(--space-sm) 0;
}
```

### Do / Don't

| Do | Don't |
|----|-------|
| `<Button>Save</Button>` | `<button style={{background: '#2563eb'}}>Save</button>` |
| `color: var(--text-primary)` | `color: #e8edf5` |
| `<Badge variant="warning">` | `<span style={{color: '#fca5a5'}}>warning</span>` |
| `<Input label="Email"/>` | `<input placeholder="Email"/>` |
| Import from `@argus/design-system` | Create local component duplicates |
