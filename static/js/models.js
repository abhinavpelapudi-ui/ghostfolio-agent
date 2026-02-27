/**
 * Model selector management.
 */
const models = {
  async init() {
    const select = document.getElementById('model-select');
    try {
      const data = await api.getModels();
      select.innerHTML = '';
      data.models.forEach((m) => {
        const opt = document.createElement('option');
        opt.value = m.model_id;
        opt.textContent = m.display_name;
        if (!m.available) {
          opt.textContent += ' (no key)';
          opt.disabled = true;
        }
        if (m.model_id === data.default) opt.selected = true;
        select.appendChild(opt);
      });
    } catch (e) {
      console.error('Failed to load models:', e);
      select.innerHTML = '<option>Failed to load models</option>';
    }
  },

  getSelected() {
    return document.getElementById('model-select').value;
  },
};
