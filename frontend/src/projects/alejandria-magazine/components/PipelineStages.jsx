import React from 'react';
import { CheckCircle, Circle, AlertCircle, Loader } from 'lucide-react';

const ICON = {
  done: <CheckCircle size={14} aria-hidden="true" />,
  current: <Loader size={14} aria-hidden="true" />,
  failed: <AlertCircle size={14} aria-hidden="true" />,
  pending: <Circle size={14} aria-hidden="true" />,
};
const COLOR = {
  done: 'var(--success)', current: 'var(--warning)', failed: 'var(--error)', pending: 'var(--text-muted)',
};
const NAME = { done: 'completada', current: 'en curso', failed: 'con problemas', pending: 'pendiente' };

/**
 * Línea de etapas del manuscrito hasta «Publicado»: de un vistazo, dónde está y
 * qué falta. El estado se deriva fuera (`stageStates`); aquí solo se pinta.
 */
export default function PipelineStages({ stages }) {
  return (
    <ol aria-label="Etapas del manuscrito" style={{
      listStyle: 'none', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)',
      padding: 0, margin: '0 0 var(--space-4)', fontSize: 'var(--font-size-xs)',
    }}>
      {stages.map((s) => (
        <li key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 4, color: COLOR[s.state] }}
          aria-label={`${s.label}: ${NAME[s.state]}`}>
          {ICON[s.state]}
          <span>{s.label}{s.detail ? ` (${s.detail})` : ''}</span>
        </li>
      ))}
    </ol>
  );
}
