# Atlas — Knowledge Operating System + AI Assistant

O **Atlas** é uma plataforma pessoal de conhecimento conectada a uma camada de
inteligência artificial (Atlas Assistant). O usuário armazena conhecimento,
ideias, projetos, decisões e experiências; o Atlas organiza e conecta essas
informações; e a IA utiliza esse conhecimento para compreender contexto,
encontrar relações, responder perguntas e sugerir conexões.

> O banco de dados é a fonte de verdade. A IA interpreta, recupera, organiza e
> utiliza o conhecimento armazenado.

## Stack

- **Backend:** Python, Django, Django REST Framework, PostgreSQL (+ pgvector),
  SimpleJWT, django-filter, Celery/Redis (quando necessário).
- **IA:** Google Gemini (via API oficial). Nenhuma dependência da OpenAI.
- **Frontend:** HTML, CSS e JavaScript puro (servido pelo próprio Django),
  sem build step e sem dependências de biblioteca.

## Estrutura

```
atlas/
├── backend/
│   ├── config/            # settings {base, local, production}, urls, wsgi/asgi
│   ├── apps/
│   │   ├── accounts/      # FASE 1: User, JWT, permissões, throttling
│   │   ├── core/          # Modelos base (UUID, timestamps, soft delete, owner)
│   │   ├── audit/         # Auditoria (AuditLog) com redação de secrets
│   │   ├── assistant/     # Interface AIProvider (contrato) — FASE 5+
│   │   ├── knowledge/     # FASE 2: Conhecimentos
│   │   ├── ideas/         # FASE 2: Ideias (→ Projetos)
│   │   ├── projects/      # FASE 2: Projetos
│   │   ├── questions/     # FASE 2: Perguntas (→ Conhecimentos)
│   │   ├── decisions/     # FASE 2: Decisões
│   │   ├── experiences/   # FASE 2: Experiências
│   │   ├── dashboard/     # FASE 2: visão agregada (contagens + recentes)
│   │   ├── relationships/ # FASE 3: relacionamentos genéricos + grafo
│   │   └── search/        # FASE 4: busca híbrida + embeddings
│   ├── manage.py
│   └── pyproject.toml
├── frontend/
│   ├── templates/atlas/   # index.html (frontend servido pelo Django)
│   └── static/atlas/      # CSS e JS puro do frontend (SPA leve por hash)
├── docs/
├── docker-compose.yml     # postgres(pgvector) + backend (servindo tudo)
├── .env.example
└── README.md
```

O frontend fica separado em `frontend/` e é servido pelo próprio Django (mesma
origem). É um SPA em JavaScript puro com rotas por hash (`#/conhecimentos`,
`#/assistente`, ...), consumindo a API em `/api`. Módulos JS em
`frontend/static/atlas/js/`: `api.js`, `auth.js`, `router.js`, `helpers.js`,
`pages/*.js` e `app.js`.

## Como rodar (desenvolvimento)

Consulte [docs/SETUP.md](docs/SETUP.md). Resumo:

```bash
# Backend (serve API + frontend)
cd backend
copy ..\.env.example .env      # ajuste se necessário (DB_ENGINE=sqlite padrão)
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver

# Acesse http://127.0.0.1:8000  (frontend + API na mesma origem)
```

## Status atual

**FASE 1 — FOUNDATION** implementada e testada:

- Autenticação por e-mail + JWT (SimpleJWT) com registro e refresh.
- Usuário com PK UUID (proteção contra enumeração/IDOR).
- Modelo base `AtlasModel` (UUID, timestamps, soft delete) e `OwnerMixin`.
- Auditoria (`AuditLog`) com redação automática de secrets.
- Seleção de ambiente (`DJANGO_ENV=development|production`), banco SQLite
  (dev) ou PostgreSQL+pgvector (produção).
- Docker Compose (postgres/pgvector + backend servindo tudo).
- Frontend em HTML/CSS/JS puro (servido pelo Django, SPA por hash) com shell
  de navegação, autenticação, token refresh e interface do Assistant.
- Testes de autenticação, segurança, soft delete e frontend (20 testes verdes).

**FASE 2 — KNOWLEDGE CORE** implementada e testada:

- Seis entidades (Knowledge, Ideas, Projects, Questions, Decisions,
  Experiences) com CRUD completo, permissões por owner (anti-IDOR) e soft
  delete, sempre isoladas por usuário.
- Transformações registradas: Ideia → Projeto e Pergunta → Conhecimento.
- Modelo base `KnowledgeEntity` + `OwnerModelViewSet`/`OwnerModelSerializer`
  reutilizados por todas as entidades.
- Migrações aplicadas e 76 testes verdes no total.
- Frontend com páginas funcionais de listar/criar/excluir cada entidade e
  ações de conversão/ resposta onde aplicável.

**Dashboard e Configurações** implementados:

- `GET /api/dashboard/` com contagens, total e atividade recente do usuário.
- Dashboard real no frontend (cards navegáveis + recentes).
- Configurações: edição de perfil, dados da conta e preferências do Assistant
  (local por enquanto).

Status de testes: **81 verdes**.

**FASE 3 — RELATIONSHIPS E GRAFO** implementada e testada:

- Modelo genérico `Relationship` (`GenericForeignKey` origin/target) com 11
  tipos configuráveis e isolamento por owner (anti-IDOR, sem self-loop/duplicatas).
- `GET /api/graph/` → `{ nodes, edges }` do usuário.
- Página de **Grafo** no frontend (visualização SVG + criação de relacionamentos).

Status de testes: **95 verdes**.

**FASE 4 — SEARCH + EMBEDDINGS** implementada e testada:

- Busca híbrida `GET /api/search/` (textual + semântica) nas 6 entidades,
  isolada por owner, com ranking de relevância.
- `EmbeddingProvider` com `GeminiEmbeddingProvider` (via `GEMINI_API_KEY`) e
  fallback determinístico offline.
- Página de **Busca** no frontend (`/busca`).

Status de testes: **111 verdes**.

## Documentação

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — arquitetura geral.
- [SETUP.md](docs/SETUP.md) — ambiente e execução.
- [SECURITY.md](docs/SECURITY.md) — segurança (dados não confiáveis, IA).
- [ROADMAP.md](docs/ROADMAP.md) — evolução em 10 fases.
- [DATA_MODEL.md](docs/DATA_MODEL.md) — modelo de dados.
- [API.md](docs/API.md) — endpoints.
- [AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) — Gemini, RAG, embeddings.
- [CHANGELOG.md](docs/CHANGELOG.md) — histórico de mudanças.

## Licença

Privado. Uso pessoal.
