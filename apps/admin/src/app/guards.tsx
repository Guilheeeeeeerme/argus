import { type ReactNode } from 'react';
import { Link } from 'react-router';
import { EmptyState } from '@argus/design-system';
import { useT } from '@argus/i18n';
import { useSession } from './SessionProvider';

/** Pages that act on the active Conta: show a prompt to choose one instead of the page. */
export function RequireAccount({ children }: { children: ReactNode }) {
  const t = useT();
  const { session, accounts, loadingContext } = useSession();
  if (session?.activeAccount) return <>{children}</>;
  if (loadingContext && accounts.length === 0) return null;
  return (
    <EmptyState
      title={t(accounts.length ? 'Selecione uma conta' : 'Nenhuma conta atribuída ainda.')}
      description={t(
        accounts.length
          ? 'Escolha uma conta na barra lateral para continuar.'
          : 'Fale com um administrador para ter acesso.',
      )}
    />
  );
}

/** Platform-only pages (Contas, Usuários). */
export function RequirePlatform({ children }: { children: ReactNode }) {
  const t = useT();
  const { isPlatform } = useSession();
  if (isPlatform) return <>{children}</>;
  return (
    <EmptyState
      title={t('Sem permissão')}
      description={t('Você não tem permissão para ver esta página.')}
      action={
        <Link to="/" className="argus-btn argus-btn--secondary argus-btn--sm">
          {t('Voltar')}
        </Link>
      }
    />
  );
}
