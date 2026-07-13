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
  login: (email: string, password: string) =>
    request<{ token: string; user: { id: number; email: string; name: string } }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, name: string) =>
    request<{ token: string; user: { id: number; email: string; name: string } }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    }),
  me: () => request<{ id: number; email: string; name: string }>('/api/auth/me'),

  sessions: {
    list: () => request<{ id: number; title: string; created_at: string }[]>('/api/sessions'),
    get: (id: number) => request<{ id: number; title: string; created_at: string; messages: any[] }>(`/api/sessions/${id}`),
    create: (title?: string) =>
      request<{ id: number; title: string; created_at: string }>('/api/sessions', {
        method: 'POST',
        body: JSON.stringify({ title }),
      }),
    delete: (id: number) =>
      request<void>(`/api/sessions/${id}`, { method: 'DELETE' }),
    patch: (id: number, data: { title?: string }) =>
      request<{ id: number; title: string; created_at: string }>(`/api/sessions/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
  },
};
