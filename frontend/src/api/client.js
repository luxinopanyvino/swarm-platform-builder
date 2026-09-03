import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: API_BASE });

// Attach JWT and the active project on every request.
//
// El proyecto viaja en una cabecera y no como parámetro de cada llamada
// (SPEC-013 / T8.5 / AC6): el aislamiento entre proyectos solo sirve si no se
// puede olvidar, y un parámetro más en cada función de `api/` se olvida en la
// siguiente que alguien añada. Aquí es automático para todas.
//
// Se lee del `localStorage` de zustand en vez de importar el store para no crear
// un ciclo `client → store → api → client`.
function activeProjectId() {
  try {
    const raw = localStorage.getItem('project-store');
    if (!raw) return null;
    return JSON.parse(raw)?.state?.activeProject?.id ?? null;
  } catch {
    // mejor-esfuerzo: sin proyecto la petición sale igual y el backend responde
    // 400 en los endpoints que lo exigen, que es más claro que fallar aquí.
    return null;
  }
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const projectId = activeProjectId();
  if (projectId) config.headers['X-Project-Id'] = projectId;
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      localStorage.removeItem('auth-store');
      globalThis.location.href = '/auth';
    }
    return Promise.reject(err);
  }
);

export default api;
