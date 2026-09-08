import { useState } from 'react';
import {
  Button,
  Input,
  Card,
  Message,
  ListRow,
  EmptyState,
  AlertDialog,
  Dialog,
} from '@argus/design-system';
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
  const [pendingDelete, setPendingDelete] = useState<Company | null>(null);
  const [editing, setEditing] = useState<Company | null>(null);
  const [editName, setEditName] = useState('');

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

  async function confirmDelete() {
    if (!pendingDelete) return;
    const company = pendingDelete;
    setPendingDelete(null);
    try {
      await call(`/v1/admin/companies/${company.id}`, { method: 'DELETE' });
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function saveEdit() {
    if (!editing || !editName.trim()) return;
    try {
      await call(`/v1/admin/companies/${editing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: editName.trim() }),
      });
      setEditing(null);
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <Card>
      <h2>{t('Companies')}</h2>
      {companies.length === 0 ? (
        <EmptyState
          title={t('No companies yet')}
          description={t('Create a company to start multi-tenant administration.')}
        />
      ) : (
        companies.map(company => (
          <ListRow
            key={company.id}
            title={company.name}
            meta={company.slug}
            actions={
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(company);
                    setEditName(company.name);
                  }}
                >
                  {t('Edit')}
                </Button>
                <Button size="sm" variant="danger" onClick={() => setPendingDelete(company)}>
                  {t('Delete')}
                </Button>
              </>
            }
          />
        ))
      )}
      <div className="argus-inline-form">
        <Input
          label={t('Company name')}
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <Button onClick={createCompany}>{t('Create company')}</Button>
      </div>
      <Message text={message} />

      <AlertDialog
        open={Boolean(pendingDelete)}
        title={t('Delete company')}
        description={t('Delete {name}? This cannot be undone.', {
          name: pendingDelete?.name ?? '',
        })}
        confirmLabel={t('Delete')}
        cancelLabel={t('Cancel')}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />

      <Dialog
        open={Boolean(editing)}
        title={t('Edit company')}
        onClose={() => setEditing(null)}
      >
        <Input
          label={t('Company name')}
          value={editName}
          onChange={e => setEditName(e.target.value)}
        />
        <div className="argus-dialog__actions">
          <Button variant="ghost" onClick={() => setEditing(null)}>
            {t('Cancel')}
          </Button>
          <Button onClick={() => void saveEdit()}>{t('Save')}</Button>
        </div>
      </Dialog>
    </Card>
  );
}
