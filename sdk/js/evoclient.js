// AUTO-EVO-AI JavaScript SDK
// 浏览器或 Node.js 使用
// npm install 或 import 到你的项目

class EvoClient {
  constructor(baseURL = 'https://autoevoai.com', apiKey = null) {
    this.base = baseURL.replace(/\/+$/, '');
    this.key = apiKey;
  }

  async _fetch(path, opts = {}) {
    const url = this.base + path;
    const headers = { 'Content-Type': 'application/json' };
    if (this.key) headers['Authorization'] = `Bearer ${this.key}`;
    try {
      const res = await fetch(url, { ...opts, headers });
      const data = await res.json();
      return { status: res.status, data };
    } catch (e) {
      return { status: 0, error: e.message };
    }
  }

  async chat(msg) { return this._fetch('/api/v1/chat', { method: 'POST', body: JSON.stringify({ message: msg }) }); }
  async smartChat(msg) { return this._fetch('/api/v2/chat', { method: 'POST', body: JSON.stringify({ message: msg }) }); }

  async modules(category) {
    let p = '/api/v1/modules';
    if (category) p += `?category=${encodeURIComponent(category)}`;
    return this._fetch(p);
  }

  async moduleDetail(name) { return this._fetch(`/api/v1/modules/${encodeURIComponent(name)}`); }
  async skills(category) {
    let p = '/api/v1/skills';
    if (category) p += `?category=${encodeURIComponent(category)}`;
    return this._fetch(p);
  }

  async skillExecute(name, params = {}) {
    return this._fetch(`/api/v1/skills/${encodeURIComponent(name)}/execute`, {
      method: 'POST', body: JSON.stringify(params)
    });
  }

  async status() { return this._fetch('/api/v1/status'); }
  async version() { return this._fetch('/api/v1/version'); }
  async health() { return this._fetch('/api/v1/health'); }

  async mcpServers() { return this._fetch('/api/v1/mcp/servers'); }
  async mcpCall(server, tool, args = {}) {
    return this._fetch(`/api/v1/mcp/${server}/${tool}`, { method: 'POST', body: JSON.stringify(args) });
  }

  async search(query) { return this._fetch(`/api/v1/search?q=${encodeURIComponent(query)}`); }
  async ragQuery(query, collection = 'default') {
    return this._fetch('/api/v1/rag/query', { method: 'POST', body: JSON.stringify({ query, collection }) });
  }
}

// Node.js export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { EvoClient };
}
