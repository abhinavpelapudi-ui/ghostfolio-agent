/**
 * API wrapper for chat backend routes.
 */
const api = {
  async login(token, email) {
    const res = await fetch('/chat/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  async signup(name, email) {
    const res = await fetch('/chat/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Signup failed');
    }
    return res.json();
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Feedback failed');
    }
    return res.json();
  },

  async getModels() {
    const res = await fetch('/chat/models');
    if (!res.ok) throw new Error('Failed to load models');
    return res.json();
  },
};
