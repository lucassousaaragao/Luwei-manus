import { useState, useEffect } from 'react';
import { Plus, Trash2, Power, PowerOff } from 'lucide-react';
import { api } from '../lib/api';

interface McpConfig {
  id: string;
  workspace_id: string;
  name: string;
  type: string;
  command: string;
  url: string;
  args: string;
  enabled: number;
}

export function McpConfig({ workspaceId }: { workspaceId: string }) {
  const [configs, setConfigs] = useState<McpConfig[]>([]);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState<'stdio' | 'sse'>('stdio');
  const [command, setCommand] = useState('');
  const [url, setUrl] = useState('');
  const [args, setArgs] = useState('');

  useEffect(() => {
    api.getMcpConfigs(workspaceId).then(setConfigs).catch(() => {});
  }, [workspaceId]);

  const handleAdd = async () => {
    if (!name.trim()) return;
    const data: any = { workspace_id: workspaceId, name: name.trim(), type };
    if (type === 'stdio') {
      data.command = command;
      data.args = args.split(' ').filter(Boolean);
    } else {
      data.url = url;
    }
    const created = await api.createMcpConfig(data);
    setConfigs(prev => [...prev, { ...created, args: JSON.stringify(created.args || []), enabled: 1, command: command, url: url, type: type, workspace_id: workspaceId }]);
    setAdding(false);
    setName('');
    setCommand('');
    setUrl('');
    setArgs('');
  };

  const handleToggle = async (cfg: McpConfig) => {
    await api.updateMcpConfig(cfg.id, { enabled: !cfg.enabled });
    setConfigs(prev => prev.map(c => c.id === cfg.id ? { ...c, enabled: c.enabled ? 0 : 1 } : c));
  };

  const handleDelete = async (id: string) => {
    await api.deleteMcpConfig(id);
    setConfigs(prev => prev.filter(c => c.id !== id));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#445C58' }}>Conexões MCP</h4>
        <button onClick={() => setAdding(true)} className="p-1 rounded hover:bg-white/5" style={{ color: '#8FA99F' }}>
          <Plus size={14} />
        </button>
      </div>
      {configs.length === 0 && !adding && (
        <p className="text-xs" style={{ color: '#445C58' }}>Nenhuma conexão MCP configurada.</p>
      )}
      {configs.map(cfg => (
        <div key={cfg.id} className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs" style={{ background: '#111A18', border: '1px solid #1A2926' }}>
          <button onClick={() => handleToggle(cfg)} className="p-1" style={{ color: cfg.enabled ? '#4CAF7A' : '#445C58' }}>
            {cfg.enabled ? <Power size={12} /> : <PowerOff size={12} />}
          </button>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate" style={{ color: '#E8EEEC' }}>{cfg.name}</p>
            <p className="truncate" style={{ color: '#445C58' }}>{cfg.type === 'stdio' ? cfg.command : cfg.url}</p>
          </div>
          <button onClick={() => handleDelete(cfg.id)} className="p-1 hover:text-red-400" style={{ color: '#445C58' }}>
            <Trash2 size={12} />
          </button>
        </div>
      ))}
      {adding && (
        <div className="space-y-2 p-3 rounded-lg" style={{ background: '#131F1C', border: '1px solid #1A2926' }}>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Nome da conexão"
            className="w-full rounded-lg px-3 py-2 text-xs outline-none focus:ring-1" style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          <select value={type} onChange={e => setType(e.target.value as any)}
            className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }}>
            <option value="stdio">stdio</option>
            <option value="sse">SSE</option>
          </select>
          {type === 'stdio' ? (
            <>
              <input value={command} onChange={e => setCommand(e.target.value)} placeholder="Comando (ex: npx)"
                className="w-full rounded-lg px-3 py-2 text-xs outline-none focus:ring-1" style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
              <input value={args} onChange={e => setArgs(e.target.value)} placeholder="Argumentos (separados por espaço)"
                className="w-full rounded-lg px-3 py-2 text-xs outline-none focus:ring-1" style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
            </>
          ) : (
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="URL do servidor SSE"
              className="w-full rounded-lg px-3 py-2 text-xs outline-none focus:ring-1" style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          )}
          <div className="flex gap-2">
            <button onClick={handleAdd} className="flex-1 py-1.5 rounded-lg text-xs font-medium text-white" style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>Adicionar</button>
            <button onClick={() => setAdding(false)} className="px-3 py-1.5 rounded-lg text-xs" style={{ background: '#1A2926', color: '#8FA99F' }}>Cancelar</button>
          </div>
        </div>
      )}
    </div>
  );
}
