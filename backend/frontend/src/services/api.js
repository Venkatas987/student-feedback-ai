import axios from 'axios';

// ML analytics endpoints (summary, clustering-metrics, umap) can take 20-40 s on
// a cold cache because they run TF-IDF keyword extraction + silhouette scoring
// over a large SQLite dataset.  90 s covers the worst-case cold-start; cached
// responses return in < 100 ms.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add the auth token header to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle 401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      // Potential redirect to login can go here
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
