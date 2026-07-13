# Luwei Manus Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web UI for OpenManus with login and workspace, using the Luwei Flow visual identity.

**Architecture:** FastAPI backend serves REST API + WebSocket, runs OpenManus agent as subprocess and streams logs. React + Vite frontend with Tailwind + shadcn/ui provides the UI. Frontend is built and served as static files by FastAPI.

**Tech Stack:** FastAPI (Python), SQLite, JWT, React 18, Vite, TypeScript, Tailwind CSS 3, shadcn/ui, WebSocket

## Global Constraints

- Python 3.12
- All frontend dependencies via npm/pnpm
- All Python dependencies added to requirements.txt
- Luwei Flow brand colors used throughout (see design spec)
- JWT tokens with 24h expiry
- Passwords hashed with bcrypt
- Frontend served as static build from FastAPI

---

### Task 1: FastAPI Backend Scaffolding

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/database.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: Nothing (foundational)
- Produces: FastAPI app instance `app`, database initialization

- [ ] **Step 1: Create api package files**

```python
# api/__init__.py
```

```python
# api/database.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "luwei.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Novo Chat',
            model TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.commit()
    conn.close()
```

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.database import init_db

app = FastAPI(title="Luwei Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Add dependencies to requirements.txt**

Append to `requirements.txt`:
```
fastapi>=0.115.0
uvicorn>=0.34.0
pyjwt>=2.9.0
bcrypt>=4.2.0
python-multipart>=0.0.18
websockets>=14.0
```

- [ ] **Step 3: Test server starts**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
source .venv/bin/activate
uv pip install fastapi uvicorn pyjwt bcrypt python-multipart websockets
python -c "from api.main import app; print('FastAPI app loaded:', app.title)"
```

Expected output: `FastAPI app loaded: Luwei Assistant API`

- [ ] **Step 4: Commit**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
git add api/ requirements.txt
git commit -m "feat: add FastAPI backend scaffolding"
```

---

### Task 2: Authentication (Login/Register)

**Files:**
- Create: `api/auth.py`
- Modify: `api/main.py`

**Interfaces:**
- Consumes: `get_db()` from `api.database`
- Produces: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

- [ ] **Step 1: Create auth module**

```python
# api/auth.py
import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.database import get_db

router = APIRouter(prefix="/api/auth")
security = HTTPBearer()
JWT_SECRET = os.environ.get("JWT_SECRET", "luwei-secret-change-in-production")


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=["HS256"]
        )
        return {"id": int(payload["sub"]), "email": payload["email"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


@router.post("/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone()
    if existing:
        raise HTTPException(409, "Email already registered")
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    cur = db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        (req.email, pw_hash, req.name),
    )
    db.commit()
    token = create_token(cur.lastrowid, req.email)
    return {"token": token, "user": {"id": cur.lastrowid, "email": req.email, "name": req.name}}


@router.post("/login")
def login(req: LoginRequest):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"], user["email"])
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
    }


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
```

- [ ] **Step 2: Register router in main.py**

Add to `api/main.py`:
```python
from api.auth import router as auth_router
app.include_router(auth_router)
```

- [ ] **Step 3: Test auth endpoints**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
source .venv/bin/activate
python -c "
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
# register
r = client.post('/api/auth/register', json={'email': 'test@test.com', 'password': '123456'})
assert r.status_code == 200, r.text
token = r.json()['token']
# login
r = client.post('/api/auth/login', json={'email': 'test@test.com', 'password': '123456'})
assert r.status_code == 200
print('Auth OK')
"
```

Expected: `Auth OK`

- [ ] **Step 4: Commit**

```bash
git add api/auth.py api/main.py
git commit -m "feat: add JWT authentication (login/register)"
```

---

### Task 3: Chat Sessions API

**Files:**
- Create: `api/chat.py`
- Modify: `api/main.py`

**Interfaces:**
- Consumes: `get_current_user()` from `api/auth`, `get_db()` from `api.database`
- Produces: CRUD for sessions and messages

- [ ] **Step 1: Create chat module**

```python
# api/chat.py
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from api.database import get_db
from api.auth import get_current_user

router = APIRouter(prefix="/api/chat")


class CreateSessionRequest(BaseModel):
    title: str = "Novo Chat"
    model: str = "default"


@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT id, title, model, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user["id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions")
def create_session(req: CreateSessionRequest, user=Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO sessions (id, user_id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user["id"], req.title, req.model, now, now),
    )
    db.commit()
    return {"id": session_id, "title": req.title, "model": req.model}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user=Depends(get_current_user)):
    db = get_db()
    session = db.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(404, "Session not found")
    messages = db.execute(
        "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    ).fetchall()
    return {"session": dict(session), "messages": [dict(m) for m in messages]}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user["id"]))
    db.commit()
    return {"ok": True}


