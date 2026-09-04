# Tarea #212 — T8.6 Frontend: extraer `platform/` (builder) de `projects/` (consumer)

## 2026-09-03 — Completada ✅

- **Rama:** `feat/212-frontend-platform`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #212`)
- **Spec/ADR:** SPEC-013, Épica E8, ADR-0005. Criterio vinculante: **AC7**.
- **Dependencias:** T8.4 (#210). **Cierra la épica E8.**

## Qué se hizo

`frontend/src/` pasa de un árbol plano (`pages/`, `store/`, `api/`, `components/`)
a dos capas:

- **`platform/`** — el *builder* reutilizable: cliente HTTP, stores de sesión y
  proyectos, componentes, y las páginas de construcción (Flow Designer, Agentes,
  Flujos, Documentos, Usuarios, Configuración, selección de proyecto).
- **`projects/alejandria-magazine/`** — las vistas de consumo: artículos, la
  revista, la maquetación de paper, y el catálogo de agentes del proyecto.

Y, sobre todo: **la dependencia va en un solo sentido**. Hay un test que lo
comprueba, porque un import al revés no rompe nada visible.

## Lo que había

**El catálogo de los cinco agentes de AlejandrIA, escrito cuatro veces:**

| Dónde | Qué llevaba |
|---|---|
| `components/flow/AgentNode.jsx` | icono, color, etiqueta y descripción |
| `pages/AgentsPage.jsx` | icono y color |
| `pages/ExecutionPage.jsx` | etiqueta y color |
| `pages/ArticleDetailPage.jsx` | etiquetas con emoji |

Cuatro copias es una que se actualiza y tres que no. Y las dos primeras vivían en
piezas **del builder**: es el equivalente en el frontend de lo que T8.3 quitó del
motor. La consecuencia concreta: el lienzo de cualquier otro proyecto pintaba
todos sus nodos grises y sin descripción, y arreglarlo pasaba por editar un
componente compartido.

**Y cinco dependencias más del builder hacia el proyecto**, todas del mismo tipo:

- `FlowDesignerPage` importaba `articleStore` y llamaba a `createArticle`: el
  botón «Ejecutar» del builder creaba el objeto de dominio de AlejandrIA.
- `FlowDesignerPage` subía las fuentes RAG a `'investigador'`, por nombre.
- `FlowsPage` decidía si un flujo publica solo con
  `flow_sequence.includes('publicador')`.
- `DashboardPage` llevaba «Artículos» en el menú y navegaba a
  `/dashboard/articles/<id>` desde las notificaciones.
- `AgentEditorModal` tenía un panel que explica el pipeline interno del
  investigador —sus etapas, sus APIs y sus modelos por defecto— detrás de un
  `agentSlug === 'investigador'`.

Ninguna de esas rompe nada hoy. Todas rompen el día que alguien monta el segundo
proyecto, que es exactamente el objetivo de E8.

## La forma de la solución

**El proyecto se registra en el builder al arrancar; el builder pregunta.** Es el
mismo patrón que el registro de agentes del motor (T8.3), y son cuatro registros
en `platform/`:

- `agentCatalog` — catálogo, dueño del RAG, agente que publica, paneles de ayuda.
- `navigation` — entradas de menú y ruta de las notificaciones.
- `runTarget` — cómo crea y renombra el proyecto lo que produce su pipeline.

`main.jsx` (y el entry público) los rellenan antes de montar nada. Si el lienzo
necesita un dato nuevo del proyecto, se añade un registro; no se importa.

## Decisiones documentadas

- **`redactor` es agente y también rol de usuario.** El test que busca nombres de
  agente en `platform/` empezó señalando `UsersPage`, el menú y el store de
  flujos, que hablan de permisos. La detección se hace sobre los cuatro nombres
  **inequívocos** (`investigador`, `revisor`, `formateador`, `publicador`) y
  descarta comentarios: los módulos que arreglaron el problema lo explican dentro.
- **Queda un residuo, declarado y con motivo.** `AgentEditorModal` mantiene
  `isFormateador` e `isRedactor`, que enseñan campos que solo tienen sentido para
  esos agentes (formato científico, palabras objetivo). Quitarlos exige un
  **esquema de campos por agente**, que es una tarea aparte. Está en
  `RESIDUOS_CONOCIDOS` con su razón, y hay un test que falla si aparece otro **o
  si este se arregla y nadie actualiza la lista**. Como en los lints de E7: una
  excepción escrita es revisable; una tolerancia silenciosa en el umbral, no.
- **`AgentsPage` conserva los agentes de los otros cuatro tipos de proyecto**
  (desarrollo, marketing, tiqueting, diseño). No son de AlejandrIA y todavía no
  tienen `template.yaml`: viven como listas en `backend/app/shared/agents_seed.py`.
  Cuando se empaqueten, esa lista se vacía igual que se vació la de AlejandrIA.
- **`services/api.js` se borra.** Era código muerto —nadie lo importaba— con su
  propio cliente axios sin el interceptor de sesión ni la cabecera `X-Project-Id`
  de T8.5. Quien lo hubiera importado habría hecho peticiones sin autenticar y sin
  proyecto.
- **`catalog.js` pasa a `catalog.jsx`**: lleva JSX (el icono de cada agente y el
  panel de ayuda), y Vite necesita la extensión para transformarlo.
- **El entry público se mueve con su proyecto** (`projects/alejandria-magazine/public/`)
  y `index.public.html` apunta ahí: la revista es una vista de consumo.

## Test nuevo

`backend/tests/test_frontend_layers.py` (11 casos):

- **Las dos capas existen** y no quedan restos del árbol plano (`src/pages/`,
  `src/store/`… ya no existen).
- **`platform/` no importa de `projects/`** — resolviendo cada import relativo, no
  por texto.
- **Ningún fichero del builder nombra agentes de un proyecto**, con la lista de
  residuos declarada aparte.
- **Y un proyecto sí puede usar la plataforma**: si no, la separación sería un
  muro en vez de una capa.
- **El catálogo vive en el proyecto y no está duplicado**, y se registra en los
  **dos** puntos de arranque: si nadie registra, el lienzo sale gris.
- **El menú no trae «Artículos» de serie.**
- **Las dos entradas de Vite apuntan a ficheros que existen**, que es como se
  detecta pronto que un build va a fallar por un movimiento.

Verificado **por mutación**: devolver el `includes('publicador')` a `FlowsPage`
hace fallar dos tests; añadir un import de `projects/` a un fichero de
`platform/` hace fallar el de la dirección de la dependencia.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 667 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

npm run build && npm run build:public     # → ambos OK (AC7 los nombra)
npx vite build --config a11y/vite.config.js   # → OK (los bancos de T7.2/T7.3)
python3 scripts/check_design_tokens.py    # → [OK]
python3 scripts/check_contrast.py         # → [OK] 68 pares AA
python3 scripts/check_async_states.py     # → [OK]
python3 scripts/validate_specs.py         # → [OK]
```

Y la aplicación construida se **cargó en Chromium**: monta sin ningún error de
página y pinta la pantalla de acceso. Es la comprobación que un movimiento de 38
ficheros necesita: que los builds compilen no garantiza que el registro del
catálogo ocurra antes de montar.

## Definition of Done

- [x] **AC7** — builder en `platform/`, consumo en `projects/`, dependencia en un
  solo sentido y comprobada, y los dos builds compilando.
- [x] Tests que cubren el cambio, en verde (11 nuevos; 667 en la suite).
- [x] Docs: SPEC-013 anotada y `CLAUDE.md` con las dos capas y la regla de
  dependencia.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **Con esta tarea la épica E8 queda completa** (T8.1 #237, T8.2 #239, T8.3 #209,
  T8.4 #210, T8.5 #211, T8.6 #212). Cuando el mantenedor cierre los issues,
  SPEC-013 puede pasar a `Done`: sus ocho criterios quedan cumplidos.
- **El residuo de `AgentEditorModal`** se cierra con un esquema de campos por
  agente, declarado en el `template.yaml` del proyecto. Encaja con la evolución
  natural de la plantilla.
- **Los otros cuatro tipos de proyecto** (desarrollo, marketing, tiqueting,
  diseño) siguen como listas en Python. Empaquetarlos como `template.yaml` los
  saca también de `AgentsPage`.
- **Los tests de capas viven en `backend/tests/`** porque es donde está el
  *runner* del repo. Si algún día el frontend tiene su propio Vitest, es su sitio
  natural.
