# Graphify | Protocolo canônico multicliente (2026-10-14)

## Prioridade e abrangência
Este documento complementa `LUWEI.md`, `.luwei/standard.lock`, `.luwei/project.yaml` e as regras de cada projeto. Não substitui RBAC, segurança, ambientes, workflows, regras de negócio nem instruções do repositório. É aplicável a GPT/ChatGPT, Codex, Claude Code, Gemini CLI e ao futuro runtime do LuweiDev, mesmo com o LuweiDev indisponível.

## Contrato de inicialização (antes de editar)
1. Ler `AGENTS.md` e a fonte canônica indicada pelo próprio projeto (`LUWEI.md` quando existir), este arquivo e somente as políticas contextuais necessárias. Inspecionar branch, HEAD, worktrees, alterações locais, PRs, CI e decisões recentes. Nunca sobrescrever mudanças de outra sessão.
2. Descobrir Graphify entre as ferramentas disponíveis. Se conectado, listar workspaces e selecionar o workspace autorizado que contém o repositório (preferir `luweidev` quando ele realmente o contém); conferir `list_repositories`, o repo completo `owner/name` e status consultável. Nunca escolher repositório por nome semelhante.
3. Consultar `recall` para decisões/histórico e descobrir no cliente a lista REAL de ferramentas disponíveis. Usar as ferramentas efetivamente anunciadas (ex.: `query_graph`, `graphify_find`, `graphify_node`, `graphify_trace`, `graphify_impact`, `impact_and_risk`, `graphify_tests_for` ou equivalentes) conforme suporte real; não assumir que todas existem em qualquer versão. Minimizar custos/contexto.
4. Registrar SHA do índice e comparar com HEAD/branch reais. Grafo antigo não comprova código atual; mudanças estruturais de risco requerem indexação compatível ou revisão direta e autorização explícita para avançar sem ela.
5. Depois de implementar, executar testes reais, revisão e checks proporcionais. Grafo não substitui testes, CI, PR aprovada, deploy ou validação em produção. Diferenciar cada estado na entrega.

## Instalação e verificação por cliente
- Fronteira de confiança: antes de conectar serviço externo a código proprietário, consultar política de segurança, registry MCP e consentimento da organização. Reutilizar o Graphify já aprovado, se existir; não substituir indevidamente o índice local nem transmitir conteúdo para serviço não autorizado. Conexão/instalação nova depende de autorização aplicável.
- MCP: nome `graphify`, URL `https://api.graphify.com/mcp`, transporte Streamable HTTP e autenticação OAuth via navegador. Reutilizar conexões existentes; não duplicar nem remover servidores MCP alheios.
- GPT/ChatGPT: usar o plugin Graphify já conectado. Se indisponível, oferecer instalação/conexão por https://chatgpt.com/plugins/plugin_asdk_app_6abe89f7f5d88191b9422522bb8562a4; esta ação pode requerer consentimento explícito do usuário e não pode ser simulada.
- Codex: verificar suporte MCP da instalação/ambiente atual, instalar entrada HTTP de acordo com o formato validado para essa versão, autenticar e testar `list_repositories`.
- Claude Code: `claude mcp add --transport http --scope user graphify https://api.graphify.com/mcp`; abrir `/mcp` para autenticar, depois testar ferramenta real.
- Gemini CLI: verificar a versão e o formato MCP aceito antes de ajustar a configuração de usuário/projeto; configurar HTTP/OAuth se suportado e testar ferramenta real.
- LuweiDev (preparação offline): declarar esta capacidade no registry MCP já existente e, quando o runtime voltar, habilitar por workspace e projeto sob permissões explícitas; propagar para agentes via Harness/Model Router existentes. Não criar segundo registry e não declarar integração pronta antes de smoke test.
- Falha de conexão, autenticação ou indexação: registrar erro exato e modo degradado; não inventar instalação. Se ferramenta/ambiente não permitir configurar cliente, fornecer passos e aguardar autorização. Nunca gravar tokens, segredos ou dados pessoais no repositório.

## Reutilização interprojetos (consulta, nunca transferência automática)
1. Descobrir os repositórios autorizados no workspace; para cada consulta enviar `repository_id` explícito. Consultar apenas fontes às quais o operador tem acesso.
2. Localizar a solução referência, obter caminho/símbolo, dependências, testes e commit indexado; comparar com código atual, licença, versão de stack, contrato e contexto do destino.
3. Adaptar, não copiar cegamente. É proibido presumir banco, autenticação, tenant, RLS, clínica, empresa, segredos, API, infraestrutura, ambiente ou deploy compartilhados.
4. Registrar origem e evidências da solução reutilizada no PR/demanda; não persistir conteúdos confidenciais do projeto fonte na memória do destino. Memórias e resumos antigos são dicas, não fontes de verdade.
5. Ao editar, manter branch/worktree própria, respeitar regras locais e passar pelos gates normais do projeto destino.

## Verificação e precedência
Ao abrir uma nova sessão, o agente deve registrar se o MCP foi encontrado e se a primeira chamada teve sucesso. Falha de instalação nunca autoriza ignorar isolamento, gates de segurança ou políticas existentes.

## Registro de execução mínimo
`cliente`, `workspace`, `repo`, `Graphify disponível?`, `index SHA`, `HEAD`, `consulta executada`, `referências externas avaliadas`, `arquivos`, `testes`, `commit`, `PR`, `CI`, `deploy`, `teste real` e `pendências`. Estados não comprovados devem permanecer pendentes.
