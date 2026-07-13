import { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';
import { api } from '../lib/api';
import { McpConfig } from './McpConfig';

export function SettingsPanel({ onClose, workspaceId }: { onClose: () => void; workspaceId: string | null }) {
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    api.getProviders().then(setProviders).catch(() => {});
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl shadow-2xl border overflow-hidden"
        style={{ background: '#0E1815', borderColor: '#1A2926' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: '#1A2926' }}>
          <h3 className="text-lg font-semibold" style={{ color: '#E8EEEC' }}>Configurações</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors" style={{ color: '#445C58' }}>
            <X size={18} />
          </button>
        </div>
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: '#445C58' }}>
              Provedores de IA
            </h4>
            <div className="space-y-2">
              {providers.length === 0 && (
                <p className="text-xs" style={{ color: '#445C58' }}>Nenhum provedor configurado.</p>
              )}
              {providers.map((p, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl" style={{ background: '#111A18', border: '1px solid #1A2926' }}>
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
                    style={{ background: 'rgba(124,58,237,0.15)', color: '#C4B5FD' }}
                  >
                    {p.name?.charAt(0).toUpperCase() || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: '#E8EEEC' }}>{p.name}</p>
                    <p className="text-xs truncate" style={{ color: '#445C58' }}>
                      {p.model?.substring(0, 60) || p.base_url?.substring(0, 60) || '—'}
                    </p>
                  </div>
                  {p.enabled !== false && <Check size={14} style={{ color: '#4CAF7A' }} />}
                </div>
              ))}
            </div>
          </div>
          {workspaceId && (
            <div>
              <McpConfig workspaceId={workspaceId} />
            </div>
          )}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: '#445C58' }}>
              Sobre
            </h4>
            <div className="space-y-2 text-xs" style={{ color: '#8FA99F' }}>
              <p>Luwei Manus v1.0.0</p>
              <p>Construído sobre OpenManus</p>
            </div>
          </div>
        </div>
        <div className="px-6 py-4 border-t flex justify-end" style={{ borderColor: '#1A2926' }}>
          <button onClick={onClose}
            className="px-6 py-2 rounded-xl text-sm font-medium text-white transition-all hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
