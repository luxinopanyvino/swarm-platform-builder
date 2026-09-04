// El objeto sobre el que se ejecuta un pipeline (SPEC-013 / T8.6 / AC7).
//
// El botón «Ejecutar» del Flow Designer creaba un **artículo**: el builder
// importaba `articleStore` del proyecto y llamaba a `createArticle`. Es la
// dependencia al revés — el objeto que produce el pipeline se llama artículo en
// AlejandrIA y se llamará otra cosa en el siguiente proyecto, o no existirá.
//
// El builder solo necesita dos cosas: crear un objetivo con un título y renombrar
// uno existente. El proyecto las aporta al arrancar, igual que su catálogo de
// agentes.
let objetivo = null;

/**
 * Da de alta cómo crea y renombra sus objetivos el proyecto activo.
 *
 * @param {{create: (title: string) => Promise<{id: string}>,
 *          rename: (id: string, title: string) => Promise<any>,
 *          label?: string}} implementacion
 */
export function setRunTarget(implementacion) {
  objetivo = implementacion || null;
}

export function runTarget() {
  return objetivo;
}

/** Cómo llama el proyecto a lo que produce, para los textos de la interfaz. */
export function runTargetLabel() {
  return objetivo?.label || 'ejecución';
}
