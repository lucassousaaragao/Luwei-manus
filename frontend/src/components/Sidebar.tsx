import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Plus, MessageSquare, LogOut, User } from 'lucide-react';

interface Session { id: string; title: string; }

export function Sidebar({ activeSession, onSelect, onNew }: {
  activeSession: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    api.getSessions().then(setSessions).catch(() => {});
  }, []);

  return (
    <div className="w-64 flex flex-col h-full border-r" style={{ background: '#0A0F0E', borderColor: '#1A2926' }}>
      <div className="p-4 border-b" style={{ borderColor: '#1A2926' }}>
        <h2 className="text-lg font-bold" style={{ color: '#E8EEEC' }}>Luwei Assistant</h2>
      </div>
      <div className="p-3">
        <button onClick={onNew}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white transition-all duration-200 hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
          <Plus size={18} /> Novo Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {sessions.map(s => (
          <button key={s.id} onClick={() => onSelect(s.id)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200"
            style={{
              background: activeSession === s.id ? 'rgba(124,58,237,0.15)' : 'transparent',
              color: activeSession === s.id ? '#E8EEEC' : '#8FA99F',
              border: activeSession === s.id ? '1px solid rgba(124,58,237,0.3)' : '1px solid transparent',
            }}>
            <MessageSquare size={16} />
            <span className="truncate">{s.title}</span>
          </button>
        ))}
      </div>
      <div className="p-3 border-t" style={{ borderColor: '#1A2926' }}>
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: '#0E1815' }}>
          <User size={16} style={{ color: '#7C3AED' }} />
          <span className="text-sm flex-1 truncate" style={{ color: '#8FA99F' }}>{user?.email}</span>
          <button onClick={logout} className="p-1 rounded-lg hover:bg-white/5 transition-colors" style={{ color: '#445C58' }}>
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