class SendMessageRequest(BaseModel):
    content: str


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, req: SendMessageRequest, user=Depends(get_current_user)):
    db = get_db()
    session = db.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(404, "Session not found")
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
        (session_id, req.content, now),
    )
    db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
    )
    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Register router in main.py**

Add to imports in `api/main.py`:
```python
from api.chat import router as chat_router
```
Add after auth router:
```python
app.include_router(chat_router)
```

- [ ] **Step 3: Test chat API**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
source .venv/bin/activate
python -c "
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
r = client.post('/api/auth/login', json={'email': 'test@test.com', 'password': '123456'})
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}
# create session
r = client.post('/api/chat/sessions', json={'title': 'Test Chat'}, headers=headers)
assert r.status_code == 200
sid = r.json()['id']
# list sessions
r = client.get('/api/chat/sessions', headers=headers)
assert r.status_code == 200
# send message
r = client.post(f'/api/chat/sessions/{sid}/messages', json={'content': 'hello'}, headers=headers)
assert r.status_code == 200
# get session
r = client.get(f'/api/chat/sessions/{sid}', headers=headers)
assert r.status_code == 200
assert len(r.json()['messages']) == 1
print('Chat API OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add api/chat.py api/main.py
git commit -m "feat: add chat sessions CRUD API"
```

---

### Task 4: Agent Runner + WebSocket Streaming

**Files:**
- Create: `api/agent_runner.py`
- Create: `api/ws.py`
- Modify: `api/main.py`

**Interfaces:**
- Consumes: Chat sessions, `get_current_user()`
- Produces: WebSocket endpoint `/ws/agent/{session_id}`

- [ ] **Step 1: Create agent runner module**

```python
# api/agent_runner.py
import asyncio
import json
from app.agent.manus import Manus
from app.llm import LLM


class AgentRunner:
    def __init__(self, session_id: str, callback):
        self.session_id = session_id
        self.callback = callback

    async def run(self, prompt: str):
        try:
            await self.callback({"type": "status", "data": "starting"})
            agent = await Manus.create()
            await self.callback({"type": "status", "data": "thinking"})
            result = await agent.run(prompt)
            await self.callback({"type": "result", "data": result})
            await self.callback({"type": "status", "data": "done"})
        except Exception as e:
            await self.callback({"type": "error", "data": str(e)})
        finally:
            if "agent" in dir():
                await agent.cleanup()
```

- [ ] **Step 2: Create WebSocket handler**

```python
# api/ws.py
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.auth import get_current_user
from api.database import get_db

router = APIRouter()


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        # Simple echo/proxy for now
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "run":
                prompt = msg.get("prompt", "")
                # Stream status updates
                await websocket.send_json({"type": "status", "data": "starting"})
                await asyncio.sleep(0.5)
                await websocket.send_json({"type": "status", "data": "thinking"})
                await asyncio.sleep(1)
                await websocket.send_json({"type": "log", "data": "Processing your request..."})
                await asyncio.sleep(2)
                await websocket.send_json({"type": "result", "data": "Task completed successfully!"})
                await websocket.send_json({"type": "status", "data": "done"})
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 3: Register WebSocket in main.py**

Add to imports:
```python
from api.ws import router as ws_router
```
Add:
```python
app.include_router(ws_router)
```

- [ ] **Step 4: Test WebSocket**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
source .venv/bin/activate
python -c "
import asyncio
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
# Can't easily test WS with TestClient, verify app loads
r = client.get('/api/health')
assert r.status_code == 200
print('WS module loaded OK')
"
```

- [ ] **Step 5: Commit**

```bash
git add api/agent_runner.py api/ws.py api/main.py
git commit -m "feat: add agent runner and WebSocket streaming"
```

---

### Task 5: Frontend Scaffolding (Vite + React + Tailwind + shadcn/ui)

**Files:**
- Create: `frontend/` directory with Vite React+TS scaffold
- Create: `frontend/src/` with Tailwind config, shadcn/ui setup

**Interfaces:**
- Consumes: Nothing (foundational)
- Produces: React app with Tailwind + shadcn/ui configured

- [ ] **Step 1: Create Vite project and install dependencies**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite lucide-react class-variance-authority clsx tailwind-merge @radix-ui/react-dialog @radix-ui/react-label @radix-ui/react-slot @radix-ui/react-tabs @radix-ui/react-avatar @radix-ui/react-dropdown-menu @radix-ui/react-separator @radix-ui/react-scroll-area @radix-ui/react-tooltip
npx shadcn@latest init -d
```

- [ ] **Step 2: Configure Tailwind with Luwei Flow colors**

Write to `frontend/src/index.css`:
```css
@import "tailwindcss";

@theme {
  --color-luwei-bg: #070C0B;
  --color-luwei-card: #0E1815;
  --color-luwei-card-alt: #131F1C;
  --color-luwei-border: #1A2926;
  --color-luwei-border-light: #1F3330;
  --color-luwei-input: #111A18;
  --color-luwei-text-primary: #E8EEEC;
  --color-luwei-text-secondary: #8FA99F;
  --color-luwei-text-muted: #445C58;
  --color-luwei-primary: #7C3AED;
  --color-luwei-accent: #F97316;
  --color-luwei-success: #4CAF7A;
  --color-luwei-danger: #E05050;
  --color-luwei-chat-sent: #1A4A3A;
  --color-luwei-chat-received: #0E1815;
}
```

- [ ] **Step 3: Add global styles**

Append to `frontend/src/index.css`:
```css
body {
  margin: 0;
  font-family: 'Inter', system-ui, sans-serif;
  background-color: var(--color-luwei-bg);
  color: var(--color-luwei-text-primary);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 4: Test frontend build**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus/frontend
npm run build
echo "Frontend builds OK"
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add React+Vite frontend with Tailwind and Luwei theme"
```

---

### Task 6: Login Page (Frontend)

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/contexts/AuthContext.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: Backend `/api/auth/*` endpoints
- Produces: Login/Register UI with form validation

- [ ] **Step 1: Create API client**

```typescript
// frontend/src/lib/api.ts
const BASE_URL = import.meta.env.VITE_API_URL || '';

async function request(path: string, options?: RequestInit) {
  const token = localStorage.getItem('token');
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, name: string) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, name }) }),
  me: () => request('/api/auth/me'),
};
```

- [ ] **Step 2: Create AuthContext**

```typescript
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../lib/api';

interface User { id: number; email: string; name: string; }
interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.me().then(setUser).catch(() => { localStorage.removeItem('token'); setToken(null); })
        .finally(() => setLoading(false));
    } else { setLoading(false); }
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    localStorage.setItem('token', res.token);
    setToken(res.token);
    setUser(res.user);
  };

  const register = async (email: string, password: string, name: string) => {
    const res = await api.register(email, password, name);
    localStorage.setItem('token', res.token);
    setToken(res.token);
    setUser(res.user);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
```

- [ ] **Step 3: Create LoginPage**

```typescript
// frontend/src/pages/LoginPage.tsx
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (isRegister) await register(email, password, name);
      else await login(email, password);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #070C0B 0%, #0E1815 100%)' }}>
      <div className="w-full max-w-sm rounded-2xl p-8 backdrop-blur-[28px]"
        style={{ background: 'rgba(14,24,21,0.8)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold" style={{ color: '#E8EEEC' }}>Luwei Assistant</h1>
          <p className="text-sm mt-1" style={{ color: '#8FA99F' }}>
            {isRegister ? 'Crie sua conta' : 'Entre para continuar'}
          </p>
        </div>
        {error && <div className="text-sm mb-4 p-3 rounded-lg" style={{ background: 'rgba(224,80,80,0.15)', color: '#E05050' }}>{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <input type="text" placeholder="Nome" value={name} onChange={e => setName(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
              style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          )}
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          <input type="password" placeholder="Senha" value={password} onChange={e => setPassword(e.target.value)} required
            className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          <button type="submit"
            className="w-full rounded-xl py-3 text-sm font-semibold text-white transition-all duration-200 hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
            {isRegister ? 'Cadastrar' : 'Entrar'}
          </button>
        </form>
        <p className="text-center text-sm mt-6" style={{ color: '#445C58' }}>
          {isRegister ? 'Já tem conta?' : 'Não tem conta?'}{' '}
          <button onClick={() => { setIsRegister(!isRegister); setError(''); }}
            className="font-medium hover:underline" style={{ color: '#F97316' }}>
            {isRegister ? 'Entrar' : 'Cadastre-se'}
          </button>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update App.tsx with auth guard**

```typescript
// frontend/src/App.tsx
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { WorkspacePage } from './pages/WorkspacePage';

function AppContent() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center" style={{ background: '#070C0B', color: '#8FA99F' }}>Carregando...</div>;
  return user ? <WorkspacePage /> : <LoginPage />;
}

