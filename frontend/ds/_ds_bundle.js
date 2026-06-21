/* @ds-bundle: {"format":3,"namespace":"AlexandriaMagazineDesignSystem_f6284e","components":[],"sourceHashes":{"ui_kits/magazine/app.jsx":"c0b76075dfbc","ui_kits/magazine/data.jsx":"92c58d5454df","ui_kits/studio/Articles.jsx":"edf1c5ab6a6c","ui_kits/studio/Auth.jsx":"f938882ad421","ui_kits/studio/Execution.jsx":"47ba36b971dc","ui_kits/studio/FlowDesigner.jsx":"b7d35ef405f8","ui_kits/studio/app.jsx":"15966cad8b73","ui_kits/studio/components.jsx":"4217e331e90e","ui_kits/studio/icons.jsx":"fb4d396b2255"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.AlexandriaMagazineDesignSystem_f6284e = window.AlexandriaMagazineDesignSystem_f6284e || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// ui_kits/magazine/app.jsx
try { (() => {
/* global React, COVERS, SCRIMS, AUTHORS, POSTS, TOPICS, Avatar, lucide */

function MIcon({
  name,
  size = 18,
  sw = 2
}) {
  const reg = window.lucide && window.lucide.icons || {};
  const node = reg[name];
  if (!node) return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24"
  });
  const camel = a => {
    const o = {};
    for (const k in a) o[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = a[k];
    return o;
  };
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: sw,
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, node.map((e, i) => React.createElement(e[0], {
    key: i,
    ...camel(e[1])
  })));
}
function Nav({
  onHome
}) {
  return /*#__PURE__*/React.createElement("nav", {
    className: "mnav"
  }, /*#__PURE__*/React.createElement("div", {
    className: "brand",
    onClick: onHome,
    style: {
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logomark.svg",
    width: "36",
    height: "36",
    alt: ""
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "nm"
  }, "Alexandria"), /*#__PURE__*/React.createElement("div", {
    className: "sub"
  }, "MAGAZINE"))), /*#__PURE__*/React.createElement("div", {
    className: "links"
  }, /*#__PURE__*/React.createElement("a", {
    className: "active",
    onClick: onHome
  }, "Inicio"), /*#__PURE__*/React.createElement("a", null, "Temas"), /*#__PURE__*/React.createElement("a", null, "Autores"), /*#__PURE__*/React.createElement("a", null, "Acerca de")), /*#__PURE__*/React.createElement("div", {
    className: "right"
  }, /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    "aria-label": "Buscar"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "search",
    size: 18
  })), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary"
  }, "Suscr\xEDbete")));
}
function Cover({
  id,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: COVERS[id]
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "scrim",
    style: {
      background: SCRIMS[id]
    }
  }), children);
}
function Home({
  onOpen
}) {
  const [topic, setTopic] = React.useState('Todos');
  const feat = POSTS.find(p => p.featured);
  const rest = POSTS.filter(p => !p.featured && (topic === 'Todos' || p.topic === topic));
  const fa = AUTHORS[feat.author];
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("header", {
    className: "hero"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-grid"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow",
    style: {
      color: feat.kc
    }
  }, feat.kicker), /*#__PURE__*/React.createElement("h1", null, feat.title), /*#__PURE__*/React.createElement("p", null, feat.excerpt), /*#__PURE__*/React.createElement("div", {
    className: "byline"
  }, /*#__PURE__*/React.createElement(Avatar, {
    a: fa,
    size: 40
  }), /*#__PURE__*/React.createElement("div", {
    className: "byline-txt"
  }, /*#__PURE__*/React.createElement("div", {
    className: "nm"
  }, fa.name), /*#__PURE__*/React.createElement("div", {
    className: "dt"
  }, feat.date, " \xB7 ", feat.read, " min de lectura")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    style: {
      marginLeft: 12
    },
    onClick: () => onOpen(feat)
  }, "Leer art\xEDculo"))), /*#__PURE__*/React.createElement("div", {
    className: "cover",
    onClick: () => onOpen(feat),
    style: {
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement(Cover, {
    id: feat.cover
  }, /*#__PURE__*/React.createElement("div", {
    className: "cap"
  }, "Figura \xB7 pipeline editorial ag\xE9ntico")))))), /*#__PURE__*/React.createElement("main", {
    className: "wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-head"
  }, /*#__PURE__*/React.createElement("h2", null, "\xDAltimos art\xEDculos")), /*#__PURE__*/React.createElement("div", {
    className: "topics",
    style: {
      marginBottom: 26
    }
  }, TOPICS.map(t => /*#__PURE__*/React.createElement("button", {
    key: t,
    className: `chip${topic === t ? ' active' : ''}`,
    onClick: () => setTopic(t)
  }, t))), /*#__PURE__*/React.createElement("div", {
    className: "feed"
  }, rest.map(p => {
    const a = AUTHORS[p.author];
    return /*#__PURE__*/React.createElement("article", {
      className: "post",
      key: p.id,
      onClick: () => onOpen(p)
    }, /*#__PURE__*/React.createElement("div", {
      className: "thumb"
    }, /*#__PURE__*/React.createElement(Cover, {
      id: p.cover
    })), /*#__PURE__*/React.createElement("span", {
      className: "kicker",
      style: {
        color: p.kc
      }
    }, p.kicker), /*#__PURE__*/React.createElement("h3", null, p.title), /*#__PURE__*/React.createElement("p", {
      className: "ex"
    }, p.excerpt), /*#__PURE__*/React.createElement("div", {
      className: "meta"
    }, /*#__PURE__*/React.createElement(Avatar, {
      a: a,
      size: 24
    }), /*#__PURE__*/React.createElement("span", null, a.name), /*#__PURE__*/React.createElement("span", {
      className: "dot",
      style: {
        width: 3,
        height: 3,
        borderRadius: 9,
        background: 'var(--neutral-40)'
      }
    }), /*#__PURE__*/React.createElement("span", null, p.read, " min")));
  }))), /*#__PURE__*/React.createElement("footer", {
    className: "mfoot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wrap cols"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logomark.svg",
    width: "30",
    height: "30",
    alt: ""
  }), /*#__PURE__*/React.createElement("span", {
    className: "nm"
  }, "Alexandria Magazine")), /*#__PURE__*/React.createElement("p", null, "Ciencia y tecnolog\xEDa redactada con rigor, revisada por personas, publicada con IA.")), /*#__PURE__*/React.createElement("div", {
    className: "col"
  }, /*#__PURE__*/React.createElement("h4", null, "Secciones"), /*#__PURE__*/React.createElement("a", null, "Inteligencia artificial"), /*#__PURE__*/React.createElement("a", null, "Sistemas"), /*#__PURE__*/React.createElement("a", null, "Metodolog\xEDa"), /*#__PURE__*/React.createElement("a", null, "\xC9tica")), /*#__PURE__*/React.createElement("div", {
    className: "col"
  }, /*#__PURE__*/React.createElement("h4", null, "Plataforma"), /*#__PURE__*/React.createElement("a", null, "Studio"), /*#__PURE__*/React.createElement("a", null, "Flow Designer"), /*#__PURE__*/React.createElement("a", null, "Agentes"), /*#__PURE__*/React.createElement("a", null, "API")), /*#__PURE__*/React.createElement("div", {
    className: "col"
  }, /*#__PURE__*/React.createElement("h4", null, "Comunidad"), /*#__PURE__*/React.createElement("a", null, "Autores"), /*#__PURE__*/React.createElement("a", null, "Newsletter"), /*#__PURE__*/React.createElement("a", null, "RSS"), /*#__PURE__*/React.createElement("a", null, "Contacto")))));
}
function Reader({
  post,
  onHome
}) {
  const a = AUTHORS[post.author];
  const [liked, setLiked] = React.useState(false);
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("article", {
    className: "reader"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "reader-head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "eyebrow",
    style: {
      color: post.kc
    }
  }, post.kicker), /*#__PURE__*/React.createElement("h1", null, post.title), /*#__PURE__*/React.createElement("p", {
    className: "lede"
  }, post.excerpt), /*#__PURE__*/React.createElement("div", {
    className: "reader-meta"
  }, /*#__PURE__*/React.createElement("div", {
    className: "m"
  }, /*#__PURE__*/React.createElement(Avatar, {
    a: a,
    size: 30
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--ink-90)',
      fontWeight: 600
    }
  }, a.name)), /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), /*#__PURE__*/React.createElement("div", {
    className: "m"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "calendar",
    size: 14
  }), post.date), /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), /*#__PURE__*/React.createElement("div", {
    className: "m"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "clock",
    size: 14
  }), post.read, " min"), /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), /*#__PURE__*/React.createElement("div", {
    className: "m"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "badge-check",
    size: 14
  }), "Revisado por pares")), /*#__PURE__*/React.createElement("div", {
    className: "tag-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, "APA"), /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, post.topic), /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, "RAG"), /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, "LangGraph"))), /*#__PURE__*/React.createElement("div", {
    className: "reader-cover"
  }, /*#__PURE__*/React.createElement(Cover, {
    id: post.cover
  }, /*#__PURE__*/React.createElement("div", {
    className: "cap",
    style: {
      position: 'absolute',
      left: 22,
      bottom: 18,
      color: 'rgba(255,255,255,.82)',
      fontSize: 12.5
    }
  }, "Figura 1 \xB7 arquitectura del pipeline editorial ag\xE9ntico"))), /*#__PURE__*/React.createElement("div", {
    className: "reader-body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "prose"
  }, /*#__PURE__*/React.createElement("p", {
    className: "has-dropcap"
  }, /*#__PURE__*/React.createElement("strong", null, "Researchers"), " lack an integrated environment that combines AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. Alexandria addresses this with a multi-agent graph compiled at runtime from a visual flow."), /*#__PURE__*/React.createElement("h2", null, "Grounding generation in evidence"), /*#__PURE__*/React.createElement("p", null, "Before composition, the redactor agent retrieves context from the author\\u2019s indexed corpus. Retrieval-augmented generation keeps each claim traceable to ", /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "cited evidence"), " rather than model priors \u2014 the difference between a draft you can submit and one you must rewrite."), /*#__PURE__*/React.createElement("blockquote", null, /*#__PURE__*/React.createElement("p", null, "The orchestrator never publishes autonomously \u2014 a human reviewer approves every article.")), /*#__PURE__*/React.createElement("h3", null, "The review agent"), /*#__PURE__*/React.createElement("p", null, "A dedicated ", /*#__PURE__*/React.createElement("code", null, "revisor"), " evaluates quality and surfaces methodological or citation bias, emitting a calibrated approval score on a 0\u2013100 scale. Articles below the configured threshold route back for revision automatically."), /*#__PURE__*/React.createElement("figure", null, /*#__PURE__*/React.createElement("div", {
    style: {
      aspectRatio: '16/7',
      borderRadius: 8,
      background: COVERS.b,
      position: 'relative',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: SCRIMS.b
    }
  })), /*#__PURE__*/React.createElement("figcaption", null, /*#__PURE__*/React.createElement("span", {
    className: "fig-label"
  }, "Fig. 2 \xB7"), " approval-score distribution across 240 generated drafts.")), /*#__PURE__*/React.createElement("p", null, "Grounded drafts reduced unsupported claims by a factor of 4.3 versus the ungrounded baseline, with no measurable cost to readability."), /*#__PURE__*/React.createElement("h2", null, "Conclusion"), /*#__PURE__*/React.createElement("p", null, "Treating scientific writing as a compiled multi-agent pipeline \u2014 with retrieval, calibrated review, and a human publication gate \u2014 yields drafts that are both faster to produce and safer to publish.")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      marginTop: 40,
      paddingTop: 28,
      borderTop: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement(Avatar, {
    a: a,
    size: 52
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-serif)',
      fontSize: 17,
      fontWeight: 700,
      color: 'var(--ink-100)'
    }
  }, a.name), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: 'var(--text-secondary)',
      marginTop: 3
    }
  }, "Autora \xB7 investigaci\xF3n en sistemas de IA aplicada a la publicaci\xF3n cient\xEDfica.")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    style: {
      marginLeft: 'auto'
    }
  }, "Seguir"))))), /*#__PURE__*/React.createElement("div", {
    className: "toolbar-float"
  }, /*#__PURE__*/React.createElement("button", {
    className: liked ? 'liked' : '',
    onClick: () => setLiked(v => !v),
    "aria-label": "Recomendar"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "heart",
    size: 17,
    sw: liked ? 0 : 2
  })), /*#__PURE__*/React.createElement("span", {
    className: "count"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "heart",
    size: 13
  }), 142 + (liked ? 1 : 0)), /*#__PURE__*/React.createElement("span", {
    className: "div"
  }), /*#__PURE__*/React.createElement("button", {
    "aria-label": "Comentar"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "message-circle",
    size: 17
  })), /*#__PURE__*/React.createElement("button", {
    "aria-label": "Guardar"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "bookmark",
    size: 17
  })), /*#__PURE__*/React.createElement("button", {
    "aria-label": "Compartir"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "share-2",
    size: 17
  })), /*#__PURE__*/React.createElement("span", {
    className: "div"
  }), /*#__PURE__*/React.createElement("button", {
    onClick: onHome,
    "aria-label": "Volar al inicio"
  }, /*#__PURE__*/React.createElement(MIcon, {
    name: "arrow-up",
    size: 17
  }))));
}
function App() {
  const [post, setPost] = React.useState(null);
  React.useEffect(() => {
    window.scrollTo(0, 0);
  }, [post]);
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Nav, {
    onHome: () => setPost(null)
  }), post ? /*#__PURE__*/React.createElement(Reader, {
    post: post,
    onHome: () => setPost(null)
  }) : /*#__PURE__*/React.createElement(Home, {
    onOpen: setPost
  }));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/magazine/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/magazine/data.jsx
