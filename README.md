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
│   │   └── assistant/     # Interface AIProvider (contrato) — FASE 5+
│   ├── templates/atlas/   # index.html (frontend servido pelo Django)
│   ├── static/atlas/      # CSS e JS puro do frontend (SDA leve por hash)
│   ├── manage.py
│   └── pyproject.toml
├── docs/
├── docker-compose.yml     # postgres(pgvector) + backend (servindo tudo)
├── .env.example
└── README.md
```

O frontend é um SPA em JavaScript puro com rotas por hash (`#/conhecimentos`,
`#/assistente`, ...), consumindo a API na mesma origem (`/api`). Módulos JS
organizados em `static/atlas/js/`: `api.js`, `auth.js`, `router.js`,
`helpers.js`, `pages/*.js` e `app.js`.

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
