# Dockerfile optimisé pour espace disque limité (Single Stage)
FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/root/.local/bin:$PATH"

# Installation des dépendances système (nettoyage immédiat pour gagner de la place)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie des requirements
COPY requirements.txt .

# 1. Installation PyTorch CPU (Version légère)
RUN pip install --user --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Installation des autres dépendances
RUN pip install --user --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des dossiers nécessaires
RUN mkdir -p audio_outputs chunks_backup

# Exposition du port
EXPOSE 8000

# Health check (plus tolérant pour le démarrage)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Démarrage optimisé pour t3.small (1 worker, timeout long)
CMD ["/root/.local/bin/gunicorn", "api_with_tts:app", \
    "--workers", "1", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "300"]
