/**
 * Auth view logic — login, signup, token display.
 */
const auth = {
  init() {
    // Tab switching
    document.querySelectorAll('.tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
      });
    });

    // Signup checkbox → enable button
    document.getElementById('signup-agree').addEventListener('change', (e) => {
      document.getElementById('signup-btn').disabled = !e.target.checked;
    });

    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('login-error');
      errEl.classList.add('hidden');
      const email = document.getElementById('login-email').value.trim();
      const token = document.getElementById('login-token').value.trim();
      if (!email || !token) { errEl.textContent = 'Please fill in all fields.'; errEl.classList.remove('hidden'); return; }

      const btn = e.target.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Validating...';
      try {
        await api.login(token, email);
        auth._saveSession(token, '', email);
        app.showChat();
      } catch (err) {
        errEl.textContent = err.message || 'Invalid token. Please try again.';
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Login';
      }
    });

    // Signup form
    document.getElementById('signup-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('signup-error');
      errEl.classList.add('hidden');
      const name = document.getElementById('signup-name').value.trim();
      const email = document.getElementById('signup-email').value.trim();
      if (!name || !email) { errEl.textContent = 'Please fill in all fields.'; errEl.classList.remove('hidden'); return; }

      const btn = document.getElementById('signup-btn');
      btn.disabled = true;
      btn.textContent = 'Creating...';
      try {
        const data = await api.signup(name, email);
        auth._showToken(data.access_token, name, email);
      } catch (err) {
        errEl.textContent = err.message || 'Failed to create account.';
        errEl.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Create Account';
      }
    });

    // Copy token
    document.getElementById('copy-token-btn').addEventListener('click', () => {
      const token = document.getElementById('token-value').textContent;
      navigator.clipboard.writeText(token).then(() => {
        const btn = document.getElementById('copy-token-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
      });
    });

    // Continue to chat after signup
    document.getElementById('continue-btn').addEventListener('click', () => {
      const token = document.getElementById('token-value').textContent;
      const name = auth._pendingName || '';
      const email = auth._pendingEmail || '';
      auth._saveSession(token, name, email);
      app.showChat();
    });
  },

  _pendingName: '',
  _pendingEmail: '',

  _showToken(token, name, email) {
    auth._pendingName = name;
    auth._pendingEmail = email;
    // Hide tabs and show token display
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
    document.querySelector('.tabs').classList.add('hidden');
    document.getElementById('token-display').classList.add('active');
    document.getElementById('signup-info').innerHTML =
      `<strong>Name:</strong> ${name}<br><strong>Email:</strong> ${email}`;
    document.getElementById('token-value').textContent = token;
  },

  _saveSession(token, name, email) {
    localStorage.setItem('gf_token', token);
    localStorage.setItem('gf_name', name);
    localStorage.setItem('gf_email', email);
  },

  getSession() {
    const token = localStorage.getItem('gf_token');
    if (!token) return null;
    return {
      token,
      name: localStorage.getItem('gf_name') || '',
      email: localStorage.getItem('gf_email') || '',
    };
  },

  clearSession() {
    localStorage.removeItem('gf_token');
    localStorage.removeItem('gf_name');
    localStorage.removeItem('gf_email');
  },
};
