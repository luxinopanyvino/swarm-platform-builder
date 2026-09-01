# Tarea #193 — T7.2 Accesibilidad AA en modales (focus trap, foco visible, Esc)

## 2026-09-01 — Completada ✅

- **Rama:** `feat/193-modal-a11y`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #193`)
- **Spec/ADR:** SPEC-003, Épica E7. Criterios vinculantes: **AC2** y **AC3**.
- **Dependencias:** ninguna declarada. Se apoya en los tokens de T7.1 (#192):
  las correcciones de contraste se hacen sobre ellos.

### Qué se hizo

**`frontend/src/components/ui/Modal.jsx`** — un único componente con el contrato
de teclado, y los **seis** diálogos de la aplicación migrados a él (editor de
agentes, alta de agente, reejecutar pipeline, rechazar artículo, ejecutar
pipeline, crear proyecto).

**Foco visible** — `:focus-visible` global con `outline` y `outline-offset`. Antes
no había **ninguna** regla de foco salvo el borde de `.input`, así que navegar con
teclado por botones, enlaces y pestañas era navegar a ciegas.

**Contraste** — `scripts/check_contrast.py`, en la CI, y 18 pares corregidos.

### Estado del que se partía

Los cinco modales se montaban a mano, cada uno con un trozo distinto del
contrato:

- **Ninguno** atrapaba el foco. Al abrir cualquiera, `Tab` seguía recorriendo la
  página de detrás: con teclado no se llegaba al diálogo.
- **Ninguno** devolvía el foco al elemento que lo abrió.
- `Esc` solo lo intentaba uno, y **no funcionaba**: el `onKeyDown` estaba en un
  `div` que nunca recibía el foco, así que el evento no llegaba nunca.
- Dos no declaraban `role="dialog"` ni `aria-modal`.
- Los que sí lo declaraban lo ponían en el **velo**, no en el panel: para un
  lector de pantalla, el fondo oscurecido formaba parte del diálogo.

### Lo que encontró el navegador y no habría encontrado leyendo el código

El componente se conduce con teclas reales en Chromium (`frontend/a11y/`, un banco
que construye el componente **de verdad**). Eso destapó tres fallos que ya estaban
escritos y parecían correctos:

1. **El scroll del fondo no se restauraba** al cerrar dos modales anidados. Cada
   instancia guardaba el `overflow` previo del body; React limpia el efecto del
   contenedor **antes** que el del hijo, así que el último en restaurar era el
   interior — que había capturado el `hidden` que puso el exterior. La página se
   quedaba sin scroll para siempre. Ahora el valor se guarda una sola vez, cuando
   la pila pasa de 0 a 1.
2. **`Esc` cerraba los dos modales anidados a la vez.** Un modal anidado se
   renderiza dentro del exterior, así que con el foco todavía en el exterior el
   evento lo atendía el de fuera. Ahora solo responde el que está en la cima de la
   pila.
3. **El anillo de foco entraba animado.** `.btn` tenía `transition: all`, que
   arrastra también `outline-width`, `outline-color` y `outline-offset`: durante
   ~200 ms el anillo no era ni azul ni de 2px. Se vio midiendo `outline-offset`
   justo después de un `Tab` — **0.03125px**, el 1,5% de la animación. Un
   indicador de foco tiene que aparecer, no llegar. La transición ahora enumera
   las propiedades que de verdad quiere animar.

Y una cuarta por lectura, pero solo porque el test la buscaba: **cuatro campos
apagaban el foco con `outline: 'none'` en estilo en línea**, que gana a cualquier
regla de la hoja. Hay un test que impide que vuelvan.

### Contraste: 18 pares por debajo de AA

`scripts/check_contrast.py` resuelve las cadenas `var(--a) → var(--b) → #hex` por
tema, compone los `rgba()` sobre su fondo real y mide 30 pares en claro y oscuro.
Al escribirlo, 18 no llegaban. Se arreglaron **en los tokens**: un par que falla
ahí falla en todos los sitios donde se usa ese token.

- **Botón primario del tema oscuro, 2.90:1.** `--brand-on` no estaba redefinido en
  oscuro, así que se quedaba con el `#ffffff` del claro sobre un azul claro. El
  valor correcto ya existía al lado, en `--text-on-brand`. **Los botones primarios
  del tema oscuro eran ilegibles**, y nadie lo había medido.
- **`--text-muted`, 3.11:1** sobre superficie. Es el color de los *placeholders* y
  de casi todo el texto secundario de la aplicación. La rampa neutra no tenía un
  escalón entre el que no llega (`-60`) y el que ya es el texto secundario
  (`-70`), así que se añade `--neutral-65`.
- **Badges**, entre 2.75:1 y 4.22:1. Los tokens de estado como texto pasan del
  escalón `-60` al `-70`; solo se usan en primer plano, los fondos son los `-bg`.
- **`--brand` no se toca**: también se usa como fondo, y oscurecerlo repintaría
  toda la identidad para arreglar una etiqueta. Se añade `--brand-on-tint` para
  ese caso concreto.
- **`btn-danger:hover` del tema oscuro, 2.78:1.** Ponía `color: white` literal
  sobre un rojo que en oscuro es claro. Nuevo token `--text-on-error`.
- **Contorno de los controles, 1.36:1.** Un input blanco sobre un panel blanco con
  un borde que no se distingue. WCAG SC 1.4.11 pide 3:1 al contorno de un control.
  Token nuevo `--border-control` en vez de oscurecer `--border-strong`: ese está
  publicado en zeroheight con un hex concreto y se usa también en separadores
  decorativos, que no tienen ese requisito.

### Decisiones documentadas

- **`role="dialog"` y `aria-modal` van en el panel, no en el velo.** El velo es la
  parte oscurecida; anunciarlo como el diálogo mete la página de fondo dentro de
  lo que el lector de pantalla considera contenido del diálogo. Hay un test que
  comprueba que el velo no los lleva.
- **El velo cierra por `mousedown` + `click`, no por `click` a secas.** Con
  `onClick` en el velo, seleccionar texto dentro del panel y soltar el ratón fuera
  cerraba el modal y se perdía lo escrito. Ahora el gesto tiene que empezar **y**
  acabar en el velo.
- **Los separadores decorativos se miden pero no bloquean.** `--border-default` da
  1.26:1, pero no es el contorno de ningún control: WCAG no le fija umbral. Se
  informa en cada ejecución para que un cambio de paleta no los hunda en silencio,
  y el motivo está escrito en el script en vez de simplemente no medirlos.
- **La capa de teclado se salta si no hay navegador.** Meter Chromium en la CI es
  una dependencia nueva del *pipeline* que esta tarea no va a decidir por su
  cuenta; el test corre en local y en cualquier máquina con Playwright, y lo dice
  en vez de fingir que pasó. La capa estructural —que nadie vuelva a montar un
  modal a mano— sí corre siempre.
- **`frontend/a11y/` no es parte de la aplicación.** No entra en ninguno de los
  dos builds de Vite y su `dist/` está ignorado; existe para que el test conduzca
  el componente real y no una copia que se desincronice.

### Test nuevo

`backend/tests/test_modal_a11y.py` (22 casos):
- **Estructural, siempre**: ninguna página monta `modal-backdrop` ni declara
  `role="dialog"` por su cuenta; el componente implementa Esc, trampa de foco,
  retorno del foco y bloqueo del fondo; hay estilo de foco visible con
  `outline-offset`; nadie apaga el `outline` (ni en CSS ni en estilo en línea, y
  sin confundirse con los comentarios que hablan de ello); `.btn` no usa
  `transition: all`.
- **De teclado, en Chromium**: el foco entra al abrir; `Tab` doce veces no sale
  del modal y da la vuelta; `Shift+Tab` tampoco escapa; el anillo es visible e
  **inmediato** (2px, azul de `--border-focus`, con desplazamiento); `Esc` cierra
  y devuelve el foco al disparador; con dos anidados `Esc` cierra solo el de
  arriba; el scroll del fondo se restaura solo al cerrar el último; un modal sin
  controles tampoco deja escapar el foco; y arrastrar desde dentro hasta el velo
  no cierra ni pierde lo escrito.
- **AC3**: el script de contraste pasa, está en la CI, y su tabla cubre los tres
  componentes que nombra el criterio.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 594 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)
