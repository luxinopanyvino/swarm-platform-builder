// Registro del catálogo de agentes del proyecto activo (SPEC-013 / T8.6 / AC7).
//
// El builder —el Flow Designer, la lista de flujos, el lienzo— tiene que pintar
// los agentes del proyecto que esté abierto: su nombre, su color, su icono. Pero
// **no puede saber cuáles son**: eso es dato del proyecto, y si el builder lo
// importa deja de ser reutilizable.
//
// Antes el catálogo estaba escrito dentro de `components/flow/AgentNode.jsx`, así
// que el lienzo de cualquier otro proyecto pintaba todos los nodos grises y sin
// descripción, y arreglarlo pasaba por editar un componente del builder.
//
// Este módulo es la inversión de esa dependencia, y el espejo en el frontend del
// registro de agentes del motor (`platform/engine/agents.py`): el proyecto se da
// de alta al arrancar y el builder pregunta.
let catalogo = {};
let conRagPropio = new Set();
let duenoDelRag = null;
let publicador = null;

/** Da de alta el catálogo del proyecto activo. Lo llama la app al arrancar. */
export function setAgentCatalog(
  nuevo,
  agentesConRagPropio = [],
  agenteDuenoDelRag = null,
  agentePublicador = null,
) {
  catalogo = nuevo || {};
  conRagPropio = new Set(agentesConRagPropio);
  duenoDelRag = agenteDuenoDelRag;
  publicador = agentePublicador;
}

/**
 * ¿Este flujo publica solo?
 *
 * La lista de flujos lo decidía con `flow_sequence.includes('publicador')`. Qué
 * agente publica es dato del proyecto: puede llamarse `publish`, `deploy` o no
 * existir, y entonces ningún flujo publica solo.
 */
export function flowAutoPublishes(flowSequence) {
  return Boolean(publicador) && (flowSequence || []).includes(publicador);
}

/**
 * Agente al que pertenecen las fuentes que se suben desde el lienzo.
 *
 * En AlejandrIA es el investigador. El builder tenía ese nombre escrito en la
 * llamada de subida.
 */
export function ragOwner() {
  return duenoDelRag || agentIds()[0] || '';
}

/** Metadatos de un agente, o un objeto vacío si el proyecto no lo declara. */
export function agentMeta(agentId) {
  return catalogo[agentId] || {};
}

/** Etiqueta legible; su propio identificador si el proyecto no lo declara. */
export function agentLabel(agentId) {
  return catalogo[agentId]?.label || agentId;
}

/** ¿Este agente consulta el RAG por su cuenta? (para la insignia del nodo). */
export function hasOwnRag(agentId) {
  return conRagPropio.has(agentId);
}

/** El catálogo entero como lista, para paletas y selectores. */
export function listAgents() {
  return Object.entries(catalogo).map(([id, meta]) => ({ id, ...meta }));
}

/** Identificadores de los agentes que declara el proyecto activo. */
export function agentIds() {
  return Object.keys(catalogo);
}

/**
 * ¿Este agente lo implementa el proyecto con su propio adapter?
 *
 * Importa para la interfaz: un agente con adapter propio decide por su cuenta si
 * consulta el RAG, así que enseñarle a la persona usuaria un interruptor de RAG
 * que no hace nada es mentirle. Antes esto era un `Set` con los cinco nombres de
 * AlejandrIA escrito dentro del editor de agentes.
 */
export function hasOwnAdapter(agentId) {
  return Object.prototype.hasOwnProperty.call(catalogo, agentId);
}

/**
 * Panel de ayuda que el proyecto quiera enseñar al editar este agente, o `null`.
 *
 * Vivía dentro del editor, con un `agentSlug === 'investigador'` delante: un
 * componente del builder explicando el pipeline interno de un agente de un
 * proyecto concreto, con sus etapas, sus APIs y sus modelos por defecto.
 */
export function agentHelpPanel(agentId) {
  return catalogo[agentId]?.help ?? null;
}
