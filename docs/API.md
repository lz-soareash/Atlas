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

## Códigos

- `200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `405`
  (método não permitido), `429` (throttled).

## API planejada (próximas fases)

- Knowledge Core: CRUD de Knowledge/Idea/Project/Question/Decision/Experience.
- Grafo: `GET /api/graph/` → `{ "nodes": [], "edges": [] }`.
- Search: busca híbrida.
- Assistant: `POST /api/assistant/chat/` com fontes, contexto e confirmações.
