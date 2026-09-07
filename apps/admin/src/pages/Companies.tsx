import { useState } from 'react';
import { Button, Input, Card, Message } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { call, Company } from '../api';

interface CompaniesProps {
  companies: Company[];
  onReload: () => void;
}

export function Companies({ companies, onReload }: CompaniesProps) {
  const t = useT();
  const [name, setName] = useState('New company');
  const [message, setMessage] = useState('');

  async function createCompany() {
    try {
      await call('/v1/admin/companies', {
        method: 'POST',
        body: JSON.stringify({
          name,
          slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
        }),
      });
      onReload();
      setMessage(t('Company created.'));
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function updateCompany(company: Company) {
    const nextName = window.prompt(t('Company name'), company.name);
    if (!nextName) return;
    try {
      await call(`/v1/admin/companies/${company.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: nextName }),
      });
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function deleteCompany(company: Company) {
    if (!window.confirm(t('Delete {name}?', { name: company.name }))) return;
    try {
      await call(`/v1/admin/companies/${company.id}`, { method: 'DELETE' });
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <Card>
      <h2>{t('Companies')}</h2>
      {companies.map(company => (
        <article key={company.id} className="argus-list-item">
          <b>{company.name}</b>
          <span>{company.slug}</span>
          <Button size="sm" variant="ghost" onClick={() => updateCompany(company)}>{t('Edit')}</Button>
          <Button size="sm" variant="danger" onClick={() => deleteCompany(company)}>{t('Delete')}</Button>
        </article>
      ))}
      <div className="argus-inline-form">
        <Input
          label={t('Company name')}
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <Button onClick={createCompany}>{t('Create company')}</Button>
      </div>
      <Message text={message} />
    </Card>
  );
}
