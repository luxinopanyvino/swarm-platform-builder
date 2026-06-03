import api from './client';

export const flowsApi = {
  list: (params = {}) => api.get('/api/v1/flows', { params }).then(r => r.data),
  get: (id) => api.get(`/api/v1/flows/${id}`).then(r => r.data),
  create: (data) => api.post('/api/v1/flows', data).then(r => r.data),
  update: (id, data) => api.put(`/api/v1/flows/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/api/v1/flows/${id}`).then(r => r.data),
};
