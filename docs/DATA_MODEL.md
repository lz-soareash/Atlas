# DATA_MODEL

## Diagrama conceitual

```
accounts.User (UUID, email+senha)
      │ 1
      │ owner
      ▼
+--------------------+  Knowledge / Idea / Project / Question /
| Entidade Knowledge |  Decision / Experience  (FASE 2)
| Core: AtlasModel   |--------------------+
| (UUID, timestamps, |                    |
|  soft delete)      |  + Relationship   |  (genérico, FASE 3)
+--------------------+  origin ── edge ──┘ target
                           type (RELACIONADO_A, USA, ...)

AuditLog (auditoria de ações + AI audit)
Version (histórico/evolução, FASE 4/22)
Embeddings (pgvector, FASE 4)
```

## Modelos da FASE 1

### `accounts.User`
- `id` UUID (não enumerável)
- `email` (único, login), `password`
- `first_name`, `last_name`
- `is_active`, `is_staff`, `is_superuser`
- `created_at`, `updated_at`

### `core.AtlasModel` (abstrato)
- `id` UUID com default automático
- `created_at`, `updated_at`
- `deleted_at` (soft delete) + métodos `soft_delete()`/`restore()`

### `core.OwnerMixin` (abstrato)
- `owner` FK → `accounts.User` (isolamento por usuário / anti-IDOR)

### `core.KnowledgeEntity` (abstrato, FASE 2)
- Herda `AtlasModel + OwnerMixin`
- `title` (255), `summary` (texto), `status` (`draft/active/archived/committed`)
- `KnowledgeManager` com `for_owner(user)` e `active()` (omite soft-deleted)

### `audit.AuditLog`
- `user` FK (nullable), `action`, `entity_type`, `entity_id`
- `summary`, `details` (JSON, com redação de secrets), `ip_address`
- `created_at`

## Modelos da FASE 2

Todas as entidades herdam `KnowledgeEntity` (ou seja, `AtlasModel + OwnerMixin`):

- **Knowledge:** `content`, `domain_level` (1–4), `tags` (JSON).
- **Idea:** `description`, `converted`; FK `project` (origem). Action de
  conversão cria um `Project`.
- **Project:** `name`, `description`, `objective`, `technologies` (JSON);
  `title` sincronizado de `name`. FK reversa de ideias de origem.
- **Question:** `question_text`, `answered`; FK `knowledge` (conhecimento
  originado). Action de resposta cria um `Knowledge`.
- **Decision:** `context`, `problem`, `alternatives` (JSON), `decision`,
  `rationale`, `consequences`, `decided_at` (data).
- **Experience:** `kind` (erro/solução/descoberta/experimento/aprendizado),
  `content`, `tags` (JSON).

## Relacionamentos (FASE 3, implementada)

### `relationships.Relationship`
- Herda `AtlasModel + OwnerMixin`.
- `origin`/`target` — `GenericForeignKey` (`ContentType` + UUID) para as
  entidades do Knowledge Core, configuradas em `settings.RELATIONSHIP_MODELS`
  (extensível: basta adicionar pares `app_label, model_name`).
- `type` — tabela `RelationshipType` (RELACIONADO_A, USA, DEPENDE_DE,
  ORIGINOU, INSPIROU, PARTICIPA_DE, RESOLVE, RESPONDE, AFETA, GEROU,
  APRENDEU_COM). Configurável e extensível.
- Restrição de unicidade (origin, target, type) para evitar duplicatas.
- A API valida que ambas as pontas pertencem ao usuário (anti-IDOR) e rejeita
  self-loops e duplicatas.

### Grafo
`GET /api/graph/` retorna `{ nodes, edges }` a partir dos relacionamentos do
usuário. Arestas órfãs (uma ponta soft-deletada) são omitidas.

## Embeddings (FASE 4)

- `EmbeddingProvider` — contrato abstrato (`available`, `embed_documents`).
- `GeminiEmbeddingProvider` — embeddings reais via Google (`google.genai`),
  disponível quando `GEMINI_API_KEY` está configurada (`EMBEDDING_MODEL`,
  padrão `text-embedding-004`).
- `FingerprintEmbeddingProvider` — fallback determinístico e offline (hashing
  de features em vetor de `EMBEDDING_DIM` dimensões); usado em dev/testes e
  quando não há chave.

### Busca híbrida
`GET /api/search/` busca nas 6 entidades do usuário combinando score textual
(relevância: prefixo no título > subtítulo > corpo) e similaridade de cosseno
sobre embeddings, quando um provider está disponível. Isolado por owner
(anti-IDOR); entidades soft-deleted são excluídas. Resultado normalizado:
`{entity, label, id, title, snippet, score, route, status, source}`.

## FASE 5 — GEMINI CORE (planejada)

Coluna `vector` (`pgvector`) associada às entidades; endereços de busca
semântica com embeddings do Gemini (via `GeminiEmbeddingProvider`).
