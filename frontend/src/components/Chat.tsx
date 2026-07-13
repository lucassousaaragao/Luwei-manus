import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Brain, Zap, ChevronDown } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';
import { ModelSelector } from './ModelSelector';

interface Message { role: string; content: string; }

export function Chat({
  sessionId,
  model,
  mode,
  speed,
  onModelChange,
  onModeChange,
  onSpeedChange,
}: {
  sessionId: string | null;
  model: string;
  mode: string;
  speed: string;
  onModelChange: (m: string) => void;
  onModeChange: (m: string) => void;
  onSpeedChange: (s: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const { messages: wsMessages, connected, send } = useWebSocket(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showSpeed, setShowSpeed] = useState(false);

  useEffect(() => {
    if (sessionId) {
      api.getSession(sessionId).then(data => {
        setMessages(data.messages || []);
        if (data.model && onModelChange) onModelChange(data.model);
        if (data.mode && onModeChange) onModeChange(data.mode);
        if (data.speed && onSpeedChange) onSpeedChange(data.speed);
      }).catch(() => {});
    } else {
      setMessages([]);
      setRunning(false);
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
    if (sessionId) {
      await api.sendMessage(sessionId, text).catch(() => {});
    }
    send({ type: 'run', prompt: text, model, mode, speed });
  };

  const speeds = [
    { key: 'slow', label: 'Lento', desc: 'Máximo raciocínio' },
    { key: 'medium', label: 'Médio', desc: 'Balanceado' },
    { key: 'fast', label: 'Rápido', desc: 'Respostas ágeis' },
  ];

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-2 border-b" style={{ borderColor: '#1A2926', background: '#0A0F0E' }}>
        {sessionId && (
          <>
            <ModelSelector current={model} onChange={onModelChange} />
            <div className="flex rounded-lg overflow-hidden border" style={{ borderColor: '#1A2926' }}>
              <button
                onClick={() => onModeChange('chat')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all"
                style={{
                  background: mode === 'chat' ? 'rgba(249,115,22,0.15)' : 'transparent',
                  color: mode === 'chat' ? '#FDA474' : '#445C58',
                }}
              >
                <Zap size={12} /> Chat
              </button>
              <button
                onClick={() => onModeChange('planning')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all"
                style={{
                  background: mode === 'planning' ? 'rgba(124,58,237,0.15)' : 'transparent',
                  color: mode === 'planning' ? '#C4B5FD' : '#445C58',
                }}
              >
                <Brain size={12} /> Planning
              </button>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowSpeed(!showSpeed)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-white/5"
                style={{ color: '#8FA99F', border: '1px solid #1A2926' }}
              >
                <Zap size={12} />
                {speeds.find(s => s.key === speed)?.label || 'Médio'}
                <ChevronDown size={10} />
              </button>
              {showSpeed && (
                <div
                  className="absolute top-full left-0 mt-1 w-36 rounded-xl z-50 shadow-2xl overflow-hidden"
                  style={{ background: '#0E1815', border: '1px solid #1A2926' }}
                >
                  {speeds.map(s => (
                    <button
                      key={s.key}
                      onClick={() => { onSpeedChange(s.key); setShowSpeed(false); }}
                      className="w-full text-left px-3 py-2 text-xs transition-all hover:bg-white/5"
                      style={{ color: speed === s.key ? '#E8EEEC' : '#8FA99F' }}
                    >
                      <div className="font-medium">{s.label}</div>
                      <div style={{ color: '#445C58' }}>{s.desc}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
        <div className="flex-1" />
        {!connected && sessionId && (
          <span className="text-xs font-medium" style={{ color: '#E05050' }}>
            Desconectado
          </span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && !sessionId && (
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
          <button onClick={handleSend} disabled={!input.trim() || running || !connected || !sessionId}
            className="p-3 rounded-xl text-white transition-all duration-200 disabled:opacity-30"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
