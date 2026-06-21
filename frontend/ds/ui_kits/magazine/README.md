# Magazine — UI Kit

**Magazine** is the public, reader-facing publication — the consumption layer that sits
on top of Studio's authoring. It's where the **Content System** (`.prose`) lives in the
wild: editorial, serif-forward, generous, calm. No login; this is the open reading
experience for technology readers.

## Run it
Open `index.html`:
- **Home** — sticky glass nav, a featured hero, topic filter chips, and a 3-up grid of
  article cards with author bylines. Click any card or the hero.
- **Reader** — centered long-form article: serif headline, lede, byline + "revisado por
  pares", cover figure, drop-cap body with headings, blockquote, inline code, a captioned
  figure, an author bio, and a floating reading toolbar (recommend / comment / save /
  share / back-to-top).

## Files
| File | Role |
|---|---|
| `index.html` | Entry — loads Lucide + React/Babel, mounts `<App>` |
| `magazine.css` | Reading-layer styles (consumes `../../colors_and_type.css` + `.prose`) |
| `data.jsx` | Sample posts, authors, cover gradients, topics, `Avatar` |
| `app.jsx` | `Nav`, `Home`, `Reader`, `App` (+ inline Lucide renderer) |

## Notes
- Covers are CSS gradients standing in for real imagery — **replace with real photos /
  figures** in production (use `<image-slot>` or `<img>`); never ship gradient
  placeholders as final art.
- The reading column is capped at a 68ch measure with serif body at 18px / 1.7 leading,
  per the Content System.
