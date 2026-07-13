import { CheckCircle2 } from 'lucide-react';

interface Message { role: string; content: string; }

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  if (isTool) {
    return (
      <div className="flex gap-3 px-4 py-3 rounded-xl my-2"
        style={{ background: '#131F1C', border: '1px solid #1A2926' }}>
        <div className="mt-0.5">{CheckCircle2 && <CheckCircle2 size={16} style={{ color: '#4CAF7A' }} />}</div>
        <div>
          <p className="text-xs font-medium mb-1" style={{ color: '#8FA99F' }}>Ferramenta executada</p>
          <pre className="text-sm whitespace-pre-wrap font-mono" style={{ color: '#E8EEEC' }}>{message.content}</pre>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} my-2`}>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${isUser ? 'rounded-br-sm' : 'rounded-bl-sm'}`}
        style={{ background: isUser ? '#1A4A3A' : '#0E1815', border: isUser ? 'none' : '1px solid #1A2926' }}>
        <p className="text-sm whitespace-pre-wrap" style={{ color: '#E8EEEC' }}>{message.content}</p>
      </div>
    </div>
  );
}
