import api from './client';

export const configApi = {
  get: () => api.get('/api/v1/config').then(r => r.data),
  update: (data) => api.put('/api/v1/config', data).then(r => r.data),
  listModels: () => api.get('/api/v1/ai/models').then(r => r.data),
  // Effective engine status (never returns key material) — see routers/config.py
  llmStatus: () => api.get('/api/v1/config/llm-status').then(r => r.data),
};

export const notificationsApi = {
  list: () => api.get('/api/v1/notifications').then(r => r.data),
  markRead: (id) => api.post(`/api/v1/notifications/${id}/read`).then(r => r.data),
  markAllRead: () => api.post('/api/v1/notifications/read-all').then(r => r.data),
};
