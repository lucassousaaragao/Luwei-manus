import { useState, useEffect } from 'react';
import { Folder, Plus, Trash2, Edit3, Check, X, Layers } from 'lucide-react';
import { api } from '../lib/api';

interface Workspace {
  id: string;
  name: string;
  description: string;
}

export function WorkspaceManager({
  activeWorkspace,
  onSelect,
}: {
  activeWorkspace: string | null;
  onSelect: (id: string | null) => void;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  useEffect(() => {
    api.getWorkspaces().then(setWorkspaces).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    const w = await api.createWorkspace(name.trim(), desc.trim());
    setWorkspaces(prev => [w, ...prev]);
    setCreating(false);
    setName('');
    setDesc('');
    onSelect(w.id);
  };

  const handleDelete = async (id: string) => {
    await api.deleteWorkspace(id);
    setWorkspaces(prev => prev.filter(w => w.id !== id));
    if (activeWorkspace === id) onSelect(null);
  };

  const handleRename = async (id: string) => {
    if (!editName.trim()) return;
    await api.updateWorkspace(id, { name: editName.trim() });
    setWorkspaces(prev => prev.map(w => w.id === id ? { ...w, name: editName.trim() } : w));
    setEditing(null);
  };

  return (
    <div>
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#445C58' }}>
          <Layers size={12} className="inline mr-1" /> Workspaces
        </span>
        <button onClick={() => setCreating(true)} className="p-1 rounded hover:bg-white/5 transition-colors" style={{ color: '#8FA99F' }}>
          <Plus size={14} />
        </button>
      </div>
      <div className="space-y-0.5 px-2">
        <button
          onClick={() => onSelect(null)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all"
          style={{
            background: !activeWorkspace ? 'rgba(124,58,237,0.1)' : 'transparent',
            color: !activeWorkspace ? '#C4B5FD' : '#8FA99F',
          }}
        >
          <Folder size={14} />
          Todas as sessões
        </button>
        {workspaces.map(w => (
          <div key={w.id} className="flex items-center gap-1">
            <button
              onClick={() => onSelect(w.id)}
              className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all text-left"
              style={{
                background: activeWorkspace === w.id ? 'rgba(124,58,237,0.1)' : 'transparent',
                color: activeWorkspace === w.id ? '#C4B5FD' : '#8FA99F',
              }}
            >
              <Folder size={14} />
              {editing === w.id ? (
                <input
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  className="flex-1 bg-transparent border-b outline-none text-xs"
                  style={{ borderColor: '#7C3AED', color: '#E8EEEC' }}
                  autoFocus
                  onKeyDown={e => { if (e.key === 'Enter') handleRename(w.id); if (e.key === 'Escape') setEditing(null); }}
                />
              ) : (
                <span className="truncate">{w.name}</span>
              )}
            </button>
            {editing === w.id ? (
              <>
                <button onClick={() => handleRename(w.id)} className="p-1 hover:text-green-400" style={{ color: '#4CAF7A' }}>
                  <Check size={12} />
                </button>
                <button onClick={() => setEditing(null)} className="p-1" style={{ color: '#445C58' }}>
                  <X size={12} />
                </button>
              </>
            ) : (
              <>
                <button onClick={() => { setEditing(w.id); setEditName(w.name); }} className="p-1 hover:text-white/80" style={{ color: '#445C58' }}>
                  <Edit3 size={10} />
                </button>
                <button onClick={() => handleDelete(w.id)} className="p-1 hover:text-red-400" style={{ color: '#445C58' }}>
                  <Trash2 size={10} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
      {creating && (
        <div className="p-3 border-t" style={{ borderColor: '#1A2926' }}>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Nome do workspace"
            className="w-full rounded-lg px-3 py-2 text-xs mb-2 outline-none focus:ring-1"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }}
            autoFocus
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false); }}
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="flex-1 py-1.5 rounded-lg text-xs font-medium text-white" style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
              Criar
            </button>
            <button onClick={() => setCreating(false)} className="px-3 py-1.5 rounded-lg text-xs" style={{ background: '#131F1C', color: '#8FA99F' }}>
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
