import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Plus, MessageSquare, LogOut, User, Settings } from 'lucide-react';
import { WorkspaceManager } from './WorkspaceManager';

interface Session { id: string; title: string; }

export function Sidebar({
  activeSession,
  onSelect,
  onNew,
  workspaceId,
  onWorkspaceChange,
  onOpenSettings,
}: {
  activeSession: string | null;
  onSelect: (id: string) => void;
  onNew: (workspaceId?: string) => void;
  workspaceId: string | null;
  onWorkspaceChange: (id: string | null) => void;
  onOpenSettings: () => void;
}) {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    api.getSessions(workspaceId || undefined).then(setSessions).catch(() => {});
  }, [workspaceId]);

  return (
    <div className="w-64 flex flex-col h-full border-r" style={{ background: '#0A0F0E', borderColor: '#1A2926' }}>
      <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: '#1A2926' }}>
        <h2 className="text-lg font-bold" style={{ color: '#E8EEEC' }}>Luwei</h2>
        <button onClick={onOpenSettings} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors" style={{ color: '#445C58' }}>
          <Settings size={16} />
        </button>
      </div>
      <div className="p-3">
        <button onClick={() => onNew(workspaceId || undefined)}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white transition-all duration-200 hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
          <Plus size={18} /> Novo Chat
        </button>
      </div>
      <div className="border-t" style={{ borderColor: '#1A2926' }}>
        <WorkspaceManager activeWorkspace={workspaceId} onSelect={onWorkspaceChange} />
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-1 mt-2">
        {sessions.length === 0 && (
          <p className="text-xs text-center px-3 py-4" style={{ color: '#445C58' }}>Nenhuma sessão ainda</p>
        )}
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
