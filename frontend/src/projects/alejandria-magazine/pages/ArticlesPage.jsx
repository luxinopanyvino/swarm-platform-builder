import React, { useEffect, useState } from 'react';
import { AsyncState, EmptyState } from '../../../platform/components/ui/states';
import { useNavigate } from 'react-router-dom';
import { FileText, Clock, CheckCircle, AlertCircle, Search, Pencil, Trash2, User } from 'lucide-react';
import { useArticleStore } from '../store/articleStore';
import { useAuthStore } from '../../../platform/store/authStore';
import toast from 'react-hot-toast';

const TABS = ['Todos', 'Drafts', 'Pendientes', 'Aprobados', 'Publicados'];

const STATUS_MAP = {
  draft: { label: 'Draft', cls: 'badge-draft', icon: <Clock size={10} /> },
  in_review: { label: 'Pendiente', cls: 'badge-pending', icon: <AlertCircle size={10} /> },
  approved: { label: 'Aprobado', cls: 'badge-approved', icon: <CheckCircle size={10} /> },
  published: { label: 'Publicado', cls: 'badge-published', icon: <CheckCircle size={10} /> },
  rejected: { label: 'Rechazado', cls: 'badge-error', icon: <AlertCircle size={10} /> },
};

const TAB_FILTER = {
  'Todos': null,
  'Drafts': 'draft',
  'Pendientes': 'in_review',
  'Aprobados': 'approved',
  'Publicados': 'published',
};

export default function ArticlesPage() {
  const navigate = useNavigate();
  const { articles, fetchArticles, updateArticle, deleteArticle, isLoading, error } = useArticleStore();
  const { user } = useAuthStore();
  const [tab, setTab] = useState('Todos');
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => { fetchArticles(); }, []);

  const filtered = articles.filter(a => {
    const statusMatch = !TAB_FILTER[tab] || a.status === TAB_FILTER[tab];
    const searchMatch = !search || a.title.toLowerCase().includes(search.toLowerCase());
    return statusMatch && searchMatch;
  });

  const startEdit = (e, article) => {
    e.stopPropagation();
    setEditingId(article.id);
    setEditTitle(article.title);
  };

  const confirmEdit = async (e, id) => {
    e.stopPropagation();
    if (!editTitle.trim()) return;
    try {
      await updateArticle(id, { title: editTitle.trim() });
      toast.success('Título actualizado');
    } catch { toast.error('Error al actualizar'); }
    setEditingId(null);
  };

  const handleDelete = async (e, id, title) => {
    e.stopPropagation();
    if (!globalThis.confirm(`¿Eliminar "${title}"? Esta acción no se puede deshacer.`)) return;
    setDeletingId(id);
    try {
      await deleteArticle(id);
      toast.success('Artículo eliminado');
    } catch { toast.error('Error al eliminar'); }
    finally { setDeletingId(null); }
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-6)' }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Artículos</h2>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>{articles.length} artículos en total</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <div className="tabs">
          {TABS.map(t => (
            <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, maxWidth: 300 }}>
          <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input className="input" style={{ padding: '6px 10px' }}
            placeholder="Buscar artículos..."
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <AsyncState
        loading={isLoading}
        error={error}
        isEmpty={filtered.length === 0}
        onRetry={() => fetchArticles()}
        loadingLabel="Cargando artículos…"
        empty={(
          <EmptyState
            icon={<FileText size={28} />}
            title={articles.length === 0 ? 'Sin artículos' : 'Ningún artículo coincide'}
            description={articles.length === 0
              ? 'Ejecuta un pipeline desde el Flow Designer para generar tu primer artículo.'
              : 'Prueba con otro filtro o cambia el término de búsqueda.'}
          />
        )}
      >
        {(
        <div className="article-grid">
          {filtered.map(article => {
            const st = STATUS_MAP[article.status] || STATUS_MAP.draft;
            const isEditing = editingId === article.id;
            const isDeleting = deletingId === article.id;
            return (
              <div key={article.id} className="article-card"
                onClick={() => !isEditing && navigate(`/dashboard/articles/${article.id}`)}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                  {isEditing ? (
                    <input
                      className="input"
                      style={{ flex: 1, padding: '4px 8px', fontSize: 'var(--font-size-sm)' }}
                      value={editTitle}
                      autoFocus
                      onClick={e => e.stopPropagation()}
                      onChange={e => setEditTitle(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') confirmEdit(e, article.id);
                        if (e.key === 'Escape') { e.stopPropagation(); setEditingId(null); }
                      }}
                    />
                  ) : (
                    <div className="article-card-title">{article.title}</div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                    {isEditing ? (
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ padding: '3px 10px', fontSize: 'var(--font-size-xs)' }}
                        onClick={e => confirmEdit(e, article.id)}
                        aria-label="Confirmar edición"
                      >
                        Guardar
                      </button>
                    ) : (
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={e => startEdit(e, article)}
                        aria-label="Editar título"
                        title="Editar título"
                      >
                        <Pencil size={13} style={{ color: 'var(--text-muted)' }} />
                      </button>
                    )}
                    <button
                      className="btn btn-ghost btn-sm btn-icon"
                      onClick={e => handleDelete(e, article.id, article.title)}
                      disabled={isDeleting}
                      aria-label="Eliminar artículo"
                      title="Eliminar artículo"
                    >
                      <Trash2 size={13} style={{ color: 'var(--error)' }} />
                    </button>
                    <span className={`badge ${st.cls}`}>
                      {st.icon} {st.label}
                    </span>
                  </div>
                </div>
                <div className="article-card-meta">
                  <Clock size={11} />
                  {new Date(article.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })}
                  {article.author_name && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                      <User size={10} />
                      {article.author_name}
                    </span>
                  )}
                  {article.scientific_format && article.scientific_format !== 'none' && (
                    <span style={{ background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: 'var(--radius-full)', fontSize: 10 }}>
                      {article.scientific_format.toUpperCase()}
                    </span>
                  )}
                </div>
                {article.body && !isEditing && (
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {article.body.replace(/[#*`]/g, '').trim()}
                  </p>
                )}
              </div>
            );
          })}
        </div>
        )}
      </AsyncState>
    </div>
  );
}
