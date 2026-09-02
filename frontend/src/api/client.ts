import axios from 'axios';

/** Base URL for the Flask API server */
// In production the frontend is served by the Flask backend itself,
// so the API lives at our own origin — which keeps alternate-port
// launches (the scratch-database mode) working. The Vite dev server
// (port 5173) is the one case where the backend is elsewhere.
const API_BASE = window.location.port === '5173'
  ? 'http://localhost:5678'
  : window.location.origin;

/** Pre-configured axios instance for all API calls */
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
export { API_BASE };
