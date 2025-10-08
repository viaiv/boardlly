# Scripts de Administração - Tactyo

Scripts utilitários para gerenciar o sistema Tactyo.

## ⚠️ Importante

**SEMPRE ative o ambiente virtual antes de executar qualquer script:**

```bash
cd api
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

## Scripts Disponíveis

### 1. `create_superuser.py`

Cria ou promove superusuários (owners) no sistema.

**Uso:**
```bash
python scripts/create_superuser.py
```

**Funcionalidades:**
- ✅ Criar novo superusuário (owner) com conta própria
- ✅ Promover usuário existente a owner
- ✅ Verifica email automaticamente para superusuários
- ✅ Cria conta automaticamente se necessário

**Quando usar:**
- Criar o primeiro administrador do sistema
- Adicionar novos superusuários
- Promover um admin existente a owner
- Recuperar acesso administrativo ao sistema

**Exemplo de criação:**
```
TACTYO - Criar/Promover Superusuário (Owner)
============================================================

📊 Total de usuários no sistema: 0

ℹ️  Nenhum usuário no sistema. Criando primeiro superusuário...

--- Criar Novo Superusuário ---

Email: admin@empresa.com
Senha (mín. 8 caracteres): ********
Nome (opcional): Administrador
Nome da conta/empresa (opcional): Minha Empresa

✅ Superusuário criado com sucesso!
   Email: admin@empresa.com
   Role: owner
   Conta: Minha Empresa
   Email Verificado: Sim
```

**Exemplo de promoção:**
```
Escolha uma opção:
  [1] Criar novo superusuário
  [2] Promover usuário existente a owner

Opção: 2

--- Promover Usuário Existente ---

Usuários disponíveis:

  [1] user@example.com    | Role: admin      | Verificado: ✓
  [2] dev@example.com     | Role: editor     | Verificado: ✗

Número do usuário para promover a owner: 1

Você está prestes a promover user@example.com para owner (superusuário).
Confirmar? (s/N): s

✅ user@example.com promovido a owner com sucesso!
```

## Hierarquia de Permissões

| Role    | Descrição                                    |
|---------|----------------------------------------------|
| owner   | Superusuário - acesso total ao sistema      |
| admin   | Administrador - gerencia projetos e usuários|
| pm      | Project Manager - gerencia projetos         |
| editor  | Editor - pode modificar itens               |
| viewer  | Visualizador - apenas leitura               |

## Troubleshooting

### Erro: "No module named 'app'"

Certifique-se de:
1. Estar no diretório `api/`
2. Ter ativado o ambiente virtual
3. Ter instalado as dependências: `pip install -r requirements.txt`

### Erro de conexão com banco de dados

Verifique:
1. PostgreSQL está rodando
2. Variável `TACTYO_DATABASE_URL` está configurada no `.env`
3. Banco de dados foi criado
4. Migrations foram aplicadas: `alembic upgrade head`

### Erro: "permission denied"

Torne o script executável:
```bash
chmod +x scripts/create_superuser.py
```

## Boas Práticas

1. **Primeiro Setup**: Sempre crie o primeiro owner usando este script
2. **Segurança**: Use senhas fortes (mínimo 12 caracteres, com símbolos)
3. **Backup**: Faça backup do banco antes de promover usuários em produção
4. **Auditoria**: Documente quando e por que novos owners são criados
5. **Mínimo Privilégio**: Crie owners apenas quando necessário

## Desenvolvimento

Para criar novos scripts de administração:

1. Crie o arquivo em `scripts/`
2. Adicione shebang: `#!/usr/bin/env python3`
3. Torne executável: `chmod +x scripts/nome_do_script.py`
4. Documente neste README
5. Adicione tratamento de erros adequado
6. Use `asyncio` para operações de banco
