import { type ReactNode } from 'react';
import { Link } from 'react-router';
import { Card, EmptyState, PageHeader, Skeleton } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync } from '@shared/hooks';
import { accounts as accountsApi, cameras as camerasApi, units as unitsApi, users as usersApi, webhooks as webhooksApi } from '../api/client';
import { useSession } from '../app/SessionProvider';
import { LinkButton } from '../components/LinkButton';

export function OverviewPage() {
  const t = useT();
  const { session, accounts, loadingContext, isPlatform } = useSession();
  const accountId = session?.activeAccount?.id ?? null;

  return (
    <>
      <PageHeader
        title={t('Visão geral')}
        description={
          session?.activeAccount
            ? t('Resumo de {name}.', { name: session.activeAccount.name })
            : undefined
        }
      />
      {accountId ? (
        <AccountStats accountId={accountId} />
      ) : loadingContext && accounts.length === 0 ? (
        <div className="argus-overview-grid">
          <StatCard title={t('Unidades')} loading />
          <StatCard title={t('Câmeras')} loading />
        </div>
      ) : (
        <EmptyState
          title={t(accounts.length ? 'Selecione uma conta' : 'Nenhuma conta atribuída ainda.')}
          description={t(
            accounts.length
              ? 'Escolha uma conta no menu para continuar.'
              : 'Fale com um administrador para ter acesso.',
          )}
          action={isPlatform && accounts.length === 0 ? <LinkButton to="/accounts/new" size="sm">{t('Nova conta')}</LinkButton> : undefined}
        />
      )}
      {isPlatform ? <PlatformStats /> : null}
    </>
  );
}

function AccountStats({ accountId }: { accountId: string }) {
  const t = useT();
  const units = useAsync(() => unitsApi.list(accountId), [accountId]);
  const cameras = useAsync(() => camerasApi.listAll(accountId), [accountId]);
  const webhooks = useAsync(() => webhooksApi.list(accountId), [accountId]);
  const firstUnit = units.data?.[0];

  return (
    <div className="argus-overview-grid">
      <StatCard
        title={t('Unidades')}
        loading={units.loading && !units.data}
        error={units.error}
        value={units.data?.length}
        link={<Link to="/units">{t('Ver todas')}</Link>}
        action={<LinkButton to="/units/new" variant="secondary" size="sm">{t('Nova unidade')}</LinkButton>}
      />
      <StatCard
        title={t('Câmeras')}
        loading={cameras.loading && !cameras.data}
        error={cameras.error}
        value={cameras.data?.length}
        link={firstUnit ? <Link to={`/units/${firstUnit.id}/cameras`}>{t('Ver todas')}</Link> : undefined}
        action={
          firstUnit ? (
            <LinkButton to={`/units/${firstUnit.id}/cameras/new`} variant="secondary" size="sm">
              {t('Nova câmera')}
            </LinkButton>
          ) : undefined
        }
      />
      <StatCard
        title={t('Webhooks')}
        loading={webhooks.loading && !webhooks.data}
        error={webhooks.error}
        value={webhooks.data?.length}
        link={firstUnit ? <Link to={`/units/${firstUnit.id}/webhooks`}>{t('Ver todos')}</Link> : undefined}
      />
    </div>
  );
}

function PlatformStats() {
  const t = useT();
  const users = useAsync(() => usersApi.list(), []);
  const accounts = useAsync(() => accountsApi.list(), []);
  return (
    <>
      <h2 className="argus-overview-section">{t('Plataforma')}</h2>
      <div className="argus-overview-grid">
        <StatCard
          title={t('Contas')}
          loading={accounts.loading && !accounts.data}
          error={accounts.error}
          value={accounts.data?.length}
          link={<Link to="/accounts">{t('Ver todas')}</Link>}
          action={<LinkButton to="/accounts/new" variant="secondary" size="sm">{t('Nova conta')}</LinkButton>}
        />
        <StatCard
          title={t('Usuários')}
          loading={users.loading && !users.data}
          error={users.error}
          value={users.data?.length}
          link={<Link to="/users">{t('Ver todos')}</Link>}
          action={<LinkButton to="/users/new" variant="secondary" size="sm">{t('Novo usuário')}</LinkButton>}
        />
      </div>
    </>
  );
}

interface StatCardProps {
  title: string;
  value?: number;
  loading?: boolean;
  error?: unknown;
  link?: ReactNode;
  action?: ReactNode;
}

function StatCard({ title, value, loading, error, link, action }: StatCardProps) {
  const t = useT();
  return (
    <Card className="argus-stat">
      <h2 className="argus-stat__title">{title}</h2>
      {loading ? (
        <Skeleton width={56} height={32} aria-label={t('Carregando')} />
      ) : error ? (
        <p className="argus-stat__error">{localizeApiError(error, t)}</p>
      ) : (
        <p className="argus-stat__value tabular-nums">{value ?? 0}</p>
      )}
      <div className="argus-stat__footer">
        {link}
        {action}
      </div>
    </Card>
  );
}