try { (() => {
/* global React */
// Magazine sample data + small shared bits.
const COVERS = {
  a: 'linear-gradient(135deg, #0b1b33, #014486)',
  b: 'linear-gradient(135deg, #014486, #0d9dda)',
  c: 'linear-gradient(135deg, #1f3a5f, #6b4fe3)',
  d: 'linear-gradient(135deg, #0b1b33, #06a59a)',
  e: 'linear-gradient(135deg, #16243d, #c47d04)',
  f: 'linear-gradient(135deg, #022a52, #1b96ff)'
};
const SCRIMS = {
  a: 'radial-gradient(circle at 28% 24%, rgba(27,150,255,.42), transparent 60%)',
  b: 'radial-gradient(circle at 70% 30%, rgba(108,192,255,.4), transparent 62%)',
  c: 'radial-gradient(circle at 30% 70%, rgba(154,130,240,.45), transparent 60%)',
  d: 'radial-gradient(circle at 75% 35%, rgba(44,212,198,.4), transparent 62%)',
  e: 'radial-gradient(circle at 30% 30%, rgba(232,176,75,.4), transparent 60%)',
  f: 'radial-gradient(circle at 65% 65%, rgba(27,150,255,.45), transparent 62%)'
};
const AUTHORS = {
  elena: {
    name: 'Elena Vázquez',
    color: '#0176d3',
    initials: 'EV'
  },
  rosa: {
    name: 'Rosa Méndez',
    color: '#6b4fe3',
    initials: 'RM'
  },
  juan: {
    name: 'Juan Soto',
    color: '#06a59a',
    initials: 'JS'
  },
  ana: {
    name: 'Ana López',
    color: '#c47d04',
    initials: 'AL'
  }
};
const POSTS = [{
  id: 'p1',
  cover: 'a',
  kicker: 'Inteligencia artificial',
  kc: '#0176d3',
  topic: 'IA',
  title: 'Retrieval-augmented drafting for marine climate science',
  excerpt: 'A reproducible pipeline that grounds generated drafts in an author\u2019s indexed corpus, preserving citation traceability end to end.',
  author: 'elena',
  date: '28 May 2026',
  read: 8,
  featured: true
}, {
  id: 'p2',
  cover: 'c',
  kicker: 'Infraestructura',
  kc: '#6b4fe3',
  topic: 'Sistemas',
  title: 'Privacy-preserving RAG with local inference',
  excerpt: 'Evaluating Qdrant + Ollama topologies for author-isolated semantic retrieval without external API calls.',
  author: 'rosa',
  date: '24 May 2026',
  read: 11
}, {
  id: 'p3',
  cover: 'd',
  kicker: 'Metodología',
  kc: '#06a59a',
  topic: 'Métodos',
  title: 'Human-in-the-loop publication gates',
  excerpt: 'Why the orchestrator never calls publish() autonomously, and how approval thresholds shape editorial trust.',
  author: 'juan',
  date: '21 May 2026',
  read: 6
}, {
  id: 'p4',
  cover: 'b',
  kicker: 'Ingeniería',
  kc: '#0d9dda',
  topic: 'Sistemas',
  title: 'Dynamic graph compilation for editorial pipelines',
  excerpt: 'Compiling a LangGraph topology at runtime from a visual flow: loops, retries, and conditional routing.',
  author: 'elena',
  date: '19 May 2026',
  read: 9
}, {
  id: 'p5',
  cover: 'e',
  kicker: 'Ética',
  kc: '#c47d04',
  topic: 'IA',
  title: 'Bias detection in the review agent',
  excerpt: 'Surfacing methodological and citation bias during automated review, with a calibrated approval score.',
  author: 'ana',
  date: '14 May 2026',
  read: 7
}, {
  id: 'p6',
  cover: 'f',
  kicker: 'Estándares',
  kc: '#1b96ff',
  topic: 'Métodos',
  title: 'APA, IEEE & Vancouver as formatting adapters',
  excerpt: 'Treating scientific citation styles as interchangeable adapters over a single structured document model.',
  author: 'rosa',
  date: '09 May 2026',
  read: 5
}];
const TOPICS = ['Todos', 'IA', 'Sistemas', 'Métodos', 'Ética', 'Estándares'];
function Avatar({
  a,
  size = 34
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "avatar",
    style: {
      width: size,
      height: size,
      background: a.color,
      fontSize: size * 0.4
    }
  }, a.initials);
}
Object.assign(window, {
  COVERS,
  SCRIMS,
  AUTHORS,
  POSTS,
  TOPICS,
  Avatar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/magazine/data.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/Articles.jsx
try { (() => {
/* global React, Icon, Badge, STATUS, SAMPLE_ARTICLES */
// Articles — filterable grid of article cards + a reading/review detail view.

const TABS = [['all', 'Todos'], ['draft', 'Borradores'], ['in_review', 'Pendientes'], ['approved', 'Aprobados'], ['published', 'Publicados']];
function ArticlesGrid({
  onOpen
}) {
  const [tab, setTab] = React.useState('all');
  const [q, setQ] = React.useState('');
  const list = SAMPLE_ARTICLES.filter(a => (tab === 'all' || a.status === tab) && a.title.toLowerCase().includes(q.toLowerCase()));
  return /*#__PURE__*/React.createElement("div", {
    className: "page"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      marginBottom: 22
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 26,
      fontWeight: 700,
      color: 'var(--ink-100)',
      letterSpacing: '-0.02em'
    }
  }, "Art\xEDculos"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13.5,
      color: 'var(--text-secondary)',
      marginTop: 4
    }
  }, SAMPLE_ARTICLES.length, " art\xEDculos en tu espacio")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Plus",
    size: 15
  }), "Nuevo art\xEDculo")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      marginBottom: 20,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "tabs"
  }, TABS.map(([id, label]) => /*#__PURE__*/React.createElement("button", {
    key: id,
    className: `tab${tab === id ? ' active' : ''}`,
    onClick: () => setTab(id)
  }, label))), /*#__PURE__*/React.createElement("div", {
    className: "search",
    style: {
      flex: 1,
      maxWidth: 280
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Search",
    size: 15,
    style: {
      color: 'var(--text-muted)'
    }
  }), /*#__PURE__*/React.createElement("input", {
    placeholder: "Buscar art\xEDculos\u2026",
    value: q,
    onChange: e => setQ(e.target.value)
  }))), list.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "empty"
  }, /*#__PURE__*/React.createElement("div", {
    className: "eic"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "FileText",
    size: 28
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      color: 'var(--text-secondary)',
      fontWeight: 600
    }
  }, "Sin art\xEDculos"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13
    }
  }, "Ejecuta un pipeline desde el Flow Designer para generar tu primer art\xEDculo.")) : /*#__PURE__*/React.createElement("div", {
    className: "grid"
  }, list.map(a => /*#__PURE__*/React.createElement("div", {
    className: "acard",
    key: a.id,
    onClick: () => onOpen(a)
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      gap: 10,
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "at"
  }, a.title), /*#__PURE__*/React.createElement(Badge, {
    status: a.status
  })), /*#__PURE__*/React.createElement("div", {
    className: "ax"
  }, a.excerpt), /*#__PURE__*/React.createElement("div", {
    className: "am"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Calendar",
    size: 13
  }), /*#__PURE__*/React.createElement("span", null, a.date), /*#__PURE__*/React.createElement(Icon, {
    name: "Clock",
    size: 13
  }), /*#__PURE__*/React.createElement("span", null, a.read, " min"), a.format !== 'none' && /*#__PURE__*/React.createElement("span", {
    className: "tag",
    style: {
      marginLeft: 'auto'
    }
  }, a.format.toUpperCase()))))));
}
function ArticleDetail({
  article,
  onBack,
  toast
}) {
  const [showReject, setShowReject] = React.useState(false);
  const a = article;
  return /*#__PURE__*/React.createElement("div", {
    className: "page",
    style: {
      maxWidth: 960
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 22
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    onClick: onBack,
    style: {
      border: '1px solid var(--border-default)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "ArrowLeft",
    size: 17
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontFamily: 'var(--font-serif)',
      fontSize: 24,
      fontWeight: 700,
      color: 'var(--ink-100)',
      letterSpacing: '-0.01em'
    }
  }, a.title), /*#__PURE__*/React.createElement(Badge, {
    status: a.status
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12.5,
      color: 'var(--text-muted)',
      marginTop: 5
    }
  }, "Creado ", a.date, a.format !== 'none' && ` · Formato ${a.format.toUpperCase()}`))), a.status === 'in_review' && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 11,
      background: 'var(--amber-05)',
      border: '1px solid #f2e0bf',
      borderRadius: 10,
      padding: 14,
      marginBottom: 22
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Clock",
    size: 17,
    style: {
      color: 'var(--amber-60)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("strong", {
    style: {
      color: 'var(--amber-70)'
    }
  }, "Pendiente de aprobaci\xF3n"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)'
    }
  }, "\xB7 revisor asignado"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 270px',
      gap: 24,
      alignItems: 'start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "card card-pad",
    style: {
      padding: 34
    }
  }, /*#__PURE__*/React.createElement("article", {
    className: "prose"
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      marginTop: 0
    }
  }, "Abstract"), /*#__PURE__*/React.createElement("p", null, "We present a reproducible editorial pipeline in which generated drafts are grounded in an author\\u2019s own indexed corpus. Retrieving evidence before composition preserves citation traceability and measurably reduces unsupported claims."), /*#__PURE__*/React.createElement("h2", null, "1 \xB7 Introduction"), /*#__PURE__*/React.createElement("p", null, "Researchers lack an integrated environment combining AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. ", /*#__PURE__*/React.createElement("code", null, "flow_sequence"), " is compiled at runtime from a visual graph."), /*#__PURE__*/React.createElement("blockquote", null, /*#__PURE__*/React.createElement("p", null, "The orchestrator never publishes autonomously \u2014 a human reviewer approves every article.")), /*#__PURE__*/React.createElement("h3", null, "1.1 \xB7 Contributions"), /*#__PURE__*/React.createElement("ul", null, /*#__PURE__*/React.createElement("li", null, "A private RAG design over Qdrant + Ollama."), /*#__PURE__*/React.createElement("li", null, "A calibrated review agent producing an approval score."), /*#__PURE__*/React.createElement("li", null, "Citation-style adapters for APA, IEEE and Vancouver.")))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16
    }
  }, a.status === 'in_review' && /*#__PURE__*/React.createElement("div", {
    className: "card card-pad"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--ink-100)',
      marginBottom: 12
    }
  }, "Acciones de revisi\xF3n"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary btn-block",
    onClick: () => toast('Artículo aprobado')
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 14
  }), "Aprobar art\xEDculo"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-danger btn-block",
    onClick: () => setShowReject(true)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 14
  }), "Rechazar"))), /*#__PURE__*/React.createElement("div", {
    className: "card card-pad"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--ink-100)',
      marginBottom: 12
    }
  }, "Detalles"), [['Estado', STATUS[a.status].label], ['Formato', a.format === 'none' ? 'N/A' : a.format.toUpperCase()], ['Lectura', `${a.read} min`], ['Creado', a.date]].map(([k, v]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 12.5,
      padding: '6px 0',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)'
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--ink-90)',
      fontWeight: 500
    }
  }, v)))), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-accent btn-block"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 14
  }), "Asistir con IA"))), showReject && /*#__PURE__*/React.createElement("div", {
    className: "backdrop",
    onClick: () => setShowReject(false)
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-h"
  }, /*#__PURE__*/React.createElement("h3", null, "Rechazar art\xEDculo"), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    onClick: () => setShowReject(false)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 17
  }))), /*#__PURE__*/React.createElement("div", {
    className: "modal-b"
  }, /*#__PURE__*/React.createElement("div", {
    className: "field"
  }, /*#__PURE__*/React.createElement("label", null, "Motivo del rechazo"), /*#__PURE__*/React.createElement("textarea", {
    className: "inp",
    placeholder: "Explica los cambios necesarios\u2026"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "modal-f"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn btn-ghost",
    onClick: () => setShowReject(false)
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-danger",
    onClick: () => {
      setShowReject(false);
      toast('Artículo rechazado');
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 14
  }), "Confirmar rechazo")))));
}
window.ArticlesGrid = ArticlesGrid;
window.ArticleDetail = ArticleDetail;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/Articles.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/Auth.jsx
try { (() => {
/* global React, Icon */
function Auth({
  onLogin
}) {
  const [tab, setTab] = React.useState('login');
  const [form, setForm] = React.useState({
    name: 'Elena Vázquez',
    email: 'elena@lab.science',
    pass: '••••••••'
  });
  const set = k => e => setForm(f => ({
    ...f,
    [k]: e.target.value
  }));
  const feats = [{
    icon: 'GitBranch',
    text: 'Flow Designer visual con LangGraph'
  }, {
    icon: 'Bot',
    text: 'Agentes: Investigador, Redactor, Revisor…'
  }, {
    icon: 'Zap',
    text: 'Ejecución en tiempo real'
  }, {
    icon: 'Shield',
    text: 'RAG privado · revisión human-in-the-loop'
  }];
  return /*#__PURE__*/React.createElement("div", {
    className: "auth"
  }, /*#__PURE__*/React.createElement("div", {
    className: "auth-left"
  }, /*#__PURE__*/React.createElement("div", {
    className: "inner"
  }, /*#__PURE__*/React.createElement("div", {
    className: "auth-brand"
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logomark.svg",
    width: "40",
    height: "40",
    alt: ""
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "name"
  }, "Alexandria"), /*#__PURE__*/React.createElement("div", {
    className: "sub"
  }, "MAGAZINE"))), /*#__PURE__*/React.createElement("h1", {
    className: "auth-head"
  }, "Redacta ciencia con rigor, publ\xEDcala con confianza."), /*#__PURE__*/React.createElement("p", {
    className: "auth-tag"
  }, "La plataforma ag\xE9ntica para crear, revisar y publicar art\xEDculos cient\xEDficos asistidos por IA."), /*#__PURE__*/React.createElement("div", {
    className: "auth-feats"
  }, feats.map((f, i) => /*#__PURE__*/React.createElement("div", {
    className: "auth-feat",
    key: i
  }, /*#__PURE__*/React.createElement("span", {
    className: "ic"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: f.icon,
    size: 15
  })), f.text))))), /*#__PURE__*/React.createElement("div", {
    className: "auth-right"
  }, /*#__PURE__*/React.createElement("form", {
    className: "auth-form",
    onSubmit: e => {
      e.preventDefault();
      onLogin({
        name: form.name,
        role: 'Autora'
      });
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 22,
      fontWeight: 600,
      color: 'var(--ink-100)'
    }
  }, tab === 'login' ? 'Iniciar sesión' : 'Crear cuenta'), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13.5,
      color: 'var(--text-muted)',
      marginTop: 4
    }
  }, tab === 'login' ? 'Accede a tu espacio de trabajo' : 'Únete a Alexandria Magazine')), /*#__PURE__*/React.createElement("div", {
    className: "tabs",
    style: {
      alignSelf: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: `tab${tab === 'login' ? ' active' : ''}`,
    onClick: () => setTab('login')
  }, "Iniciar sesi\xF3n"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: `tab${tab === 'register' ? ' active' : ''}`,
    onClick: () => setTab('register')
  }, "Registrarse")), tab === 'register' && /*#__PURE__*/React.createElement("div", {
    className: "field"
  }, /*#__PURE__*/React.createElement("label", null, "Nombre completo"), /*#__PURE__*/React.createElement("input", {
    className: "inp",
    value: form.name,
    onChange: set('name')
  })), /*#__PURE__*/React.createElement("div", {
    className: "field"
  }, /*#__PURE__*/React.createElement("label", null, "Email"), /*#__PURE__*/React.createElement("input", {
    className: "inp",
    type: "email",
    value: form.email,
    onChange: set('email')
  })), /*#__PURE__*/React.createElement("div", {
    className: "field"
  }, /*#__PURE__*/React.createElement("label", null, "Contrase\xF1a"), /*#__PURE__*/React.createElement("input", {
    className: "inp",
    type: "password",
    value: form.pass,
    onChange: set('pass')
  })), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary btn-lg btn-block",
    type: "submit"
  }, tab === 'login' ? 'Entrar' : 'Crear cuenta'), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 12.5,
      color: 'var(--text-muted)',
      textAlign: 'center'
    }
  }, tab === 'login' ? '¿No tienes cuenta? ' : '¿Ya tienes cuenta? ', /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setTab(tab === 'login' ? 'register' : 'login'),
    style: {
      background: 'none',
      border: 'none',
      color: 'var(--brand)',
      fontWeight: 600,
      fontSize: 'inherit',
      cursor: 'pointer'
    }
  }, tab === 'login' ? 'Regístrate' : 'Inicia sesión')))));
}
window.Auth = Auth;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/Auth.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/Execution.jsx
try { (() => {
/* global React, Icon, AGENTS */
// Execution — watches the pipeline run step-by-step, streams a log, and
// renders the generated article (Content System .prose) as it completes.

const RUN_SEQ = ['investigador', 'redactor', 'revisor', 'formateador'];
const LOG = [{
  t: 'info',
  m: '→ Compilando grafo dinámico (LangGraph)…'
}, {
  t: 'ok',
  m: '✓ investigador · 12 fuentes recuperadas de Qdrant'
}, {
  t: 'ok',
  m: '✓ redactor · borrador generado (1 842 palabras)'
}, {
  t: 'info',
  m: '→ revisor · evaluando calidad y sesgos…'
}, {
  t: 'ok',
  m: '✓ revisor · approval_score = 86'
}, {
  t: 'ok',
  m: '✓ formateador · estilo APA aplicado'
}];
function Execution({
  title,
  onOpenArticle
}) {
  const [step, setStep] = React.useState(0); // index of currently-running step
  const logRef = React.useRef(null);
  React.useEffect(() => {
    if (step >= RUN_SEQ.length) return;
    const t = setTimeout(() => setStep(s => s + 1), 1100);
    return () => clearTimeout(t);
  }, [step]);
  const done = step >= RUN_SEQ.length;
  const shownLogs = LOG.slice(0, Math.min(LOG.length, step * 1.5 + 1));
  return /*#__PURE__*/React.createElement("div", {
    className: "exec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "exec-side"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 18px',
      borderBottom: '1px solid var(--border-default)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '.07em',
      color: 'var(--text-muted)'
    }
  }, "Ejecuci\xF3n"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-serif)',
      fontSize: 16,
      fontWeight: 700,
      color: 'var(--ink-100)',
      marginTop: 5,
      lineHeight: 1.3
    }
  }, title)), /*#__PURE__*/React.createElement("div", {
    className: "exec-steps"
  }, RUN_SEQ.map((id, i) => {
    const a = AGENTS[id];
    const st = i < step ? 'done' : i === step ? 'running' : 'idle';
    return /*#__PURE__*/React.createElement("div", {
      className: `step${st === 'done' ? ' done' : st === 'running' ? ' running' : ''}`,
      key: id
    }, /*#__PURE__*/React.createElement("div", {
      className: "sic",
      style: {
        background: a.tint,
        color: a.color
      }
    }, st === 'running' ? /*#__PURE__*/React.createElement(Icon, {
      name: "LoaderCircle",
      size: 16,
      style: {
        animation: 'spin 0.8s linear infinite'
      }
    }) : /*#__PURE__*/React.createElement(Icon, {
      name: st === 'done' ? 'Check' : a.icon,
      size: 16
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "snm"
    }, a.label), /*#__PURE__*/React.createElement("div", {
      className: "sst"
    }, st === 'done' ? 'Completado' : st === 'running' ? 'En ejecución…' : 'En espera')), st === 'done' && /*#__PURE__*/React.createElement(Icon, {
      name: "CircleCheck",
      size: 16,
      style: {
        color: 'var(--green-60)'
      }
    }));
  })), /*#__PURE__*/React.createElement("div", {
    className: "exec-log",
    ref: logRef
  }, shownLogs.map((l, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: l.t
  }, l.m)), done && /*#__PURE__*/React.createElement("div", {
    className: "ok"
  }, "\u2713 pipeline finalizado \xB7 estado = in_review"))), /*#__PURE__*/React.createElement("div", {
    className: "exec-main"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '14px 24px',
      borderBottom: '1px solid var(--border-default)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--bg-shell)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: `badge ${done ? 'b-review' : 'b-draft'}`
  }, /*#__PURE__*/React.createElement(Icon, {
    name: done ? 'Clock' : 'LoaderCircle',
    size: 11
  }), done ? 'En revisión' : 'Generando…'), /*#__PURE__*/React.createElement("span", {
    className: "tag"
  }, "APA")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary btn-sm",
    disabled: !done,
    onClick: onOpenArticle
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "ArrowRight",
    size: 14
  }), "Abrir art\xEDculo")), /*#__PURE__*/React.createElement("div", {
    className: "exec-doc"
  }, /*#__PURE__*/React.createElement("article", {
    className: "prose",
    style: {
      margin: '0 auto'
    }
  }, /*#__PURE__*/React.createElement("h1", null, "Retrieval-augmented drafting for marine climate science"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--text-secondary)'
    }
  }, "Borrador generado \xB7 ", RUN_SEQ.length, " agentes \xB7 formato APA"), /*#__PURE__*/React.createElement("h2", null, "Abstract"), /*#__PURE__*/React.createElement("p", null, done ? 'We present a reproducible editorial pipeline in which generated drafts are grounded in an author\u2019s own indexed corpus. By retrieving evidence before composition, the system preserves citation traceability and reduces unsupported claims.' : 'Generando resumen…'), done && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("h2", null, "1 \xB7 Introduction"), /*#__PURE__*/React.createElement("p", null, "Researchers lack an integrated environment that combines AI-assisted writing over private sources, structured scientific formatting, and a controlled review-and-publish workflow. Alexandria addresses this with a multi-agent graph compiled at runtime from a visual flow."), /*#__PURE__*/React.createElement("blockquote", null, /*#__PURE__*/React.createElement("p", null, "The orchestrator never publishes autonomously \u2014 a human reviewer must approve every article.")), /*#__PURE__*/React.createElement("p", null, "The remainder of this article describes the retrieval design, the review agent\\u2019s scoring, and an evaluation against an ungrounded baseline."))))));
}
window.Execution = Execution;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/Execution.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/FlowDesigner.jsx
try { (() => {
/* global React, Icon, AGENTS */
// Flow Designer — palette + canvas of agent nodes wired by edges + toolbar.
// Cosmetic recreation of the @xyflow-based designer (positions are fixed).

const NODES = [{
  id: 'investigador',
  x: 56,
  y: 70,
  type: 'agent'
}, {
  id: 'redactor',
  x: 330,
  y: 70,
  type: 'agent'
}, {
  id: 'revisor',
  x: 604,
  y: 70,
  type: 'agent'
}, {
  id: 'cond',
  x: 626,
  y: 252,
  type: 'cond'
}, {
  id: 'formateador',
  x: 330,
  y: 252,
  type: 'agent'
}, {
  id: 'publicador',
  x: 56,
  y: 252,
  type: 'agent'
}];
const EDGES = ['M244,116 C290,116 290,116 330,116', 'M518,116 C564,116 564,116 604,116', 'M698,162 C698,205 700,210 700,252', 'M626,291 C560,291 580,298 518,298', 'M330,298 C290,298 290,298 244,298'];
function Palette() {
  return /*#__PURE__*/React.createElement("div", {
    className: "palette"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ptitle"
  }, "Agentes"), Object.entries(AGENTS).map(([id, a]) => /*#__PURE__*/React.createElement("div", {
    className: "pnode",
    key: id,
    draggable: true
  }, /*#__PURE__*/React.createElement("div", {
    className: "pic",
    style: {
      background: a.tint,
      color: a.color
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: a.icon,
    size: 15
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "pnm"
  }, a.label), /*#__PURE__*/React.createElement("div", {
    className: "pds"
  }, a.desc)))), /*#__PURE__*/React.createElement("div", {
    className: "ptitle",
    style: {
      marginTop: 8
    }
  }, "L\xF3gica"), /*#__PURE__*/React.createElement("div", {
    className: "pnode",
    draggable: true
  }, /*#__PURE__*/React.createElement("div", {
    className: "pic",
    style: {
      background: 'var(--amber-05)',
      color: 'var(--amber-60)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "GitFork",
    size: 15
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "pnm"
  }, "Condici\xF3n"), /*#__PURE__*/React.createElement("div", {
    className: "pds"
  }, "Bifurcaci\xF3n condicional"))));
}
function AgentNodeBox({
  node,
  selected,
  onSelect
}) {
  if (node.type === 'cond') {
    return /*#__PURE__*/React.createElement("div", {
      className: "node",
      onClick: () => onSelect(node.id),
      style: {
        left: node.x,
        top: node.y,
        width: 150,
        background: 'var(--amber-05)',
        borderColor: '#f2e0bf',
        textAlign: 'center'
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "handle",
      style: {
        left: -5,
        border: '2px solid var(--amber-60)'
      }
    }), /*#__PURE__*/React.createElement(Icon, {
      name: "GitFork",
      size: 16,
      style: {
        color: 'var(--amber-60)'
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 13,
        fontWeight: 600,
        color: 'var(--amber-70)',
        marginTop: 4
      }
    }, "Condici\xF3n"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 10.5,
        color: 'var(--text-muted)',
        marginTop: 3
      }
    }, "score >= 80"), /*#__PURE__*/React.createElement("span", {
      className: "handle",
      style: {
        right: -5,
        top: '34%',
        border: '2px solid var(--green-60)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      className: "handle",
      style: {
        right: -5,
        top: '70%',
        border: '2px solid var(--red-60)'
      }
    }));
  }
  const a = AGENTS[node.id];
  return /*#__PURE__*/React.createElement("div", {
    className: `node${selected ? ' sel' : ''}`,
    onClick: () => onSelect(node.id),
    style: {
      left: node.x,
      top: node.y
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "handle",
    style: {
      left: -5,
      border: `2px solid ${a.color}`
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "nhead"
  }, /*#__PURE__*/React.createElement("div", {
    className: "nic",
    style: {
      background: a.tint,
      color: a.color
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: a.icon,
    size: 16
  })), /*#__PURE__*/React.createElement("span", {
    className: "nnm"
  }, a.label)), /*#__PURE__*/React.createElement("div", {
    className: "nds"
  }, a.desc), /*#__PURE__*/React.createElement("span", {
    className: "nbg",
    style: {
      background: a.tint,
      color: a.color
    }
  }, "agent"), /*#__PURE__*/React.createElement("span", {
    className: "handle",
    style: {
      right: -5,
      border: `2px solid ${a.color}`
    }
  }));
}
function FlowDesigner({
  onRun,
  toast
}) {
  const [selected, setSelected] = React.useState('redactor');
  const [showRun, setShowRun] = React.useState(false);
  const [title, setTitle] = React.useState('');
  const seq = NODES.filter(n => n.type === 'agent').map(n => AGENTS[n.id].label);
  return /*#__PURE__*/React.createElement("div", {
    className: "flow-wrap"
  }, /*#__PURE__*/React.createElement(Palette, null), /*#__PURE__*/React.createElement("div", {
    className: "canvas"
  }, /*#__PURE__*/React.createElement("svg", {
    style: {
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      pointerEvents: 'none'
    }
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("marker", {
    id: "arrow",
    markerWidth: "9",
    markerHeight: "9",
    refX: "7",
    refY: "4.5",
    orient: "auto"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1,1 L7,4.5 L1,8",
    fill: "none",
    stroke: "#0176d3",
    strokeWidth: "1.6",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), EDGES.map((d, i) => /*#__PURE__*/React.createElement("path", {
    key: i,
    d: d,
    fill: "none",
    stroke: "#0176d3",
    strokeWidth: "2",
    markerEnd: "url(#arrow)",
    strokeDasharray: "5 4",
    opacity: "0.85"
  }, /*#__PURE__*/React.createElement("animate", {
    attributeName: "stroke-dashoffset",
    from: "18",
    to: "0",
    dur: "0.9s",
    repeatCount: "indefinite"
  })))), NODES.map(n => /*#__PURE__*/React.createElement(AgentNodeBox, {
    key: n.id,
    node: n,
    selected: selected === n.id,
    onSelect: setSelected
  })), /*#__PURE__*/React.createElement("div", {
    className: "flow-toolbar"
  }, /*#__PURE__*/React.createElement("input", {
    className: "inp",
    style: {
      width: 190,
      padding: '6px 10px'
    },
    placeholder: "Nombre del flujo",
    value: title,
    onChange: e => setTitle(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 1,
      height: 22,
      background: 'var(--border-default)'
    }
  }), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    title: "Limpiar"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Trash2",
    size: 15
  })), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-secondary btn-sm",
    onClick: () => toast('Flujo guardado')
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Save",
    size: 14
  }), "Guardar"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary btn-sm",
    onClick: () => setShowRun(true)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Play",
    size: 14
  }), "Ejecutar"))), showRun && /*#__PURE__*/React.createElement("div", {
    className: "backdrop",
    onClick: () => setShowRun(false)
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-h"
  }, /*#__PURE__*/React.createElement("h3", null, "Ejecutar pipeline"), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    onClick: () => setShowRun(false)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 17
  }))), /*#__PURE__*/React.createElement("div", {
    className: "modal-b"
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13.5,
      color: 'var(--text-secondary)',
      lineHeight: 1.6
    }
  }, "Se crear\xE1 un nuevo art\xEDculo y se ejecutar\xE1 el pipeline sobre \xE9l."), /*#__PURE__*/React.createElement("div", {
    className: "field"
  }, /*#__PURE__*/React.createElement("label", null, "T\xEDtulo del art\xEDculo"), /*#__PURE__*/React.createElement("input", {
    className: "inp",
    autoFocus: true,
    placeholder: "Ej: El impacto del cambio clim\xE1tico en ecosistemas marinos",
    value: title,
    onChange: e => setTitle(e.target.value)
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--bg-sunken)',
      borderRadius: 8,
      padding: 12,
      fontSize: 12,
      color: 'var(--text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("strong", {
    style: {
      color: 'var(--ink-90)'
    }
  }, "Secuencia:"), " ", seq.join('  →  '))), /*#__PURE__*/React.createElement("div", {
    className: "modal-f"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn btn-ghost",
    onClick: () => setShowRun(false)
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    onClick: () => {
      setShowRun(false);
      onRun(title || 'Nuevo artículo');
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Play",
    size: 14
  }), "Ejecutar pipeline")))));
}
window.FlowDesigner = FlowDesigner;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/FlowDesigner.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/app.jsx
try { (() => {
/* global React, ReactDOM, Icon, AGENTS, Sidebar, TopBar, Auth, FlowDesigner, Execution, ArticlesGrid, ArticleDetail, SAMPLE_ARTICLES */

function AgentsPage() {
  return /*#__PURE__*/React.createElement("div", {
    className: "page"
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 26,
      fontWeight: 700,
      color: 'var(--ink-100)',
      letterSpacing: '-0.02em'
    }
  }, "Agentes"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13.5,
      color: 'var(--text-secondary)',
      margin: '4px 0 22px'
    }
  }, "Los cinco agentes editoriales disponibles para tus flujos."), /*#__PURE__*/React.createElement("div", {
    className: "grid"
  }, Object.entries(AGENTS).map(([id, a]) => /*#__PURE__*/React.createElement("div", {
    className: "card card-pad",
    key: id,
    style: {
      display: 'flex',
      gap: 14,
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "nic",
    style: {
      width: 40,
      height: 40,
      borderRadius: 10,
      background: a.tint,
      color: a.color,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: a.icon,
    size: 20
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 600,
      color: 'var(--ink-100)'
    }
  }, a.label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12.5,
      color: 'var(--text-secondary)',
      marginTop: 4,
      lineHeight: 1.5
    }
  }, a.desc))))));
}
function ConfigPage() {
  const rows = [['min_approval_score', '80', 'Score mínimo del revisor para aprobar'], ['default_model', 'llama3.2', 'Modelo de inferencia local (Ollama)'], ['vector_size', '1536', 'Dimensión del embedding (Qdrant)'], ['allow_custom_topology', 'true', 'Permitir flujos personalizados']];
  return /*#__PURE__*/React.createElement("div", {
    className: "page",
    style: {
      maxWidth: 760
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 26,
      fontWeight: 700,
      color: 'var(--ink-100)',
      letterSpacing: '-0.02em'
    }
  }, "Configuraci\xF3n"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13.5,
      color: 'var(--text-secondary)',
      margin: '4px 0 22px'
    }
  }, "Par\xE1metros globales (config.yaml)."), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '13px 18px',
      borderBottom: '1px solid var(--border-subtle)',
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--ink-100)',
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "SlidersHorizontal",
    size: 15
  }), "Reglas editoriales"), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '6px 18px'
    }
  }, rows.map(([k, v, d]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 16,
      padding: '13px 0',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 13,
      color: 'var(--ink-90)'
    }
  }, k), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: 'var(--text-muted)',
      marginTop: 2
    }
  }, d)), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 13,
      color: 'var(--brand)',
      background: 'var(--blue-05)',
      padding: '4px 10px',
      borderRadius: 6
    }
  }, v))))));
}
const TITLES = {
  flow: 'Flow Designer',
  articles: 'Artículos',
  agents: 'Agentes',
  config: 'Configuración',
  exec: 'Ejecución'
};
function App() {
  const [authed, setAuthed] = React.useState(false);
  const [user, setUser] = React.useState({
    name: 'Elena Vázquez',
    role: 'Autora'
  });
  const [page, setPage] = React.useState('flow');
  const [execTitle, setExecTitle] = React.useState('');
  const [openArticle, setOpenArticle] = React.useState(null);
  const [toastMsg, setToastMsg] = React.useState(null);
  const toast = m => {
    setToastMsg(m);
    clearTimeout(window.__t);
    window.__t = setTimeout(() => setToastMsg(null), 2200);
  };
  if (!authed) return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Auth, {
    onLogin: u => {
      setUser(u);
      setAuthed(true);
      setPage('flow');
    }
  }));
  let content,
    title = TITLES[page];
  if (openArticle) {
    content = /*#__PURE__*/React.createElement(ArticleDetail, {
      article: openArticle,
      onBack: () => setOpenArticle(null),
      toast: toast
    });
    title = 'Artículo';
  } else if (page === 'flow') content = /*#__PURE__*/React.createElement(FlowDesigner, {
    onRun: t => {
      setExecTitle(t);
      setPage('exec');
    },
    toast: toast
  });else if (page === 'exec') content = /*#__PURE__*/React.createElement(Execution, {
    title: execTitle,
    onOpenArticle: () => {
      setOpenArticle(SAMPLE_ARTICLES[0]);
    }
  });else if (page === 'articles') content = /*#__PURE__*/React.createElement(ArticlesGrid, {
    onOpen: setOpenArticle
  });else if (page === 'agents') content = /*#__PURE__*/React.createElement(AgentsPage, null);else if (page === 'config') content = /*#__PURE__*/React.createElement(ConfigPage, null);
  const fullBleed = (page === 'flow' || page === 'exec') && !openArticle;
  const navActive = openArticle ? 'articles' : page === 'exec' ? 'flow' : page;
  return /*#__PURE__*/React.createElement("div", {
    className: "app"
  }, /*#__PURE__*/React.createElement(Sidebar, {
    active: navActive,
    onNav: p => {
      setOpenArticle(null);
      setPage(p);
    },
    user: user
  }), /*#__PURE__*/React.createElement("div", {
    className: "main"
  }, /*#__PURE__*/React.createElement(TopBar, {
    title: title
  }, page === 'flow' && !openArticle && /*#__PURE__*/React.createElement("button", {
    className: "btn btn-secondary btn-sm"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Plus",
    size: 14
  }), "Nuevo flujo")), fullBleed ? /*#__PURE__*/React.createElement("div", {
    className: "body",
    style: {
      overflow: 'hidden'
    }
  }, content) : /*#__PURE__*/React.createElement("div", {
    className: "body"
  }, content)), toastMsg && /*#__PURE__*/React.createElement("div", {
    className: "toast"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 15,
    style: {
      color: '#6ee7a8'
    }
  }), toastMsg));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/components.jsx
