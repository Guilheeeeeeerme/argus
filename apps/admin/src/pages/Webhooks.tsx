import { useEffect, useState } from 'react';
import {
  Button,
  Input,
  Select,
  Card,
  Message,
  ListRow,
  EmptyState,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { call, Establishment, WebhookEndpoint } from '../api';

interface WebhooksProps {
  establishments: Establishment[];
  companyId: string;
}

export function Webhooks({ establishments, companyId }: WebhooksProps) {
  const t = useT();
  const [endpoints, setEndpoints] = useState<WebhookEndpoint[]>([]);
  const [name, setName] = useState('Novo webhook');
  const [establishmentId, setEstablishmentId] = useState('');
  const [message, setMessage] = useState('');
  const [createdToken, setCreatedToken] = useState<string | null>(null);

  async function load() {
    try {
      setEndpoints(
        (await call(`/v1/companies/${companyId}/webhook-endpoints`)) as WebhookEndpoint[],
      );
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  useEffect(() => {
    void load();
  }, [companyId]);

  useEffect(() => {
    if (!establishmentId && establishments[0]) {
      setEstablishmentId(establishments[0].id);
    }
  }, [establishments, establishmentId]);

  async function createWebhook() {
    if (!establishmentId) return;
    try {
      const created = (await call(`/v1/companies/${companyId}/webhook-endpoints`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          establishment_id: establishmentId,
        }),
      })) as WebhookEndpoint;
      setCreatedToken(created.token ?? null);
      setMessage(
        t('Webhook criado. Copie o token agora — ele não será exibido novamente.'),
      );
      await load();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  const establishmentName = (id: string | null) =>
    establishments.find(e => e.id === id)?.name ?? id ?? '—';

  return (
    <Card>
      <h2>{t('Webhooks')}</h2>
      {endpoints.length === 0 ? (
        <EmptyState
          title={t('Nenhum webhook ainda')}
          description={t('Crie um webhook para receber eventos externos.')}
        />
      ) : (
        endpoints.map(endpoint => (
          <ListRow
            key={endpoint.id}
            title={endpoint.name}
            meta={establishmentName(endpoint.establishment_id)}
          />
        ))
      )}
      <div className="argus-inline-form">
        <Input label={t('Nome do webhook')} value={name} onChange={e => setName(e.target.value)} />
        <Select
          label={t('Estabelecimento')}
          value={establishmentId}
          onChange={e => setEstablishmentId(e.target.value)}
          options={[
            { value: '', label: t('Selecione…') },
            ...establishments.map(e => ({ value: e.id, label: e.name })),
          ]}
        />
        <Button onClick={() => void createWebhook()} disabled={!establishmentId}>
          {t('Criar webhook')}
        </Button>
      </div>
      {createdToken ? (
        <div className="argus-webhook-token">
          <p className="argus-webhook-token__label">{t('Token (copie agora)')}</p>
          <code className="argus-webhook-token__value">{createdToken}</code>
        </div>
      ) : null}
      <Message text={message} />
    </Card>
  );
}
