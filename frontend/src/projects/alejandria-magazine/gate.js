import { agentMeta } from './catalog';

// Compuerta de publicación (SPEC-032, ADR-0011): textos y ayudas para mostrarla.
//
// El backend responde con códigos estables (`detail.code`); aquí se traducen a algo
// que una persona pueda actuar. Si el backend añade un código y aquí no se traduce,
// un test estructural lo detecta (`test_frontend_gate.py`).

export const CRITERION_LABELS = {
  reference_existence: 'Las referencias existen y coinciden',
  reference_structure: 'Las referencias están completas',
  placeholders: 'Sin marcadores de posición',
  imrad_structure: 'Estructura IMRaD',
};

export const CRITERION_STATUS = {
  passed: { label: 'Superado', cls: 'badge-approved' },
  failed: { label: 'No supera', cls: 'badge-error' },
  not_verified: { label: 'No verificado', cls: 'badge-pending' },
  not_implemented: { label: 'Pendiente de fase', cls: 'badge-draft' },
};

// Un criterio `failed` o `not_verified` bloquea; `not_implemented` no (AC5).
export const BLOCKING = new Set(['failed', 'not_verified']);

/** Nombre de un agente: sale del catálogo del proyecto, que es la única lista (T8.6). */
export function agentLabel(agentId) {
  return agentMeta(agentId).label || agentId;
}

// Códigos de 409/403 de `approve`, `publish` y `responsible-author`.
export const GATE_ERROR_MESSAGES = {
  no_responsible_author: 'Declara un autor responsable antes de aprobar.',
  no_gate_report: 'Aún no hay informe de la compuerta: evalúa el texto antes de aprobar.',
  text_changed: 'El texto cambió desde la última evaluación: reevalúa la compuerta.',
  gate_blockers: 'La compuerta tiene bloqueantes: corrígelos y vuelve a evaluar.',
  not_reviewer: 'Solo el administrador o el revisor asignado puede aprobar.',
  owner_cannot_approve: 'Quien lanzó el pipeline no puede aprobar su propio artículo.',
  review_missing: 'El texto no ha pasado por una revisión: ejecútalo con el Revisor.',
  review_not_verified: 'El Revisor no pudo producir una revisión válida: vuelve a ejecutarlo.',
  score_below_threshold: 'La revisión no alcanza la puntuación mínima.',
  not_coherent: 'El Revisor considera el texto incoherente.',
  no_approval: 'Falta la aprobación humana.',
  approval_stale: 'La aprobación es de una versión anterior del texto.',
};

/**
 * Texto de un error de la API de artículos: acepta `detail` como cadena o como
 * `{code, message}` y prefiere la explicación accionable de este módulo.
 */
export function describeApiError(err, fallback = 'No se pudo completar la acción') {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  return GATE_ERROR_MESSAGES[detail.code] || detail.message || fallback;
}

/** Resumen de una línea de la evidencia de un criterio. */
export function evidenceLines(criterion) {
  const out = [];
  for (const e of criterion?.evidence || []) {
    if (e.reason) out.push(`${e.title ? `«${e.title}»: ` : ''}${e.reason}`);
    else if (e.missing) out.push(`«${e.title}»: falta ${e.missing.join(', ')}`);
    else if (e.pattern) out.push(`${e.pattern} (línea ${e.line}, columna ${e.column})`);
    else if (e.problem) out.push(`${e.section}: ${e.problem}`);
  }
  return out;
}
