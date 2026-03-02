/**
 * API wrapper for chat backend routes.
 */
class ApiError extends Error {
  constructor(message, status, retryAfter = null) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function _handleResponse(res) {
  if (res.ok) return res.json();
  const retryAfter = res.headers.get('Retry-After');
  const err = await res.json().catch(() => ({}));
  throw new ApiError(
    err.detail || `Request failed (${res.status})`,
    res.status,
    retryAfter ? parseInt(retryAfter, 10) : null,
  );
}

const api = {
  async login(token, email) {
    const res = await fetch('/chat/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, email }),
    });
    return _handleResponse(res);
  },

  async signup(name, email) {
    const res = await fetch('/chat/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email }),
    });
    return _handleResponse(res);
  },

  async send(message, modelId, history, token) {
    const res = await fetch('/chat/send', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Ghostfolio-Token': token,
      },
      body: JSON.stringify({ message, model_id: modelId, history }),
    });
    return _handleResponse(res);
  },

  async feedback(traceId, rating, token, query = '') {
    const res = await fetch('/chat/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Ghostfolio-Token': token,
      },
      body: JSON.stringify({ trace_id: traceId, rating, query }),
    });
    return _handleResponse(res);
  },

  async getModels() {
    const res = await fetch('/chat/models');
    if (!res.ok) throw new ApiError('Failed to load models', res.status);
    return res.json();
  },

  async validateToken(token) {
    const res = await fetch('/chat/validate', {
      method: 'POST',
      headers: { 'X-Ghostfolio-Token': token },
    });
    return res.ok;
  },
};
