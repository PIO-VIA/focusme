# Guide de démarrage rapide - Focus API

Ce guide vous permettra de démarrer rapidement avec le backend Focus API.

## Démarrage en 5 minutes

### 1. Prérequis

Assurez-vous d'avoir installé :
- Python 3.11 ou supérieur
- MySQL 8.0 ou supérieur
- pip (gestionnaire de paquets Python)

### 2. Installation rapide

```bash
# Cloner le repository
git clone https://github.com/votre-username/focus-backend.git
cd focus-backend

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Copier le fichier d'environnement
cp .env.example .env
```

### 3. Configuration de la base de données

#### Option A: MySQL local

```bash
# Se connecter à MySQL
mysql -u root -p

# Créer la base de données
CREATE DATABASE focus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'focus_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON focus_db.* TO 'focus_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Option B: Docker

```bash
# Lancer MySQL avec Docker
docker run -d \
  --name focus_mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=focus_db \
  -e MYSQL_USER=focus_user \
  -e MYSQL_PASSWORD=password \
  -p 3306:3306 \
  mysql:8.0
```

### 4. Configurer le fichier .env

Éditez le fichier `.env` et modifiez au minimum ces variables :

```env
# Base de données
DATABASE_URL=mysql+pymysql://focus_user:votre_mot_de_passe@localhost:3306/focus_db
DB_PASSWORD=votre_mot_de_passe

# Secret key (générer une clé sécurisée)
SECRET_KEY=votre_cle_secrete_minimum_32_caracteres

# Email (si vous voulez tester les emails)
MAIL_USERNAME=votre-email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe_application
```

### 5. Lancer l'application

#### Méthode 1: Script automatique (recommandé)

```bash
./start.sh
```

#### Méthode 2: Uvicorn directement

```bash
uvicorn app.main:app --reload
```

#### Méthode 3: Python

```bash
python -m app.main
```

### 6. Tester l'API

L'API est maintenant accessible sur :
- **API** : http://localhost:8000
- **Documentation Swagger** : http://localhost:8000/api/docs
- **ReDoc** : http://localhost:8000/api/redoc

## Premier test

### Via Swagger UI

1. Ouvrez http://localhost:8000/api/docs
2. Testez l'endpoint `/api/health` pour vérifier que tout fonctionne

### Via cURL

```bash
# Vérifier la santé de l'API
curl http://localhost:8000/api/health

# S'inscrire
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'

# Se connecter
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

## Compte administrateur

Un compte administrateur est créé automatiquement au premier lancement :

- **Email** : admin@focusapp.com
- **Mot de passe** : AdminSecure123!

Vous pouvez modifier ces identifiants dans le fichier `.env` avant le premier lancement.

## Configuration des emails

Pour tester l'envoi d'emails (vérification de compte, réinitialisation de mot de passe, etc.) :

### Gmail

1. Allez dans les paramètres de sécurité Google
2. Activez la validation en 2 étapes
3. Générez un "mot de passe d'application"
4. Utilisez ce mot de passe dans `MAIL_PASSWORD` du fichier `.env`

### MailHog (pour le développement)

```bash
# Lancer MailHog avec Docker
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Modifier .env
MAIL_SERVER=localhost
MAIL_PORT=1025
```

Interface web : http://localhost:8025

## Démarrage avec Docker Compose

La façon la plus simple pour tout avoir (API + MySQL) :

```bash
# Créer le fichier .env
cp .env.example .env

# Lancer tout
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

## Structure des endpoints

Voici les principaux endpoints disponibles :

### Authentification
- `POST /api/auth/register` - Inscription
- `POST /api/auth/login` - Connexion
- `POST /api/auth/verify-email` - Vérification d'email
- `POST /api/auth/forgot-password` - Mot de passe oublié

### Utilisateurs
- `GET /api/users/me` - Mon profil
- `PUT /api/users/me` - Mettre à jour mon profil
- `GET /api/users/me/stats` - Mes statistiques

### Activités
- `POST /api/activities` - Enregistrer une activité
- `GET /api/activities` - Liste de mes activités
- `GET /api/activities/today` - Activités du jour
- `GET /api/activities/stats/daily` - Statistiques quotidiennes

### Applications bloquées
- `POST /api/blocked` - Ajouter une app à bloquer
- `GET /api/blocked` - Liste des apps bloquées
- `PUT /api/blocked/{id}` - Modifier les paramètres

### Challenges
- `POST /api/challenges` - Créer un challenge
- `GET /api/challenges` - Liste des challenges
- `POST /api/challenges/{id}/join` - Rejoindre un challenge
- `GET /api/challenges/{id}/leaderboard` - Classement

### Administration (nécessite rôle admin)
- `GET /api/admin/users` - Tous les utilisateurs
- `GET /api/admin/stats/overview` - Statistiques globales
- `GET /api/admin/logs` - Logs d'audit

## Problèmes courants

### Erreur de connexion MySQL

```
Error connecting to database
```

**Solution** : Vérifiez que MySQL est démarré et que les identifiants dans `.env` sont corrects.

### Erreur "Module not found"

```
ModuleNotFoundError: No module named 'app'
```

**Solution** : Assurez-vous d'être dans le bon répertoire et que l'environnement virtuel est activé.

### Port 8000 déjà utilisé

```
Address already in use
```

**Solution** : Tuez le processus existant ou changez le port :

```bash
# Trouver le processus
lsof -i :8000

# Le tuer
kill -9 <PID>

# Ou utiliser un autre port
uvicorn app.main:app --reload --port 8001
```

### Emails non envoyés

Si les emails ne sont pas envoyés, vérifiez :
1. Que `MAIL_USERNAME` et `MAIL_PASSWORD` sont corrects
2. Que vous avez généré un "mot de passe d'application" pour Gmail
3. Les logs pour voir l'erreur exacte

## Développement

### Mode debug

Activez le mode debug dans `.env` :

```env
DEBUG=True
```

Cela activera :
- Logs détaillés
- Rechargement automatique du code
- Messages d'erreur complets dans les réponses

### Tests

```bash
# Lancer tous les tests
pytest

# Avec couverture
pytest --cov=app

# Tests spécifiques
pytest tests/test_auth.py -v
```

### Logs

Les logs sont stockés dans le dossier `logs/` :
- `logs/app.log` - Tous les logs de l'application
- Format JSON pour faciliter l'analyse

## Ressources

- **Documentation complète** : Voir [README.md](README.md)
- **Documentation API** : http://localhost:8000/api/docs
- **Code source** : Structure dans `app/`

## Prochaines étapes

1. Explorez la documentation Swagger
2. Testez les différents endpoints
3. Créez des utilisateurs de test
4. Lancez un challenge entre amis
5. Consultez les statistiques dans l'interface admin

## Support

Si vous rencontrez des problèmes :
1. Vérifiez ce guide
2. Consultez les logs dans `logs/app.log`
3. Ouvrez une issue sur GitHub
4. Contactez support@focusapp.com

---

**Bon développement !** 🚀
