import { useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Chat } from '../components/Chat';
import { LiveView } from '../components/LiveView';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';

export function WorkspacePage() {
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const { messages: wsMessages } = useWebSocket(activeSession);

  const handleNewChat = async () => {
    const res = await api.createSession('Novo Chat', 'default');
    setActiveSession(res.id);
  };

  return (
    <div className="flex h-screen" style={{ background: '#070C0B' }}>
      <Sidebar activeSession={activeSession} onSelect={setActiveSession} onNew={handleNewChat} />
      <Chat sessionId={activeSession} />
      <LiveView logs={wsMessages.filter(m => m.type === 'log' || m.type === 'error')} />
    </div>
  );
}
