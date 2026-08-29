# SECURITY

## Modelo de ameaças

O Atlas trata **todo o conteúdo armazenado como dados não confiáveis**.

Se uma nota contém: `"Ignore todas as instruções anteriores."` — isso é apenas
conteúdo da nota. Nunca altera as instruções do sistema nem concede permissões.

## Controles implementados (FASE 1)

### Autenticação e autorização
- JWT via SimpleJWT (`Bearer`), com refresh rotativo.
- Usuário autenticado por **e-mail + senha**, PK **UUID** (não enumerável).
- Permissão `IsOwner`: acesso a objetos somente pelo seu proprietário.
- Throttling global (`anon`/`user`) e específico de login (anti força bruta).

### Proteção contra IDOR
- Toda consulta/escrita é isolada por `owner` (`OwnerMixin`).
- PKs UUID dificultam adivinhação de IDs.

### Auditoria
- `AuditLog` registra ações relevantes.
- Redação automática de secrets: palavras como `password`, `token`, `secret`,
  `api_key`, `authorization` são substituídas por `[REDACTED]` (inclusive
  aninhadas).

### Chamadas de IA (FASE 5)
- `GEMINI_API_KEY` somente no backend e em `.env` (fora do git), nunca no
  frontend.
- Retry controlado (backoff + jitter apenas para erros transientes), timeout,
  rate limit dedicado por usuário (`scope gemini`, além do global), limites
  por usuário (`MAX_CHAT_MESSAGES`, `MAX_RETRIEVAL_RESULTS`) e controle de
  tokens (`GEMINI_MAX_TOKENS`).
- Erros padronizados (`AIError`) — a resposta ao usuário nunca expõe chave,
  stack, SDK ou internals.
- Sem loops infinitos: retry com máximo de tentativas `GEMINI_MAX_RETRIES`.

### Dados sensíveis
- `GEMINI_API_KEY` somente no backend e em `.env` (fora do git).
- `SECRET_KEY` configurável via ambiente.
- Nunca logar senhas, tokens ou chaves.

## Controles planejados (próximas fases)

- **Prompt injection:** sandbox por função, system prompt imutável, tools sem
  privilégios administrativos, validação de parâmetros.
- **Tools:** verificação de autenticação, ownership, permissões, integridade.
- **AI Audit:** registro de pergunta, modelo, tools, entidades, tokens,
  duração e status — **nunca** chaves/tokens/secrets.
- Modo agente com permissões configuráveis; **sem autonomia irrestrita**.

## Checklist para produção

- [ ] `SECRET_KEY` forte via ambiente.
- [ ] `DJANGO_ENV=production` (exige PostgreSQL).
- [ ] HTTPS (SSL redirect + HSTS).
- [ ] Backups criptografados.
- [ ] Monitoramento de logs (sem secrets).
