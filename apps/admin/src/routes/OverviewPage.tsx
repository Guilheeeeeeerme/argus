import { PageHeader } from '@argus/design-system';
import { useT } from '@argus/i18n';
import { RequireCompany } from '../app/guards';

export function OverviewPage() {
  const t = useT();
  return (
    <>
      <PageHeader title={t('Visão geral')} />
      <RequireCompany>{null}</RequireCompany>
    </>
  );
}
