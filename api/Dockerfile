# Multi-stage build para otimizar tamanho da imagem

# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar dependências de build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

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

# Criar diretório para SQLite (fallback)
RUN mkdir -p /app/data

# Expor porta
EXPOSE 8000

# Variáveis de ambiente padrão (podem ser sobrescritas no EasyPanel)
ENV TACTYO_DEBUG=false \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/')" || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
