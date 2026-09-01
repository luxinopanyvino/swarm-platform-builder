import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader, AlertCircle, Columns2, Columns3, ImagePlus } from 'lucide-react';
import { articlesApi } from '../api/articles';
import toast from 'react-hot-toast';
import { PAPER_ACCENTS } from '../paperTheme';

/**
 * Paper design studio: edit the article's text and presentation with a live
 * preview of the final layout (SPEC-022 / T11.4).
 *
 * The preview is rendered **server-side** by the same function that produces the
 * published paper, so what you see here is what the PDF will be. The user never
 * writes CSS — every control picks from a closed allowlist that the backend
 * validates again on save.
 */

// Mirrors the allowlists in backend/app/modules/agents/adapters/paper_layout.py.
// The backend is the source of truth: anything it does not recognise falls back
// to the format preset, so a drift here degrades gracefully instead of breaking.
const FONTS = [
  { value: 'times', label: 'Times New Roman', preview: "'Times New Roman', serif" },
  { value: 'georgia', label: 'Georgia', preview: 'Georgia, serif' },
  { value: 'palatino', label: 'Palatino', preview: "'Palatino Linotype', serif" },
  { value: 'helvetica', label: 'Helvetica', preview: 'Helvetica, Arial, sans-serif' },
  { value: 'arial', label: 'Arial', preview: 'Arial, sans-serif' },
  { value: 'verdana', label: 'Verdana', preview: 'Verdana, sans-serif' },
];

// Espejo de `_THEME_ACCENTS` del backend: son los colores del **paper**, no de la
// interfaz. Ver el porqué en src/paperTheme.js.
const ACCENTS = PAPER_ACCENTS;

const FORMATS = [
  { value: 'apa', label: 'APA (1 columna)' },
  { value: 'ieee', label: 'IEEE (2 columnas)' },
  { value: 'acl', label: 'ACL — conferencia (2 columnas)' },
  { value: 'vancouver', label: 'Vancouver' },
  { value: 'chicago', label: 'Chicago' },
  { value: 'nature', label: 'Nature' },
];

const PREVIEW_DEBOUNCE_MS = 400;   // AC3 requires the repaint within 1 s of the last change

