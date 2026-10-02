import { useEffect, useState } from 'react';
import { Button, useToast } from '@argus/design-system';
import { useT } from '@argus/i18n';

interface TokenRevealProps {
  token: string;
}

/** One-time secret display with a copy button. */
export function TokenReveal({ token }: TokenRevealProps) {
  const t = useT();
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      toast.success(t('Token copiado.'));
    } catch {
      toast.error(t('Ocorreu um erro. Tente novamente.'));
    }
  }

  return (
    <div className="argus-webhook-token">
      <p className="argus-webhook-token__label">{t('Token (copie agora)')}</p>
      <code className="argus-webhook-token__value">{token}</code>
      <div className="argus-webhook-token__actions">
        <Button size="sm" variant="secondary" onClick={() => void copy()}>
          {copied ? t('Copiado') : t('Copiar')}
        </Button>
      </div>
    </div>
  );
}
