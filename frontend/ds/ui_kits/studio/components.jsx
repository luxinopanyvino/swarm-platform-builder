/* global React, Icon */
// Shared Studio primitives, app shell, agent metadata & sample data.

const AGENTS = {
  investigador: { label: 'Investigador', icon: 'Search',   color: '#0d9dda', tint: '#e6f6fc', desc: 'Busca contexto en RAG y APIs científicas' },
  redactor:     { label: 'Redactor',     icon: 'PenLine',  color: '#6b4fe3', tint: '#f1eefe', desc: 'Genera el borrador con Ollama' },
  revisor:      { label: 'Revisor',      icon: 'Eye',      color: '#c47d04', tint: '#fdf3e3', desc: 'Evalúa calidad · score 0–100' },
  formateador:  { label: 'Formateador',  icon: 'FileText', color: '#2e844a', tint: '#ebf7ee', desc: 'Aplica formato APA / IEEE / Vancouver' },
  publicador:   { label: 'Publicador',   icon: 'Send',     color: '#cb4b3f', tint: '#fdeeec', desc: 'Publica el artículo' },
};

const STATUS = {
  draft:     { label: 'Borrador',  cls: 'b-draft',     icon: 'CircleDashed' },
  in_review: { label: 'En revisión', cls: 'b-review',  icon: 'Clock' },
  approved:  { label: 'Aprobado',  cls: 'b-approved',  icon: 'Check' },
  published: { label: 'Publicado', cls: 'b-published', icon: 'Globe' },
  rejected:  { label: 'Rechazado', cls: 'b-rejected',  icon: 'X' },
};

const SAMPLE_ARTICLES = [
  { id: 'a1', title: 'Retrieval-augmented drafting for marine climate science', status: 'published', format: 'apa', date: '28 May 2026', read: 8,
    excerpt: 'A reproducible pipeline that grounds generated drafts in an author\u2019s indexed corpus, preserving citation traceability end to end.' },
  { id: 'a2', title: 'Privacy-preserving RAG with local inference', status: 'in_review', format: 'ieee', date: '24 May 2026', read: 11,
    excerpt: 'We evaluate Qdrant + Ollama topologies for author-isolated semantic retrieval without external API calls.' },
  { id: 'a3', title: 'Human-in-the-loop publication gates', status: 'approved', format: 'apa', date: '21 May 2026', read: 6,
    excerpt: 'Why the orchestrator never calls publish() autonomously, and how approval thresholds shape editorial trust.' },
  { id: 'a4', title: 'Dynamic graph compilation for editorial pipelines', status: 'draft', format: 'none', date: '19 May 2026', read: 9,
    excerpt: 'Compiling a LangGraph topology at runtime from a visual flow: loops, retries, and conditional routing.' },
  { id: 'a5', title: 'Bias detection in the review agent', status: 'published', format: 'vancouver', date: '14 May 2026', read: 7,
    excerpt: 'Surfacing methodological and citation bias during automated review, with a calibrated approval score.' },
  { id: 'a6', title: 'Structured formats: APA, IEEE & Vancouver as adapters', status: 'rejected', format: 'none', date: '09 May 2026', read: 5,
    excerpt: 'Treating scientific citation styles as interchangeable formatting adapters over a single document model.' },
];

function Avatar({ name, size = 32 }) {
  const initials = name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  return <div className="avatar" style={{ width: size, height: size, fontSize: size * 0.4 }}>{initials}</div>;
}

function Badge({ status }) {
  const s = STATUS[status] || STATUS.draft;
  return <span className={`badge ${s.cls}`}><Icon name={s.icon} size={11} />{s.label}</span>;
}

function Sidebar({ active, onNav, user }) {
  const items = [
    { sec: 'Workspace' },
    { id: 'flow', label: 'Flow Designer', icon: 'GitBranch' },
    { id: 'articles', label: 'Artículos', icon: 'FileText' },
    { id: 'agents', label: 'Agentes', icon: 'Bot' },
    { sec: 'Cuenta' },
    { id: 'config', label: 'Configuración', icon: 'Settings' },
  ];
  return (
    <aside className="sidebar">
      <div className="side-logo">
        <img src="../../assets/logomark.svg" width="34" height="34" alt="" />
        <div className="wm"><span className="name">AlejandrIA</span><span className="sub">MAGAZINE</span></div>
      </div>
      <nav className="side-nav">
        {items.map((it, i) => it.sec
          ? <div className="nav-sec" key={i}>{it.sec}</div>
          : <button key={it.id} className={`nav-item${active === it.id ? ' active' : ''}`} onClick={() => onNav(it.id)}>
              <Icon name={it.icon} size={17} />{it.label}
            </button>
        )}
      </nav>
      <div className="side-foot">
        <div className="user-row">
          <Avatar name={user.name} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="nm">{user.name}</div>
            <div className="rl">{user.role}</div>
          </div>
          <Icon name="LogOut" size={15} style={{ color: 'var(--text-muted)' }} />
        </div>
      </div>
    </aside>
  );
}

function TopBar({ title, children }) {
  return (
    <header className="topbar">
      <div className="ttl">{title}</div>
      <div className="actions">
        {children}
        <button className="icon-btn"><Icon name="Bell" size={18} /><span className="notif-dot" /></button>
        <button className="icon-btn"><Icon name="CircleHelp" size={18} /></button>
      </div>
    </header>
  );
}

Object.assign(window, { AGENTS, STATUS, SAMPLE_ARTICLES, Avatar, Badge, Sidebar, TopBar });