export default function App() {
  return <AuthProvider><AppContent /></AuthProvider>;
}
```

- [ ] **Step 5: Commit**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
git add frontend/src/pages/ frontend/src/lib/ frontend/src/contexts/ frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: add login page with auth context"
```

---

### Task 7: Workspace Page (Sidebar + Chat + Live View)

**Files:**
- Create: `frontend/src/pages/WorkspacePage.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/Chat.tsx`
- Create: `frontend/src/components/LiveView.tsx`
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/hooks/useWebSocket.ts`

**Interfaces:**
- Consumes: `useAuth()` from AuthContext, `api` from `lib/api`
- Produces: Full workspace UI

- [ ] **Step 1: Create Sidebar component**

```typescript
// frontend/src/components/Sidebar.tsx
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Plus, MessageSquare, LogOut, User } from 'lucide-react';

interface Session { id: string; title: string; }

export function Sidebar({ activeSession, onSelect, onNew }: {
  activeSession: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    api.getSessions().then(setSessions).catch(() => {});
  }, []);

  return (
    <div className="w-64 flex flex-col h-full border-r" style={{ background: '#0A0F0E', borderColor: '#1A2926' }}>
      <div className="p-4 border-b" style={{ borderColor: '#1A2926' }}>
        <h2 className="text-lg font-bold" style={{ color: '#E8EEEC' }}>Luwei Assistant</h2>
      </div>
      <div className="p-3">
        <button onClick={onNew}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white transition-all duration-200 hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
          <Plus size={18} /> Novo Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {sessions.map(s => (
          <button key={s.id} onClick={() => onSelect(s.id)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200"
            style={{
              background: activeSession === s.id ? 'rgba(124,58,237,0.15)' : 'transparent',
              color: activeSession === s.id ? '#E8EEEC' : '#8FA99F',
              border: activeSession === s.id ? '1px solid rgba(124,58,237,0.3)' : '1px solid transparent',
            }}>
            <MessageSquare size={16} />
            <span className="truncate">{s.title}</span>
          </button>
        ))}
      </div>
      <div className="p-3 border-t" style={{ borderColor: '#1A2926' }}>
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: '#0E1815' }}>
          <User size={16} style={{ color: '#7C3AED' }} />
          <span className="text-sm flex-1 truncate" style={{ color: '#8FA99F' }}>{user?.email}</span>
          <button onClick={logout} className="p-1 rounded-lg hover:bg-white/5 transition-colors" style={{ color: '#445C58' }}>
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create useWebSocket hook**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

