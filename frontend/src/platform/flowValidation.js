// Validación del grafo del Flow Designer (BUG-001 / VAL-004).
//
// Es feedback inmediato, no la garantía: el backend (`app/platform/flow_validation.py`)
// revalida al guardar porque cualquiera puede saltarse la interfaz. Los códigos de
// regla y los mensajes coinciden con los suyos.

export const ERROR = 'error';
export const WARNING = 'warning';

export const SELF_LOOP = 'self_loop';
export const SELF_LOOP_MESSAGE = 'Un agente no puede conectarse consigo mismo';

export const isSelfLoop = (edge) =>
  Boolean(edge) && edge.source != null && edge.source === edge.target;

/** Valida una conexión en curso (arrastre o soltado). `null` si es válida. */
export function validateConnection(connection) {
  if (isSelfLoop(connection)) {
    return { code: SELF_LOOP, severity: ERROR, message: SELF_LOOP_MESSAGE, nodes: [connection.source], edges: [] };
  }
  return null;
}

/** Todos los problemas del grafo, bloqueantes y avisos. */
export function validateFlow(nodes, edges) {
  return (edges || [])
    .filter(isSelfLoop)
    .map((edge) => ({
      code: SELF_LOOP,
      severity: ERROR,
      message: SELF_LOOP_MESSAGE,
      nodes: [edge.source],
      edges: [edge.id],
    }));
}

export const blocking = (issues) => issues.filter((i) => i.severity === ERROR);

/** Quita las autoconexiones que pudieran venir de flujos guardados antes del arreglo. */
export const sanitizeEdges = (edges) => (edges || []).filter((edge) => !isSelfLoop(edge));
