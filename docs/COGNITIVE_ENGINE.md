# Cognitive Engine + JARVIS API (Fase 10)

> Visão de engenharia do **motor cognitivo** do Atlas e da **integração
> serviço-a-serviço** que permite a um agente externo (o "Jarvis") raciocinar
> sobre o conhecimento do Atlas. Complementa `docs/API.md` (catálogo) e
> `docs/JARVIS_INTEGRATION.md` (contrato de integração).

## 1. Objetivo

Expor ao Jarvis uma **API estável e read-only de raciocínio** sobre o acervo do
Atlas — reutilizando **toda** a infraestrutura já existente (busca híbrida,
grafo, memórias, provider de IA com fallback e classificação), sem duplicar nem
quebrar as Fases 1–9.

### O que NÃO é (regras absolutas)

- **Sem voz / STT / TTS.**
- **Sem controle de PC** (abrir apps, clicar, digitar).
- **Sem autonomia irrestrita**: escritas continuam exigindo aprovação do usuário
  via `ToolProposal`. O cognitive **não** executa tools — é **read-only**.
- **Sem dependência do Jarvis**: o Atlas funciona sozinho; o Jarvis é um cliente
  opcional.

## 2. Autenticação serviço-a-serviço

| Conta | Auth | Uso |
|-------|------|-----|
| Humano   | JWT `Authorization: Bearer` | sessão do usuário no frontend |
| Serviço  | `X-API-Key: svc_...`        | chamadas automatizadas (Jarvis) |

- `ServiceCredential` guarda apenas `key_hash` (HMAC-SHA256 com `SECRET_KEY`),
  nunca a chave crua; `key_hint` para exibição.
- A conta de serviço emite/rota-ção/revoga as próprias chaves em
  `POST /api/service-credentials/`.
- Isolamento por `owner` (anti-IDOR) vale para os dois tipos.

## 3. Modelos (app `cognitive`)

- **`CognitiveSession`** — sessão persistente: `name`, `project_context` (JSON),
  `metadata` (JSON), `is_active`, `closed_at`; `close()` encerra. Herda
  `AtlasModel + OwnerMixin`, manager = `KnowledgeManager` (`for_owner`/`active`).
- **`SessionMessage`** — turno da sessão: `role` (`user`/`assistant`),
  `content`, `sources` (JSON). Compõe o histórico.
- **`IntegrationEvent`** — evento recebido de integração: `type`, `payload`
  (JSON), `processed`, `error`.

## 4. CognitiveService (raciocínio read-only)

Fluxo de `POST /api/cognitive/sessions/:id/query/`:

1. `ContextManager.build()` — `build_context(owner, query)` (reuses retrieval:
   fontes, grafo, memórias) **somado** ao `project_context`/identidade da sessão;
   em erro de contexto, usa fallback vazio (não derruba a pergunta).
2. Montagem de mensagens ao provider (system prompt + contexto + histórico
   limitado a `MAX_CONTEXT_MESSAGES`).
3. `resolve_chat_provider()` — **`GeminiProvider`** se houver `GEMINI_API_KEY`,
   senão **`DeterministicProvider`** (modo offline). Fallback automático.
4. `parse_classification` reutilizado → resposta com
   `{answer, sources, classification, provider, semantic_available}`.
5. A view persiste o turno (`save_turn`) e registra `AuditLog COGNITIVE_*`
   (sem secrets).

**Read-only por design**: o serviço não injeta nem executa tools de escrita.
Uma conta de serviço só pode **consultar** — nada é criado/altera-lado por aqui
(anti-burla da aprovação via `ToolProposal`).

## 5. Eventos de integração (whitelist)

`POST /api/integration/events/` aceita apenas tipos registrados em
`apps/cognitive/integration.py::INTEGRATION_EVENT_TYPES`:

- `jarvis.notify` — notificação geral
- `jarvis.sync_request` — pedido de sincronização de dados
- `jarvis.status` — atualização de status/contexto

Política de segurança: tipo **não listado** é rejeitado (`400`), nunca processado
de forma implícita (**anti prompt-injection / extensão não autorizada**).
`WRITE_EVENT_TYPES` fica vazio (reservado); hoje nenhum evento é executado.
Payload limitado a 100 chaves.

## 6. Observabilidade

Todas as rotas registram `AuditLog` sem secrets:

- `COGNITIVE_SESSION_CREATE` / `COGNITIVE_QUERY` / `COGNITIVE_SESSION_CLOSE`
- `INTEGRATION_EVENT`, `SERVICE_CREDENTIAL_*` (criação/rotação/revogação)

## 7. Testes

15 testes novos em `apps/cognitive/tests.py` (sessão CRUD, query determinística
com provider injetado, close, anti-IDOR, whitelist, X-API-Key para conta de
serviço, AuditLog sem secrets) → **total 202 verdes** (171 anteriores + 16
ServiceCredential + 15 cognitive).