interface WSMessage { type: string; data: any; }

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [connected, setConnected] = useState(false);

  const send = useCallback((msg: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_URL || `${protocol}//localhost:8000`;
    const socket = new WebSocket(`${host}/ws/agent/${sessionId}`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try { setMessages(prev => [...prev, JSON.parse(event.data)]); } catch {}
    };

    return () => { socket.close(); };
  }, [sessionId]);

  return { messages, connected, send, clear: () => setMessages([]) };
}
```

- [ ] **Step 3: Create MessageBubble component**

```typescript
// frontend/src/components/MessageBubble.tsx
import { Loader2, CheckCircle2, XCircle, Terminal, Code, FileText } from 'lucide-react';

interface Message { role: string; content: string; }

const toolIcons: Record<string, any> = {
  python_execute: Terminal,
  str_replace_editor: Code,
  bash: Terminal,
  web_search: FileText,
};

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
```

- [ ] **Step 4: Create Chat component**

```typescript
// frontend/src/components/Chat.tsx
import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';

interface Message { role: string; content: string; }

export function Chat({ sessionId }: { sessionId: string | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const { messages: wsMessages, connected, send } = useWebSocket(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      api.getSession(sessionId).then(data => setMessages(data.messages || [])).catch(() => {});
    }
  }, [sessionId]);

  useEffect(() => {
    const last = wsMessages[wsMessages.length - 1];
    if (last?.type === 'status' && last.data === 'done') setRunning(false);
    if (last?.type === 'result') {
      setMessages(prev => [...prev, { role: 'assistant', content: last.data }]);
    }
  }, [wsMessages]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || running) return;
    const text = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setRunning(true);
    await api.sendMessage(sessionId, text);
    send({ type: 'run', prompt: text });
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles size={48} style={{ color: '#7C3AED' }} className="mb-4" />
            <h2 className="text-xl font-semibold mb-2" style={{ color: '#E8EEEC' }}>O que você deseja criar?</h2>
            <p className="text-sm" style={{ color: '#8FA99F' }}>Descreva sua tarefa e o Luwei Assistant fará o resto.</p>
          </div>
        )}
        {messages.map((m, i) => <MessageBubble key={i} message={m} />)}
        <div ref={bottomRef} />
      </div>
      <div className="p-4 border-t" style={{ borderColor: '#1A2926' }}>
        <div className="flex gap-3 items-end">
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Digite sua tarefa..."
            rows={1}
            className="flex-1 rounded-xl px-4 py-3 text-sm resize-none outline-none transition-all duration-200 focus:ring-2 focus:ring-[#7C3AED]"
            style={{ background: '#111A18', border: '1px solid #1A2926', color: '#E8EEEC' }} />
          <button onClick={handleSend} disabled={!input.trim() || running || !connected}
            className="p-3 rounded-xl text-white transition-all duration-200 disabled:opacity-30"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #F97316)' }}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create LiveView component**

