/**
 * Colores de acento del **paper impreso** (SPEC-022 / T11.2).
 *
 * NO son tokens de la interfaz, y por eso viven aquí y no en el design system:
 * son un espejo exacto de `_THEME_ACCENTS` en
 * `backend/app/modules/agents/adapters/paper_layout.py`, que es quien decide con
 * qué color se maqueta el artículo. La muestra de color del panel de diseño tiene
 * que enseñar **ese** color, no el de la aplicación; sustituirlos por `var(--…)`
 * haría que el usuario viera una muestra que miente sobre el PDF que va a obtener.
 *
 * Están en un módulo aparte para que el acoplamiento con el backend se vea de un
 * vistazo, en lugar de quedar enterrado en un componente. El lint de tokens de
 * diseño (`scripts/check_design_tokens.py`) excluye este fichero por ese motivo.
 *
 * Si cambia la lista del backend, cambia aquí.
 */
export const PAPER_ACCENTS = [
  { value: 'ink', label: 'Tinta', hex: '#0b1b33' },
  { value: 'blue', label: 'Azul', hex: '#0176d3' },
  { value: 'violet', label: 'Violeta', hex: '#6b4fe3' },
  { value: 'green', label: 'Verde', hex: '#2e844a' },
  { value: 'amber', label: 'Ámbar', hex: '#c47d04' },
  { value: 'red', label: 'Rojo', hex: '#ba0517' },
  { value: 'teal', label: 'Turquesa', hex: '#06a59a' },
];
