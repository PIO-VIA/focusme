## Guide - CI/CD, OAuth Google & WebSocket

Ce guide explique comment utiliser le CI/CD avec GitHub Actions, l'authentification OAuth Google et les notifications temps réel via WebSocket.

## Table des matières

- [CI/CD avec GitHub Actions](#cicd-avec-github-actions)
- [OAuth Google](#oauth-google)
- [WebSocket Notifications](#websocket-notifications)
- [Exemples d'utilisation](#exemples-dutilisation)

---

## CI/CD avec GitHub Actions

### Workflows disponibles

Le projet inclut 2 workflows GitHub Actions :

#### 1. **CI (Continuous Integration)** - `.github/workflows/ci.yml`

Déclenché sur :
- Push sur `main` ou `develop`
- Pull requests vers `main` ou `develop`

**Jobs exécutés :**

1. **Test** :
   - Linting avec `black` et `flake8`
   - Type checking avec `mypy`
   - Tests unitaires avec `pytest`
   - Couverture de code avec `codecov`
   - Services : MySQL + Redis

2. **Security** :
   - Scan des dépendances avec `safety`
   - Analyse de sécurité avec `bandit`

3. **Docker** :
   - Build de l'image Docker
   - Test du conteneur

#### 2. **CD (Continuous Deployment)** - `.github/workflows/cd.yml`

Déclenché sur :
- Push sur `main`
- Tags `v*` (releases)

**Jobs exécutés :**

1. **Deploy** :
   - Build et push de l'image Docker
   - Déploiement sur le serveur via SSH
   - Nettoyage Docker

2. **Release** :
   - Génération du changelog
   - Création de la release GitHub

3. **Notify** :
   - Notifications Slack

### Configuration des secrets GitHub

Allez dans **Settings > Secrets and variables > Actions** et ajoutez :

```
DOCKER_USERNAME         # Votre username Docker Hub
DOCKER_PASSWORD         # Votre password/token Docker Hub
SERVER_HOST             # IP ou domaine de votre serveur
SERVER_USERNAME         # Username SSH
SERVER_SSH_KEY          # Clé privée SSH
SLACK_WEBHOOK           # Webhook Slack (optionnel)
```

### Badges pour le README

```markdown
![CI](https://github.com/votre-username/focus-backend/workflows/CI/badge.svg)
![CD](https://github.com/votre-username/focus-backend/workflows/CD/badge.svg)
[![codecov](https://codecov.io/gh/votre-username/focus-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/votre-username/focus-backend)
```

### Déploiement manuel

```bash
# Créer un tag pour déclencher le déploiement
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## OAuth Google

### Configuration Google Cloud

#### 1. Créer un projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet : "Focus API"
3. Activez l'**OAuth consent screen**

#### 2. Configurer OAuth 2.0

1. Allez dans **APIs & Services > Credentials**
2. Cliquez sur **Create Credentials > OAuth client ID**
3. Type d'application : **Web application**
4. Nom : "Focus API OAuth"

5. **Authorized redirect URIs** :
   ```
   http://localhost:8000/api/auth/google/callback
   https://votre-domaine.com/api/auth/google/callback
   ```

6. Récupérez :
   - **Client ID**
   - **Client secret**

#### 3. Configuration dans `.env`

```env
# Activer OAuth
OAUTH_ENABLED=True

# Credentials Google
GOOGLE_CLIENT_ID=123456789-xxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

### Utilisation de l'API OAuth

#### 1. Initier la connexion

```bash
# Récupérer l'URL d'autorisation
curl http://localhost:8000/api/auth/google

# Réponse:
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token"
}
```

Le frontend doit rediriger l'utilisateur vers `authorization_url`.

#### 2. Callback

Après autorisation, Google redirige vers :
```
http://localhost:8000/api/auth/google/callback?code=xxx&state=yyy
```

L'API :
- Échange le code contre un token Google
- Récupère les infos utilisateur
- Crée ou connecte l'utilisateur
- Retourne des JWT tokens

#### 3. Réponse

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "username": "john_doe",
    "email": "john@gmail.com",
    "full_name": "John Doe",
    "avatar_url": "https://lh3.googleusercontent.com/..."
  }
}
```

### Exemple frontend (JavaScript)

```javascript
// 1. Initier la connexion
async function loginWithGoogle() {
  const response = await fetch('http://localhost:8000/api/auth/google');
  const data = await response.json();

  // Stocker le state pour vérification
  localStorage.setItem('oauth_state', data.state);

  // Rediriger vers Google
  window.location.href = data.authorization_url;
}

// 2. Gérer le callback (dans une route /auth/google/callback)
async function handleGoogleCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');

  // Vérifier le state
  const storedState = localStorage.getItem('oauth_state');
  if (state !== storedState) {
    console.error('Invalid state');
    return;
  }

  // L'API gère automatiquement l'échange de code
  // Les tokens sont retournés dans la réponse
  const response = await fetch(
    `http://localhost:8000/api/auth/google/callback?code=${code}&state=${state}`
  );

  const data = await response.json();

  // Stocker les tokens
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);

  // Rediriger vers l'app
  window.location.href = '/dashboard';
}
```

---

## WebSocket Notifications

### Connexion WebSocket

#### URL

```
ws://localhost:8000/api/ws/notifications?token=<jwt_access_token>
```

L'utilisateur doit être authentifié avec un JWT valide.

### Types de messages

#### 1. Messages reçus du serveur

**Connection confirmée** :
```json
{
  "type": "connection",
  "message": "Connexion etablie avec succes",
  "timestamp": "2024-10-30T10:30:00"
}
```

**Heartbeat** (toutes les 30 secondes) :
```json
{
  "type": "heartbeat",
  "timestamp": "2024-10-30T10:30:30"
}
```

**Notification** :
```json
{
  "type": "notification",
  "notification_type": "warning",
  "title": "Limite bientot atteinte",
  "message": "Vous avez utilise 80% de votre limite pour Instagram",
  "data": {
    "app_name": "Instagram",
    "percentage": 80
  },
  "timestamp": "2024-10-30T10:31:00"
}
```

**Erreur** :
```json
{
  "type": "error",
  "message": "Action inconnue"
}
```

#### 2. Messages envoyés par le client

**Ping** (test connexion) :
```json
{
  "action": "ping",
  "timestamp": "2024-10-30T10:30:00"
}
```

**S'abonner à des événements** :
```json
{
  "action": "subscribe",
  "events": ["activities", "challenges", "limits"]
}
```

**Se désabonner** :
```json
{
  "action": "unsubscribe",
  "events": ["activities"]
}
```

**Obtenir les stats** :
```json
{
  "action": "get_stats"
}
```

### Exemples d'utilisation

#### JavaScript (Frontend)

```javascript
// 1. Connexion
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/api/ws/notifications?token=${token}`);

// 2. Gestion des événements
ws.onopen = () => {
  console.log('WebSocket connecté');

  // S'abonner aux notifications
  ws.send(JSON.stringify({
    action: 'subscribe',
    events: ['activities', 'challenges', 'limits']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'connection':
      console.log('Connexion confirmée');
      break;

    case 'heartbeat':
      // Heartbeat reçu
      break;

    case 'notification':
      // Afficher la notification
      showNotification(data.title, data.message, data.notification_type);
      break;

    case 'error':
      console.error('Erreur WebSocket:', data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('Erreur WebSocket:', error);
};

ws.onclose = () => {
  console.log('WebSocket déconnecté');
  // Reconnecter après 5 secondes
  setTimeout(() => connectWebSocket(), 5000);
};

// 3. Envoyer un ping
function sendPing() {
  ws.send(JSON.stringify({
    action: 'ping',
    timestamp: new Date().toISOString()
  }));
}

// 4. Fermer la connexion
function disconnect() {
  ws.close();
}
```