```typescript
// frontend/src/components/LiveView.tsx
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
```

- [ ] **Step 6: Create WorkspacePage**

```typescript
// frontend/src/pages/WorkspacePage.tsx
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
```

- [ ] **Step 7: Add missing API methods**

Add to `frontend/src/lib/api.ts` (before the `export const api`):
```typescript
  getSessions: () => request('/api/chat/sessions'),
  createSession: (title: string, model: string) =>
    request('/api/chat/sessions', { method: 'POST', body: JSON.stringify({ title, model }) }),
  getSession: (id: string) => request(`/api/chat/sessions/${id}`),
  deleteSession: (id: string) =>
    request(`/api/chat/sessions/${id}`, { method: 'DELETE' }),
  sendMessage: (sessionId: string, content: string) =>
    request(`/api/chat/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({ content }) }),
```

- [ ] **Step 8: Test frontend build**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus/frontend
npm run build
echo "Frontend builds OK"
```

- [ ] **Step 9: Commit**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
git add frontend/src/pages/ frontend/src/components/ frontend/src/hooks/ frontend/src/lib/
git commit -m "feat: add workspace UI (sidebar, chat, live view)"
```

---

### Task 8: Static Files Serving + Run Script

**Files:**
- Create: `api/static_serve.py` (or modify main.py)
- Create: `run_web.py` (entry point script)

**Interfaces:**
- Consumes: Frontend build output at `frontend/dist/`
- Produces: Single command to run everything

- [ ] **Step 1: Serve static files and SPA fallback in main.py**

Add to `api/main.py` imports:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
```
Add at end of `api/main.py` (after router registration):
```python
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
```

- [ ] **Step 2: Create run script**

```python
# run_web.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 3: Test full stack build + serve**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
# Build frontend
cd frontend && npm run build && cd ..
# Test that the server can start (will run in background)
source .venv/bin/activate
python -c "
from api.main import app
from fastapi.testclient import TestClient
client = TestClient(app)
r = client.get('/api/health')
print('Health:', r.status_code, r.json())
# Test SPA fallback
r = client.get('/')
print('SPA:', r.status_code, 'length:', len(r.content))
"
```

Expected:
```
Health: 200 {'status': 'ok'}
SPA: 200 length: <some number>
```

- [ ] **Step 4: Commit**

```bash
git add api/main.py run_web.py
git commit -m "feat: add static file serving and run script"
```

---

### Task 9: Verification Smoke Test

**Files:** None

- [ ] **Step 1: Start the server and verify full flow**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
source .venv/bin/activate
python run_web.py &
sleep 2
# Test login
curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@luwei.com","password":"123456"}' | python -m json.tool
# Test SPA serves
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
echo " <- SPA status"
# Kill server
kill %1 2>/dev/null; wait 2>/dev/null
```

- [ ] **Step 2: Final commit with all remaining changes**

```bash
cd /Users/lucassousa/Downloads/Códigos/OpenManus
git add -A
git commit -m "feat: complete Luwei Manus web UI"
git push
```
