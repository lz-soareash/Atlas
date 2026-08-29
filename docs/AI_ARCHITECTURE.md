# AI_ARCHITECTURE

## Provedor (abstração)

```
AIProvider (interface, apps/assistant/providers/base.py)
      ↓
GeminiProvider  (FASE 5, via SDK oficial do Google)
```

Toda regra de negócio depende da **interface**, nunca do SDK. Trocar de provedor
no futuro = implementar a interface, sem tocar em RAG/tools/contexto/memória.

A interface define: `generate_text`, `embed_text`, `embed_texts`.

## RAG

```
PERGUNTA
   ↓
QUERY ANALYSIS
   ↓
RETRIEVAL
   ├── Busca textual
   ├── Busca semântica (pgvector + embeddings Gemini)
   └── Relacionamentos (grafo)
   ↓
CONTEXT BUILDER
   ↓
GEMINI
   ↓
RESPOSTA (com fontes)
```

- Nunca envia o banco inteiro — apenas contexto relevante.
- Resposta com rastreabilidade: `📁 Projeto`, `🧠 Conhecimento`,
  `⚖️ Decisão`, `📝 Experiência`.

## Classificação da resposta

O modelo inicia a resposta com uma tag obrigatória que a API/UI traduzem:

- **`[FATO]`** — informação encontrada no Atlas (fontes).
- **`[INFERÊNCIA]`** — conclusão a partir dos dados (nunca como fato).
- **`[SUGESTÃO]`** — recomendação da IA.
- **`[INFORMAÇÃO EXTERNA]`** — obtida fora do Atlas (rotulada explicitamente).

Fallback heurístico caso o modelo não siga o formato (com fontes → Fato; sem
fontes → Sugestão). Ver `services/chat.py:parse_classification`.

## Embeddings

`EmbeddingProvider → GeminiEmbeddingProvider` (não implementar manualmente).
Vetores em `pgvector`, associados a qualquer entidade do Knowledge Core.

## Tools

A IA **não** acessa o banco diretamente. Ferramentas controladas:

- **Leitura:** `search_knowledge|projects|ideas|questions|decisions|experiences|relationships`,
  `get_entity`, `get_project_context`, `get_entity_history`, `find_related_entities`.
- **Escrita:** `create_idea|question|knowledge|relationship|decision`
  — exigem **confirmação** do usuário.

Toda tool valida autenticação, ownership, permissões, parâmetros e integridade.

## Memória

Modelo `assistant.Memory` (FASE 6), categorias: Preferências, Contexto,
Objetivos, Projetos, Decisões, Experiências. Criadas **explicitamente** pelo
usuário via `/api/memories/`; injetadas como contexto no chat
(`MAX_MEMORIES`). Nada é salvo automaticamente — permanentes são explícitas ou
sugeridas e confirmadas.

## Controle da API Gemini (FASE 5)

Retry controlado, timeout, rate limiting, limites por usuário, controle de
tokens, logs e métricas. Sem loops infinitos e com limite de execução de tools.

## Evolução (Jarvis)

Nível 1 chat → 2 RAG → 3 memória → 4 tools → 5 agente → 6 proativo → 7 voz →
8 integrações. A arquitetura em camadas permite essa evolução sem reescrever
o sistema.
