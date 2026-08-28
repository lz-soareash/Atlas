# CHANGELOG

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
