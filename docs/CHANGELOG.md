# CHANGELOG

## [0.7.0] — FASE 7: TOOLS

### Adicionado
- Camada de **tools** controladas (`apps/assistant/tools/`): a IA nunca acessa o
  banco diretamente; só usa ferramentas declaradas (function calling).
  - **Leitura** (execução imediata, ownership validado): `search_entities`,
    `get_entity`, `get_project_context`, `find_related_entities`.
  - **Escrita** (exigem confirmação do usuário): `create_idea`, `create_question`,
    `create_knowledge`, `create_project`, `create_decision`,
    `create_experience`, `create_relationship`.
- **ToolProposal** (modelo `assistant.ToolProposal`): toda tool de escrita gera
  uma proposta `pending` — nada é criado sem aprovação explícita do usuário.
- Endpoints: `GET|POST? /api/tools/proposals/:id/approve/`, `reject/`, listagem de
  propostas pendentes (isoladas por owner).
- `ChatService` integra as tools: se o Gemini pedir tool de leitura, executa e
  faz segunda chamada com o resultado (multi-turn); se pedir escrita, cria
  proposta e retorna em `proposals` no payload do chat.
- Frontend: proposta renderizada no chat com botões **Aprovar/Rejeitar**
  (aprovação cria a entidade; rejeição descarta).
- Migração `0002_toolproposal`; documentos de tools em `tools/registry.py`.
- 11 testes novos (total 154 verdes).

## [0.6.0] — FASE 6: ATLAS ASSISTANT

### Adicionado
- **Classificação completa da resposta** no chat:
  - O modelo inicia a resposta com uma tag obrigatória (`[FATO]`, `[INFERÊNCIA]`,
    `[SUGESTÃO]`, `[INFORMAÇÃO EXTERNA]`) — ver `services/chat.py:parse_classification`.
  - A API e o frontend mostram a classificação com rótulo amigável e
    `source_based` (Fato/Inferência exigem fontes). Fallback heurístico quando o
    modelo não segue o formato.
- **Memória persistente** (modelo `assistant.Memory`):
  - Kinds: Preferência, Contexto, Objetivo, Projeto, Decisão, Experiência.
  - `MemoryViewSet` (CRUD isolado por owner + soft delete) → `GET|POST /api/memories/`,
    `GET|PATCH|DELETE /api/memories/:id/`.
  - `build_context` injeta as memórias do usuário no prompt do chat
    (`MAX_MEMORIES` configurável) e o `DeterministicProvider` também as cita.
- Frontend: módulo **Memória** (`/memoria`) com criação/listagem/exclusão
  (config `memoria` em `pages/entities.js`, com cabeçalhos de coluna
  configuráveis `config.headers`) e Assistente marcado como Fase 6.
- Migração `0001_initial` (Memory) e `MAX_MEMORIES` no settings.
- 10 testes novos (total 143 verdes).

## [0.5.0] — FASE 5: GEMINI CORE

### Adicionado
- App `assistant` (Fase 5 — Gemini Core):
  - `AIProvider` (contrato em `providers/base.py`) → `GeminiProvider`
    (`providers/gemini.py`) via SDK oficial `google.genai` (`generate_content`
    com `system_instruction`, `max_output_tokens`, `temperature`, tools
    placeholders e extração de `tool_calls`) e `DeterministicProvider`
    (`providers/deterministic.py`, fallback offline sem chave).
  - `resolve_chat_provider()`: escolhe automaticamente Gemini quando há
    `GEMINI_API_KEY`, senão o modo determinístico.
  - Exceções padronizadas (`exceptions.py`) que nunca expõem detalhes internos
    (AIError, ProviderUnavailableError, RateLimitExceededError, TokenLimitError,
    MaxRetriesExceededError).
  - `retry_with_backoff` (`retry.py`): backoff exponencial + jitter apenas para
    erros transientes (429/5xx/timeouts).
  - Prompts (`prompts.py`): system prompt com rastreabilidade ([fonte]) e
    classificação Fato/Inferência/Sugestão/Informação externa.
  - `ChatService` (`services/chat.py`) + `build_context` (`services/context.py`):
    recupera contexto do usuário via busca híbrida (Fase 4) + grafo (Fase 3),
    sanitiza/limita histórico, e retorna `{ answer, sources, provider,
    classification, semantic_available }`.
  - `POST /api/assistant/chat/` (`views.py`) com throttle `gemini` por usuário
    (`throttling.py`), além do throttle global do DRF.
