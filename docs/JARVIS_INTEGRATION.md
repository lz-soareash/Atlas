# Integração Externa — Jarvis (Contrato de API)

> **Escopo:** documento de referência para um **futuro** assistente pessoal
> ("Jarvis") consumir a API do Atlas como cliente externo. Este guia define os
> contratos técnicos. **O Jarvis em si não é implementado no Atlas** — apenas a
> API fica preparada e documentada para recebê-lo.

Complementa o `docs/API.md` (catálogo completo por entidade). Aqui o foco é:
autenticação, permissões, isolamento, paginação, throttle, e os contratos de
dados que um agente externo deve respeitar.

---

## 1. Visão geral

- **Base URL:** `http://127.0.0.1:8000/api` (produção usará host configurado em `ALLOWED_HOSTS`).
- **Formato:** JSON (`Content-Type: application/json`).
- **Autenticação:** JWT Bearer (access + refresh rotativo).
- **Isolamento:** cada usuário vê **somente** o próprio conteúdo (anti-IDOR em 2 camadas).
- **ID único:** `UUID4` (não enumerável) em todas as entidades.
- **Soft delete:** remover um item não o apaga do banco — apenas o marca `is_deleted`.

### Fluxo de credenciais do cliente externo

O Jarvis não pode compartilhar a sessão do usuário. Dois padrões:

1. **Em nome do usuário:** usar as credenciais (email/senha) da conta para obter
   tokens via `POST /api/auth/token/` e armazená-los com segurança.
2. **Em nome próprio (serviço):** criar um usuário de **tipo `service`** e
   emitir uma `ServiceCredential` (chave `svc_…`, header **`X-API-Key`**).
   Indicado para integrações automatizadas (por exemplo, o ato de o Jarvis
   consultar/no futuro notificar o Atlas) que não devem trafegar credenciais
   de usuário humano. *(Ver `docs/COGNITIVE_ENGINE.md`.)*

---

## 2. Autenticação

### 2.1 Login — `POST /api/auth/token/` *(público, throttle)*

```json
{ "email": "a@b.com", "password": "..." }
```

**200:**
```json
{
  "access": "<jwt access>",
  "refresh": "<jwt refresh>"
}
```

- `access`: válido por **60min** (configurável via `ACCESS_TOKEN_MINUTES`).
- `refresh`: válido por **1 dia** (configurável via `REFRESH_TOKEN_DAYS`).
- Throttle dedicado: **10/min** (`LoginThrottle`, por IP) — prevenção de força bruta.
- `401` em credenciais inválidas.

### 2.2 Renovar access — `POST /api/auth/token/refresh/` *(público)*

```json
{ "refresh": "<jwt refresh>" }
```

- Como `ROTATE_REFRESH_TOKENS=True`, retorna **novo `access` e novo `refresh`**.
- O antigo refresh é **revogado** (blacklist) quando `BLACKLIST_AFTER_ROTATION=True`.
- `401` se o refresh for inválido, expirado ou já revogado.

**200:**
```json
{ "access": "<novo>", "refresh": "<novo>" }
```

### 2.3 Logout — `POST /api/auth/logout/` *(autenticado)*

```json
{ "refresh": "<jwt refresh>" }
```

- Revoga o refresh token (blacklist). O access atual continua válido até expirar.
- **204** em sucesso; **400** se o refresh for inválido/revogado; **401** sem token.

```text
Authorization: Bearer <access>
```

### 2.4 Cabeçalho padrão

Toda requisição autenticada:
```text
Authorization: Bearer <jwt access>
```

Erro de autenticação → **401** `{ "detail": "...", "code": "token_not_valid" }`.

### 2.5 Auth de serviço — `X-API-Key` (Fase 10)

Contas de **tipo `service`** autenticam sem JWT, enviando a chave de API:
```text
X-API-Key: svc_...
```
- A chave é emitida/gerenciada em `POST /api/service-credentials/` (a conta
  `service` cria e rotaciona as próprias chaves).
- É sem estado para o cliente (não expira em 60min como o JWT); **revogação**
  responde na hora via `revoke`.
