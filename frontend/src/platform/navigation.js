// Entradas de navegación que aporta el proyecto (SPEC-013 / T8.6 / AC7).
//
// El menú del dashboard mezclaba entradas del builder —Flow Designer, Agentes,
// Flujos, Documentos, Usuarios— con «Artículos», que es del proyecto: el objeto
// que produce el pipeline de AlejandrIA se llama artículo, pero el de otro
// proyecto se llamará otra cosa o no existirá.
//
// Mismo patrón que `agentCatalog`: el builder expone el hueco y el proyecto lo
// rellena al arrancar.
let entradas = [];

/** Da de alta las entradas de menú del proyecto activo. */
export function setProjectNavItems(nuevas) {
  entradas = nuevas || [];
}

export function projectNavItems() {
  return entradas;
}

//: Ruta a la que lleva una notificación sobre lo que produce el pipeline. El
//: shell navegaba a `/dashboard/articles/<id>`, que es la ruta de AlejandrIA.
let rutaNotificacion = null;

export function setNotificationRoute(constructor) {
  rutaNotificacion = constructor;
}

export function notificationRoute(id) {
  return rutaNotificacion ? rutaNotificacion(id) : null;
}