try { (() => {
/* global React, Icon */
// Shared Studio primitives, app shell, agent metadata & sample data.

const AGENTS = {
  investigador: {
    label: 'Investigador',
    icon: 'Search',
    color: '#0d9dda',
    tint: '#e6f6fc',
    desc: 'Busca contexto en RAG y APIs científicas'
  },
  redactor: {
    label: 'Redactor',
    icon: 'PenLine',
    color: '#6b4fe3',
    tint: '#f1eefe',
    desc: 'Genera el borrador con Ollama'
  },
  revisor: {
    label: 'Revisor',
    icon: 'Eye',
    color: '#c47d04',
    tint: '#fdf3e3',
    desc: 'Evalúa calidad · score 0–100'
  },
  formateador: {
    label: 'Formateador',
    icon: 'FileText',
    color: '#2e844a',
    tint: '#ebf7ee',
    desc: 'Aplica formato APA / IEEE / Vancouver'
  },
  publicador: {
    label: 'Publicador',
    icon: 'Send',
    color: '#cb4b3f',
    tint: '#fdeeec',
    desc: 'Publica el artículo'
  }
};
const STATUS = {
  draft: {
    label: 'Borrador',
    cls: 'b-draft',
    icon: 'CircleDashed'
  },
  in_review: {
    label: 'En revisión',
    cls: 'b-review',
    icon: 'Clock'
  },
  approved: {
    label: 'Aprobado',
    cls: 'b-approved',
    icon: 'Check'
  },
  published: {
    label: 'Publicado',
    cls: 'b-published',
    icon: 'Globe'
  },
  rejected: {
    label: 'Rechazado',
    cls: 'b-rejected',
    icon: 'X'
  }
};
const SAMPLE_ARTICLES = [{
  id: 'a1',
  title: 'Retrieval-augmented drafting for marine climate science',
  status: 'published',
  format: 'apa',
  date: '28 May 2026',
  read: 8,
  excerpt: 'A reproducible pipeline that grounds generated drafts in an author\u2019s indexed corpus, preserving citation traceability end to end.'
}, {
  id: 'a2',
  title: 'Privacy-preserving RAG with local inference',
  status: 'in_review',
  format: 'ieee',
  date: '24 May 2026',
  read: 11,
  excerpt: 'We evaluate Qdrant + Ollama topologies for author-isolated semantic retrieval without external API calls.'
}, {
  id: 'a3',
  title: 'Human-in-the-loop publication gates',
  status: 'approved',
  format: 'apa',
  date: '21 May 2026',
  read: 6,
  excerpt: 'Why the orchestrator never calls publish() autonomously, and how approval thresholds shape editorial trust.'
}, {
  id: 'a4',
  title: 'Dynamic graph compilation for editorial pipelines',
  status: 'draft',
  format: 'none',
  date: '19 May 2026',
  read: 9,
  excerpt: 'Compiling a LangGraph topology at runtime from a visual flow: loops, retries, and conditional routing.'
}, {
  id: 'a5',
  title: 'Bias detection in the review agent',
  status: 'published',
  format: 'vancouver',
  date: '14 May 2026',
  read: 7,
  excerpt: 'Surfacing methodological and citation bias during automated review, with a calibrated approval score.'
}, {
  id: 'a6',
  title: 'Structured formats: APA, IEEE & Vancouver as adapters',
  status: 'rejected',
  format: 'none',
  date: '09 May 2026',
  read: 5,
  excerpt: 'Treating scientific citation styles as interchangeable formatting adapters over a single document model.'
}];
function Avatar({
  name,
  size = 32
}) {
  const initials = name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  return /*#__PURE__*/React.createElement("div", {
    className: "avatar",
    style: {
      width: size,
      height: size,
      fontSize: size * 0.4
    }
  }, initials);
}
function Badge({
  status
}) {
  const s = STATUS[status] || STATUS.draft;
  return /*#__PURE__*/React.createElement("span", {
    className: `badge ${s.cls}`
  }, /*#__PURE__*/React.createElement(Icon, {
    name: s.icon,
    size: 11
  }), s.label);
}
function Sidebar({
  active,
  onNav,
  user
}) {
  const items = [{
    sec: 'Workspace'
  }, {
    id: 'flow',
    label: 'Flow Designer',
    icon: 'GitBranch'
  }, {
    id: 'articles',
    label: 'Artículos',
    icon: 'FileText'
  }, {
    id: 'agents',
    label: 'Agentes',
    icon: 'Bot'
  }, {
    sec: 'Cuenta'
  }, {
    id: 'config',
    label: 'Configuración',
    icon: 'Settings'
  }];
  return /*#__PURE__*/React.createElement("aside", {
    className: "sidebar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "side-logo"
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logomark.svg",
    width: "34",
    height: "34",
    alt: ""
  }), /*#__PURE__*/React.createElement("div", {
    className: "wm"
  }, /*#__PURE__*/React.createElement("span", {
    className: "name"
  }, "Alexandria"), /*#__PURE__*/React.createElement("span", {
    className: "sub"
  }, "MAGAZINE"))), /*#__PURE__*/React.createElement("nav", {
    className: "side-nav"
  }, items.map((it, i) => it.sec ? /*#__PURE__*/React.createElement("div", {
    className: "nav-sec",
    key: i
  }, it.sec) : /*#__PURE__*/React.createElement("button", {
    key: it.id,
    className: `nav-item${active === it.id ? ' active' : ''}`,
    onClick: () => onNav(it.id)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: it.icon,
    size: 17
  }), it.label))), /*#__PURE__*/React.createElement("div", {
    className: "side-foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "user-row"
  }, /*#__PURE__*/React.createElement(Avatar, {
    name: user.name
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "nm"
  }, user.name), /*#__PURE__*/React.createElement("div", {
    className: "rl"
  }, user.role)), /*#__PURE__*/React.createElement(Icon, {
    name: "LogOut",
    size: 15,
    style: {
      color: 'var(--text-muted)'
    }
  }))));
}
function TopBar({
  title,
  children
}) {
  return /*#__PURE__*/React.createElement("header", {
    className: "topbar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ttl"
  }, title), /*#__PURE__*/React.createElement("div", {
    className: "actions"
  }, children, /*#__PURE__*/React.createElement("button", {
    className: "icon-btn"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Bell",
    size: 18
  }), /*#__PURE__*/React.createElement("span", {
    className: "notif-dot"
  })), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "CircleHelp",
    size: 18
  }))));
}
Object.assign(window, {
  AGENTS,
  STATUS,
  SAMPLE_ARTICLES,
  Avatar,
  Badge,
  Sidebar,
  TopBar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/components.jsx", error: String((e && e.message) || e) }); }

// ui_kits/studio/icons.jsx
try { (() => {
/* global React */
// Icon — renders Lucide icons from the UMD `lucide.icons` registry.
// Lucide is the product's icon system (lucide-react). Names are PascalCase.
(function () {
  const cache = {};
  function camel(attrs) {
    const out = {};
    for (const k in attrs) {
      const ck = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      out[ck] = attrs[k];
    }
    return out;
  }
  function Icon({
    name,
    size = 16,
    strokeWidth = 2,
    style,
    className
  }) {
    const reg = window.lucide && window.lucide.icons || {};
    const node = reg[name];
    if (!node) {
      // graceful fallback: empty box so layout never breaks
      return React.createElement('svg', {
        width: size,
        height: size,
        viewBox: '0 0 24 24'
      });
    }
    const children = node.map((entry, i) => {
      const [tag, attrs] = entry;
      return React.createElement(tag, Object.assign({
        key: i
      }, camel(attrs)));
    });
    return React.createElement('svg', {
      width: size,
      height: size,
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      strokeWidth,
      strokeLinecap: 'round',
      strokeLinejoin: 'round',
      style,
      className
    }, children);
  }
  window.Icon = Icon;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/studio/icons.jsx", error: String((e && e.message) || e) }); }

})();
