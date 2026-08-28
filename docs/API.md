# API

Base URL: `/api` — desenvolvimento em `http://127.0.0.1:8000/api`.

Autenticação: cabeçalho `Authorization: Bearer <access>`, exceto onde indicado.

## Autenticação (FASE 1)

### `POST /api/auth/token/`
Loga e retorna tokens JWT. *(público)*
```json
{ "email": "a@b.com", "password": "..." }
→ 200 { "access": "...", "refresh": "..." }
```

### `POST /api/auth/token/refresh/`
Gera novo access a partir do refresh. *(público)*
```json
{ "refresh": "..." }
→ 200 { "access": "..." }
```

## Contas

### `POST /api/accounts/register/`
Cria conta e retorna tokens (login automático). *(público)*
```json
{
  "email": "a@b.com",
  "first_name": "Ana",
  "password": "senha-forte-123",
  "password_confirmation": "senha-forte-123"
}
→ 201 { "user": {...}, "access": "...", "refresh": "..." }
```

### `GET /api/accounts/me/`
Perfil do usuário autenticado. *(autenticado)*
```json
→ 200 { "id": "...", "email": "...", "first_name": "...", "last_name": "...", ... }
```
Não expõe `password` nem `is_superuser`.

## Knowledge Core (FASE 2)

Cada entidade expõe CRUD completo (list/create/retrieve/update/partial/delete
com soft delete), paginado, com busca (`?search=`) e ordenação (`?ordering=`).
Todas isoladas por `owner` (anti-IDOR) e autenticadas.

Endpoints:
- `GET|POST /api/knowledge/` · `GET|PATCH|DELETE /api/knowledge/:id/`
- `GET|POST /api/ideas/` · `GET|PATCH|DELETE /api/ideas/:id/`
- `GET|POST /api/projects/` · `GET|PATCH|DELETE /api/projects/:id/`
- `GET|POST /api/questions/` · `GET|PATCH|DELETE /api/questions/:id/`
- `GET|POST /api/decisions/` · `GET|PATCH|DELETE /api/decisions/:id/`
- `GET|POST /api/experiences/` · `GET|PATCH|DELETE /api/experiences/:id/`

Exemplo de criação (Knowledge):
```json
POST /api/knowledge/
{ "title": "Django", "content": "Framework web", "domain_level": 3 }
→ 201 { "id": "...", "title": "Django", "status": "draft", "owner": "..." }
```

### Transformações
- `POST /api/ideas/:id/convert/` — transforma a Ideia em um `Project`.
  ```json
  { "name": "Projeto X" } → 201 { "id": "...", "name": "Projeto X", "idea": "..." }
  ```
- `POST /api/questions/:id/respond/` — responde a Pergunta criando um
  `Knowledge`.
  ```json
  { "content": "IA generativa" } → 201 { "id": "...", "title": "...", "question": "..." }
  ```

Campos por entidade (além de `id`, `owner`, `created_at`, `updated_at`,
`title`, `summary`, `status`):
- **Knowledge:** `content`, `domain_level` (1–4), `tags`[].
- **Idea:** `description`, `converted`, `project`.
- **Project:** `name`, `description`, `objective`, `technologies`[].
- **Question:** `question_text`, `answered`, `knowledge`.
- **Decision:** `context`, `problem`, `alternatives`[], `decision`, `rationale`,
  `consequences`, `decided_at`.
- **Experience:** `kind`, `content`, `tags`[].

## Códigos

- `200 OK`, `201 Created`, `204 No Content`, `400 Bad Request`, `401
  Unauthorized`, `404 Not Found`, `405` (método não permitido), `429`
  (throttled).

## API planejada (próximas fases)

- Grafo: `GET /api/graph/` → `{ "nodes": [], "edges": [] }`.
- Search: busca híbrida.
- Assistant: `POST /api/assistant/chat/` com fontes, contexto e confirmações.
