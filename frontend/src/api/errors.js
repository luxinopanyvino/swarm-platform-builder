// Mensaje de error de carga — SPEC-003 / T7.3.
//
// Un único sitio para decidir qué se le enseña a alguien cuando una petición
// falla, porque si cada store lo resuelve a su manera acabamos con la mitad
// enseñando `[object Object]` y la otra mitad tragándose el detalle del backend.

/**
 * Saca un mensaje legible de un error de axios.
 *
 * El `detail` del backend se prefiere cuando existe: es el que explica *por qué*
 * («proyecto no encontrado», «sin permiso»). Sin conexión no hay respuesta, y ahí
 * el mensaje genérico es lo único honesto que se puede decir.
 */
export function mensajeDeCarga(err, porDefecto = 'No se pudieron cargar los datos') {
  const detalle = err?.response?.data?.detail;
  if (typeof detalle === 'string' && detalle.trim()) return detalle;
  if (!err?.response) return 'Sin conexión con el servidor.';
  if (err.response.status >= 500) return 'El servidor ha fallado al responder.';
  return porDefecto;
}
