// Validación del grafo del Flow Designer (BUG-001 / VAL-004).
//
// Es feedback inmediato, no la garantía: el backend (`app/platform/flow_validation.py`)
// revalida al guardar y al ejecutar porque cualquiera puede saltarse la interfaz.
// Los códigos de regla, los mensajes y el orden de ejecución coinciden con los
// suyos. Las reglas de dependencia entre agentes **no están aquí**: las declara el
// proyecto en su `template.yaml` y llegan por `GET /api/v1/flows/rules`.

export const ERROR = 'error';
export const WARNING = 'warning';

export const SELF_LOOP = 'self_loop';
export const CYCLE = 'cycle';
export const ORPHAN = 'orphan';
export const MISSING_DEPENDENCY = 'missing_dependency';
export const WRONG_ORDER = 'wrong_order';

export const SELF_LOOP_MESSAGE = 'Un agente no puede conectarse consigo mismo';

export const NO_RULES = { requires: [], orphans: null };

const label = (agent) => agent.charAt(0).toUpperCase() + agent.slice(1);

export const isSelfLoop = (edge) =>
  Boolean(edge) && edge.source != null && edge.source === edge.target;

/** Valida una conexión en curso (arrastre o soltado). `null` si es válida. */
export function validateConnection(connection) {
  if (isSelfLoop(connection)) {
    return { code: SELF_LOOP, severity: ERROR, message: SELF_LOOP_MESSAGE, nodes: [connection.source], edges: [] };
  }
  return null;
}

const edgeId = (e) => e.id || `${e.source}->${e.target}`;

const agentNodes = (nodes) =>
  (nodes || [])
    .filter((n) => n && n.id != null && n.data?.agentId)
    .map((n) => ({ id: String(n.id), agent: String(n.data.agentId) }));

const linksBetween = (edges, known) =>
  (edges || [])
    .filter((e) => e && e.source != null && e.target != null && e.source !== e.target
      && known.has(String(e.source)) && known.has(String(e.target)))
    .map((e) => ({ id: edgeId(e), source: String(e.source), target: String(e.target) }));

function cycleNodes(ids, links) {
  const alive = new Set(ids);
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of [...alive]) {
      const entra = links.some((l) => l.target === n && alive.has(l.source));
      const sale = links.some((l) => l.source === n && alive.has(l.target));
      if (!(entra && sale)) {
        alive.delete(n);
        changed = true;
      }
    }
  }
  return alive;
}

/**
 * Orden de ejecución de los nodos de agente: topológico y, en los empates, el
 * del lienzo. Es el que ejecuta el motor, que corre `flow_sequence` y no las
 * aristas. Un ciclo no tiene orden: sus nodos van al final.
 */
export function effectiveOrder(nodes, edges) {
  const agents = agentNodes(nodes);
  const index = new Map(agents.map((a, i) => [a.id, i]));
  const links = linksBetween(edges, new Set(index.keys()));
  const incoming = new Map(agents.map((a) => [a.id, 0]));
  links.forEach((l) => incoming.set(l.target, incoming.get(l.target) + 1));
  const byIndex = (a, b) => index.get(a) - index.get(b);
  const ready = agents.filter((a) => incoming.get(a.id) === 0).map((a) => a.id).sort(byIndex);
  const order = [];
  while (ready.length) {
    const n = ready.shift();
    order.push(n);
    links.filter((l) => l.source === n).forEach((l) => {
      incoming.set(l.target, incoming.get(l.target) - 1);
      if (incoming.get(l.target) === 0) ready.push(l.target);
    });
    ready.sort(byIndex);
  }
  const rest = agents.map((a) => a.id).filter((id) => !order.includes(id)).sort(byIndex);
  return [...order, ...rest];
}

/** Los ids de agente en el orden en que se ejecutarán (`flow_sequence`). */
export function effectiveSequence(nodes, edges) {
  const byId = new Map(agentNodes(nodes).map((a) => [a.id, a.agent]));
  return effectiveOrder(nodes, edges).map((id) => byId.get(id));
}

function checkRequirements(ordered, rules, links) {
  const issues = [];
  for (const req of rules.requires || []) {
    ordered.forEach(({ id, agent }, pos) => {
      if (agent !== req.agent) return;
      const before = new Set(ordered.slice(0, pos).map((o) => o.agent));
      if (req.any_of.some((a) => before.has(a))) return;
      const after = ordered.slice(pos + 1).filter((o) => req.any_of.includes(o.agent)).map((o) => o.id);
      const required = req.any_of.map(label).join(', ');
      const wrong = after.length > 0;
      issues.push({
        code: wrong ? WRONG_ORDER : MISSING_DEPENDENCY,
        severity: req.severity,
        message: wrong
          ? `${label(agent)} no puede ejecutarse antes de ${required}`
          : `${label(agent)} necesita ${required} antes en el flujo`,
        nodes: [id, ...after],
        edges: wrong
          ? links.filter((l) => l.source === id && after.includes(l.target)).map((l) => l.id)
          : links.filter((l) => l.target === id).map((l) => l.id),
      });
    });
  }
  return issues;
}

/** Todos los problemas del grafo, bloqueantes y avisos. */
export function validateFlow(nodes, edges, rules = NO_RULES) {
  const issues = (edges || []).filter(isSelfLoop).map((edge) => ({
    code: SELF_LOOP, severity: ERROR, message: SELF_LOOP_MESSAGE, nodes: [edge.source], edges: [edge.id],
  }));

  const agents = agentNodes(nodes);
  const links = linksBetween(edges, new Set(agents.map((a) => a.id)));

  const cycle = cycleNodes(agents.map((a) => a.id), links);
  if (cycle.size) {
    const inCycle = agents.filter((a) => cycle.has(a.id));
    issues.push({
      code: CYCLE,
      severity: ERROR,
      message: `El flujo tiene un ciclo entre ${inCycle.map((a) => label(a.agent)).join(', ')}`,
      nodes: inCycle.map((a) => a.id),
      edges: links.filter((l) => cycle.has(l.source) && cycle.has(l.target)).map((l) => l.id),
    });
  }

  if (rules.orphans && agents.length > 1) {
    const connected = new Set(links.flatMap((l) => [l.source, l.target]));
    agents.filter((a) => !connected.has(a.id)).forEach((a) => issues.push({
      code: ORPHAN,
      severity: rules.orphans,
      message: `${label(a.agent)} no está conectado al flujo`,
      nodes: [a.id],
      edges: [],
    }));
  }

  const byId = new Map(agents.map((a) => [a.id, a.agent]));
  const ordered = effectiveOrder(nodes, edges).map((id) => ({ id, agent: byId.get(id) }));
  return [...issues, ...checkRequirements(ordered, rules, links)];
}

export const blocking = (issues) => issues.filter((i) => i.severity === ERROR);

/** Quita las autoconexiones que pudieran venir de flujos guardados antes del arreglo. */
export const sanitizeEdges = (edges) => (edges || []).filter((edge) => !isSelfLoop(edge));

/** Mensaje legible de una respuesta 422 del backend, o `null` si no lo es. */
export function issueFromError(err) {
  const detail = err?.response?.data?.detail;
  return detail?.issues?.[0]?.message || detail?.message || null;
}
