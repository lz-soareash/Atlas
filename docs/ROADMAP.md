# ROADMAP

O Atlas evolui em 10 fases, sempre com base funcional e testada.

## FASE 1 — FOUNDATION ✅ (implementada)
- [x] Django + estruturas de settings (`base`/`local`/`production`)
- [x] PostgreSQL (+ pgvector) e SQLite local configuráveis
- [x] Docker Compose (db com pgvector, backend)
- [x] JWT (SimpleJWT): registro, login, refresh, `/me`
- [x] `accounts` (User por e-mail, UUID), throttling, permissões
- [x] `core` (modelos base: UUID, timestamps, soft delete, owner)
- [x] `audit` (AuditLog + redação de secrets)
- [x] Frontend HTML/CSS/JS puro servido pelo Django (SPA por hash)
- [x] Testes (auth, segurança, soft delete) — 20 verdes

## FASE 2 — KNOWLEDGE CORE ✅ (implementada)
- [x] Entidades: Knowledge, Ideas, Projects, Questions, Decisions, Experiences
- [x] CRUD, permissões por owner, soft delete, histórico de transformações
      (Ideia → Projeto, Pergunta → Conhecimento)
- [x] Migrações + 56 novos testes (total 76 verdes)
- [x] Frontend: páginas de listagem/criação por entidade

## FASE 3 — RELATIONSHIPS E GRAFO ✅ (implementada)
- [x] Modelo genérico `Relationship` (GenericForeignKey origin/target, owner)
- [x] Tipos configuráveis (RELACIONADO_A, USA, DEPENDE_DE, ORIGINOU, INSPIROU,
      PARTICIPA_DE, RESOLVE, RESPONDE, AFETA, GEROU, APRENDEU_COM)
- [x] CRUD de relacionamentos com validação de owner (anti-IDOR) e unicidade
- [x] API `GET /api/graph/` → `{nodes, edges}`
- [x] Frontend: página de grafo (visualização SVG) + criação de relacionamentos
- [x] Migrações + 14 testes novos (total 95 verdes)

## FASE 4 — SEARCH + EMBEDDINGS ✅ (implementada)
- [x] Busca textual + filtros + ordenação/ranking de relevância multi-entidade
- [x] `EmbeddingProvider` (contrato) → `GeminiEmbeddingProvider` (google.genai,
      por `GEMINI_API_KEY`) + `FingerprintEmbeddingProvider` (fallback
      determinístico, sem API)
- [x] `GET /api/search/` unificado sobre as 6 entidades, isolado por owner
- [x] Combinação textual + semântica (score híbrido) quando provider disponível
- [x] Frontend: página de Busca (`/busca`)
- [x] Migrações não necessárias + 16 testes novos (total 111 verdes)

## FASE 5 — GEMINI CORE ✅ (implementada)
- [x] `AIProvider → GeminiProvider` (implementação via SDK oficial)
- [x] `services/` (chat, context) — chat RAG com fontes rastreáveis e
      classificação da resposta
- [x] Prompts, tratamento de erros, retry, timeout, rate limit, controle de tokens
- [x] `POST /api/assistant/chat/` + frontend do Assistente
- [x] Migrações não necessárias + 22 testes novos (total 133 verdes)

## FASE 6 — ATLAS ASSISTANT ✅ (implementada)
- [x] Chat com RAG real (Retrieval → Context Builder → Gemini) — Fase 5
- [x] Fontes/rastreabilidade (📁 Projeto, 🧠 Conhecimento, ⚖️ Decisão, 📝 Experiência)
- [x] Classificação Fato/Inferência/Sugestão/Informação externa (tag obrigatória)
- [x] Memória (Preferências, Contexto, Objetivos, Projetos, Decisões,
      Experiências; explícitas pelo usuário)
- [x] Migração `0001_initial` + 10 testes novos (total 143 verdes)

## FASE 7 — TOOLS ✅ (implementada)
- [x] Leitura: search_*, get_entity, get_project_context, find_related_entities
- [x] Escrita: create_* (exigem confirmação do usuário, via ToolProposal)
- [x] Validação de autenticação/ownership/permissões/integridade
- [x] Migração `0002_toolproposal` + 11 testes novos (total 154 verdes)

## FASE 8 — INTELLIGENCE ✅ (implementada)
- [x] Inbox inteligente (classificação sugere tipo/destino; nada automático)
- [x] Detecção de duplicatas (sem merge automático)
- [x] Sugestão de relacionamentos
- [x] Gap Analysis (tópicos sem Conhecimento dedicado)
- [x] Camada de produtividade/conselho (`/api/intelligence/insights/`):
      perguntas em aberto, ideias pendentes, erros sem solução, decisões
      pendentes, itens negligenciados
- [x] Migração `0001_initial` + 10 testes (total 164 verdes)

## FASE 9 — AGENT
- Tool chaining, planejamento, execução controlada (sem autonomia irrestrita)

## FASE 10 — JARVIS
- Assistente proativo (configurável), voz (STT/TTS), integrações externas,
  automações, contexto multimodal
