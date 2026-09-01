"""Whitelist de eventos de integração (Fase 10).

Tipos de evento que o Atlas aceita via POST /api/integration/events/.
A lista é pequena e extensível: para adicionar um novo tipo, basta registrá-lo
aqui (o contrato da API não muda).

Política de segurança: um tipo NÃO listado é rejeitado com erro claro, nunca
processado de forma implícita (anti prompt-injection / eventos desconhecidos).
"""

# Tipos externos (Jarvis → Atlas) aceitos. Palavras-chave em minúsculas.
INTEGRATION_EVENT_TYPES = {
    "jarvis.notify",       # notificação geral do Jarvis para o Atlas
    "jarvis.sync_request", # pedido de sincronização de dados
    "jarvis.status",       # atualização de status/contexto do Jarvis
}

# Tipos que exigem processamento local de escrita (exigem confirmação, via
# ToolProposal) — reservado para evolução futura; hoje nenhum é executado.
WRITE_EVENT_TYPES: set[str] = set()
