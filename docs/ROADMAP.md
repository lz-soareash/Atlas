# ROADMAP

O Atlas evolui em 10 fases, sempre com base funcional e testada.

## FASE 1 — FOUNDATION ✅ (implementada)
- [x] Django + estruturas de settings (`base`/`local`/`production`)
- [x] PostgreSQL (+ pgvector) e SQLite local configuráveis
- [x] Docker Compose (db com pgvector, backend, frontend)
- [x] JWT (SimpleJWT): registro, login, refresh, `/me`
- [x] `accounts` (User por e-mail, UUID), throttling, permissões
- [x] `core` (modelos base: UUID, timestamps, soft delete, owner)
- [x] `audit` (AuditLog + redação de secrets)
- [x] Frontend React/Vite/TS (shell, rotas, auth, token refresh)
- [x] Testes (auth, segurança, soft delete)

## FASE 2 — KNOWLEDGE CORE
- Entidades: Knowledge, Ideas, Projects, Questions, Decisions, Experiences
- CRUD, permissões por owner, soft delete, histórico de transformações
  (Ideia → Projeto, Pergunta → Conhecimento)

## FASE 3 — RELATIONSHIPS E GRAFO
- Relacionamentos genéricos (tipos configuráveis) + API `{nodes, edges}`
- Tipos: RELACIONADO_A, USA, DEPENDE_DE, ORIGINOU, INSPIROU, PARTICIPA_DE,
  RESOLVE, RESPONDE, AFETA, GEROU, APRENDEU_COM

## FASE 4 — SEARCH + EMBEDDINGS
- Busca textual + filtros + ordenação
- `EmbeddingProvider → GeminiEmbeddingProvider` (embeddings do Google)
- `pgvector` e busca semântica; combinação textual + semântica + grafo

## FASE 5 — GEMINI CORE
- `AIProvider → GeminiProvider` (implementação via SDK oficial)
- `services/` (chat, context, retrieval, memory, reasoning, agent)
- Prompts, tratamento de erros, retry, timeout, rate limit, controle de tokens

## FASE 6 — ATLAS ASSISTANT
- Chat com RAG real (Query analysis → Retrieval → Context Builder → Gemini)
- Fontes/rastreabilidade (📁 Projeto, 🧠 Conhecimento, ⚖️ Decisão, 📝 Experiência)
- Classificação Fato/Inferência/Sugestão/Informação externa
- Memória (preferências, contexto, objetivos; apenas explícitas/confirmadas)

## FASE 7 — TOOLS
- Leitura: search_*, get_entity, get_project_context, find_related_entities
- Escrita: create_* (exigem confirmação do usuário)
- Validação de autenticação/ownership/permissões/integridade

## FASE 8 — INTELLIGENCE
- Inbox inteligente, detecção de duplicatas (sem merge automático)
- Sugestão de relacionamentos, Gap Analysis, Decision Intelligence

## FASE 9 — AGENT
- Tool chaining, planejamento, execução controlada (sem autonomia irrestrita)

## FASE 10 — JARVIS
- Assistente proativo (configurável), voz (STT/TTS), integrações externas,
  automações, contexto multimodal
