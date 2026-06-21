/* global React, ReactDOM, Icon, AGENTS, Sidebar, TopBar, Auth, FlowDesigner, Execution, ArticlesGrid, ArticleDetail, SAMPLE_ARTICLES */

function AgentsPage() {
  return (
    <div className="page">
      <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink-100)', letterSpacing: '-0.02em' }}>Agentes</h1>
      <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', margin: '4px 0 22px' }}>Los cinco agentes editoriales disponibles para tus flujos.</p>
      <div className="grid">
        {Object.entries(AGENTS).map(([id, a]) => (
          <div className="card card-pad" key={id} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <div className="nic" style={{ width: 40, height: 40, borderRadius: 10, background: a.tint, color: a.color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><Icon name={a.icon} size={20} /></div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink-100)' }}>{a.label}</div>
              <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>{a.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConfigPage() {
  const rows = [
    ['min_approval_score', '80', 'Score mínimo del revisor para aprobar'],
    ['default_model', 'llama3.2', 'Modelo de inferencia local (Ollama)'],
    ['vector_size', '1536', 'Dimensión del embedding (Qdrant)'],
    ['allow_custom_topology', 'true', 'Permitir flujos personalizados'],
  ];
  return (
    <div className="page" style={{ maxWidth: 760 }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink-100)', letterSpacing: '-0.02em' }}>Configuración</h1>
      <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', margin: '4px 0 22px' }}>Parámetros globales (config.yaml).</p>
      <div className="card">
        <div style={{ padding: '13px 18px', borderBottom: '1px solid var(--border-subtle)', fontSize: 13, fontWeight: 600, color: 'var(--ink-100)', display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="SlidersHorizontal" size={15} />Reglas editoriales</div>
        <div style={{ padding: '6px 18px' }}>
          {rows.map(([k, v, d]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '13px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <div><div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--ink-90)' }}>{k}</div><div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{d}</div></div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--brand)', background: 'var(--blue-05)', padding: '4px 10px', borderRadius: 6 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const TITLES = { flow: 'Flow Designer', articles: 'Artículos', agents: 'Agentes', config: 'Configuración', exec: 'Ejecución' };

function App() {
  const [authed, setAuthed] = React.useState(false);
  const [user, setUser] = React.useState({ name: 'Elena Vázquez', role: 'Autora' });
  const [page, setPage] = React.useState('flow');
  const [execTitle, setExecTitle] = React.useState('');
  const [openArticle, setOpenArticle] = React.useState(null);
  const [toastMsg, setToastMsg] = React.useState(null);
  const toast = (m) => { setToastMsg(m); clearTimeout(window.__t); window.__t = setTimeout(() => setToastMsg(null), 2200); };

  if (!authed) return <><Auth onLogin={(u) => { setUser(u); setAuthed(true); setPage('flow'); }} /></>;

  let content, title = TITLES[page];
  if (openArticle) { content = <ArticleDetail article={openArticle} onBack={() => setOpenArticle(null)} toast={toast} />; title = 'Artículo'; }
  else if (page === 'flow') content = <FlowDesigner onRun={(t) => { setExecTitle(t); setPage('exec'); }} toast={toast} />;
  else if (page === 'exec') content = <Execution title={execTitle} onOpenArticle={() => { setOpenArticle(SAMPLE_ARTICLES[0]); }} />;
  else if (page === 'articles') content = <ArticlesGrid onOpen={setOpenArticle} />;
  else if (page === 'agents') content = <AgentsPage />;
  else if (page === 'config') content = <ConfigPage />;

  const fullBleed = (page === 'flow' || page === 'exec') && !openArticle;

  const navActive = openArticle ? 'articles' : (page === 'exec' ? 'flow' : page);

  return (
    <div className="app">
      <Sidebar active={navActive} onNav={(p) => { setOpenArticle(null); setPage(p); }} user={user} />
      <div className="main">
        <TopBar title={title}>
          {page === 'flow' && !openArticle && <button className="btn btn-secondary btn-sm"><Icon name="Plus" size={14} />Nuevo flujo</button>}
        </TopBar>
        {fullBleed ? <div className="body" style={{ overflow: 'hidden' }}>{content}</div> : <div className="body">{content}</div>}
      </div>
      {toastMsg && <div className="toast"><Icon name="Check" size={15} style={{ color: '#6ee7a8' }} />{toastMsg}</div>}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
