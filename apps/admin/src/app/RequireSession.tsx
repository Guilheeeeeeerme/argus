import { Outlet } from 'react-router';
import { Skeleton } from '@argus/design-system';
import { useT } from '@argus/i18n';
import { useSession } from './SessionProvider';
import { LoginPage } from '../routes/LoginPage';

/** Renders the login form in place (query string preserved) until a session exists. */
export function RequireSession() {
  const t = useT();
  const { booted, session } = useSession();

  if (!booted) {
    return (
      <div className="argus-boot" role="status" aria-live="polite">
        <Skeleton width={180} height={20} aria-label={t('Carregando')} />
        <Skeleton width={120} height={14} aria-label="" />
      </div>
    );
  }
  if (!session) return <LoginPage />;
  return <Outlet />;
}
