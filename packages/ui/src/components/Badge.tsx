import { ReactNode } from 'react';

/** Badge visual variants — triage MVP + legacy decision aliases. */
export type BadgeVariant =
  | 'normal'
  | 'weird'
  | 'warning'
  | 'resolved'
  | 'neutral'
  | 'open'
  | 'confirmed'
  | 'dismissed'
  | 'false_positive'
  | 'true_positive'
  | 'false_negative';

interface BadgeProps {
  variant: BadgeVariant;
  children: ReactNode;
}

const TRIAGE_STATE_TO_BADGE: Record<string, BadgeVariant> = {
  open: 'open',
  confirmed: 'confirmed',
  dismissed: 'dismissed',
  false_positive: 'false_positive',
};

/** Map TriageCase.state → Badge variant (Linear state color). */
export function badgeVariantForTriageState(state: string): BadgeVariant {
  return TRIAGE_STATE_TO_BADGE[state] ?? 'neutral';
}

export function Badge({ variant, children }: BadgeProps) {
  return <span className={`argus-badge argus-badge--${variant}`}>{children}</span>;
}
