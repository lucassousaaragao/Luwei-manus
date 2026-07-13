import { useState, useCallback } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Chat } from '../components/Chat';
import { LiveView } from '../components/LiveView';
import { SettingsPanel } from '../components/SettingsPanel';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';

export function WorkspacePage() {
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [model, setModel] = useState('opencode-go');
  const [mode, setMode] = useState('chat');
  const [speed, setSpeed] = useState('medium');
  const { messages: wsMessages, clear: clearWs } = useWebSocket(activeSession);

  const handleNewChat = useCallback(async (wid?: string) => {
    const res = await api.createSession('Novo Chat', model, mode, speed, wid || workspaceId || undefined);
    clearWs();
    setActiveSession(res.id);
    setModel(res.model || model);
    setMode(res.mode || mode);
    setSpeed(res.speed || speed);
  }, [model, mode, speed, workspaceId]);

  const handleSelect = useCallback((id: string) => {
    clearWs();
    setActiveSession(id);
  }, []);

  const handleWorkspaceChange = useCallback((id: string | null) => {
    setWorkspaceId(id);
    setActiveSession(null);
    clearWs();
  }, []);

  const handleModelChange = useCallback(async (m: string) => {
    setModel(m);
    if (activeSession) {
      await api.updateSession(activeSession, { model: m }).catch(() => {});
    }
  }, [activeSession]);

  const handleModeChange = useCallback(async (m: string) => {
    setMode(m);
    if (activeSession) {
      await api.updateSession(activeSession, { mode: m }).catch(() => {});
    }
  }, [activeSession]);

  const handleSpeedChange = useCallback(async (s: string) => {
    setSpeed(s);
    if (activeSession) {
      await api.updateSession(activeSession, { speed: s }).catch(() => {});
    }
  }, [activeSession]);

  return (
    <div className="flex h-screen" style={{ background: '#070C0B' }}>
      <Sidebar
        activeSession={activeSession}
        onSelect={handleSelect}
        onNew={handleNewChat}
        workspaceId={workspaceId}
        onWorkspaceChange={handleWorkspaceChange}
        onOpenSettings={() => setShowSettings(true)}
      />
      <Chat
        sessionId={activeSession}
        model={model}
        mode={mode}
        speed={speed}
        onModelChange={handleModelChange}
        onModeChange={handleModeChange}
        onSpeedChange={handleSpeedChange}
      />
      <LiveView logs={wsMessages.filter(m => m.type === 'log' || m.type === 'error')} />
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} workspaceId={workspaceId} />}
    </div>
  );
}
