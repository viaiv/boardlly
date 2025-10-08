# Configuração de Email (SMTP)

O Tactyo envia emails de notificação para convites de projeto. Esta funcionalidade é **opcional** - se não configurada, os convites continuam funcionando normalmente, mas sem notificação por email.

## Variáveis de Ambiente

Adicione as seguintes variáveis no arquivo `api/.env`:

```bash
# SMTP Configuration
TACTYO_SMTP_HOST=smtp.gmail.com
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=seu-email@gmail.com
TACTYO_SMTP_PASSWORD=sua-senha-de-app
TACTYO_SMTP_FROM_EMAIL=noreply@tactyo.com
TACTYO_SMTP_FROM_NAME=Tactyo
TACTYO_SMTP_USE_TLS=true

# Frontend URL (usado nos links dos emails)
TACTYO_FRONTEND_URL=https://tactyo.viaiv.com.br
```

## Configuração por Provedor

### Gmail

1. **Ative a verificação em 2 etapas** na sua conta Google
2. **Gere uma senha de app**:
   - Acesse: https://myaccount.google.com/apppasswords
   - Crie uma nova senha de app para "Mail"
   - Use essa senha no `TACTYO_SMTP_PASSWORD`

```bash
TACTYO_SMTP_HOST=smtp.gmail.com
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=seu-email@gmail.com
TACTYO_SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # senha de app gerada
TACTYO_SMTP_USE_TLS=true
```

### Outlook/Hotmail

```bash
TACTYO_SMTP_HOST=smtp-mail.outlook.com
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=seu-email@outlook.com
TACTYO_SMTP_PASSWORD=sua-senha
TACTYO_SMTP_USE_TLS=true
```

### SendGrid

```bash
TACTYO_SMTP_HOST=smtp.sendgrid.net
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=apikey
TACTYO_SMTP_PASSWORD=sua-api-key-do-sendgrid
TACTYO_SMTP_FROM_EMAIL=noreply@seudominio.com
TACTYO_SMTP_USE_TLS=true
```

### Mailgun

```bash
TACTYO_SMTP_HOST=smtp.mailgun.org
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=postmaster@seu-dominio.mailgun.org
TACTYO_SMTP_PASSWORD=sua-senha-smtp-do-mailgun
TACTYO_SMTP_FROM_EMAIL=noreply@seudominio.com
TACTYO_SMTP_USE_TLS=true
```

### Amazon SES

```bash
TACTYO_SMTP_HOST=email-smtp.us-east-1.amazonaws.com  # ajuste região
TACTYO_SMTP_PORT=587
TACTYO_SMTP_USER=suas-credenciais-iam-smtp
TACTYO_SMTP_PASSWORD=sua-senha-smtp
TACTYO_SMTP_FROM_EMAIL=noreply@seudominio.com  # precisa estar verificado no SES
TACTYO_SMTP_USE_TLS=true
```

## Quando os Emails São Enviados

- **Convite para projeto**: Quando um admin/owner convida alguém para um projeto
  - Email contém link para visualizar convites pendentes
  - Se a pessoa não tem conta, é orientada a criar uma com o email convidado

## Comportamento Sem SMTP Configurado

Se `TACTYO_SMTP_HOST` não estiver definido:
- Os convites são criados normalmente no banco de dados
- Nenhum email é enviado
- Log mostra: `⚠️  SMTP não configurado. Email NÃO foi enviado.`
- Usuários precisam verificar manualmente em "Convites Recebidos"

## Testando o Envio de Emails

Após configurar, crie um convite de projeto para verificar se o email é enviado corretamente:

1. Acesse as configurações do projeto
2. Vá em "Membros"
3. Adicione um novo membro usando um email de teste
4. Verifique a caixa de entrada do email convidado
5. Verifique os logs do backend para mensagens de sucesso/erro

## Troubleshooting

### Email não está sendo enviado

1. **Verifique os logs do backend**:
   ```bash
   docker logs tactyo-api
   # ou
   tail -f api/logs/app.log
   ```

2. **Verifique se o SMTP_HOST está definido**:
   ```bash
   echo $TACTYO_SMTP_HOST
   ```

3. **Teste as credenciais manualmente**:
   ```bash
   # No container da API:
   python -c "from app.services.email import send_email; import asyncio; asyncio.run(send_email('seu-email@teste.com', 'Teste', '<h1>Teste</h1>'))"
   ```

### Erro de autenticação

- Verifique se a senha está correta
- Para Gmail, certifique-se de usar senha de app (não a senha normal da conta)
- Verifique se a conta permite acesso SMTP

### Emails vão para spam

- Configure SPF, DKIM e DMARC no seu domínio
- Use um provedor de email transacional (SendGrid, Mailgun, SES)
- Verifique se o `TACTYO_SMTP_FROM_EMAIL` usa um domínio que você controla

## Próximos Passos

Funcionalidades planejadas:
- Templates personalizáveis
- Notificações por email para atualizações de itens
- Digest semanal de atividades do projeto
- Confirmação de leitura de convites