- Settings: `GEMINI_MODEL` (padrão `gemini-3.6-flash`), `GEMINI_MAX_RETRIES`,
  `GEMINI_TIMEOUT`, `GEMINI_MAX_TOKENS`, `GEMINI_RATE_LIMIT_PER_MIN`,
  `MAX_CHAT_MESSAGES`, `MAX_RETRIEVAL_RESULTS`; `.env.example` atualizado.
- Embeddings: `EMBEDDING_MODEL=gemini-embedding-001` (3072 dimensões) e
  `EMBEDDING_DIM=3072`; default ajustado no `GeminiEmbeddingProvider`.
- Frontend: página do Assistente (`pages/assistant.js`) consome o chat real —
  bolhas com estado "digitando", fontes clicáveis, classificação e
  provedor (gemini/local); estilos de chat em `app.css`.
- Dependência `google-genai` declarada em `requirements.txt`/`pyproject.toml`
  (substitui o SDK antigo `google-generativeai`).
- 22 testes novos (total 133 verdes).

## [0.4.0] — FASE 4: SEARCH + EMBEDDINGS

### Adicionado
- App `search`: serviço de busca híbrida com ranking de relevância sobre as
  6 entidades do Knowledge Core (prefixo no título > subtítulo > corpo),
  isolado por owner e excluindo soft-deleted.
- `GET /api/search/?q=&type=&limit=` — endpoint unificado (aceita `type` em
  português) que combina score textual com similaridade de cosseno.
- `EmbeddingProvider` (contrato) com `GeminiEmbeddingProvider` (google.genai,
  por `GEMINI_API_KEY`, `EMBEDDING_MODEL`) e `FingerprintEmbeddingProvider`
  (fallback determinístico/offline em `EMBEDDING_DIM` dimensões).
- Frontend: página de **Busca** (`pages/search.js`, rota `/busca`) com busca
  por termo/tipo e resultados clicáveis.
- Settings: `GEMINI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`;
  `.env.example` atualizado. `google.genai` já listado.
- 16 testes novos (total 111 verdes).

## [0.3.0] — FASE 3: RELATIONSHIPS E GRAFO

### Adicionado
- App `relationships`: modelo `Relationship` com `origin`/`target` via
  `GenericForeignKey`, `type` (11 tipos), herda `AtlasModel + OwnerMixin`.
- Entidades elegíveis configuráveis em `settings.RELATIONSHIP_MODELS`.
- `RelationshipViewSet` (CRUD com isolamento por owner, anti-IDOR, sem
  self-loop e sem duplicatas).
- `GET /api/graph/` → `{ nodes, edges }` (grafo do usuário; arestas com ponta
  soft-deletada omitidas).
- Frontend: página de **Grafo** (`pages/graph.js`) com visualização SVG dos
  nós/arestas, criação de relacionamentos e exclusão de arestas.
- Migrações e 14 testes novos (total 95 verdes).

## [0.2.2] — Frontend separado do backend

### Movido
- Frontend (HTML/CSS/JS puro) movido de `backend/templates/` e `backend/static/`
  para uma pasta dedicada **`frontend/`** na raiz do repositório
  (`frontend/templates/atlas/` e `frontend/static/atlas/`).
- `settings_base.py`: `TEMPLATES[0].DIRS` e `STATICFILES_DIRS` agora apontam
  para `<repo>/frontend` (`FRONTEND_DIR`).
- Django continua servindo o frontend (mesma origem, sem build step); nada muda
  na API nem nas URLs dos estáticos.

## [0.2.1] — Dashboard e Configurações

