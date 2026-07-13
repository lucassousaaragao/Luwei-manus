import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check, Sparkles } from 'lucide-react';
import { api } from '../lib/api';

interface ModelCatalog {
  [key: string]: {
    name: string;
    provider: string;
    models?: string[];
  };
}

export function ModelSelector({
  current,
  onChange,
}: {
  current: string;
  onChange: (model: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [catalog, setCatalog] = useState<ModelCatalog>({});
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getModels().then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const allModels: { key: string; label: string }[] = [];
  for (const [key, group] of Object.entries(catalog)) {
    if (group.models) {
      for (const m of group.models) {
        allModels.push({ key: `${key}/${m}`, label: `${group.name} — ${m}` });
      }
    } else {
      allModels.push({ key, label: group.name });
    }
  }

  const currentLabel = allModels.find(m => m.key === current)?.label || current;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-white/5"
        style={{ background: 'rgba(124,58,237,0.1)', color: '#C4B5FD', border: '1px solid rgba(124,58,237,0.2)' }}
      >
        <Sparkles size={12} />
        {currentLabel}
        <ChevronDown size={12} />
      </button>
      {open && (
        <div
          className="absolute top-full left-0 mt-1 w-64 max-h-72 overflow-y-auto rounded-xl z-50 shadow-2xl"
          style={{ background: '#0E1815', border: '1px solid #1A2926' }}
        >
          {allModels.map(m => (
            <button
              key={m.key}
              onClick={() => { onChange(m.key); setOpen(false); }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all hover:bg-white/5 text-left"
              style={{ color: current === m.key ? '#E8EEEC' : '#8FA99F' }}
            >
              <span className="flex-1">{m.label}</span>
              {current === m.key && <Check size={14} style={{ color: '#7C3AED' }} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
