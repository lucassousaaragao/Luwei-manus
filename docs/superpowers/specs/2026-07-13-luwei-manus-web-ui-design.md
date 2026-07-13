# Luwei Manus — Web UI Design

## Objetivo

Criar uma interface web amigável para o OpenManus, similar ao Manus.IA (manus.im), com a identidade visual da Luwei Flow.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS 3 + shadcn/ui |
| Backend | Python FastAPI |
| Comunicação | REST API + WebSocket (streaming de logs do agente) |
| Autenticação | JWT + SQLite (bcrypt para senhas) |

## Telas

### 1. Tela de Login

- Fundo escuro com mesh animado (#070C0B → #0E1815)
- Card centralizado com glassmorphism (backdrop-filter: blur(28px))
- Logo Luwei Flow no topo
- Título: "Luwei Assistant"
- Inputs de email e senha (estilo Luwei: bg #111A18, border #1A2926)
- Botão "Entrar" com gradiente roxo → laranja (#7C3AED → #F97316)
- Link "Cadastre-se" para criar conta
- Footer: "© 2026 Luwei Software House"

#### Funcionalidades:
- POST /api/auth/login → valida credenciais → retorna JWT
- POST /api/auth/register → cria novo usuário
- GET /api/auth/me → valida token e retorna dados do usuário

### 2. Workspace (3 Painéis)

#### Sidebar (esquerda, 250px)
- Logo + "Luwei Assistant"
- Botão "Novo Chat" (gradiente roxo→laranja)
- Lista de conversas anteriores (scroll)
- Footer com nome do usuário + logout

#### Chat (centro, flexível)
- Header: nome da conversa + seletor de modelo LLM
- Mensagens formatadas:
  - Usuário → balão verde escuro (#1A4A3A)
  - Agente → balão card (#0E1815)
  - Tool calls → cards colapsáveis com status (⏳→✅)
  - Código → bloco monospace com copiar
- Input expansível + botão enviar

#### Live View (direita, 380px)
- Abas: Terminal | Browser | Arquivos
- Terminal: output em tempo real (WebSocket)
- Browser: screenshot preview
- Arquivos: árvore de arquivos gerados

### Comunicação Backend → Frontend

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| /api/auth/login | POST | Login |
| /api/auth/register | POST | Cadastro |
| /api/chat/sessions | GET | Listar sessões |
| /api/chat/sessions | POST | Criar sessão |
| /api/chat/sessions/:id/messages | GET | Histórico de mensagens |
| /api/chat/sessions/:id/run | POST | Executar agente |
| /ws/agent/:session_id | WS | Streaming de logs em tempo real |

### Estrutura de Diretórios

```
OpenManus/
├── frontend/                    # Novo: React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui components
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Chat.tsx
│   │   │   ├── LiveView.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── LoginForm.tsx
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   └── WorkspacePage.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   ├── lib/
│   │   │   └── api.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tailwind.config.ts
│   └── package.json
│
├── api/                         # Novo: FastAPI backend
│   ├── main.py                  # App FastAPI
│   ├── auth.py                  # Rotas de autenticação
│   ├── chat.py                  # Rotas de chat
│   ├── ws.py                    # WebSocket handler
│   ├── database.py              # SQLite + models
│   └── agent_runner.py          # Subprocesso OpenManus
│
├── app/                         # OpenManus original (inalterado)
├── config/
└── ...
```

## Padrões Visuais (Luwei Flow)

- **Fundo**: #070C0B
- **Card/Superfície**: #0E1815
- **Bordas**: #1A2926
- **Inputs**: bg #111A18, border #1F3330
- **Texto primário**: #E8EEEC
- **Texto secundário**: #8FA99F
- **Placeholder**: #445C58
- **Primary**: #7C3AED (roxo)
- **Accent**: #F97316 (laranja)
- **Gradiente botões**: linear-gradient(135deg, #7C3AED, #F97316)
- **Font**: Inter (Google Fonts)
- **Glassmorphism**: backdrop-filter: blur(28px) saturate(180%)
