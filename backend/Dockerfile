# Dockerfile multi-stage pour optimisation
FROM python:3.12-slim as builder

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer répertoire de travail
WORKDIR /app

# Copier requirements et installer les dépendances
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# =============================================================================
# Stage final
# =============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Installer seulement les dépendances runtime nécessaires
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les packages Python depuis le builder
COPY --from=builder /root/.local /root/.local

# Copier le code de l'application
COPY *.py ./
COPY tts_service.py ./
COPY rag_conversational_agent_correction.py ./
COPY complete_rag.py ./
COPY rag_with_gemini.py ./

# Créer les répertoires nécessaires
RUN mkdir -p audio_outputs chunks_backup

# Copier les données (images et documents)
# Note: Pour production, considérer utiliser S3 ou volume monté
COPY Donnees_soutenance ./Donnees_soutenance

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de démarrage avec Gunicorn
CMD ["gunicorn", "api_with_tts:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