- Ausente/Inválida → **401**; os mesmos anti-IDOR, paginação e throttle se aplicam.
- Contas `service` são **read-only por design** nas rotas que envolvem IA
  (Cognitive Engine não executa tools de escrita).

---

## 3. Permissões e ownership

### 3.1 Modelo de permissões

| Grupo                 | Endpoints                                  | Requisito                    |
|-----------------------|--------------------------------------------|------------------------------|
| Público               | `token/`, `token/refresh/`, `register/`    | anônimo                      |
| Autenticado (CRUD do usuário) | todas as entidades, dashboard, grafo, search, intelligence | `IsAuthenticated` + owner |
| Proposta de escrita   | `tools/proposals/`                         | leitura + `approve`/`reject`; **create bloqueado (405)** |
| Contas de serviço     | `service-credentials/`                     | `IsAuthenticated` (JWT ou X-API-Key) + owner |
| Cognitive Engine (read-only) | `cognitive/sessions/`, `cognitive/sessions/:id/query/`, `close/` | `IsAuthenticated` (JWT ou X-API-Key) + owner |
| Eventos de integração | `integration/events/`                      | `IsAuthenticated` (JWT ou X-API-Key) + owner + whitelist |

### 3.2 Isolamento por owner (anti-IDOR) — REGRA CRÍTICA

Todos os endpoints de dados aplicam duas camadas:

1. **Queryset filtrado:** `Model.objects.for_owner(request.user).active()`
   (nunca se filtra por PK global).
2. **Perfil de permissão:** `IsOwner` — o objeto pertence ao `owner` do request.

> **Contrato para o Jarvis:** nunca se deve confiar em IDs retornados para acessar
> conteúdo de outro usuário. Tentativas em objetos de terceiros → **404** (não 403,
> para não vazar existência). O cliente deve tratar 404 como "não pertence a você".

---

## 4. Convenções de listagem

Toda listagem paginada segue o envelope DRF `PageNumberPagination`:

