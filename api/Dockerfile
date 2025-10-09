# Multi-stage build para otimizar tamanho da imagem

# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar dependências de build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user --timeout=300 -v -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Instalar apenas runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependências Python instaladas do builder
COPY --from=builder /root/.local /root/.local

# Adicionar ao PATH
ENV PATH=/root/.local/bin:$PATH

# Copiar código da aplicação
COPY . .

# Copiar e dar permissão ao entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Criar diretório para SQLite (fallback)
RUN mkdir -p /app/data

# Expor porta
EXPOSE 8000

# Variáveis de ambiente padrão (podem ser sobrescritas no EasyPanel)
# IMPORTANTE: A TACTYO_ENCRYPTION_KEY abaixo é apenas para desenvolvimento!
# SEMPRE sobrescreva em produção com uma chave gerada pelo scripts/generate_secrets.py
#
# NOTA: Não defina TACTYO_CORS_ORIGINS como string vazia!
# - Para usar padrão: não defina a variável
# - Para customizar: defina como "http://site1.com,http://site2.com"
ENV TACTYO_DEBUG=false \
    PYTHONUNBUFFERED=1 \
    TACTYO_ENCRYPTION_KEY=2uQEO8aR7fqVeHQUgZgPCeNj4dAgZsu_VGsSQBeQnoo=

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/')" || exit 1

# Comando para iniciar a aplicação (com migrations automáticas)
CMD ["/app/entrypoint.sh"]
