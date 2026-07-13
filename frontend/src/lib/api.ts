const BASE_URL = import.meta.env.VITE_API_URL || '';

interface RequestInitWithTimeout extends RequestInit {
  timeout?: number;
}

async function request<T = any>(path: string, options?: RequestInitWithTimeout): Promise<T> {
  const token = localStorage.getItem('token');
  const controller = new AbortController();
  const timeout = options?.timeout ?? 30000;
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      signal: options?.signal ?? controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ token: string; user: { id: number; email: string; name: string } }>('/api/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, name: string) =>
    request<{ token: string; user: { id: number; email: string; name: string } }>('/api/auth/register', {
      method: 'POST', body: JSON.stringify({ email, password, name }),
    }),
  me: () => request<{ id: number; email: string; name: string }>('/api/auth/me'),

  // Sessions
  getSessions: (workspaceId?: string) =>
    request(`/api/chat/sessions${workspaceId ? `?workspace_id=${workspaceId}` : ''}`),
  createSession: (title: string, model: string, mode = 'chat', speed = 'medium', workspaceId?: string) =>
    request('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title, model, mode, speed, workspace_id: workspaceId }),
    }),
  getSession: (id: string) => request(`/api/chat/sessions/${id}`),
  updateSession: (id: string, data: { title?: string; model?: string; mode?: string; speed?: string }) =>
    request(`/api/chat/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSession: (id: string) =>
    request(`/api/chat/sessions/${id}`, { method: 'DELETE' }),
  sendMessage: (sessionId: string, content: string) =>
    request(`/api/chat/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({ content }) }),

  // Models
  getModels: () => request('/api/models'),
  getProviders: () => request('/api/models/providers'),

  // Workspaces
  getWorkspaces: () => request('/api/workspaces'),
  createWorkspace: (name: string, description?: string) =>
    request('/api/workspaces', { method: 'POST', body: JSON.stringify({ name, description }) }),
  updateWorkspace: (id: string, data: { name?: string; description?: string }) =>
    request(`/api/workspaces/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWorkspace: (id: string) =>
    request(`/api/workspaces/${id}`, { method: 'DELETE' }),

  // MCP
  getMcpConfigs: (workspaceId: string) =>
    request(`/api/mcp/configs?workspace_id=${workspaceId}`),
  createMcpConfig: (data: { workspace_id: string; name: string; type: string; command?: string; url?: string; args?: string[] }) =>
    request('/api/mcp/configs', { method: 'POST', body: JSON.stringify(data) }),
  updateMcpConfig: (id: string, data: any) =>
    request(`/api/mcp/configs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMcpConfig: (id: string) =>
    request(`/api/mcp/configs/${id}`, { method: 'DELETE' }),
};
