import { useState } from 'react';
import { Terminal, Globe, FolderTree } from 'lucide-react';

type Tab = 'terminal' | 'browser' | 'files';

export function LiveView({ logs }: { logs: { type: string; data: string }[] }) {
  const [activeTab, setActiveTab] = useState<Tab>('terminal');

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'browser', label: 'Navegador', icon: Globe },
    { id: 'files', label: 'Arquivos', icon: FolderTree },
  ];

  return (
    <div className="w-[380px] flex flex-col h-full border-l" style={{ background: '#070C0B', borderColor: '#1A2926' }}>
      <div className="flex border-b" style={{ borderColor: '#1A2926' }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className="flex items-center gap-2 px-4 py-3 text-xs font-medium transition-all duration-200 border-b-2"
            style={{
              color: activeTab === t.id ? '#E8EEEC' : '#445C58',
              borderColor: activeTab === t.id ? '#7C3AED' : 'transparent',
            }}>
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs">
        {activeTab === 'terminal' && (
          <div className="space-y-1">
            {logs.length === 0 && <span style={{ color: '#445C58' }}>Aguardando comando...</span>}
            {logs.map((log, i) => (
              <div key={i} style={{ color: log.type === 'error' ? '#E05050' : '#8FA99F' }}>
                <span style={{ color: '#4CAF7A' }}>$</span> {log.data}
              </div>
            ))}
          </div>
        )}
        {activeTab === 'browser' && (
          <div className="flex items-center justify-center h-full" style={{ color: '#445C58' }}>
            <p className="text-sm">Preview do navegador aparecerá aqui</p>
          </div>
        )}
        {activeTab === 'files' && (
          <div className="flex items-center justify-center h-full" style={{ color: '#445C58' }}>
            <p className="text-sm">Arquivos gerados aparecerão aqui</p>
          </div>
        )}
      </div>
    </div>
  );
}
