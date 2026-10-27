/**
 * Academic Timetable Management API Client.
 *
 * Provides normalized, error-safe HTTP communication with the FastAPI backend
 * with support for deployed Vercel/Render configurations and local development.
 */

// Normalizes API endpoint URLs to avoid accidental double slashes or duplicated '/api' segments
export const buildApiUrl = (baseUrl, endpoint = '') => {
  const base = (baseUrl || 'http://127.0.0.1:8000').trim().replace(/\/+$/, '');
  const path = endpoint.trim().startsWith('/') ? endpoint.trim() : `/${endpoint.trim()}`;

  if (base.endsWith('/api') && path.startsWith('/api/')) {
    return `${base}${path.slice(4)}`;
  }
  if (base.endsWith(path)) {
    return base;
  }
  return `${base}${path}`;
};

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

/**
 * Standard fetch wrapper that parses JSON and provides structured error messages.
 */
async function request(endpoint, options = {}) {
  const url = buildApiUrl(API_BASE_URL, endpoint);
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers || {}),
    },
  };

  try {
    const response = await fetch(url, config);
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorMessage =
        (typeof data === 'object' && data?.message) ||
        (typeof data === 'object' && data?.detail) ||
        `Request failed with status ${response.status}`;
      const error = new Error(errorMessage);
      error.status = response.status;
      error.payload = data;
      throw error;
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkError = new Error(
        'Unable to reach scheduling service. Please ensure the backend is running.'
      );
      networkError.isNetworkError = true;
      throw networkError;
    }
    throw err;
  }
}

/**
 * Retrieve supported academic dataset scopes.
 */
export async function getDatasets() {
  return request('/api/datasets');
}

/**
 * Retrieve the latest verified timetable from SQLite.
 */
export async function getLatestTimetable(dataset = 'default', divisionId = null) {
  let endpoint = `/api/timetable/latest?dataset=${encodeURIComponent(dataset)}`;
  if (divisionId && divisionId !== 'ALL') {
    endpoint += `&division_id=${encodeURIComponent(divisionId)}`;
  }
  return request(endpoint);
}

/**
 * Retrieve the course conflict network formatted for React Flow.
 */
export async function getConflictGraph(dataset = 'default') {
  return request(`/api/graph?dataset=${encodeURIComponent(dataset)}`);
}

/**
 * Trigger automated timetable generation on the backend.
 */
export async function generateTimetable({
  dataset = 'default',
  seed = 42,
  maxAttempts = 10,
  optimizerIterations = 500,
} = {}) {
  return request('/api/generate', {
    method: 'POST',
    body: JSON.stringify({
      dataset,
      seed,
      max_attempts: maxAttempts,
      optimizer_iterations: optimizerIterations,
    }),
  });
}

/**
 * Lightweight health check for verification.
 */
export async function checkBackendHealth() {
  return request('/api/health');
}
