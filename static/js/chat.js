/**
 * Chat view logic — messages, sending, rendering.
 */
const TOOL_ICONS = {
  portfolio_summary: '📊', portfolio_performance: '📈',
  holding_detail: '🔍', transactions: '💸',
  dividend_history: '💰', symbol_search: '🔎',
  market_sentiment: '⚖️', add_trade: '➕',
};

const chat = {
  history: [],   // [{role, content, tools?, cost?, traceId?}]
  sending: false,
  _lastFailedMessage: null,

  init() {
    const session = auth.getSession();
    // Update sidebar
    const name = session?.name || '';
    const email = session?.email || '';
    const token = session?.token || '';
    document.getElementById('user-name-display').textContent = name ? `User: ${name}` : '';
    document.getElementById('user-email-display').textContent = email ? `Email: ${email}` : '';
    document.getElementById('user-token-display').textContent = token ? `Token: ...${token.slice(-8)}` : '';

    // Load persisted history and re-render
    chat._loadHistory();

    // Welcome message (only if no history)
    if (chat.history.length === 0) {
      const display = name || email || 'there';
      chat._appendWelcome(display);
    }

    // Chat form
    document.getElementById('chat-form').addEventListener('submit', (e) => {
      e.preventDefault();
      chat.send();
    });

    // Sidebar toggle (mobile)
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    document.getElementById('menu-toggle').addEventListener('click', () => {
      sidebar.classList.toggle('open');
      backdrop.classList.toggle('open');
    });
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
      auth.clearSession();
      chat.history = [];
      localStorage.removeItem('gf_chat_history');
      document.getElementById('messages').innerHTML = '';
      app.showAuth();
    });
  },

  async send(retryMessage) {
    if (chat.sending) return;
    const input = document.getElementById('chat-input');
    const message = retryMessage || input.value.trim();
    if (!message) return;

    const session = auth.getSession();
    if (!session) { app.showAuth(); return; }

    if (!retryMessage) input.value = '';
    chat.sending = true;
    document.getElementById('send-btn').disabled = true;
    chat._lastFailedMessage = null;

    // Show user message (only if not a retry — retry already has the message shown)
    if (!retryMessage) {
      chat.history.push({ role: 'user', content: message });
      chat._saveHistory();
      chat._renderMessage('user', message);
    }

    // Show typing indicator
    const typing = chat._showTyping();

    try {
      // Send last 18 messages for context
      const historySlice = chat.history.slice(-18);
      const data = await api.send(message, models.getSelected(), historySlice, session.token);

      typing.remove();
      chat.history.push({
        role: 'assistant', content: data.response,
        tools: data.tools_called, cost: data.cost_usd,
        traceId: data.trace_id, skillUsed: data.skill_used,
      });
      chat._saveHistory();
      chat._renderAssistant(data.response, data.tools_called, data.cost_usd, data.trace_id, data.skill_used);
    } catch (err) {
      typing.remove();
      chat._lastFailedMessage = message;

      if (err.status === 401) {
        chat._renderError('Your session has expired. Redirecting to login...', false);
        auth.clearSession();
        setTimeout(() => app.showAuth(), 2000);
      } else if (err.status === 429) {
        const wait = err.retryAfter || 30;
        chat._renderError(
          `Rate limited by the portfolio service. Please wait ${wait} seconds and try again.`,
          true,
          message,
        );
      } else if (err.status === 502) {
        chat._renderError(
          'Cannot connect to the portfolio service. It may be temporarily down.',
          true,
          message,
        );
      } else {
        chat._renderError(
          `Something went wrong: ${err.message}`,
          true,
          message,
        );
      }
    } finally {
      chat.sending = false;
      document.getElementById('send-btn').disabled = false;
      input.focus();
    }
  },

  _appendWelcome(displayName) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message welcome';
    div.innerHTML = chat._md(
      `**Welcome, ${displayName}!** Your portfolio is ready.\n\n` +
      'Try asking:\n' +
      '- "I bought 10 shares of AAPL at $230"\n' +
      '- "Show me my portfolio summary"\n' +
      '- "How has my portfolio performed?"\n' +
      '- "Search for Apple stock"'
    );
    container.appendChild(div);
  },

  _renderMessage(role, content) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = role === 'user' ? chat._escapeHtml(content) : chat._md(content);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  },

  _renderError(text, showRetry, retryMsg) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message assistant error-message';
    div.innerHTML = `<p style="color:#e74c3c">${chat._escapeHtml(text)}</p>`;
    if (showRetry && retryMsg) {
      const btn = document.createElement('button');
      btn.className = 'retry-btn';
      btn.textContent = 'Retry';
      btn.addEventListener('click', () => {
        div.remove();
        chat.send(retryMsg);
      });
      div.appendChild(btn);
    }
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  },

  _renderAssistant(content, tools, cost, traceId, skillUsed) {
    const container = document.getElementById('messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'message assistant';
    wrapper.innerHTML = chat._md(content);

    if ((tools && tools.length > 0) || skillUsed) {
      const bar = document.createElement('div');
      bar.className = 'tools-bar';
      if (skillUsed) {
        const skillPill = document.createElement('span');
        skillPill.className = 'tool-pill skill-pill';
        skillPill.textContent = skillUsed.replace(/_/g, ' ');
        bar.appendChild(skillPill);
      }
      if (tools) {
        tools.forEach((t) => {
          const pill = document.createElement('span');
          pill.className = 'tool-pill';
          pill.textContent = `${TOOL_ICONS[t] || '🔧'} ${t}`;
          bar.appendChild(pill);
        });
      }
      wrapper.appendChild(bar);
    }

    // Meta row: cost + feedback
    const meta = document.createElement('div');
    meta.className = 'meta-bar';

    if (cost && cost > 0) {
      const costEl = document.createElement('span');
      costEl.className = 'cost-label';
      costEl.textContent = `Cost: $${cost.toFixed(6)}`;
      meta.appendChild(costEl);
    }

    if (traceId) {
      const fb = document.createElement('span');
      fb.className = 'feedback-bar';
      fb.innerHTML =
        `<button class="btn-feedback" data-rating="up" title="Helpful">&#x1F44D;</button>` +
        `<button class="btn-feedback" data-rating="down" title="Not helpful">&#x1F44E;</button>`;
      fb.querySelectorAll('.btn-feedback').forEach((btn) => {
        btn.addEventListener('click', () => chat._sendFeedback(btn, traceId));
      });
      meta.appendChild(fb);
    }

    wrapper.appendChild(meta);
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
  },

  async _sendFeedback(btn, traceId) {
    const bar = btn.parentElement;
    const rating = btn.dataset.rating;
    bar.querySelectorAll('.btn-feedback').forEach((b) => {
      b.disabled = true;
      b.classList.remove('active');
    });
    btn.classList.add('active');
    try {
      const session = auth.getSession();
      // Find the user query that preceded this assistant response
      const idx = chat.history.findIndex((m) => m.traceId === traceId);
      const query = idx > 0 ? chat.history[idx - 1].content : '';
      if (session) await api.feedback(traceId, rating, session.token, query);
    } catch (e) {
      console.error('Feedback failed:', e);
    }
  },

  _showTyping() {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
  },

  /** Simple markdown → HTML */
  _md(text) {
    let html = chat._escapeHtml(text);
    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Unordered list items
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    // Single newlines (not inside pre)
    html = html.replace(/\n/g, '<br>');
    return `<p>${html}</p>`;
  },

  _saveHistory() {
    try {
      localStorage.setItem('gf_chat_history', JSON.stringify(chat.history));
    } catch (e) { /* quota exceeded — ignore */ }
  },

  _loadHistory() {
    try {
      const raw = localStorage.getItem('gf_chat_history');
      if (!raw) return;
      const items = JSON.parse(raw);
      if (!Array.isArray(items)) return;
      chat.history = items;
      for (const item of items) {
        if (item.role === 'user') {
          chat._renderMessage('user', item.content);
        } else if (item.role === 'assistant') {
          chat._renderAssistant(item.content, item.tools, item.cost, item.traceId, item.skillUsed);
        }
      }
    } catch (e) { /* corrupt data — start fresh */ }
  },

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};
