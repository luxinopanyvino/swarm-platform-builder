import React from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import {
  agentLabel, BLOCKING, CRITERION_LABELS, CRITERION_STATUS, evidenceLines,
} from '../gate';

/**
 * Informe de la compuerta de publicación (SPEC-032/AC6). Dice, por criterio, si
 * se supera, qué lo impide y a qué agente le corresponde; lista aparte lo que aún
 * no se comprueba. Sin informe lo dice, en vez de callarlo: los artículos
 * anteriores a la compuerta no tienen.
 */
export default function GateReportPanel({ data, loading, error, onRetry, onReevaluate, busy }) {
  const report = data?.report;
  const criteria = report?.criteria?.criteria || [];
  const pending = report?.criteria?.pending || [];

  return (
    <div className="card" aria-label="Informe de la compuerta de publicación">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 'var(--space-3)' }}>
        <ShieldCheck size={14} />
        <strong style={{ fontSize: 'var(--font-size-sm)', flex: 1 }}>Compuerta de publicación</strong>
        {onReevaluate && (
          <button className="btn btn-ghost btn-sm" onClick={onReevaluate} disabled={busy}
            aria-label="Reevaluar la compuerta sobre el texto actual">
            <RefreshCw size={12} /> Reevaluar
          </button>
        )}
      </div>

      {loading && <div style={{ color: 'var(--text-muted)' }}>Cargando informe…</div>}

      {!loading && error && (
        <div role="alert" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--error)' }}>
          {error}{' '}
          {onRetry && <button className="btn btn-ghost btn-sm" onClick={onRetry}>Reintentar</button>}
        </div>
      )}

      {!loading && !error && !report && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
          Sin informe. Se genera al terminar el pipeline o al reevaluar.
        </div>
      )}

      {report && (
        <>
          <div style={{ marginBottom: 'var(--space-3)' }}>
            <span className={`badge ${report.criteria.passed ? 'badge-approved' : 'badge-error'}`}>
              {report.criteria.passed ? 'Sin bloqueantes' : 'Con bloqueantes'}
            </span>
            {!data.current && (
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--warning)', marginTop: 6 }}>
                El texto cambió desde esta evaluación: reevalúa antes de aprobar.
              </div>
            )}
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
              Evaluado el {new Date(report.created_at).toLocaleString('es-ES')}
            </div>
          </div>

          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {criteria.map((c) => {
              const st = CRITERION_STATUS[c.status] || CRITERION_STATUS.not_verified;
              const lines = evidenceLines(c);
              return (
                <li key={c.criterion}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span className={`badge ${st.cls}`}>{st.label}</span>
                    <span style={{ fontSize: 'var(--font-size-sm)' }}>
                      {CRITERION_LABELS[c.criterion] || c.criterion}
                    </span>
                  </div>
                  {BLOCKING.has(c.status) && (
                    <div style={{ fontSize: 'var(--font-size-xs)', marginTop: 4, color: 'var(--text-secondary)' }}>
                      {lines.slice(0, 5).map((l, i) => <div key={i}>{l}</div>)}
                      {lines.length > 5 && <div>… y {lines.length - 5} más</div>}
                      {c.responsible_agent && (
                        <div style={{ marginTop: 2 }}>
                          Corresponde a: <strong>{agentLabel(c.responsible_agent)}</strong>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          {pending.length > 0 && (
            <details style={{ marginTop: 'var(--space-3)' }}>
              <summary style={{ cursor: 'pointer', fontSize: 'var(--font-size-xs)' }}>
                {pending.length} criterios aún sin comprobar (no bloquean)
              </summary>
              <ul style={{ fontSize: 'var(--font-size-xs)', paddingLeft: 18, margin: '6px 0 0' }}>
                {pending.map((p) => <li key={p.id}>{p.id} — {p.phase}</li>)}
              </ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}
