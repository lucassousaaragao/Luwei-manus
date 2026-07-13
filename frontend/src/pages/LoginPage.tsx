import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #070C0B 0%, #0E1815 100%)' }}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-8 backdrop-blur-[28px]"
        style={{ background: 'rgba(14,24,21,0.8)', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold" style={{ color: '#E8EEEC' }}>Luwei Assistant</h1>
          <p className="text-sm mt-1" style={{ color: '#8FA99F' }}>
            {isRegister ? 'Crie sua conta' : 'Entre para continuar'}
          </p>
        </div>

        {error && (
          <div
            className="text-sm mb-4 p-3 rounded-lg"
            style={{ background: 'rgba(224,80,80,0.15)', color: '#E05050' }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <input
              type="text"
              placeholder="Nome"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
              style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }}
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }}
          />
          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }}
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl py-3 text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}
          >
            {loading ? 'Aguarde...' : isRegister ? 'Cadastrar' : 'Entrar'}
          </button>
        </form>

        <p className="text-center text-sm mt-6" style={{ color: '#445C58' }}>
          {isRegister ? 'Já tem conta?' : 'Não tem conta?'}{' '}
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            className="font-medium hover:underline"
            style={{ color: '#F97316' }}
          >
            {isRegister ? 'Entrar' : 'Cadastre-se'}
          </button>
        </p>
      </div>
    </div>
  );
}