python3 scripts/check_contrast.py --table     # → [OK] 60 pares AA en claro y oscuro
python3 scripts/check_design_tokens.py        # → [OK]
npm run build && npm run build:public         # → ambos OK
python3 scripts/validate_specs.py             # → [OK]
```

Revisión visual en Chromium, tema claro y oscuro: el anillo de foco se ve en
ambos, los contornos de input ya se distinguen del panel, y el modal migrado
conserva su aspecto.

### Definition of Done

- [x] **AC2** — foco atrapado, visible y `Esc` que devuelve el foco al disparador,
  en los seis diálogos, comprobado con teclas reales.
- [x] **AC3** — los pares texto/fondo de botones, badges e inputs cumplen WCAG 2.1
  AA en los dos temas, con medición automatizada en la CI.
- [x] Tests que cubren el cambio, en verde (22 nuevos; 594 en la suite).
- [x] Builds de frontend en verde, las dos.
- [x] Docs: SPEC-003 anotada; el porqué de cada decisión, en el propio código.
- [x] Sin secretos ni PII; sin dependencias nuevas de la aplicación.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **Los cambios de `ds/colors_and_type.css` hay que devolverlos a zeroheight.**
  Ese fichero se regenera desde allí: si la paleta corregida no sube, la siguiente
  regeneración reintroduce los 18 pares que fallaban. Los cambios son
  `--neutral-65`, `--border-control`, `--brand-on-tint`, `--text-on-error`, el
  escalón `-70` de los estados y el `--brand-on` del tema oscuro.
- **El enlace de salto al contenido** («skip link») queda fuera: necesita un
  `<main>` único en el layout, que la aplicación todavía no tiene. Se escribió el
  CSS y se retiró antes de subirlo para no dejar estilo muerto.
- **Chromium en la CI**: cuando se decida meterlo, la capa de teclado deja de
  saltarse sin tocar el test.
- **#194 (T7.3)** cierra AC4 y con él AC5. Los estados loading/empty/error deberán
  usar los tokens ya corregidos aquí.
