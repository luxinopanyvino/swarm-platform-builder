import { create } from 'zustand';
import { articlesApi } from '../api/articles';
import { mensajeDeCarga } from '../api/errors';
import { useProjectStore } from './projectStore';
import { useAuthStore } from './authStore';

const getProjectId = () => {
  const role = useAuthStore.getState().user?.role;
  if (role === 'admin' || role === 'redactor') return null; // see all accessible content
  return useProjectStore.getState().activeProject?.id ?? null;
};

// For writes: always scope to the active project regardless of role
const getWriteProjectId = () =>
  useProjectStore.getState().activeProject?.id ?? null;

export const useArticleStore = create((set, get) => ({
  articles: [],
  currentArticle: null,
  isLoading: false,
  error: null,

  fetchArticles: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const projectId = getProjectId();
      const merged = { ...(projectId ? { project_id: projectId } : {}), ...params };
      const data = await articlesApi.list(merged);
      set({ articles: data.items || data, isLoading: false });
    } catch (err) {
      // Se guarda el error en vez de tragárselo: sin esto la página no puede
      // distinguir «no hay artículos» de «no he podido preguntarlo».
      set({ isLoading: false, error: mensajeDeCarga(err, 'No se pudieron cargar los artículos') });
    }
  },

  fetchArticle: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const data = await articlesApi.get(id);
      set({ currentArticle: data, isLoading: false });
      return data;
    } catch (err) {
      set({ isLoading: false, error: mensajeDeCarga(err, 'No se pudo cargar el artículo') });
    }
  },

  createArticle: async (title, body = '') => {
    const projectId = getWriteProjectId();
    const data = await articlesApi.create({ title, body, ...(projectId ? { project_id: projectId } : {}) });
    set(s => ({ articles: [data, ...s.articles] }));
    return data;
  },

  updateArticle: async (id, payload) => {
    const data = await articlesApi.update(id, payload);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: s.currentArticle?.id === id ? data : s.currentArticle,
    }));
    return data;
  },

  deleteArticle: async (id) => {
    await articlesApi.delete(id);
    set(s => ({
      articles: s.articles.filter(a => a.id !== id),
      currentArticle: s.currentArticle?.id === id ? null : s.currentArticle,
    }));
  },

  approveArticle: async (id) => {
    const data = await articlesApi.approve(id);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: data,
    }));
  },

  publishArticle: async (id) => {
    const data = await articlesApi.publish(id);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: data,
    }));
  },

  rejectArticle: async (id, comment) => {
    const data = await articlesApi.reject(id, comment);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: data,
    }));
  },

  assignReviewer: async (id, identifier) => {
    const data = await articlesApi.assignReviewer(id, identifier);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: data,
    }));
  },

  formatBody: async (id) => {
    const data = await articlesApi.formatBody(id);
    set(s => ({
      articles: s.articles.map(a => a.id === id ? data : a),
      currentArticle: s.currentArticle?.id === id ? data : s.currentArticle,
    }));
    return data;
  },

  setCurrentArticle: (article) => set({ currentArticle: article }),
}));
