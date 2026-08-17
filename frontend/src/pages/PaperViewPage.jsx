import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer, Loader, AlertCircle } from 'lucide-react';
import { articlesApi } from '../api/articles';
import toast from 'react-hot-toast';

/**
 * Full-screen printable paper-layout view.
 * Fetches the self-contained HTML produced by the Publicador (authenticated)
 * and renders it inside an isolated iframe via srcdoc. The Print button targets
 * the iframe so the user gets the paper layout — not the app chrome — in the PDF.
 */
export default function PaperViewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const iframeRef = useRef(null);
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    articlesApi.getPaper(id)
      .then(content => { if (active) setHtml(content); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  const handlePrint = () => {
    const win = iframeRef.current?.contentWindow;
    if (!win) { toast.error('La vista aún no está lista'); return; }
    win.focus();
    win.print();
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      {/* Toolbar */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 20px', borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)', flexShrink: 0,
      }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Volver
        </button>
        <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Vista de maquetación
        </span>
        <button className="btn btn-primary btn-sm" onClick={handlePrint} disabled={loading || error}>
          <Printer size={15} /> Imprimir / PDF
        </button>
      </header>

      {/* Body */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {loading ? (
          <div style={{ margin: 'auto', display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-muted)' }}>
            <Loader size={20} style={{ animation: 'spin 1s linear infinite' }} /> Generando maquetación…
          </div>
        ) : error ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
            <AlertCircle size={40} style={{ color: 'var(--status-error)', marginBottom: 12 }} />
            <h3>No se pudo cargar la maquetación</h3>
            <p style={{ fontSize: 'var(--font-size-sm)' }}>Revisa que el artículo exista y tengas permisos.</p>
          </div>
        ) : (
          <iframe
            ref={iframeRef}
            title="Maquetación del artículo"
            srcDoc={html}
            // Sandboxed without `allow-scripts` (SPEC-016/AC1): the paper is
            // static HTML+CSS, so no script in it can ever run — including one
            // smuggled in through article content. `allow-same-origin` is kept
            // because the Print button reaches into contentWindow, and
            // `allow-modals` because print() opens a modal; neither grants
            // script execution on its own, and the dangerous pair
            // (same-origin + scripts) is never combined.
            sandbox="allow-same-origin allow-modals"
            style={{ flex: 1, border: 'none', width: '100%', height: '100%', background: '#fff' }}
          />
        )}
      </div>
    </div>
  );
}
