import axios from 'axios';

/** Base URL for the Flask API server */
const API_BASE = 'http://localhost:5678';

/** Pre-configured axios instance for all API calls */
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
export { API_BASE };
