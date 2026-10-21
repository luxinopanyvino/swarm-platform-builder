# Tarea #414 — UX-002 Estado vacío del Flow Designer desalineado

## 2026-10-21 — Completada ✅ (pendiente de revisión visual)

- **Rama:** `fix/ux-002-estado-vacio`
- **PR:** [#419](https://github.com/onpremialabs/swarm-platform-builder/pull/419) → `develop` (`Closes #414`)
- **Origen:** informe de pruebas funcionales; plan `plan_fix_alejandria_magazine.md`
- **Dependencias:** ninguna.

### Dónde estaba el problema

`frontend/src/platform/pages/FlowDesignerPage.jsx`: el estado vacío se envolvía en un
`div` con `position: absolute; inset: 0` pero **sin layout propio**. El `EmptyState`
(`display:flex; column`) fluía desde el borde superior de ese contenedor, no centrado,
y quedaba justo debajo/encima de la barra de acciones flotante (`.flow-toolbar`,
`position:absolute; top: var(--space-4)`), con la que se superponía.

### Qué se modificó y por qué

- **`FlowDesignerPage.jsx`:** el estilo en línea pasa a la clase `flow-empty`.
- **`frontend/src/index.css`, `.flow-empty`:** flex centrado en ambos ejes, con
  `padding-top` calculado a partir de la altura de la barra de acciones para que el
  contenido se centre en el espacio que ésta deja libre. Mantiene `pointer-events:none`
  para no bloquear el lienzo ni la barra. Reduce el padding de `.empty-state` dentro del
  lienzo (de `--space-16` a `--space-6`) para que quepa en ventanas pequeñas.

### Definition of Done

- [x] **AC1** icono, título y descripción alineados y sin superposición:
  `tests/test_flow_empty_state.py` fija el centrado, `pointer-events:none` y la
  reserva del hueco de la barra.
- [ ] **Revisión visual** en escritorio, portátil pequeño y ventana reducida:
  **no hecha**, no hay navegador en esta sesión. La altura de la barra (48 px) está
  estimada, no medida.

### Verificación

- `npm run build` OK; tests estructurales en verde.
