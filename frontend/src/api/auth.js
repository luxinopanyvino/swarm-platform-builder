import api from './client';

export const authApi = {
  register: (data) => api.post('/api/v1/auth/register', data).then(r => r.data),
  login: (data) => api.post('/api/v1/auth/login', data).then(r => r.data),
  me: () => api.get('/api/v1/auth/me').then(r => r.data),
  promoteReviewer: () => api.post('/api/v1/auth/dev/promote-reviewer').then(r => r.data),
  // Admin — users
  listUsers: () => api.get('/api/v1/auth/users').then(r => r.data),
  assignRole: (userId, role) => api.put(`/api/v1/auth/users/${userId}/role`, { role }).then(r => r.data),
  // Admin — project access
  getUserProjects: (userId) => api.get(`/api/v1/projects/access/${userId}`).then(r => r.data),
  grantProject: (userId, projectId) => api.post(`/api/v1/projects/access/${userId}/${projectId}`).then(r => r.data),
  revokeProject: (userId, projectId) => api.delete(`/api/v1/projects/access/${userId}/${projectId}`).then(r => r.data),
};
