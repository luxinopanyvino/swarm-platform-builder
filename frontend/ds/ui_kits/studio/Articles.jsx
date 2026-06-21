/* global React, Icon, Badge, STATUS, SAMPLE_ARTICLES */
// Articles — filterable grid of article cards + a reading/review detail view.

const TABS = [['all', 'Todos'], ['draft', 'Borradores'], ['in_review', 'Pendientes'], ['approved', 'Aprobados'], ['published', 'Publicados']];

function ArticlesGrid({ onOpen }) {
  const [tab, setTab] = React.useState('all');
  const [q, setQ] = React.useState('');
  const list = SAMPLE_ARTICLES.filter(a =>
    (tab === 'all' || a.status === tab) && a.title.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 22 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink-100)', letterSpacing: '-0.02em' }}>Artículos</h1>
          <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginTop: 4 }}>{SAMPLE_ARTICLES.length} artículos en tu espacio</p>
        </div>
        <button className="btn btn-primary"><Icon name="Plus" size={15} />Nuevo artículo</button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="tabs">
          {TABS.map(([id, label]) => <button key={id} className={`tab${tab === id ? ' active' : ''}`} onClick={() => setTab(id)}>{label}</button>)}
        </div>
        <div className="search" style={{ flex: 1, maxWidth: 280 }}>
          <Icon name="Search" size={15} style={{ color: 'var(--text-muted)' }} />
          <input placeholder="Buscar artículos…" value={q} onChange={e => setQ(e.target.value)} />
        </div>
      </div>
      {list.length === 0
        ? <div className="empty"><div className="eic"><Icon name="FileText" size={28} /></div><h3 style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Sin artículos</h3><p style={{ fontSize: 13 }}>Ejecuta un pipeline desde el Flow Designer para generar tu primer artículo.</p></div>
        : <div className="grid">
            {list.map(a => (
              <div className="acard" key={a.id} onClick={() => onOpen(a)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                  <div className="at">{a.title}</div>
                  <Badge status={a.status} />
                </div>
                <div className="ax">{a.excerpt}</div>
                <div className="am">
                  <Icon name="Calendar" size={13} /><span>{a.date}</span>
                  <Icon name="Clock" size={13} /><span>{a.read} min</span>
                  {a.format !== 'none' && <span className="tag" style={{ marginLeft: 'auto' }}>{a.format.toUpperCase()}</span>}
                </div>
              </div>
            ))}
          </div>}
    </div>
  );
}

function ArticleDetail({ article, onBack, toast }) {
  const [showReject, setShowReject] = React.useState(false);
  const a = article;
  return (
    <div className="page" style={{ maxWidth: 960 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 22 }}>
        <button className="icon-btn" onClick={onBack} style={{ border: '1px solid var(--border-default)' }}><Icon name="ArrowLeft" size={17} /></button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 700, color: 'var(--ink-100)', letterSpacing: '-0.01em' }}>{a.title}</h1>
            <Badge status={a.status} />
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 5 }}>Creado {a.date}{a.format !== 'none' && ` · Formato ${a.format.toUpperCase()}`}</div>
        </div>
      </div>

      {a.status === 'in_review' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, background: 'var(--amber-05)', border: '1px solid #f2e0bf', borderRadius: 10, padding: 14, marginBottom: 22 }}>
          <Icon name="Clock" size={17} style={{ color: 'var(--amber-60)' }} />
          <div style={{ fontSize: 13 }}><strong style={{ color: 'var(--amber-70)' }}>Pendiente de aprobación</strong> <span style={{ color: 'var(--text-muted)' }}>· revisor asignado</span></div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 270px', gap: 24, alignItems: 'start' }}>
        <div className="card card-pad" style={{ padding: 34 }}>
          <article className="prose">
            <h2 style={{ marginTop: 0 }}>Abstract</h2>
            <p>We present a reproducible editorial pipeline in which generated drafts are grounded in an author\u2019s own indexed corpus. Retrieving evidence before composition preserves citation traceability and measurably reduces unsupported claims.</p>
            <h2>1 · Introduction</h2>
            <p>Researchers lack an integrated environment combining AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. <code>flow_sequence</code> is compiled at runtime from a visual graph.</p>
            <blockquote><p>The orchestrator never publishes autonomously — a human reviewer approves every article.</p></blockquote>
            <h3>1.1 · Contributions</h3>
            <ul><li>A private RAG design over Qdrant + Ollama.</li><li>A calibrated review agent producing an approval score.</li><li>Citation-style adapters for APA, IEEE and Vancouver.</li></ul>
          </article>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {a.status === 'in_review' && (
            <div className="card card-pad">
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-100)', marginBottom: 12 }}>Acciones de revisión</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button className="btn btn-primary btn-block" onClick={() => toast('Artículo aprobado')}><Icon name="Check" size={14} />Aprobar artículo</button>
                <button className="btn btn-danger btn-block" onClick={() => setShowReject(true)}><Icon name="X" size={14} />Rechazar</button>
              </div>
            </div>
          )}
          <div className="card card-pad">
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-100)', marginBottom: 12 }}>Detalles</div>
            {[['Estado', STATUS[a.status].label], ['Formato', a.format === 'none' ? 'N/A' : a.format.toUpperCase()], ['Lectura', `${a.read} min`], ['Creado', a.date]].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>{k}</span><span style={{ color: 'var(--ink-90)', fontWeight: 500 }}>{v}</span>
              </div>
            ))}
          </div>
          <button className="btn btn-accent btn-block"><Icon name="Sparkles" size={14} />Asistir con IA</button>
        </div>
      </div>

      {showReject && (
        <div className="backdrop" onClick={() => setShowReject(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-h"><h3>Rechazar artículo</h3><button className="icon-btn" onClick={() => setShowReject(false)}><Icon name="X" size={17} /></button></div>
            <div className="modal-b"><div className="field"><label>Motivo del rechazo</label><textarea className="inp" placeholder="Explica los cambios necesarios…" /></div></div>
            <div className="modal-f"><button className="btn btn-ghost" onClick={() => setShowReject(false)}>Cancelar</button><button className="btn btn-danger" onClick={() => { setShowReject(false); toast('Artículo rechazado'); }}><Icon name="X" size={14} />Confirmar rechazo</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
window.ArticlesGrid = ArticlesGrid;
window.ArticleDetail = ArticleDetail;
