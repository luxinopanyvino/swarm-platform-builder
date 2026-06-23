/* global React, Icon, AGENTS */
// Execution — watches the pipeline run step-by-step, streams a log, and
// renders the generated article (Content System .prose) as it completes.

const RUN_SEQ = ['investigador', 'redactor', 'revisor', 'formateador'];
const LOG = [
  { t: 'info', m: '→ Compilando grafo dinámico (LangGraph)…' },
  { t: 'ok',   m: '✓ investigador · 12 fuentes recuperadas de Qdrant' },
  { t: 'ok',   m: '✓ redactor · borrador generado (1 842 palabras)' },
  { t: 'info', m: '→ revisor · evaluando calidad y sesgos…' },
  { t: 'ok',   m: '✓ revisor · approval_score = 86' },
  { t: 'ok',   m: '✓ formateador · estilo APA aplicado' },
];

function Execution({ title, onOpenArticle }) {
  const [step, setStep] = React.useState(0); // index of currently-running step
  const logRef = React.useRef(null);
  React.useEffect(() => {
    if (step >= RUN_SEQ.length) return;
    const t = setTimeout(() => setStep(s => s + 1), 1100);
    return () => clearTimeout(t);
  }, [step]);
  const done = step >= RUN_SEQ.length;
  const shownLogs = LOG.slice(0, Math.min(LOG.length, step * 1.5 + 1));

  return (
    <div className="exec">
      <div className="exec-side">
        <div style={{ padding: '16px 18px', borderBottom: '1px solid var(--border-default)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', color: 'var(--text-muted)' }}>Ejecución</div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 700, color: 'var(--ink-100)', marginTop: 5, lineHeight: 1.3 }}>{title}</div>
        </div>
        <div className="exec-steps">
          {RUN_SEQ.map((id, i) => {
            const a = AGENTS[id];
            const st = i < step ? 'done' : i === step ? 'running' : 'idle';
            return (
              <div className={`step${st === 'done' ? ' done' : st === 'running' ? ' running' : ''}`} key={id}>
                <div className="sic" style={{ background: a.tint, color: a.color }}>
                  {st === 'running' ? <Icon name="LoaderCircle" size={16} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Icon name={st === 'done' ? 'Check' : a.icon} size={16} />}
                </div>
                <div style={{ flex: 1 }}>
                  <div className="snm">{a.label}</div>
                  <div className="sst">{st === 'done' ? 'Completado' : st === 'running' ? 'En ejecución…' : 'En espera'}</div>
                </div>
                {st === 'done' && <Icon name="CircleCheck" size={16} style={{ color: 'var(--green-60)' }} />}
              </div>
            );
          })}
        </div>
        <div className="exec-log" ref={logRef}>
          {shownLogs.map((l, i) => <div key={i} className={l.t}>{l.m}</div>)}
          {done && <div className="ok">✓ pipeline finalizado · estado = in_review</div>}
        </div>
      </div>
      <div className="exec-main">
        <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-shell)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className={`badge ${done ? 'b-review' : 'b-draft'}`}><Icon name={done ? 'Clock' : 'LoaderCircle'} size={11} />{done ? 'En revisión' : 'Generando…'}</span>
            <span className="tag">APA</span>
          </div>
          <button className="btn btn-primary btn-sm" disabled={!done} onClick={onOpenArticle}><Icon name="ArrowRight" size={14} />Abrir artículo</button>
        </div>
        <div className="exec-doc">
          <article className="prose" style={{ margin: '0 auto' }}>
            <h1>Retrieval-augmented drafting for marine climate science</h1>
            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--text-secondary)' }}>Borrador generado · {RUN_SEQ.length} agentes · formato APA</p>
            <h2>Abstract</h2>
            <p>{done
              ? 'We present a reproducible editorial pipeline in which generated drafts are grounded in an author\u2019s own indexed corpus. By retrieving evidence before composition, the system preserves citation traceability and reduces unsupported claims.'
              : 'Generando resumen…'}</p>
            {done && <>
              <h2>1 · Introduction</h2>
              <p>Researchers lack an integrated environment that combines AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. AlejandrIA addresses this with a multi-agent graph compiled at runtime from a visual flow.</p>
              <blockquote><p>The orchestrator never publishes autonomously — a human reviewer must approve every article.</p></blockquote>
              <p>The remainder of this article describes the retrieval design, the review agent\u2019s scoring, and an evaluation against an ungrounded baseline.</p>
            </>}
          </article>
        </div>
      </div>
    </div>
  );
}
window.Execution = Execution;
