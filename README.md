# Focus API - Backend

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

API REST moderne et sécurisée pour **Focus**, l'application intelligente qui aide les utilisateurs à mesurer et contrôler leur temps passé sur les réseaux sociaux.

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Documentation API](#documentation-api)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Contributions](#contributions)

## Fonctionnalités

### Authentification et Sécurité
- Inscription et connexion avec JWT (JSON Web Tokens)
- Vérification d'email obligatoire
- Réinitialisation de mot de passe sécurisée
- Hachage des mots de passe avec bcrypt
- Système de rôles (user/admin)
- Protection CORS configurable

### Gestion des Utilisateurs
- Profils utilisateurs complets
- Paramètres personnalisables
- Statistiques d'utilisation personnelles
- Gestion des préférences de notification

### Suivi des Activités
- Enregistrement du temps passé sur chaque application
- Statistiques quotidiennes, hebdomadaires et mensuelles
- Catégorisation des applications
- Historique complet des activités

### Blocage Intelligent
- Définition de limites de temps par application
- Blocage automatique après dépassement
- Planification horaire du blocage
- Notifications de rappel (80% de la limite)
- Réinitialisation quotidienne automatique

### Challenges Entre Amis
- Création de challenges personnalisés
- Challenges publics ou privés (avec code d'invitation)
- Système de classement et de scores
- Notifications des résultats par email
- Calcul automatique du gagnant

### Administration
- Tableau de bord complet
- Gestion des utilisateurs (activation/désactivation/suppression)
- Statistiques globales de l'application
- Logs d'audit détaillés
- Monitoring de la santé du système

### Emails Automatiques
- Confirmation de compte
- Réinitialisation de mot de passe
- Rappels quotidiens
- Résumés hebdomadaires
- Résultats des challenges
- Alertes de limite

## Architecture

```
┌─────────────────┐
│   Client Apps   │  (Web, Mobile)
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│   FastAPI App   │  (REST API)
├─────────────────┤
│   Middleware    │  (CORS, Auth, Logs)
├─────────────────┤
│   Routers       │  (Endpoints)
├─────────────────┤
│   Services      │  (Business Logic)
├─────────────────┤
│   Models/ORM    │  (SQLAlchemy)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MySQL DB      │
└─────────────────┘
```

## Technologies

### Backend
- **FastAPI** 0.115.0 - Framework web moderne et rapide
- **Python** 3.11+ - Langage de programmation
- **SQLAlchemy** 2.0+ - ORM pour la base de données
- **Pydantic** 2.9+ - Validation des données

### Base de données
- **MySQL** 8.0+ - Base de données relationnelle
- **Alembic** - Migrations de base de données

### Sécurité
- **python-jose** - JWT (JSON Web Tokens)
- **passlib** + **bcrypt** - Hachage des mots de passe
- **python-dotenv** - Gestion des variables d'environnement

### Emails
- **FastAPI-Mail** - Envoi d'emails
- **Jinja2** - Templates HTML

### Tests
- **pytest** - Framework de tests
- **pytest-asyncio** - Tests asynchrones
- **httpx** - Client HTTP pour les tests

## Installation

### Prérequis

- Python 3.11 ou supérieur
- MySQL 8.0 ou supérieur
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le repository**

```bash
git clone https://github.com/votre-username/focus-backend.git
cd focus-backend
```

2. **Créer un environnement virtuel**

```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

4. **Créer la base de données MySQL**

```bash
mysql -u root -p
CREATE DATABASE focus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'focus_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON focus_db.* TO 'focus_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

5. **Configurer les variables d'environnement**

Créez un fichier `.env` à la racine du projet (voir [Configuration](#configuration))

```bash
cp .env.example .env
# Éditez .env avec vos paramètres
```

6. **Initialiser la base de données**

```bash
# Les tables seront créées automatiquement au premier lancement
python -m app.main
```

## Configuration

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```env
# Application
APP_NAME=Focus API
APP_VERSION=1.0.0
DEBUG=False

# Base de données
DATABASE_URL=mysql+pymysql://focus_user:votre_mot_de_passe@localhost:3306/focus_db
DB_HOST=localhost
DB_PORT=3306
DB_USER=focus_user
DB_PASSWORD=votre_mot_de_passe
DB_NAME=focus_db

# JWT
SECRET_KEY=votre_secret_key_super_securisee_32_caracteres_minimum
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (Gmail)
MAIL_USERNAME=votre-email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe_application
MAIL_FROM=noreply@focusapp.com
MAIL_FROM_NAME=Focus App
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_TLS=True
MAIL_SSL=False

# URLs Frontend
FRONTEND_URL=http://localhost:3000
EMAIL_VERIFY_URL=http://localhost:3000/verify-email
PASSWORD_RESET_URL=http://localhost:3000/reset-password

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:19006

# Admin par défaut
ADMIN_EMAIL=admin@focusapp.com
ADMIN_PASSWORD=AdminSecure123!
ADMIN_USERNAME=admin
```

### Note sur les emails Gmail

Pour utiliser Gmail, vous devez :
1. Activer la validation en 2 étapes
2. Générer un "mot de passe d'application" dans les paramètres de sécurité Google
3. Utiliser ce mot de passe dans `MAIL_PASSWORD`

## Utilisation

### Démarrer le serveur de développement

```bash
# Méthode 1: Directement avec Python
python -m app.main

# Méthode 2: Avec Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Méthode 3: Mode debug
uvicorn app.main:app --reload --log-level debug
```

Le serveur sera accessible sur : `http://localhost:8000`

### Documentation interactive

FastAPI génère automatiquement une documentation interactive :

- **Swagger UI** : http://localhost:8000/api/docs
- **ReDoc** : http://localhost:8000/api/redoc
- **OpenAPI JSON** : http://localhost:8000/api/openapi.json

## Documentation API

### Endpoints principaux

#### Authentification (`/api/auth`)

```http
POST   /api/auth/register              # Inscription
POST   /api/auth/login                 # Connexion
POST   /api/auth/verify-email          # Vérification d'email
POST   /api/auth/resend-verification   # Renvoyer l'email de vérification
POST   /api/auth/forgot-password       # Demander réinitialisation
POST   /api/auth/reset-password        # Réinitialiser le mot de passe
POST   /api/auth/refresh               # Rafraîchir le token
```

#### Utilisateurs (`/api/users`)

```http
GET    /api/users/me                   # Profil actuel
PUT    /api/users/me                   # Mettre à jour le profil
GET    /api/users/me/stats             # Statistiques personnelles
DELETE /api/users/me                   # Supprimer son compte
```

#### Activités (`/api/activities`)

```http
POST   /api/activities                 # Enregistrer une activité
GET    /api/activities                 # Liste des activités
GET    /api/activities/today           # Activités du jour
GET    /api/activities/stats/daily     # Stats quotidiennes
GET    /api/activities/stats/weekly    # Stats hebdomadaires
DELETE /api/activities/{id}            # Supprimer une activité
```

#### Applications bloquées (`/api/blocked`)

```http
POST   /api/blocked                    # Ajouter une app à bloquer
GET    /api/blocked                    # Liste des apps bloquées
GET    /api/blocked/{id}               # Détails d'une app
PUT    /api/blocked/{id}               # Modifier les paramètres
DELETE /api/blocked/{id}               # Retirer du blocage
POST   /api/blocked/{id}/reset         # Réinitialiser le compteur
```

#### Challenges (`/api/challenges`)

```http
POST   /api/challenges                 # Créer un challenge
GET    /api/challenges                 # Liste des challenges
GET    /api/challenges/my-challenges   # Mes challenges
GET    /api/challenges/{id}            # Détails d'un challenge
POST   /api/challenges/{id}/join       # Rejoindre un challenge
POST   /api/challenges/{id}/leave      # Quitter un challenge
GET    /api/challenges/{id}/leaderboard # Classement
DELETE /api/challenges/{id}            # Supprimer (créateur seulement)
```

#### Administration (`/api/admin`)

```http
# Utilisateurs
GET    /api/admin/users                # Liste tous les utilisateurs
GET    /api/admin/users/{id}           # Détails d'un utilisateur
PUT    /api/admin/users/{id}           # Modifier un utilisateur
PATCH  /api/admin/users/{id}/deactivate # Désactiver
PATCH  /api/admin/users/{id}/activate  # Réactiver
DELETE /api/admin/users/{id}           # Supprimer

# Statistiques
GET    /api/admin/stats/overview       # Vue d'ensemble
GET    /api/admin/stats/users-growth   # Croissance des utilisateurs
GET    /api/admin/stats/app-usage      # Usage des applications

# Challenges
GET    /api/admin/challenges           # Tous les challenges
DELETE /api/admin/challenges/{id}      # Supprimer un challenge

# Logs
GET    /api/admin/logs                 # Liste des logs
GET    /api/admin/logs/stats           # Statistiques des logs
DELETE /api/admin/logs/cleanup         # Nettoyer les vieux logs

# Système
GET    /api/admin/system/health        # Santé du système
```

### Authentification

L'API utilise des JWT (Bearer Tokens). Après connexion, incluez le token dans l'en-tête :

```http
Authorization: Bearer <votre_access_token>
```

### Exemples de requêtes

#### Inscription

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

#### Connexion

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

#### Enregistrer une activité

```bash
curl -X POST "http://localhost:8000/api/activities" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "Instagram",
    "app_package": "com.instagram.android",
    "duration_minutes": 45.5,
    "activity_date": "2024-10-30"
  }'
```

## Structure du projet

```
focus_backend/
├── app/
│   ├── main.py                    # Point d'entrée de l'application
│   ├── config.py                  # Configuration et variables d'environnement
│   ├── database.py                # Configuration de la base de données
│   │
│   ├── models/                    # Modèles SQLAlchemy
│   │   ├── __init__.py
│   │   ├── user.py               # Modèle utilisateur
│   │   ├── activity.py           # Modèle activité
│   │   ├── challenge.py          # Modèles challenge et participants
│   │   ├── blocked_app.py        # Modèle app bloquée
│   │   └── log.py                # Modèle logs
│   │
│   ├── schemas/                   # Schémas Pydantic (validation)
│   │   ├── __init__.py
│   │   ├── user_schema.py
│   │   ├── activity_schema.py
│   │   ├── challenge_schema.py
│   │   ├── blocked_schema.py
│   │   └── log_schema.py
│   │
│   ├── routers/                   # Endpoints de l'API
│   │   ├── __init__.py
│   │   ├── auth_router.py        # Authentification
│   │   ├── user_router.py        # Utilisateurs
│   │   ├── activity_router.py    # Activités
│   │   ├── challenge_router.py   # Challenges
│   │   ├── blocked_router.py     # Applications bloquées
│   │   └── admin_router.py       # Administration
│   │
│   ├── services/                  # Logique métier
│   │   ├── __init__.py
│   │   ├── email_service.py      # Envoi d'emails
│   │   ├── challenge_service.py  # Gestion des challenges
│   │   ├── timer_service.py      # Services de timing
│   │   └── log_service.py        # Logging
│   │
│   ├── utils/                     # Utilitaires
│   │   ├── __init__.py
│   │   ├── security.py           # Sécurité (hash, tokens)
│   │   └── jwt_handler.py        # Gestion JWT
│   │
│   └── __init__.py
│
├── logs/                          # Logs de l'application
├── tests/                         # Tests unitaires et d'intégration
├── .env                          # Variables d'environnement (non versionné)
├── .env.example                  # Exemple de configuration
├── .gitignore
├── requirements.txt              # Dépendances Python
└── README.md                     # Ce fichier
```

## Tests

### Lancer les tests

```bash
# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_auth.py
pytest tests/test_challenges.py -v

# Mode verbose
pytest -v -s
```

### Structure des tests

```
tests/
├── conftest.py              # Configuration pytest
├── test_auth.py            # Tests d'authentification
├── test_users.py           # Tests utilisateurs
├── test_activities.py      # Tests activités
├── test_challenges.py      # Tests challenges
└── test_admin.py           # Tests administration
```

## Déploiement

### Avec Docker

```bash
# Build l'image
docker build -t focus-api .

# Lancer le conteneur
docker run -d \
  --name focus-api \
  -p 8000:8000 \
  --env-file .env \
  focus-api
```

### Avec Docker Compose

```bash
docker-compose up -d
```

### Sur un serveur (Production)

1. **Installer les dépendances système**

```bash
sudo apt update
sudo apt install python3.11 python3-pip mysql-server nginx
```

2. **Configurer MySQL**

```bash
sudo mysql_secure_installation
# Créer la base de données et l'utilisateur
```

3. **Cloner et configurer l'application**

```bash
git clone https://github.com/votre-username/focus-backend.git
cd focus-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configurer Gunicorn**

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

5. **Configurer Nginx comme reverse proxy**

```nginx
server {
    listen 80;
    server_name api.focusapp.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

6. **Configurer systemd pour démarrage automatique**

Créer `/etc/systemd/system/focus-api.service`

```ini
[Unit]
Description=Focus API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/focus-backend
Environment="PATH=/var/www/focus-backend/venv/bin"
ExecStart=/var/www/focus-backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable focus-api
sudo systemctl start focus-api
```

## Bonnes Pratiques

- Tous les mots de passe sont hachés avec bcrypt
- Les tokens JWT expirent après 30 minutes (configurable)
- Les emails de vérification expirent après 24 heures
- Les tokens de réinitialisation expirent après 1 heure
- CORS configuré pour les origines autorisées uniquement
- Validation stricte de toutes les entrées avec Pydantic
- Logs détaillés de toutes les actions importantes
- Gestion propre des erreurs avec messages clairs

## Sécurité

### Recommandations

1. **Utilisez HTTPS en production**
2. **Changez les mots de passe par défaut**
3. **Gardez `SECRET_KEY` secret et complexe**
4. **Activez les sauvegardes de la base de données**
5. **Mettez à jour régulièrement les dépendances**
6. **Limitez les tentatives de connexion**
7. **Utilisez des mots de passe forts**

## Contributions

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Support

Pour toute question ou problème :

- **Email** : support@focusapp.com
- **Issues GitHub** : [github.com/votre-username/focus-backend/issues](https://github.com/votre-username/focus-backend/issues)

## Auteurs

- **Votre Nom** - *Développement initial* - [@votre-username](https://github.com/votre-username)

## Remerciements

- FastAPI pour l'excellent framework
- La communauté Python
- Tous les contributeurs

---

**Focus API** - Reprenez le contrôle de votre temps 🎯
