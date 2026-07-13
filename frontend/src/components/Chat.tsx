import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';

interface Message { role: string; content: string; }

export function Chat({ sessionId }: { sessionId: string | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const { messages: wsMessages, connected, send } = useWebSocket(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      api.getSession(sessionId).then(data => setMessages(data.messages || [])).catch(() => {});
    }
  }, [sessionId]);

  useEffect(() => {
    const last = wsMessages[wsMessages.length - 1];
    if (last?.type === 'status' && last.data === 'done') setRunning(false);
    if (last?.type === 'result') {
      setMessages(prev => [...prev, { role: 'assistant', content: last.data }]);
    }
  }, [wsMessages]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || running) return;
    const text = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setRunning(true);
    await api.sendMessage(sessionId, text);
    send({ type: 'run', prompt: text });
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles size={48} style={{ color: '#7C3AED' }} className="mb-4" />
            <h2 className="text-xl font-semibold mb-2" style={{ color: '#E8EEEC' }}>O que você deseja criar?</h2>
            <p className="text-sm" style={{ color: '#8FA99F' }}>Descreva sua tarefa e o Luwei Assistant fará o resto.</p>
          </div>
        )}
        {messages.map((m, i) => <MessageBubble key={i} message={m} />)}
        <div ref={bottomRef} />
      </div>
      <div className="p-4 border-t" style={{ borderColor: '#1A2926' }}>
        <div className="flex gap-3 items-end">
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Digite sua tarefa..."
            rows={1}
            className="flex-1 rounded-xl px-4 py-3 text-sm resize-none outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          <button onClick={handleSend} disabled={!input.trim() || running || !connected}
            className="p-3 rounded-xl text-white transition-all duration-200 disabled:opacity-30"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
