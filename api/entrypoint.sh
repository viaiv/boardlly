#!/bin/bash
set -e

echo "🚀 Starting Tactyo API..."

# Executar migrations
echo "📦 Running database migrations..."
python -m alembic upgrade head

echo "✅ Migrations completed"

# Iniciar servidor
echo "🌐 Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
