#!/bin/bash

# Script de démarrage rapide pour Focus API
# Usage: ./start.sh [dev|prod]

MODE="${1:-dev}"

echo "=========================================="
echo "  Démarrage de Focus API - Mode: $MODE"
echo "=========================================="

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vérification de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Environnement virtuel non trouvé. Création en cours...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Erreur lors de la création de l'environnement virtuel${NC}"
        exit 1
    fi
    echo -e "${GREEN}Environnement virtuel créé avec succès${NC}"
fi

# Activation de l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Installation/mise à jour des dépendances
echo "Vérification des dépendances..."
pip install -r requirements.txt --quiet

# Vérification du fichier .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Fichier .env non trouvé${NC}"
    if [ -f ".env.example" ]; then
        echo "Copie de .env.example vers .env..."
        cp .env.example .env
        echo -e "${RED}ATTENTION: Veuillez configurer le fichier .env avant de continuer${NC}"
        echo "Édition du fichier .env..."
        sleep 2
        ${EDITOR:-nano} .env
    else
        echo -e "${RED}Erreur: .env.example non trouvé${NC}"
        exit 1
    fi
fi

# Création du dossier logs si nécessaire
if [ ! -d "logs" ]; then
    echo "Création du dossier logs..."
    mkdir -p logs
fi

# Lancement du serveur selon le mode
echo ""
echo "=========================================="
if [ "$MODE" = "prod" ]; then
    echo "  Mode PRODUCTION"
    echo "=========================================="
    echo "Démarrage avec Gunicorn..."

    # Vérification de Gunicorn
    if ! command -v gunicorn &> /dev/null; then
        echo "Installation de Gunicorn..."
        pip install gunicorn
    fi

    gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info
else
    echo "  Mode DÉVELOPPEMENT"
    echo "=========================================="
    echo ""
    echo -e "${GREEN}Serveur disponible sur: http://localhost:8000${NC}"
    echo -e "${GREEN}Documentation Swagger: http://localhost:8000/api/docs${NC}"
    echo -e "${GREEN}Documentation ReDoc: http://localhost:8000/api/redoc${NC}"
    echo ""
    echo "Appuyez sur CTRL+C pour arrêter le serveur"
    echo ""

    # Lancement avec Uvicorn en mode reload
    uvicorn app.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info
fi
