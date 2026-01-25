#!/bin/bash

# =============================================================================
# Script de déploiement automatisé pour AWS EC2
# Usage: ./deploy.sh [production|staging]
# =============================================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
APP_NAME="benin-heritage-api"
DOCKER_IMAGE="$APP_NAME:latest"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Déploiement Backend - Patrimoine Béninois${NC}"
echo -e "${GREEN}Environnement: $ENVIRONMENT${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Vérifier que .env existe
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env introuvable!${NC}"
    echo -e "${YELLOW}Créez un fichier .env avec vos variables d'environnement${NC}"
    exit 1
fi

# Charger les variables d'environnement
source .env

# Vérifier les variables critiques
if [ -z "$PINECONE_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}❌ Variables d'environnement manquantes!${NC}"
    echo -e "${YELLOW}Vérifiez PINECONE_API_KEY et GEMINI_API_KEY dans .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Variables d'environnement chargées${NC}\n"

# Étape 1: Arrêter les conteneurs existants
echo -e "${YELLOW}🛑 Arrêt des conteneurs existants...${NC}"
docker compose down || true
echo -e "${GREEN}✅ Conteneurs arrêtés${NC}\n"

# Étape 2: Build de l'image Docker
echo -e "${YELLOW}🔨 Build de l'image Docker...${NC}"
docker build -t $DOCKER_IMAGE . --no-cache
echo -e "${GREEN}✅ Image construite: $DOCKER_IMAGE${NC}\n"

# Étape 3: Démarrer les conteneurs
echo -e "${YELLOW}🚀 Démarrage des conteneurs...${NC}"
docker compose up -d
echo -e "${GREEN}✅ Conteneurs démarrés${NC}\n"

# Étape 4: Attendre que l'API soit prête
echo -e "${YELLOW}⏳ Attente du démarrage de l'API...${NC}"
sleep 10

# Étape 5: Health check
echo -e "${YELLOW}🏥 Vérification de la santé de l'API...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API opérationnelle!${NC}\n"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT+1))
        echo -e "${YELLOW}Tentative $RETRY_COUNT/$MAX_RETRIES...${NC}"
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ L'API ne répond pas après $MAX_RETRIES tentatives${NC}"
    echo -e "${YELLOW}Vérifiez les logs: docker-compose logs -f${NC}"
    exit 1
fi

# Étape 6: Afficher les informations
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Déploiement réussi!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}📊 Informations:${NC}"
echo -e "  - API URL: http://localhost:8000"
echo -e "  - Documentation: http://localhost:8000/docs"
echo -e "  - Health Check: http://localhost:8000/health"
echo -e ""

echo -e "${YELLOW}📝 Commandes utiles:${NC}"
echo -e "  - Voir les logs: ${GREEN}docker compose logs -f${NC}"
echo -e "  - Arrêter: ${GREEN}docker compose down${NC}"
echo -e "  - Redémarrer: ${GREEN}docker compose restart${NC}"
echo -e "  - Status: ${GREEN}docker compose ps${NC}"
echo -e ""

# Afficher les logs en temps réel (optionnel)
read -p "Voulez-vous voir les logs en temps réel? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose logs -f
fi
