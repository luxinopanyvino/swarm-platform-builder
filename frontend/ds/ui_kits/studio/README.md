# Studio — UI Kit

**Studio** is the authenticated authoring workspace of Alexandria Magazine: where
researchers design agent flows, run pipelines, and review/publish articles. A
high-fidelity, mostly-cosmetic recreation of the product's React app
(`alejandria-magazine/frontend`), restyled onto the modern light SLDS-blue foundations.

## Run it
Open `index.html` — an interactive click-through:

1. **Auth** — the form is pre-filled; press **Entrar**.
2. **Flow Designer** — agent palette + canvas with wired agent nodes and a toolbar.
   Press **Ejecutar**, name the article, run.
3. **Execution** — watch the pipeline step through the agents (streaming log + live
   serif article preview), then **Abrir artículo**.
4. **Artículos** — filterable grid of article cards → reading/review detail with reviewer
   actions and AI assist.
5. **Agentes** / **Configuración** — supporting screens.

## Files
| File | Role |
|---|---|
| `index.html` | Entry — loads Lucide + React/Babel + every component, mounts `<App>` |
| `studio.css` | Kit layout & component styles (consumes `../../colors_and_type.css`) |
| `icons.jsx` | `<Icon name size>` — renders Lucide icons from the UMD registry |
| `components.jsx` | `AGENTS` / `STATUS` / `SAMPLE_ARTICLES` data + `Avatar`, `Badge`, `Sidebar`, `TopBar` |
| `Auth.jsx` | Split-screen login / register |
| `FlowDesigner.jsx` | Palette, positioned agent nodes, animated edges, run modal |
| `Execution.jsx` | Step monitor, streaming log, live `.prose` draft |
| `Articles.jsx` | `ArticlesGrid` (filter/search) + `ArticleDetail` (review) |
| `app.jsx` | Navigation shell, agents/config pages, toast host |

## Notes
- Icons are **Lucide** (the product's real `lucide-react`), loaded via CDN.
- Components are deliberately cosmetic — no real backend, routing, or graph engine.
- Dark theme: add `data-theme="dark"` to `<html>` (tokens flip automatically; a few
  kit-specific surfaces may want spot-checking).