```json
{
  "count": 42,
  "next": "http://host/api/knowledge/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

- `?page=N` para paginar; `PAGE_SIZE` padrão **20**.
- Filtros:
  - `?search=<texto>` — busca textual (SearchFilter).
  - `?ordering=<campo>` — ordenação; prefixe `-` para descendente.
  - `?<campo>=<valor>` — filtros de exatidão por app (DjangoFilterBackend).

---

## 5. Catálogo de endpoints

### 5.1 Contas

| Método | Rota                       | Autenticação | Descrição                         |
|--------|----------------------------|--------------|-----------------------------------|
| POST   | `/accounts/register/`      | público      | cria conta + retorna tokens       |
| GET    | `/accounts/me/`            | autenticado  | perfil do usuário (`me`)          |
| POST   | `/auth/token/`             | público      | login                             |
| POST   | `/auth/token/refresh/`     | público      | renovar access                    |
| POST   | `/accounts/logout/`        | autenticado  | revoga refresh                    |

### 5.2 Knowledge Core — CRUD completo *(autenticado, owner)*

Para cada entidade: `GET|POST /api/<plura>/`, `GET|PATCH|DELETE /api/<plura>/:id/`.

| Entidade   | Rota            | Ações extras                          |
|------------|-----------------|---------------------------------------|
| Knowledge  | `/knowledge/`   | —                                     |
| Idea       | `/ideas/`       | `POST /ideas/:id/convert/`            |
| Project    | `/projects/`    | —                                     |
| Question   | `/questions/`   | `POST /questions/:id/respond/`        |
| Decision   | `/decisions/`   | —                                     |
| Experience | `/experiences/` | —                                     |

Campos comuns: `id`, `owner`, `title`/`name`, `summary`, `status`, `created_at`, `updated_at`.

### 5.3 Relacionamentos e grafo

| Método | Rota                    | Descrição                                          |
|--------|-------------------------|----------------------------------------------------|
| CRUD   | `/relationships/`       | relacionamentos entre entidades (owner)            |
| GET    | `/graph/`               | `{ "nodes": [...], "edges": [...] }` do usuário    |

`Relationship` conecta entidades via **content types** (`origin` e `target`
genéricos — `app_label:model:pk`).

### 5.4 Busca híbrida — `GET /search/`

```
GET /search/?q=<texto>&type=<tipo>&limit=<1..100>
```
```json
{ "query": "...", "semantic_available": true, "results": [ ... ] }
```
- `type` aceita chave canônica (`knowledge`, `idea`, ...) ou alias (`conhecimentos`, `ideias`, ...).
- Considera `embeddings`; retorna entidades normalizadas, isoladas por owner.

### 5.5 Dashboard — `GET /dashboard/`

```json
{ "counts": [ { "key", "label", "count", "route" } ], "total": N, "recent": [ ... ] }
```
Agrega contagens e itens recentes das 6 entidades para o usuário.

### 5.6 Assistant (IA) — *(autenticado)*

| Método | Rota                          | Descrição                                              |
|--------|-------------------------------|--------------------------------------------------------|
| POST   | `/assistant/chat/`            | chat com contexto; **throttle `gemini`**               |
| CRUD   | `/memories/`                  | memórias do usuário (owner)                            |
| GET    | `/agent-runs/`                | execuções do agente — **somente leitura**              |
| GET    | `/tools/proposals/`           | propostas pendentes de escrita                         |
| POST   | `/tools/proposals/:id/approve/` | executa a proposta (cria entidade)                   |
| POST   | `/tools/proposals/:id/reject/`  | rejeita a proposta                                   |
| POST   | `/tools/proposals/`           | **405** — criação só via ChatService (bloqueado)       |

**`POST /assistant/chat/`**
```json
{ "messages": [ { "role": "user"|"assistant", "content": "..." } ] }
```
```json
{ "answer": "...", "sources": [], "provider": "gemini", "classification": "...", "semantic_available": true }
```
- **429** ao estourar o throttle Gemini (`GEMINI_RATE_LIMIT_PER_MIN`, padrão 20/min);
- **400** se histórico inválido; **502** em falha do provedor de IA.

### 5.7 Intelligence — *(autenticado, owner)*

| Método | Rota                                 | Descrição                                  |
|--------|--------------------------------------|--------------------------------------------|
| CRUD   | `/inbox/`                            | itens do inbox (captura rápida)            |
| POST   | `/inbox/:id/classify/`               | sugestão heurística (tipo/destino)         |
| GET    | `/intelligence/duplicates/`          | detecção de duplicatas                     |
| GET    | `/intelligence/relationship-suggestions/` | sugestões de vínculos                |
| GET    | `/intelligence/gaps/`                | análise de lacunas                         |
| GET    | `/intelligence/insights/`            | insights de produtividade                  |

**`POST /inbox/:id/classify/`** marca o item como `classified` e sugere
`kind`/`destination` (não move nada).

Campos do InboxItem: `id`, `content`, `status`, `kind`, `destination`, `summary`,
`owner`, `created_at`, `updated_at`. `kind`/`destination`/`summary` são **read-only**
(gerados pelo classify).

### 5.8 Cognitive Engine + eventos (Fase 10) — *(autenticado, owner)*

| Método | Rota                                        | Descrição                                    |
|--------|---------------------------------------------|----------------------------------------------|
| CRUD   | `/service-credentials/`                     | chaves de API de conta `service` (rotate/revoke) |
| GET/POST | `/cognitive/sessions/`                    | sessões cognitivas persistentes              |
| GET    | `/cognitive/sessions/:id/`                  | detalhe com histórico (`messages`)           |
| POST   | `/cognitive/sessions/:id/query/`            | pergunta → resposta estruturada (read-only)  |
| POST   | `/cognitive/sessions/:id/close/`            | encerra a sessão                             |
| GET/POST | `/integration/events/`                    | eventos de integração (whitelist)            |

**`POST /api/cognitive/sessions/:id/query/`**
```json
{ "query": "o que devo fazer sobre o projeto Atlas?" }
```
```json
{
  "answer": "...",
  "sources": [ { "id": "...", "entity": "decision", "label": "Decisão",
                 "title": "…", "route": "/decisoes", "score": 8.8 } ],
  "classification": { "kind": "fato", "label": "Fato", "source_based": true },
  "provider": "gemini" | "deterministic",
  "semantic_available": true,
  "session_id": "<uuid>"
}
```
- **Read-only**: o cognitive **não** executa tools de escrita — o Jarvis não pode
  criar/alterar conteúdo por aqui; escritas seguem exigindo `ToolProposal`
  aprovação do usuário. Falha de IA → **502**.

**`POST /api/integration/events/`**
```json
{ "type": "jarvis.sync_request", "payload": { "since": "2026-08-01" } }
```
- `type` precisa estar na whitelist (`jarvis.notify`, `jarvis.sync_request`,
  `jarvis.status`) de `apps/cognitive/integration.py`; desconhecido → **400**
  (nada é processado implicitamente). Payload limitado a 100 chaves.

---

## 6. Throttle (limites)

| Escopo    | Endpoints                       | Taxa            | Alvo      |
|-----------|---------------------------------|-----------------|-----------|
| `anon`    | qualquer (não autenticado)      | 20/min          | IP        |
| `user`    | todos os autenticados           | 100/min         | usuário   |
| `login`   | `token/`, `register/`           | 10/min          | IP        |
| `gemini`  | `/assistant/chat/`              | 20/min (env)    | usuário   |

Respostas com excesso → **429** `{ "detail": "Request was throttled." }`
(header retry em `Retry-After`).

Excesso nas **chamadas de IA** não é erro de contrato — o Jarvis deve respeitar
`Retry-After`/backoff antes de repetir.

---

## 7. Códigos de erro padrão

| Código | Significado                                              |
|--------|----------------------------------------------------------|
| 200    | OK                                                       |
| 201    | Criado                                                   |
| 204    | Sucesso sem corpo (ex.: logout)                          |
| 400    | Validação de payload (campo `detail` ou `{"campo": [...]}`) |
| 401    | Não autenticado / token inválido/expirado                 |
| 404    | Não encontrado **ou** não pertence ao owner (anti-IDOR)   |
| 405    | Método não permitido (ex.: create em proposals)           |
| 409    | Conflito de estado (ex.: proposta já resolvida)           |
| 429    | Throttle excedido                                         |
| 502    | Falha do provedor de IA (chat)                            |

---

## 8. Prontidão para produção (Jarvis)

Antes de expor a um cliente externo em produção:

- [ ] Definir `SECRET_KEY` forte no ambiente (sem fallback de dev).
- [ ] Configurar `ALLOWED_HOSTS` e `CORS_ALLOWED_ORIGINS` com o host do Jarvis.
- [ ] Usar Postgres (`DB_ENGINE=postgres`) com `pgvector` p/ busca semântica.
- [ ] Ajustar `ACCESS_TOKEN_MINUTES`/`REFRESH_TOKEN_DAYS` conforme a política.
- [ ] Limites de throttle (variáveis `THROTTLE_*`, `GEMINI_RATE_LIMIT_PER_MIN`) por ambiente.
- [ ] Revogação de tokens: blacklist **instalado e migrado** (`token_blacklist`);
      endpoint `logout` presente.
- [ ] HTTPS em produção (tokens trafegam no cabeçalho).
- [ ] Rotação/expiração: o Jarvis deve guardar o `refresh` e renovar o `access`
      proativamente (o access expira a cada 60min).

---

## 9. Segurança — lembretes ao motorista do Jarvis

1. **Nunca use IDs de um usuário para acessar dados de outro** (anti-IDOR).
2. **Nunca logue tokens ou senhas.**
3. **Não persista o `access` por mais tempo que o necessário** — só o `refresh`.
4. **Respeite os 404** como fronteira de propriedade.
5. **Não contorne o throttle de IA** — use backoff nos 429.
6. O backend jamais expõe `password`/`is_superuser` nos serializers.
