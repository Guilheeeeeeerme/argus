import { useState } from 'react';
import { Button, Select, Textarea, Card, Badge, Message } from '@argus/design-system';
import { authedFetch } from '../api';

interface Evidence {
  id: string;
  severity_score: number;
  captured_at: string;
  vlm_result?: { reasoning?: string; description?: string };
}

interface Decision {
  id: string;
  state: string;
  evidence_count: number;
  cumulative_severity: number;
  updated_at: string;
  evidences?: Evidence[];
}

interface DecisionDetailProps {
  decision: Decision;
  company: string;
  onResolved: () => void;
}

export function DecisionDetail({ decision, company, onResolved }: DecisionDetailProps) {
  const [state, setState] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');

  async function resolve() {
    const response = await authedFetch(`/v1/companies/${company}/decisions/${decision.id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        disposition: state,
        reasoning: reason,
        updated_at: decision.updated_at,
      }),
    });
    if (response.ok) {
      onResolved();
    } else {
      setMessage(await response.text());
    }
  }

  return (
    <Card>
      <h2>Decision detail</h2>
      <p>
        <Badge variant={decision.state as any}>{decision.state}</Badge>
        {' · '}{decision.evidence_count} evidences
      </p>
      {decision.evidences?.map((evidence: Evidence) => (
        <article key={evidence.id} className="argus-evidence">
          <b>{evidence.severity_score}</b>
          <span>{new Date(evidence.captured_at).toLocaleString()}</span>
          <p>{evidence.vlm_result?.reasoning ?? evidence.vlm_result?.description}</p>
        </article>
      ))}
      <Select
        label="Disposition"
        value={state}
        onChange={e => setState(e.target.value)}
        options={[
          { value: '', label: 'Select...' },
          { value: 'true_positive', label: 'True Positive' },
          { value: 'false_positive', label: 'False Positive' },
          { value: 'false_negative', label: 'False Negative' },
        ]}
      />
      <Textarea
        label="Reasoning (required for false positive/negative)"
        value={reason}
        onChange={e => setReason(e.target.value)}
      />
      <Button onClick={resolve}>Resolve</Button>
      <Message text={message} variant="error" />
    </Card>
  );
}
