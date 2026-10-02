import { AlertDialog } from '@argus/design-system';
import { useT } from '@argus/i18n';

interface ConfirmDeleteProps {
  open: boolean;
  title: string;
  /** Name shown in "Excluir {name}?". */
  name: string;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Destructive confirmation that stays open (busy) until the request settles. */
export function ConfirmDelete({ open, title, name, busy, onConfirm, onCancel }: ConfirmDeleteProps) {
  const t = useT();
  return (
    <AlertDialog
      open={open}
      busy={busy}
      title={title}
      description={t('Excluir {name}? Essa ação não pode ser desfeita.', { name })}
      confirmLabel={busy ? t('Excluindo…') : t('Excluir')}
      cancelLabel={t('Cancelar')}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}
