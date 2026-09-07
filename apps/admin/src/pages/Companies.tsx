import { useState } from 'react';
import { Button, Input, Card, Message } from '@argus/design-system';
import { call, Company } from '../api';

interface CompaniesProps {
  companies: Company[];
  onReload: () => void;
}

export function Companies({ companies, onReload }: CompaniesProps) {
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
      setMessage('Company created.');
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function updateCompany(company: Company) {
    const nextName = window.prompt('Company name', company.name);
    if (!nextName) return;
    try {
      await call(`/v1/admin/companies/${company.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: nextName }),
      });
      onReload();
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function deleteCompany(company: Company) {
    if (!window.confirm(`Delete ${company.name}?`)) return;
    try {
      await call(`/v1/admin/companies/${company.id}`, { method: 'DELETE' });
      onReload();
    } catch (error) {
      setMessage(String(error));
    }
  }

  return (
    <Card>
      <h2>Companies</h2>
      {companies.map(company => (
        <article key={company.id} className="argus-list-item">
          <b>{company.name}</b>
          <span>{company.slug}</span>
          <Button size="sm" variant="ghost" onClick={() => updateCompany(company)}>Edit</Button>
          <Button size="sm" variant="danger" onClick={() => deleteCompany(company)}>Delete</Button>
        </article>
      ))}
      <div className="argus-inline-form">
        <Input
          label="Company name"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <Button onClick={createCompany}>Create company</Button>
      </div>
      <Message text={message} />
    </Card>
  );
}
