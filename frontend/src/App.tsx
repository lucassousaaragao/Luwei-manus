import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './pages/LoginPage';
// import { WorkspacePage } from './pages/WorkspacePage';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#070C0B', color: '#8FA99F' }}
      >
        Carregando...
      </div>
    );
  }

  return user ? <div /> : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
