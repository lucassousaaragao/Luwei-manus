import { useEffect, useRef, useState, useCallback } from 'react';

interface WSMessage { type: string; task_id?: string; data: any; }

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [connected, setConnected] = useState(false);

  const send = useCallback((msg: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const token = localStorage.getItem('token');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_URL || `${protocol}//localhost:8000`;
    const socket = new WebSocket(`${host}/ws/agent/${sessionId}?token=${token || ''}`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try { setMessages(prev => [...prev, JSON.parse(event.data)]); } catch {}
    };

    return () => { socket.close(); };
  }, [sessionId]);

  const clear = useCallback(() => setMessages([]), []);

  return { messages, connected, send, clear };
}
