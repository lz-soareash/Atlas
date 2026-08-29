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

## Relacionamentos e Grafo (FASE 3)

### `GET|POST /api/relationships/` · `GET|PATCH|DELETE /api/relationships/:id/`
CRUD de relacionamentos do usuário. `origin` e `target` são `GenericForeignKey`
representados por `{ "model": "app.model", "id": "uuid" }` (modelos elegíveis
listados em `settings.RELATIONSHIP_MODELS`). *(autenticado)*

```json
POST /api/relationships/
{
  "type": "USA",
  "origin": { "model": "projects.project", "id": "<uuid>" },
  "target": { "model": "knowledge.knowledge", "id": "<uuid>" }
}
→ 201 { "id": "...", "type": "USA", "origin": { "model": "...", "id": "..." },
        "target": { "model": "...", "id": "..." }, "owner": "..." }
```

Validações: ambas as pontas devem pertencer ao usuário (anti-IDOR), não é
permitido self-loop e não são permitidas duplicatas (origin, target, type).

Tipos: `RELACIONADO_A`, `USA`, `DEPENDE_DE`, `ORIGINOU`, `INSPIROU`,
`PARTICIPA_DE`, `RESOLVE`, `RESPONDE`, `AFETA`, `GEROU`, `APRENDEU_COM`.

### `GET /api/graph/`
Gera o grafo do usuário a partir dos relacionamentos. *(autenticado)*
```json
→ 200 {
  "nodes": [ { "id": "...", "entity": "projects", "label": "Projeto", "title": "Atlas", "emoji": "📁", "route": "/projetos", "status": "active" } ],
  "edges": [ { "id": "...", "source": "...", "target": "...", "type": "USA", "label": "Usa" } ]
}
```
Arestas com alguma ponta soft-deletada são omitidas.

## Códigos

- `200 OK`, `201 Created`, `204 No Content`, `400 Bad Request`, `401
  Unauthorized`, `404 Not Found`, `405` (método não permitido), `429`
  (throttled).

## Busca (FASE 4)

### `GET /api/search/?q=...&type=...&limit=...`
Busca híbrida sobre as 6 entidades do usuário. *(autenticado)*
```json
→ 200 {
  "query": "django",
  "semantic_available": true,
  "results": [
    { "id": "...", "entity": "knowledge", "label": "Conhecimento",
      "title": "Django REST Framework", "snippet": "APIs REST com Django...",
      "score": 8.83, "route": "/conhecimentos", "status": "active",
      "source": "semantic" }
  ]
}
```
- `q` (obrigatório, mas vazio → `results: []`), `type` (chave da entidade ou
  alias em português, ex.: `knowledge`/`conhecimento`), `limit` (1–100).
- Combina score textual (prefixo no título > subtítulo > corpo) com
  similaridade de cosseno sobre embeddings quando um provider está disponível
  (Gemini se `GEMINI_API_KEY`, senão fallback determinístico).
- Isolado por owner; entidades soft-deleted são excluídas.
- `source`: `textual` (sem provider) ou `semantic` (híbrido).

## Assistant (FASE 5)

### `POST /api/assistant/chat/`
Chat com contexto do Atlas (RAG). *(autenticado — throttle `gemini`)*
```json
{ "messages": [ { "role": "user"|"assistant", "content": "o que sei sobre django?" } ] }
→ 200 {
  "answer": "Você tem 1 conhecimento sobre Django: ...",
  "sources": [ { "id": "...", "entity": "knowledge", "label": "Conhecimento",
                 "title": "Django REST Framework", "route": "/conhecimentos",
                 "score": 8.83 } ],
  "provider": "gemini" | "deterministic",
  "classification": { "kind": "fato"|"sugestao", "label": "...", "source_based": true },
  "semantic_available": true
}
```
- Recupera contexto relevante do usuário (busca híbrida + grafo), sanitiza e
  limita o histórico (`MAX_CHAT_MESSAGES`) e responde citando as fontes.
- Sem `GEMINI_API_KEY` usa o `DeterministicProvider` (modo offline): `provider:
  "deterministic"`.
- Erros mapeados: `429` (rate limit atingido), `400` (mensagens inválidas/limite
  de tokens), `502` (IA indisponível). Detalhes internos nunca são expostos.

## Memória (FASE 6)

### `GET|POST /api/memories/` · `GET|PATCH|DELETE /api/memories/:id/`
CRUD de memórias persistentes do usuário (isolamento por owner + soft delete,
mesmos padrões do Knowledge Core). *(autenticado)*

```json
POST /api/memories/
{ "kind": "objetivo", "content": "Quero dominar Django" }
→ 201 { "id": "...", "kind": "objetivo", "kind_label": "Objetivo",
        "content": "Quero dominar Django", "owner": "...", "created_at": "..." }
```
- `kind`: `preferencia` | `contexto` | `objetivo` | `projeto` | `decisao` |
  `experiencia`.
- As memórias ativas do usuário são injetadas como contexto no chat
  (`POST /api/assistant/chat/`), limitadas por `MAX_MEMORIES`.

## API planejada (próximas fases)

- Tools (leitura/escrita com confirmação) e agente (Fases 7–9).
