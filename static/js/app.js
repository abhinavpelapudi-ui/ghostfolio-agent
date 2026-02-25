/**
 * Main entry point — view switching and initialization.
 */
const app = {
  init() {
    auth.init();
    const session = auth.getSession();
    if (session && session.token) {
      app.showChat();
    } else {
      app.showAuth();
    }
  },

  showAuth() {
    document.getElementById('auth-view').classList.remove('hidden');
    document.getElementById('chat-view').classList.add('hidden');
    // Reset auth form state
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
    document.querySelector('.tab[data-tab="login"]').classList.add('active');
    document.getElementById('tab-login').classList.add('active');
    document.querySelector('.tabs').classList.remove('hidden');
    // Clear form inputs
    document.getElementById('login-email').value = '';
    document.getElementById('login-token').value = '';
    document.getElementById('signup-name').value = '';
    document.getElementById('signup-email').value = '';
    document.getElementById('signup-agree').checked = false;
    document.getElementById('signup-btn').disabled = true;
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('signup-error').classList.add('hidden');
  },

  showChat() {
    document.getElementById('auth-view').classList.add('hidden');
    document.getElementById('chat-view').classList.remove('hidden');
    models.init();
    chat.init();
    document.getElementById('chat-input').focus();
  },
};

document.addEventListener('DOMContentLoaded', app.init);
