import { Select, Spinner } from '@argus/design-system';
import { useT } from '@argus/i18n';
import type { Unit } from '../api';

interface UnitPickerProps {
  units: Unit[];
  value: string | null;
  loading?: boolean;
  switching?: boolean;
  onChange: (unitId: string | null) => void;
}

export function UnitPicker({ units, value, loading, switching, onChange }: UnitPickerProps) {
  const t = useT();
  return (
    <div className="argus-unit-picker">
      <Select
        label={t('Unidade')}
        value={value ?? ''}
        disabled={loading || switching}
        onChange={e => onChange(e.target.value || null)}
        options={[
          { value: '', label: loading ? t('Carregando…') : t('Nenhuma unidade selecionada') },
          ...units.map(unit => ({ value: unit.id, label: unit.name })),
        ]}
      />
      {switching ? <Spinner size="sm" label={t('Trocando…')} className="argus-unit-picker__spinner" /> : null}
    </div>
  );
}
