# CHANGELOG

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
