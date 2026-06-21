---
name: alexandria-design
description: Use this skill to generate well-branded interfaces and assets for Alexandria Magazine, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, light & dark themes, dataviz, WCAG 2.1 rules, and UI kit components for prototyping a scientific content-creation & publishing product.
user-invocable: true
---

# Alexandria Magazine — design skill

Alexandria Magazine is an agentic platform for writing, reviewing, and publishing
technical & scientific articles. This skill lets you design on-brand for it: a modern,
light, SLDS-blue product surface (**Studio**) plus an editorial serif reading layer
(**Magazine**), with a Content System for long-form scientific content.

## How to use this skill
1. **Read `README.md` first** — it carries the full context: content fundamentals (voice,
   Spanish-first UI copy, casing, no emoji), visual foundations, and iconography.
2. **Link `colors_and_type.css`** in every artifact. It is the token source of truth:
   primitive + semantic CSS vars, **light & dark themes** (`data-theme="dark"`), the
   dataviz palette, and the `.prose` Content System. Never hard-code hex you could pull
   from a token.
3. **Consult `tokens.md`** for the token architecture and design patterns, and
   **`ACCESSIBILITY.md`** for the binding **WCAG 2.1 AA** rules (contrast, focus,
   targets, forms, semantics, motion).
4. **Reuse the UI kits** in `ui_kits/studio/` and `ui_kits/magazine/` — they recreate the
   real product UI with Lucide icons. Lift components/screens rather than reinventing.
5. **Browse `preview/`** for component specimens (buttons, fields, badges, alerts, toasts,
   avatars, selection controls, charts, stat tiles, etc.).

## When creating artifacts
- For **visual artifacts** (slides, mocks, throwaway prototypes): copy the assets you need
  (`assets/logomark.svg`, `assets/wordmark.svg`) out and produce static HTML files for the
  user to view. Use real images, never gradient placeholders, for final art.
- For **production code**: copy assets and follow the rules here to design as an expert in
  this brand. Respect the two registers — sans UI chrome vs. serif `.prose` content.
- Icons: **Lucide**, 1.5px stroke, `currentColor`. No emoji in product UI or content.
- Always support **light & dark** and meet **WCAG 2.1 AA**.

If invoked without guidance, ask what the user wants to build, ask a few focused
questions, then act as an expert designer who outputs HTML artifacts _or_ production code
as the need dictates.

## Sources (explore for higher fidelity)
- Product codebase: `alejandria-magazine/` (React + Vite; `@xyflow/react`, `lucide-react`)
- Salesforce Lightning Design System (token structure): https://github.com/salesforce-ux/design-system
- SLDS reference: https://www.lightningdesignsystem.com
