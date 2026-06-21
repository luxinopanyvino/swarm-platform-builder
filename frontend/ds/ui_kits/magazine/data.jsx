/* global React */
// Magazine sample data + small shared bits.
const COVERS = {
  a: 'linear-gradient(135deg, #0b1b33, #014486)',
  b: 'linear-gradient(135deg, #014486, #0d9dda)',
  c: 'linear-gradient(135deg, #1f3a5f, #6b4fe3)',
  d: 'linear-gradient(135deg, #0b1b33, #06a59a)',
  e: 'linear-gradient(135deg, #16243d, #c47d04)',
  f: 'linear-gradient(135deg, #022a52, #1b96ff)',
};
const SCRIMS = {
  a: 'radial-gradient(circle at 28% 24%, rgba(27,150,255,.42), transparent 60%)',
  b: 'radial-gradient(circle at 70% 30%, rgba(108,192,255,.4), transparent 62%)',
  c: 'radial-gradient(circle at 30% 70%, rgba(154,130,240,.45), transparent 60%)',
  d: 'radial-gradient(circle at 75% 35%, rgba(44,212,198,.4), transparent 62%)',
  e: 'radial-gradient(circle at 30% 30%, rgba(232,176,75,.4), transparent 60%)',
  f: 'radial-gradient(circle at 65% 65%, rgba(27,150,255,.45), transparent 62%)',
};

const AUTHORS = {
  elena: { name: 'Elena Vázquez', color: '#0176d3', initials: 'EV' },
  rosa:  { name: 'Rosa Méndez', color: '#6b4fe3', initials: 'RM' },
  juan:  { name: 'Juan Soto', color: '#06a59a', initials: 'JS' },
  ana:   { name: 'Ana López', color: '#c47d04', initials: 'AL' },
};

const POSTS = [
  { id: 'p1', cover: 'a', kicker: 'Inteligencia artificial', kc: '#0176d3', topic: 'IA',
    title: 'Retrieval-augmented drafting for marine climate science',
    excerpt: 'A reproducible pipeline that grounds generated drafts in an author\u2019s indexed corpus, preserving citation traceability end to end.',
    author: 'elena', date: '28 May 2026', read: 8, featured: true },
  { id: 'p2', cover: 'c', kicker: 'Infraestructura', kc: '#6b4fe3', topic: 'Sistemas',
    title: 'Privacy-preserving RAG with local inference',
    excerpt: 'Evaluating Qdrant + Ollama topologies for author-isolated semantic retrieval without external API calls.',
    author: 'rosa', date: '24 May 2026', read: 11 },
  { id: 'p3', cover: 'd', kicker: 'Metodología', kc: '#06a59a', topic: 'Métodos',
    title: 'Human-in-the-loop publication gates',
    excerpt: 'Why the orchestrator never calls publish() autonomously, and how approval thresholds shape editorial trust.',
    author: 'juan', date: '21 May 2026', read: 6 },
  { id: 'p4', cover: 'b', kicker: 'Ingeniería', kc: '#0d9dda', topic: 'Sistemas',
    title: 'Dynamic graph compilation for editorial pipelines',
    excerpt: 'Compiling a LangGraph topology at runtime from a visual flow: loops, retries, and conditional routing.',
    author: 'elena', date: '19 May 2026', read: 9 },
  { id: 'p5', cover: 'e', kicker: 'Ética', kc: '#c47d04', topic: 'IA',
    title: 'Bias detection in the review agent',
    excerpt: 'Surfacing methodological and citation bias during automated review, with a calibrated approval score.',
    author: 'ana', date: '14 May 2026', read: 7 },
  { id: 'p6', cover: 'f', kicker: 'Estándares', kc: '#1b96ff', topic: 'Métodos',
    title: 'APA, IEEE & Vancouver as formatting adapters',
    excerpt: 'Treating scientific citation styles as interchangeable adapters over a single structured document model.',
    author: 'rosa', date: '09 May 2026', read: 5 },
];

const TOPICS = ['Todos', 'IA', 'Sistemas', 'Métodos', 'Ética', 'Estándares'];

function Avatar({ a, size = 34 }) {
  return <div className="avatar" style={{ width: size, height: size, background: a.color, fontSize: size * 0.4 }}>{a.initials}</div>;
}

Object.assign(window, { COVERS, SCRIMS, AUTHORS, POSTS, TOPICS, Avatar });