#### React Hook

```javascript
import { useEffect, useState, useRef } from 'react';

function useWebSocket(token) {
  const [notifications, setNotifications] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    if (!token) return;

    // Connexion
    ws.current = new WebSocket(
      `ws://localhost:8000/api/ws/notifications?token=${token}`
    );

    ws.current.onopen = () => {
      setIsConnected(true);

      // S'abonner
      ws.current.send(JSON.stringify({
        action: 'subscribe',
        events: ['activities', 'challenges', 'limits']
      }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'notification') {
        setNotifications(prev => [...prev, data]);
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
    };

    // Cleanup
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  return { notifications, isConnected, ws: ws.current };
}

// Utilisation
function App() {
  const token = localStorage.getItem('access_token');
  const { notifications, isConnected } = useWebSocket(token);

  return (
    <div>
      <p>Status: {isConnected ? 'Connecté' : 'Déconnecté'}</p>

      {notifications.map((notif, index) => (
        <div key={index} className={`notification ${notif.notification_type}`}>
          <h3>{notif.title}</h3>
          <p>{notif.message}</p>
        </div>
      ))}
    </div>
  );
}
```

### Envoi de notifications depuis le backend

```python
from app.services.websocket_service import notification_service

# 1. Notification simple
await notification_service.notify_user(
    user_id=123,
    notification_type="info",
    title="Nouvelle activité",
    message="Activité enregistrée avec succès",
    data={"app_name": "Instagram", "duration": 45}
)

# 2. Avertissement de limite
await notification_service.notify_limit_warning(
    user_id=123,
    app_name="Instagram",
    percentage=80.0
)

# 3. Application bloquée
await notification_service.notify_app_blocked(
    user_id=123,
    app_name="Instagram"
)

# 4. Mise à jour de challenge
await notification_service.notify_challenge_update(
    user_id=123,
    challenge_title="Challenge Octobre",
    update_type="leaderboard_update",
    message="Vous êtes maintenant 2e au classement!",
    data={"rank": 2, "score": 850}
)

# 5. Notification à plusieurs utilisateurs (leaderboard)
await notification_service.notify_leaderboard_update(
    user_ids=[123, 456, 789],
    challenge_title="Challenge Octobre",
    leaderboard_data={"updated_at": "2024-10-30T10:30:00"}
)
```

### Vérifier les connexions actives

```bash
# Via l'endpoint REST
curl http://localhost:8000/api/ws/stats

# Réponse:
{
  "websocket_enabled": true,
  "active_users": 15,
  "active_connections": 18,
  "connected_user_ids": [1, 2, 3, ...]
}
```

### Intégration dans les routers

```python
from app.services.websocket_service import notification_service

@router.post("/activities")
async def create_activity(
    activity: ActivityCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    # Créer l'activité
    new_activity = create_activity_in_db(activity, current_user.id, db)

    # Notifier via WebSocket
    await notification_service.notify_activity_update(
        user_id=current_user.id,
        activity_data={
            "app_name": activity.app_name,
            "duration_minutes": activity.duration_minutes
        }
    )

    return new_activity
```

### Bonnes pratiques

1. **Reconnexion automatique** :
   ```javascript
   function connectWithRetry() {
     connect();
     ws.onclose = () => {
       setTimeout(connectWithRetry, 5000);
     };
   }
   ```

2. **Gestion des erreurs** :
   ```javascript
   ws.onerror = (error) => {
     console.error('WebSocket error:', error);
     // Afficher un message à l'utilisateur
   };
   ```

3. **Déconnexion propre** :
   ```javascript
   window.addEventListener('beforeunload', () => {
     ws.close();
   });
   ```

4. **Limiter les notifications** :
   - Dédupliquer les notifications similaires
   - Grouper les notifications multiples
   - Limiter la fréquence d'envoi

---

## Exemples complets

### Application React complète

```javascript
import React, { useEffect, useState } from 'react';

function FocusApp() {
  const [user, setUser] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [ws, setWs] = useState(null);

  // OAuth Login
  const loginWithGoogle = async () => {
    const response = await fetch('http://localhost:8000/api/auth/google');
    const data = await response.json();
    window.location.href = data.authorization_url;
  };

  // WebSocket Setup
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const websocket = new WebSocket(
      `ws://localhost:8000/api/ws/notifications?token=${token}`
    );

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'notification') {
        setNotifications(prev => [...prev, data]);

        // Notification navigateur
        if (Notification.permission === 'granted') {
          new Notification(data.title, {
            body: data.message,
            icon: '/logo.png'
          });
        }
      }
    };

    setWs(websocket);

    return () => websocket.close();
  }, []);

  return (
    <div>
      {!user ? (
        <button onClick={loginWithGoogle}>
          Se connecter avec Google
        </button>
      ) : (
        <>
          <h1>Bienvenue {user.full_name}</h1>

          <div className="notifications">
            {notifications.map((notif, i) => (
              <div key={i} className={`alert alert-${notif.notification_type}`}>
                <strong>{notif.title}</strong>
                <p>{notif.message}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

---

## Troubleshooting

### OAuth

**Erreur : "redirect_uri_mismatch"**
- Vérifiez que l'URI dans Google Cloud Console correspond exactement à celle dans `.env`

**Erreur : "invalid_client"**
- Vérifiez `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET`

### WebSocket

**Connexion refusée**
- Vérifiez que `WEBSOCKET_ENABLED=True`
- Vérifiez le token JWT

**Déconnexions fréquentes**
- Vérifiez la configuration du reverse proxy (Nginx)
- Augmentez `WEBSOCKET_HEARTBEAT_INTERVAL`

### CI/CD

**Tests échouent**
- Vérifiez que les services (MySQL, Redis) sont disponibles
- Vérifiez les variables d'environnement

**Déploiement échoue**
- Vérifiez les secrets GitHub
- Vérifiez la clé SSH

---

**Focus API** - CI/CD, OAuth & WebSocket intégrés ! 🚀
