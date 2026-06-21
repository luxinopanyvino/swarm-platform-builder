/* global React, Icon, AGENTS */
// Flow Designer — palette + canvas of agent nodes wired by edges + toolbar.
// Cosmetic recreation of the @xyflow-based designer (positions are fixed).

const NODES = [
  { id: 'investigador', x: 56,  y: 70,  type: 'agent' },
  { id: 'redactor',     x: 330, y: 70,  type: 'agent' },
  { id: 'revisor',      x: 604, y: 70,  type: 'agent' },
  { id: 'cond',         x: 626, y: 252, type: 'cond' },
  { id: 'formateador',  x: 330, y: 252, type: 'agent' },
  { id: 'publicador',   x: 56,  y: 252, type: 'agent' },
];
const EDGES = [
  'M244,116 C290,116 290,116 330,116',
  'M518,116 C564,116 564,116 604,116',
  'M698,162 C698,205 700,210 700,252',
  'M626,291 C560,291 580,298 518,298',
  'M330,298 C290,298 290,298 244,298',
];

function Palette() {
  return (
    <div className="palette">
      <div className="ptitle">Agentes</div>
      {Object.entries(AGENTS).map(([id, a]) => (
        <div className="pnode" key={id} draggable>
          <div className="pic" style={{ background: a.tint, color: a.color }}><Icon name={a.icon} size={15} /></div>
          <div><div className="pnm">{a.label}</div><div className="pds">{a.desc}</div></div>
        </div>
      ))}
      <div className="ptitle" style={{ marginTop: 8 }}>Lógica</div>
      <div className="pnode" draggable>
        <div className="pic" style={{ background: 'var(--amber-05)', color: 'var(--amber-60)' }}><Icon name="GitFork" size={15} /></div>
        <div><div className="pnm">Condición</div><div className="pds">Bifurcación condicional</div></div>
      </div>
    </div>
  );
}

function AgentNodeBox({ node, selected, onSelect }) {
  if (node.type === 'cond') {
    return (
      <div className="node" onClick={() => onSelect(node.id)}
        style={{ left: node.x, top: node.y, width: 150, background: 'var(--amber-05)', borderColor: '#f2e0bf', textAlign: 'center' }}>
        <span className="handle" style={{ left: -5, border: '2px solid var(--amber-60)' }} />
        <Icon name="GitFork" size={16} style={{ color: 'var(--amber-60)' }} />
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--amber-70)', marginTop: 4 }}>Condición</div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>score &gt;= 80</div>
        <span className="handle" style={{ right: -5, top: '34%', border: '2px solid var(--green-60)' }} />
        <span className="handle" style={{ right: -5, top: '70%', border: '2px solid var(--red-60)' }} />
      </div>
    );
  }
  const a = AGENTS[node.id];
  return (
    <div className={`node${selected ? ' sel' : ''}`} onClick={() => onSelect(node.id)} style={{ left: node.x, top: node.y }}>
      <span className="handle" style={{ left: -5, border: `2px solid ${a.color}` }} />
      <div className="nhead"><div className="nic" style={{ background: a.tint, color: a.color }}><Icon name={a.icon} size={16} /></div><span className="nnm">{a.label}</span></div>
      <div className="nds">{a.desc}</div>
      <span className="nbg" style={{ background: a.tint, color: a.color }}>agent</span>
      <span className="handle" style={{ right: -5, border: `2px solid ${a.color}` }} />
    </div>
  );
}

function FlowDesigner({ onRun, toast }) {
  const [selected, setSelected] = React.useState('redactor');
  const [showRun, setShowRun] = React.useState(false);
  const [title, setTitle] = React.useState('');
  const seq = NODES.filter(n => n.type === 'agent').map(n => AGENTS[n.id].label);

  return (
    <div className="flow-wrap">
      <Palette />
      <div className="canvas">
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
          <defs>
            <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
              <path d="M1,1 L7,4.5 L1,8" fill="none" stroke="#0176d3" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </marker>
          </defs>
          {EDGES.map((d, i) => (
            <path key={i} d={d} fill="none" stroke="#0176d3" strokeWidth="2" markerEnd="url(#arrow)"
              strokeDasharray="5 4" opacity="0.85">
              <animate attributeName="stroke-dashoffset" from="18" to="0" dur="0.9s" repeatCount="indefinite" />
            </path>
          ))}
        </svg>
        {NODES.map(n => <AgentNodeBox key={n.id} node={n} selected={selected === n.id} onSelect={setSelected} />)}

        <div className="flow-toolbar">
          <input className="inp" style={{ width: 190, padding: '6px 10px' }} placeholder="Nombre del flujo" value={title} onChange={e => setTitle(e.target.value)} />
          <div style={{ width: 1, height: 22, background: 'var(--border-default)' }} />
          <button className="icon-btn" title="Limpiar"><Icon name="Trash2" size={15} /></button>
          <button className="btn btn-secondary btn-sm" onClick={() => toast('Flujo guardado')}><Icon name="Save" size={14} />Guardar</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowRun(true)}><Icon name="Play" size={14} />Ejecutar</button>
        </div>
      </div>

      {showRun && (
        <div className="backdrop" onClick={() => setShowRun(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-h"><h3>Ejecutar pipeline</h3><button className="icon-btn" onClick={() => setShowRun(false)}><Icon name="X" size={17} /></button></div>
            <div className="modal-b">
              <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>Se creará un nuevo artículo y se ejecutará el pipeline sobre él.</p>
              <div className="field"><label>Título del artículo</label>
                <input className="inp" autoFocus placeholder="Ej: El impacto del cambio climático en ecosistemas marinos" value={title} onChange={e => setTitle(e.target.value)} /></div>
              <div style={{ background: 'var(--bg-sunken)', borderRadius: 8, padding: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--ink-90)' }}>Secuencia:</strong> {seq.join('  →  ')}
              </div>
            </div>
            <div className="modal-f">
              <button className="btn btn-ghost" onClick={() => setShowRun(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={() => { setShowRun(false); onRun(title || 'Nuevo artículo'); }}><Icon name="Play" size={14} />Ejecutar pipeline</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
window.FlowDesigner = FlowDesigner;
