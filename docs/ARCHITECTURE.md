# ARCHITECTURE

## Visão geral

```
                   USUÁRIO
                      ↓
              ATLAS ASSISTANT
                      ↓
                GEMINI
                      ↓
              CONTEXT ENGINE
                      ↓
       ┌──────────────┼──────────────┐
       ↓              ↓              ↓
      RAG           MEMORY          GRAPH
       │              │              │
       └──────────────┼──────────────┘
                      ↓
               KNOWLEDGE CORE
                      ↓
                 PostgreSQL
```

- **Gemini** fornece inteligência.
- **Atlas** fornece contexto.
- **PostgreSQL** fornece memória estruturada.
- **Grafo** fornece relações.
- **RAG** fornece conhecimento relevante.
- **Tools** permitem ação controlada.

## Camadas do backend

O backend é modular, com apps Django sob `backend/apps/`:

| App           | Fase | Responsabilidade                                  |
|---------------|------|---------------------------------------------------|
| `accounts`    | 1    | Usuário, autenticação JWT, permissões, throttling |
| `core`        | 1    | Modelos base (UUID, soft delete, owner)           |
| `audit`       | 1    | Auditoria de ações + AI audit                     |
| `knowledge`   | 2    | Conhecimento adquirido                            |
| `ideas`       | 2    | Ideias (que podem virar projetos)                 |
| `projects`    | 2    | Projetos                                          |
| `questions`   | 2    | Perguntas                                         |
| `decisions`   | 2    | Decisões                                          |
| `experiences` | 2    | Experiências                                      |
| `relationships` | 3  | Relacionamentos genéricos + grafo                 |
| `versions`    | 4/22 | Versionamento da evolução do conhecimento        |
| `search`      | 4    | Busca híbrida (textual + semântica)               |
| `inbox`       | 8    | Inbox inteligente                                 |
| `assistant`   | 5+   | AI Core (+providers, services, tools, prompts)    |

## Separação de configurações

`DJANGO_ENV` seleciona o módulo de settings:

- `development` → `settings_local` (SQLite, DEBUG).
- `production` → `settings_production` (PostgreSQL, exige `DB_ENGINE=postgres`).

Secrets ficam em `.env` (nunca versionado). A `GEMINI_API_KEY` vive
exclusivamente no backend.

## Frontend

O frontend é **HTML, CSS e JavaScript puro**, servido pelo próprio Django a
partir de `backend/templates/atlas/` (página) e `backend/static/atlas/`
(estilos e scripts). É um SPA leve com roteamento por hash
(`#/conhecimentos`, `#/assistente`, ...), sem framework e sem build step.

Módulos JS (`static/atlas/js/`):

- `api.js` — cliente HTTP com JWT e refresh automático.
- `auth.js` — estado de sessão (login/registro/logout, usuário atual).
- `router.js` — roteador SPA por hash (+ guarda de autenticação).
- `helpers.js` — utilitários (escape anti-XSS, criação de elementos, erros).
- `pages/auth.js` — páginas de login e cadastro.
- `pages/app.js` — Dashboard e módulos do Knowledge Core (placeholder).
- `pages/assistant.js` — interface do Atlas Assistant.
- `app.js` — bootstrap (layout, rotas, eventos).

## Princípios

1. **Banco = fonte de verdade** — a IA nunca substitui os dados.
2. **IA desacoplada** — regras de negócio dependem de `AIProvider`, não do SDK.
3. **Escrita controlada** — tools de escrita exigem confirmação do usuário.
4. **Dados não confiáveis** — conteúdo do Atlas jamais altera instruções do sistema.
5. **Isolamento por owner** — todo registro pertence a um usuário (anti-IDOR).
6. **Evolução sem reescrita** — arquitetura em camadas preparada para
   Nível 1→8 (Jarvis).
