import { Link, Outlet, useMatch, useNavigate, useParams } from 'react-router';
import { EmptyState, PageHeader, Skeleton, Tabs } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync } from '@shared/hooks';
import { units as unitsApi } from '../api/client';
import type { Establishment } from '../api/types';
import { RequireCompany } from '../app/guards';
import { useCompanyId } from '../app/SessionProvider';
import { LinkButton } from '../components/LinkButton';

export interface UnitOutletContext {
  unitId: string;
  unit: Establishment | null;
}

export function UnitDetailPage() {
  return (
    <RequireCompany>
      <UnitDetail />
    </RequireCompany>
  );
}

function UnitDetail() {
  const t = useT();
  const navigate = useNavigate();
  const companyId = useCompanyId();
  const { unitId = '' } = useParams();
  const match = useMatch('/units/:unitId/:tab/*');
  const tab = match?.params.tab ?? 'cameras';
  const unit = useAsync(() => unitsApi.get(companyId, unitId), [companyId, unitId]);

  if (unit.error) {
    return (
      <>
        <PageHeader
          breadcrumbs={<Link to="/units">{t('Unidades')}</Link>}
          title={t('Unidade não encontrada.')}
        />
        <EmptyState
          title={t('Unidade não encontrada.')}
          description={localizeApiError(unit.error, t)}
          action={<LinkButton to="/units" variant="secondary" size="sm">{t('Voltar')}</LinkButton>}
        />
      </>
    );
  }

  const tabs = [
    { id: 'cameras', label: t('Câmeras'), href: `/units/${unitId}/cameras` },
    { id: 'prompts', label: t('Instruções'), href: `/units/${unitId}/prompts` },
    { id: 'webhooks', label: t('Webhooks'), href: `/units/${unitId}/webhooks` },
  ];
  const context: UnitOutletContext = { unitId, unit: unit.data };

  return (
    <>
      <PageHeader
        breadcrumbs={
          <>
            <Link to="/units">{t('Unidades')}</Link>
            <span aria-hidden="true">›</span>
            <span>{unit.data?.name ?? '…'}</span>
          </>
        }
        breadcrumbsLabel={t('Navegação estrutural')}
        title={unit.data?.name ?? ' '}
        description={
          unit.data ? `${unit.data.address || t('sem endereço')} · ${unit.data.timezone}` : undefined
        }
        actions={
          <LinkButton to={`/units/${unitId}/edit`} variant="secondary" size="sm">
            {t('Editar unidade')}
          </LinkButton>
        }
      />
      {unit.loading && !unit.data ? <Skeleton width={240} height={14} aria-label={t('Carregando')} /> : null}
      <Tabs
        tabs={tabs}
        value={tab}
        onChange={id => navigate(`/units/${unitId}/${id}`)}
        aria-label={t('Seções da unidade')}
      />
      <Outlet context={context} />
    </>
  );
}
