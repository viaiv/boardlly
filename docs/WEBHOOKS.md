# Configuração de Webhooks do GitHub

Este guia explica como configurar webhooks do GitHub para sincronização em tempo real de Projects, Issues e Pull Requests.

## 📋 Pré-requisitos

1. Acesso de administrador ao repositório/organização no GitHub
2. Tactyo API rodando e acessível publicamente (ou via ngrok/tunnel)
3. Variável de ambiente `TACTYO_WEBHOOK_SECRET` configurada

## 🔐 1. Configurar Webhook Secret

### Gerar Secret

```bash
# Gerar secret aleatório (32 bytes em hex)
openssl rand -hex 32
```

### Configurar no Tactyo

Adicione ao arquivo `.env` da API:

```env
TACTYO_WEBHOOK_SECRET=seu_secret_gerado_acima
```

**⚠️ Importante:** Use o MESMO secret no GitHub (passo 2.4)

## 🔧 2. Criar Webhook no GitHub

### Para Repositório

1. Vá em **Settings** → **Webhooks** → **Add webhook**
2. Configure:
   - **Payload URL**: `https://seu-dominio.com/api/github/webhooks`
   - **Content type**: `application/json`
   - **Secret**: Cole o secret gerado no passo 1
   - **SSL verification**: ✅ Enable (recomendado)

3. **Which events would you like to trigger this webhook?**
   - Selecione "Let me select individual events"
   - Marque:
     - ✅ **Issues** (opened, edited, closed, reopened)
     - ✅ **Pull requests** (opened, closed, merged, edited)
     - ✅ **Project cards** (created, moved, deleted)

4. Clique **Add webhook**

### Para Organização

1. Vá em **Settings** (da organização) → **Webhooks** → **Add webhook**
2. Siga os mesmos passos acima
3. ⚠️ Webhooks de organização afetam TODOS os repositórios

## 📡 3. Testar Webhook

### Via GitHub UI

1. Vá em **Settings** → **Webhooks** → Selecione seu webhook
2. Vá na aba **Recent Deliveries**
3. Clique em **Redeliver** em uma entrega existente
4. Ou crie/edite uma Issue para gerar novo evento

### Via curl (desenvolvimento local)

```bash
# Simular evento de issue criada
curl -X POST http://localhost:8000/api/github/webhooks \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: test-delivery-123" \
  -H "X-Hub-Signature-256: sha256=$(echo -n '{"action":"opened"}' | openssl dgst -sha256 -hmac 'seu_secret' | cut -d' ' -f2)" \
  -d '{"action":"opened","issue":{"node_id":"test"}}'
```

## 🔍 4. Verificar Logs

### Logs da API

```bash
# Ver logs do webhook
tail -f api/logs/tactyo.log | grep webhook
```

Logs esperados:
- ✅ `Received GitHub webhook: event=issues, action=opened`
- ✅ `Successfully processed issues webhook`
- ❌ `Webhook signature mismatch` → Secret incorreto

### Logs no GitHub

1. **Settings** → **Webhooks** → Seu webhook
2. Aba **Recent Deliveries**
3. Clique em uma entrega para ver:
   - Request headers e payload
   - Response status e body
   - Redelivery (para retry manual)

## 📊 5. Eventos Suportados

| Evento | Ação | O que acontece |
|--------|------|----------------|
| `project_v2_item` | `created` | Sincroniza projeto quando item é adicionado |
| `project_v2_item` | `edited` | Atualiza campos do item (status, iteration, etc) |
| `project_v2_item` | `deleted` | Remove item do banco local |
| `issues` | `opened` | Sincroniza projeto se issue está no projeto |
| `issues` | `edited` | Atualiza título, descrição, labels |
| `issues` | `closed` | Atualiza status |
| `pull_request` | `opened` | Sincroniza PR adicionado ao projeto |
| `pull_request` | `closed` | Atualiza status (merged ou closed) |

## 🛡️ 6. Segurança

### Validação HMAC-SHA256

Todos os webhooks são validados com HMAC-SHA256:

```python
# Validação automática no endpoint
verify_webhook_signature(payload_bytes, signature, secret)
```

### Headers de Segurança

Sempre verifique:
- ✅ `X-Hub-Signature-256` está presente
- ✅ Signature corresponde ao payload
- ✅ SSL habilitado (produção)

### Rate Limiting

GitHub pode enviar múltiplos webhooks rapidamente. O Tactyo:
- Processa webhooks de forma assíncrona
- Não bloqueia threads
- Retorna 200 rapidamente para evitar timeout

## ⚡ 7. Performance

### Estratégia de Sincronização

**Para `project_v2_item` events:**
- Sincroniza projeto completo (mais simples)
- Alternativa: Atualizar apenas item específico (implementação futura)

**Para `issues` e `pull_request`:**
- Busca item no banco pelo `node_id`
- Sincroniza apenas projetos afetados

### Evitar Loops

- Webhook NÃO dispara quando Tactyo cria Issues
- Apenas eventos externos (via GitHub UI ou API externa)

## 🚨 8. Troubleshooting

### Webhook não está sendo disparado

- ✅ Verifique eventos selecionados no GitHub
- ✅ Teste com "Redeliver" no GitHub
- ✅ Verifique se API está acessível publicamente

### Erro 401 (Unauthorized)

- ❌ Secret no `.env` diferente do configurado no GitHub
- ❌ Formato de assinatura inválido

### Erro 500 (Internal Server Error)

- ❌ `TACTYO_WEBHOOK_SECRET` não configurado
- ❌ Erro no handler (verifique logs)

### Evento ignorado

```json
{"status": "ignored", "reason": "Event type 'push' not supported"}
```

- ℹ️ Normal para eventos não implementados
- Webhook retorna 200 para evitar retry

## 📖 9. Desenvolvimento Local

### Expor localhost com ngrok

```bash
# Instalar ngrok
brew install ngrok  # ou baixe de https://ngrok.com

# Expor porta 8000
ngrok http 8000

# Use a URL gerada no webhook:
# https://abc123.ngrok.io/api/github/webhooks
```

### Alternativa: Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

## 📚 10. Referências

- [GitHub Webhooks Documentation](https://docs.github.com/en/webhooks)
- [Securing Webhooks](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
- [GraphQL API Events](https://docs.github.com/en/graphql/reference/objects#projectv2item)

---

**Dúvidas?** Abra uma issue no [GitHub](https://github.com/viaiv/tactyo/issues)
