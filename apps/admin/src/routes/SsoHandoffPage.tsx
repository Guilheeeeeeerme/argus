import { useEffect } from 'react';
import { getToken, isAllowedReturn, type Session } from '@shared/auth';
import { APP } from '../api/client';
import { LoginPage } from './LoginPage';

/** `/sso/handoff?returnUrl=…`: forward an existing token to an allowed origin, or sign in first. */
export function SsoHandoffPage() {
  const params = new URLSearchParams(window.location.search);
  const target = params.get('returnUrl') ?? APP;
  const token = getToken();
  const canForward = Boolean(token) && isAllowedReturn(target);

  useEffect(() => {
    if (canForward) window.location.assign(`${target}#token=${encodeURIComponent(token ?? '')}`);
  }, [canForward, target, token]);

  if (canForward) return null;
  return (
    <LoginPage
      onLogin={(session: Session) => {
        if (isAllowedReturn(target)) {
          window.location.assign(
            `${target}#token=${encodeURIComponent(session.token ?? getToken() ?? '')}`,
          );
        }
      }}
    />
  );
}
