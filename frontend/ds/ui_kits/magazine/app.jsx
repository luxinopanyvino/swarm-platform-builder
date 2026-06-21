/* global React, COVERS, SCRIMS, AUTHORS, POSTS, TOPICS, Avatar, lucide */

function MIcon({ name, size = 18, sw = 2 }) {
  const reg = (window.lucide && window.lucide.icons) || {};
  const node = reg[name];
  if (!node) return <svg width={size} height={size} viewBox="0 0 24 24" />;
  const camel = (a) => { const o = {}; for (const k in a) o[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = a[k]; return o; };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    {node.map((e, i) => React.createElement(e[0], { key: i, ...camel(e[1]) }))}
  </svg>;
}

function Nav({ onHome }) {
  return (
    <nav className="mnav">
      <div className="brand" onClick={onHome} style={{ cursor: 'pointer' }}>
        <img src="../../assets/logomark.svg" width="36" height="36" alt="" />
        <div><div className="nm">Alexandria</div><div className="sub">MAGAZINE</div></div>
      </div>
      <div className="links">
        <a className="active" onClick={onHome}>Inicio</a>
        <a>Temas</a><a>Autores</a><a>Acerca de</a>
      </div>
      <div className="right">
        <button className="icon-btn" aria-label="Buscar"><MIcon name="search" size={18} /></button>
        <button className="btn btn-primary">Suscríbete</button>
      </div>
    </nav>
  );
}

function Cover({ id, children }) {
  return <div style={{ position: 'absolute', inset: 0, background: COVERS[id] }}><div className="scrim" style={{ background: SCRIMS[id] }} />{children}</div>;
}

function Home({ onOpen }) {
  const [topic, setTopic] = React.useState('Todos');
  const feat = POSTS.find(p => p.featured);
  const rest = POSTS.filter(p => !p.featured && (topic === 'Todos' || p.topic === topic));
  const fa = AUTHORS[feat.author];
  return (
    <>
      <header className="hero"><div className="wrap"><div className="hero-grid">
        <div>
          <span className="eyebrow" style={{ color: feat.kc }}>{feat.kicker}</span>
          <h1>{feat.title}</h1>
          <p>{feat.excerpt}</p>
          <div className="byline">
            <Avatar a={fa} size={40} />
            <div className="byline-txt"><div className="nm">{fa.name}</div><div className="dt">{feat.date} · {feat.read} min de lectura</div></div>
            <button className="btn btn-primary" style={{ marginLeft: 12 }} onClick={() => onOpen(feat)}>Leer artículo</button>
          </div>
        </div>
        <div className="cover" onClick={() => onOpen(feat)} style={{ cursor: 'pointer' }}>
          <Cover id={feat.cover}><div className="cap">Figura · pipeline editorial agéntico</div></Cover>
        </div>
      </div></div></header>

      <main className="wrap">
        <div className="sec-head"><h2>Últimos artículos</h2></div>
        <div className="topics" style={{ marginBottom: 26 }}>
          {TOPICS.map(t => <button key={t} className={`chip${topic === t ? ' active' : ''}`} onClick={() => setTopic(t)}>{t}</button>)}
        </div>
        <div className="feed">
          {rest.map(p => {
            const a = AUTHORS[p.author];
            return (
              <article className="post" key={p.id} onClick={() => onOpen(p)}>
                <div className="thumb"><Cover id={p.cover} /></div>
                <span className="kicker" style={{ color: p.kc }}>{p.kicker}</span>
                <h3>{p.title}</h3>
                <p className="ex">{p.excerpt}</p>
                <div className="meta"><Avatar a={a} size={24} /><span>{a.name}</span><span className="dot" style={{ width: 3, height: 3, borderRadius: 9, background: 'var(--neutral-40)' }} /><span>{p.read} min</span></div>
              </article>
            );
          })}
        </div>
      </main>

      <footer className="mfoot"><div className="wrap cols">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><img src="../../assets/logomark.svg" width="30" height="30" alt="" /><span className="nm">Alexandria Magazine</span></div>
          <p>Ciencia y tecnología redactada con rigor, revisada por personas, publicada con IA.</p>
        </div>
        <div className="col"><h4>Secciones</h4><a>Inteligencia artificial</a><a>Sistemas</a><a>Metodología</a><a>Ética</a></div>
        <div className="col"><h4>Plataforma</h4><a>Studio</a><a>Flow Designer</a><a>Agentes</a><a>API</a></div>
        <div className="col"><h4>Comunidad</h4><a>Autores</a><a>Newsletter</a><a>RSS</a><a>Contacto</a></div>
      </div></footer>
    </>
  );
}

function Reader({ post, onHome }) {
  const a = AUTHORS[post.author];
  const [liked, setLiked] = React.useState(false);
  return (
    <>
      <article className="reader"><div className="wrap">
        <div className="reader-head">
          <span className="eyebrow" style={{ color: post.kc }}>{post.kicker}</span>
          <h1>{post.title}</h1>
          <p className="lede">{post.excerpt}</p>
          <div className="reader-meta">
            <div className="m"><Avatar a={a} size={30} /><span style={{ color: 'var(--ink-90)', fontWeight: 600 }}>{a.name}</span></div>
            <span className="dot" /><div className="m"><MIcon name="calendar" size={14} />{post.date}</div>
            <span className="dot" /><div className="m"><MIcon name="clock" size={14} />{post.read} min</div>
            <span className="dot" /><div className="m"><MIcon name="badge-check" size={14} />Revisado por pares</div>
          </div>
          <div className="tag-row"><span className="tag">APA</span><span className="tag">{post.topic}</span><span className="tag">RAG</span><span className="tag">LangGraph</span></div>
        </div>
        <div className="reader-cover"><Cover id={post.cover}><div className="cap" style={{ position: 'absolute', left: 22, bottom: 18, color: 'rgba(255,255,255,.82)', fontSize: 12.5 }}>Figura 1 · arquitectura del pipeline editorial agéntico</div></Cover></div>

        <div className="reader-body">
          <div className="prose">
            <p className="has-dropcap"><strong>Researchers</strong> lack an integrated environment that combines AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. Alexandria addresses this with a multi-agent graph compiled at runtime from a visual flow.</p>
            <h2>Grounding generation in evidence</h2>
            <p>Before composition, the redactor agent retrieves context from the author\u2019s indexed corpus. Retrieval-augmented generation keeps each claim traceable to <a href="#">cited evidence</a> rather than model priors — the difference between a draft you can submit and one you must rewrite.</p>
            <blockquote><p>The orchestrator never publishes autonomously — a human reviewer approves every article.</p></blockquote>
            <h3>The review agent</h3>
            <p>A dedicated <code>revisor</code> evaluates quality and surfaces methodological or citation bias, emitting a calibrated approval score on a 0–100 scale. Articles below the configured threshold route back for revision automatically.</p>
            <figure><div style={{ aspectRatio: '16/7', borderRadius: 8, background: COVERS.b, position: 'relative', overflow: 'hidden' }}><div style={{ position: 'absolute', inset: 0, background: SCRIMS.b }} /></div><figcaption><span className="fig-label">Fig. 2 ·</span> approval-score distribution across 240 generated drafts.</figcaption></figure>
            <p>Grounded drafts reduced unsupported claims by a factor of 4.3 versus the ungrounded baseline, with no measurable cost to readability.</p>
            <h2>Conclusion</h2>
            <p>Treating scientific writing as a compiled multi-agent pipeline — with retrieval, calibrated review, and a human publication gate — yields drafts that are both faster to produce and safer to publish.</p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 40, paddingTop: 28, borderTop: '1px solid var(--border-subtle)' }}>
            <Avatar a={a} size={52} />
            <div><div style={{ fontFamily: 'var(--font-serif)', fontSize: 17, fontWeight: 700, color: 'var(--ink-100)' }}>{a.name}</div><div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 3 }}>Autora · investigación en sistemas de IA aplicada a la publicación científica.</div></div>
            <button className="btn btn-primary" style={{ marginLeft: 'auto' }}>Seguir</button>
          </div>
        </div>
      </div></article>

      <div className="toolbar-float">
        <button className={liked ? 'liked' : ''} onClick={() => setLiked(v => !v)} aria-label="Recomendar"><MIcon name="heart" size={17} sw={liked ? 0 : 2} /></button>
        <span className="count"><MIcon name="heart" size={13} />{142 + (liked ? 1 : 0)}</span>
        <span className="div" />
        <button aria-label="Comentar"><MIcon name="message-circle" size={17} /></button>
        <button aria-label="Guardar"><MIcon name="bookmark" size={17} /></button>
        <button aria-label="Compartir"><MIcon name="share-2" size={17} /></button>
        <span className="div" />
        <button onClick={onHome} aria-label="Volar al inicio"><MIcon name="arrow-up" size={17} /></button>
      </div>
    </>
  );
}

function App() {
  const [post, setPost] = React.useState(null);
  React.useEffect(() => { window.scrollTo(0, 0); }, [post]);
  return (
    <>
      <Nav onHome={() => setPost(null)} />
      {post ? <Reader post={post} onHome={() => setPost(null)} /> : <Home onOpen={setPost} />}
    </>
  );
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