export default function PaperDesignPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [draft, setDraft] = useState(null);      // {title, abstract, body, scientific_format, theme}
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Guards against an out-of-order response overwriting a newer preview.
  const requestSeq = useRef(0);

  useEffect(() => {
    articlesApi.get(id)
      .then(a => {
        setDraft({
          title: a.title || '',
          abstract: a.abstract || '',
          body: a.body || '',
          scientific_format: (a.scientific_format && a.scientific_format !== 'none')
            ? a.scientific_format : 'apa',
          theme: a.theme || {},
        });
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  const renderPreview = useCallback(async (current) => {
    const seq = ++requestSeq.current;
    setRendering(true);
    try {
      const out = await articlesApi.previewPaper(id, current);
      if (seq === requestSeq.current) setHtml(out);   // ignore stale responses
    } catch {
      if (seq === requestSeq.current) toast.error('No se pudo generar la vista previa');
    } finally {
      if (seq === requestSeq.current) setRendering(false);
    }
  }, [id]);

  // Debounced repaint: one request after the user stops typing / clicking.
  useEffect(() => {
    if (!draft) return undefined;
    const t = setTimeout(() => renderPreview(draft), PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [draft, renderPreview]);

  const update = (patch) => {
    setDraft(d => ({ ...d, ...patch }));
    setDirty(true);
  };
  const updateTheme = (patch) => {
    setDraft(d => ({ ...d, theme: { ...d.theme, ...patch } }));
    setDirty(true);
  };

  const handleInsertImage = async (file) => {
    if (!file) return;
    try {
      const asset = await articlesApi.uploadAsset(id, file);
      // Append the reference at the end of the body; the preview picks it up on
      // the next debounce tick, so the figure shows up without a manual step.
      update({ body: `${draft.body}\n\n${asset.markdown}\n` });
      toast.success('Figura insertada');
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(detail || 'No se pudo subir la figura');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await articlesApi.update(id, {
        title: draft.title,
        abstract: draft.abstract,
        body: draft.body,
        scientific_format: draft.scientific_format,
        theme: draft.theme,
      });
      setDirty(false);
      toast.success('Cambios guardados');
    } catch {
      toast.error('No se pudieron guardar los cambios');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-body">
        <div className="empty-state"><div className="spinner spinner-lg" /></div>
      </div>
    );
  }

  if (error || !draft) {
    return (
      <div className="page-body">
        <div className="empty-state" style={{ textAlign: 'center' }}>
          <AlertCircle size={40} style={{ color: 'var(--status-error)', marginBottom: 12 }} />
          <h3>No se pudo cargar el artículo</h3>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>Revisa que exista y que tengas permisos.</p>
        </div>
      </div>
    );
  }

  const columns = draft.theme.columns;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
        padding: 'var(--space-3) var(--space-5)', borderBottom: '1px solid var(--border-default)',
        background: 'var(--bg-surface)', flex: 'none',
      }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)} aria-label="Volver">
          <ArrowLeft size={15} /> Volver
        </button>
        <strong style={{ flex: 1 }}>Diseño del paper</strong>
        {rendering && (
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            <Loader size={12} style={{ animation: 'spin 1s linear infinite', verticalAlign: 'middle' }} />
            {' '}Actualizando previa…
          </span>
        )}
        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving || !dirty}>
          <Save size={15} /> {saving ? 'Guardando…' : dirty ? 'Guardar' : 'Guardado'}
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* ── Controls + text ─────────────────────────────────────────── */}
        <div style={{
          width: 380, flex: 'none', overflowY: 'auto', padding: 'var(--space-5)',
          borderRight: '1px solid var(--border-default)', background: 'var(--bg-surface)',
          display: 'flex', flexDirection: 'column', gap: 'var(--space-5)',
        }}>
          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Formato de cita</h4>
            <select
              className="input" style={{ width: '100%' }}
              value={draft.scientific_format}
              onChange={e => update({ scientific_format: e.target.value })}
              aria-label="Formato de cita"
            >
              {FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </section>

          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Tipografía</h4>
            <select
              className="input" style={{ width: '100%' }}
              value={draft.theme.font || ''}
              onChange={e => updateTheme({ font: e.target.value || undefined })}
              aria-label="Tipografía"
            >
              <option value="">(la del formato)</option>
              {FONTS.map(f => (
                <option key={f.value} value={f.value} style={{ fontFamily: f.preview }}>{f.label}</option>
              ))}
            </select>
          </section>

          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Color de acento</h4>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {ACCENTS.map(a => {
                const active = (draft.theme.accent_color || 'ink') === a.value;
                return (
                  <button
                    key={a.value}
                    onClick={() => updateTheme({ accent_color: a.value })}
                    title={a.label}
                    aria-label={`Acento ${a.label}`}
                    aria-pressed={active}
                    style={{
                      width: 30, height: 30, borderRadius: '50%', background: a.hex,
                      border: active ? '3px solid var(--brand-primary)' : '1px solid var(--border-default)',
                      cursor: 'pointer', padding: 0,
                    }}
                  />
                );
              })}
            </div>
          </section>

          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Columnas</h4>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={`btn btn-sm ${columns === 1 ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => updateTheme({ columns: 1 })} aria-pressed={columns === 1}
              >
                <Columns2 size={14} /> Una
              </button>
              <button
                className={`btn btn-sm ${columns === 2 ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => updateTheme({ columns: 2 })} aria-pressed={columns === 2}
              >
                <Columns3 size={14} /> Dos
              </button>
              <button
                className={`btn btn-sm ${!columns ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => updateTheme({ columns: undefined })} aria-pressed={!columns}
              >
                Auto
              </button>
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 6 }}>
              «Auto» usa las columnas propias del formato de cita.
            </p>
          </section>

          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Figuras</h4>
            <label className="btn btn-ghost btn-sm" style={{ cursor: 'pointer' }}>
              <ImagePlus size={14} /> Insertar imagen
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.gif,.webp"
                style={{ display: 'none' }}
                onChange={e => { handleInsertImage(e.target.files?.[0]); e.target.value = ''; }}
                aria-label="Insertar imagen en el artículo"
              />
            </label>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 6 }}>
              Se valida por contenido real y se añade al cuerpo como
              {' '}<code>![pie](asset:…)</code>. Máx. 5 MB.
            </p>
          </section>

          <section>
            <h4 style={{ margin: '0 0 var(--space-3)' }}>Contenido</h4>
            <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Título</label>
            <input
              className="input" style={{ width: '100%', marginBottom: 'var(--space-3)' }}
              value={draft.title} onChange={e => update({ title: e.target.value })}
              aria-label="Título del artículo"
            />
            <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Abstract</label>
            <textarea
              className="input" rows={4} style={{ width: '100%', marginBottom: 'var(--space-3)' }}
              value={draft.abstract} onChange={e => update({ abstract: e.target.value })}
              aria-label="Abstract"
            />
            <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Cuerpo (markdown)</label>
            <textarea
              className="input" rows={14}
              style={{ width: '100%', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}
              value={draft.body} onChange={e => update({ body: e.target.value })}
              aria-label="Cuerpo del artículo"
            />
          </section>
        </div>

        {/* ── Live preview ────────────────────────────────────────────── */}
        <div style={{ flex: 1, minWidth: 0, background: 'var(--bg-canvas)' }}>
          <iframe
            title="Vista previa de la maquetación"
            srcDoc={html}
            // Static HTML+CSS only: no scripts, no same-origin (T2.2).
            sandbox=""
            style={{ width: '100%', height: '100%', border: 'none', background: 'var(--paper-surface)' }}
          />
        </div>
      </div>
    </div>
  );
}
