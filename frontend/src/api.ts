import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

// Request interceptor for debugging
api.interceptors.request.use((config) => {
  console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data || '');
  return config;
});

// Response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.status);
    return response;
  },
  (error) => {
    console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export default api;
