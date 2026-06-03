import api from './client';

export const articlesApi = {
  list: (params) => api.get('/api/v1/articles', { params }).then(r => r.data),
  get: (id) => api.get(`/api/v1/articles/${id}`).then(r => r.data),
  create: (data) => api.post('/api/v1/articles', data).then(r => r.data),
  update: (id, data) => api.put(`/api/v1/articles/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/api/v1/articles/${id}`).then(r => r.data),
  submit: (id) => api.post(`/api/v1/articles/${id}/submit`).then(r => r.data),
  approve: (id) => api.post(`/api/v1/articles/${id}/approve`).then(r => r.data),
  reject: (id, comment) => api.post(`/api/v1/articles/${id}/reject`, { comment }).then(r => r.data),
  publish: (id) => api.post(`/api/v1/articles/${id}/publish`).then(r => r.data),
  // reviewer_identifier can be an email address or a full name
  assignReviewer: (id, reviewerIdentifier) =>
    api.post(`/api/v1/articles/${id}/assign-reviewer`, { reviewer_identifier: reviewerIdentifier }).then(r => r.data),

  // Run the formateador agent on the current article body and save the result
  formatBody: (id) =>
    api.post(`/api/v1/articles/${id}/format-body`).then(r => r.data),
};