### Adicionado
- `GET /api/dashboard/` (app `dashboard`): contagens das 6 entidades do usuário,
  total e itens recentes — sempre isolado por `owner` e ignorando soft-deleted.
- Página **Dashboard** real no frontend: cards de contagem (navegáveis para cada
  entidade) e lista de atividade recente.
- Página **Configurações** (`pages/settings.js`): edição de perfil
  (`PATCH /accounts/me/`), exibição de dados da conta e preferências do Assistant
  (tema/tom/sugestões) salvas em `localStorage` por enquanto.
- Estilos novos em `app.css` (dashboard e configurações).
- 5 testes novos (total 81 verdes).

## [0.2.0] — FASE 2: KNOWLEDGE CORE

### Adicionado
- Modelo base `core.KnowledgeEntity` (`AtlasModel + OwnerMixin` abstrato) com
  `title`, `summary`, `status` e o `KnowledgeManager` (`for_owner`/`active`).
- `core.Status` (draft/active/archived/committed), `core.OwnerModelViewSet`
  (isolamento por owner, `owner=request.user` na criação e soft delete no
  `destroy`) e `core.OwnerModelSerializer` + `core.tests_common`.
- Seis apps do Knowledge Core, cada um com CRUD completo, permissões por owner,
  soft delete, busca/ordenação e admin:
  - `knowledge`: `content`, `domain_level` (1–4), `tags`.
  - `ideas`: `description`, `converted`; action `POST .../convert/` transforma a
    ideia em um `Project`.
  - `projects`: `name`, `description`, `objective`, `technologies` (com `title`
    sincronizado de `name`).
  - `questions`: `question_text`, `answered`; action `POST .../respond/` cria um
    `Knowledge` a partir da pergunta.
  - `decisions`: `context`, `problem`, `alternatives`, `decision`, `rationale`,
    `consequences`, `decided_at`.
  - `experiences`: `kind` (erro/solução/descoberta/experimento/aprendizado),
    `content`, `tags`.
- Rotas `api/{knowledge|ideas|projects|questions|decisions|experiences}/`.
- Migrações e 56 novos testes (total 76 verdes).
- Frontend: página genérica por entidade em `pages/entities.js` (listar, criar,
  excluir e, onde aplicável, converter/responder) com estilos em `app.css`.

## [0.1.1] — FASE 1: Frontend em HTML/CSS/JS puro

### Trocado
- Frontend reescrito de React/Vite/TypeScript para **HTML, CSS e JavaScript
  puro**, organizado em módulos ES e **servido pelo próprio Django** (mesma
  origem, `/` para o frontend e `/api` para a API).
- Removidas as dependências/build de Node/Vite; removido o serviço `frontend`
  do Docker Compose (o backend agora entrega tudo).
- Módulos JS em `backend/static/atlas/js/`: `api.js` (HTTP + JWT + refresh),
  `auth.js` (estado de sessão), `router.js` (SPA por hash), `helpers.js`,
  `pages/*.js` (auth, app, assistant) e `app.js` (bootstrap).
- Estilos em `backend/static/atlas/css/app.css`; página em
  `backend/templates/atlas/index.html`.
- Testes acrescidos de verificação do frontend servido (20 verdes no total).

## [0.1.0] — FASE 1: FOUNDATION

### Adicionado
- Estrutura de projeto (backend + docs).
- Settings por ambiente (`DJANGO_ENV=development|production`), com DB
  configurável (SQLite local / PostgreSQL + pgvector em produção).
- `accounts`: User por e-mail com PK UUID, registro, JWT (login/refresh),
  `GET /accounts/me/`, permissão `IsOwner`, throttling de login.
- `core`: `AtlasModel` (UUID, timestamps, soft delete) e `OwnerMixin`.
- `audit`: `AuditLog` com redação automática de secrets.
- `assistant.providers.base`: interface `AIProvider` (contrato).
- Docker Compose (pgvector + backend) e Dockerfile.
- Documentação: README, ARCHITECTURE, SETUP, SECURITY, ROADMAP, DATA_MODEL,
  API, AI_ARCHITECTURE.
