# Guide - Caching & Monitoring

Ce guide explique comment utiliser le système de cache Redis et le monitoring Prometheus/Grafana dans Focus API.

## Table des matières

- [Cache Redis](#cache-redis)
- [Monitoring Prometheus](#monitoring-prometheus)
- [Grafana Dashboard](#grafana-dashboard)
- [Metriques disponibles](#metriques-disponibles)
- [Exemples d'utilisation](#exemples-dutilisation)

## Cache Redis

### Configuration

Le cache Redis est configuré via les variables d'environnement `.env` :

```env
# Configuration Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=True
CACHE_TTL=300  # 5 minutes par défaut
```

### Utilisation dans le code

#### 1. Service de cache

Le service de cache est disponible globalement :

```python
from app.services.cache_service import cache_service

# Récupérer une valeur
value = await cache_service.get("user:123")

# Stocker une valeur (avec TTL optionnel)
await cache_service.set("user:123", user_data, ttl=600)

# Supprimer une clé
await cache_service.delete("user:123")

# Supprimer par pattern
await cache_service.delete_pattern("user:*")

# Vérifier l'existence
exists = await cache_service.exists("user:123")

# Vider tout le cache
await cache_service.clear_all()
```

#### 2. Décorateur @cached

Pour mettre en cache automatiquement une fonction :

```python
from app.services.cache_service import cached

@cached(ttl=300, key_prefix="user")
async def get_user_stats(user_id: int, db: Session):
    """
    Cette fonction sera mise en cache automatiquement
    La clé sera : user:user_id
    """
    # Calculs complexes...
    return stats
```

#### 3. Invalidation du cache

```python
from app.services.cache_service import (
    invalidate_user_cache,
    invalidate_challenge_cache
)

# Invalider le cache d'un utilisateur
await invalidate_user_cache(user_id=123)

# Invalider le cache d'un challenge
await invalidate_challenge_cache(challenge_id=456)
```

### Exemples d'utilisation dans les endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.cache_service import cache_service, cached

router = APIRouter()

@router.get("/users/{user_id}/stats")
async def get_user_statistics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint avec cache manuel
    """
    # Essaie de récupérer depuis le cache
    cache_key = f"user:{user_id}:stats"
    cached_stats = await cache_service.get(cache_key)

    if cached_stats:
        return cached_stats

    # Si pas en cache, calcule les stats
    stats = calculate_user_stats(user_id, db)

    # Met en cache pour 10 minutes
    await cache_service.set(cache_key, stats, ttl=600)

    return stats


# Ou avec le décorateur (plus simple)
@cached(ttl=600, key_prefix="challenge_leaderboard")
async def get_challenge_leaderboard(challenge_id: int, db: Session):
    """
    Cette fonction est automatiquement mise en cache
    """
    return db.query(Leaderboard).filter(
        Leaderboard.challenge_id == challenge_id
    ).all()
```

### Stratégies de cache

#### Cache-aside (Lazy Loading)

```python
# Lire du cache, sinon charger de la DB
async def get_user_with_cache(user_id: int, db: Session):
    cache_key = f"user:{user_id}"

    # 1. Cherche dans le cache
    user = await cache_service.get(cache_key)
    if user:
        return user

    # 2. Si pas en cache, charge de la DB
    user = db.query(User).filter(User.id == user_id).first()

    # 3. Stocke en cache
    if user:
        await cache_service.set(cache_key, user, ttl=3600)

    return user
```

#### Write-through

```python
# Écrire dans la DB et le cache simultanément
async def update_user_with_cache(user_id: int, data: dict, db: Session):
    # 1. Met à jour la DB
    user = db.query(User).filter(User.id == user_id).first()
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()

    # 2. Met à jour le cache
    await cache_service.set(f"user:{user_id}", user, ttl=3600)

    return user
```

#### Cache invalidation

```python
# Invalider le cache lors d'une mise à jour
async def delete_user(user_id: int, db: Session):
    # 1. Supprime de la DB
    db.query(User).filter(User.id == user_id).delete()
    db.commit()

    # 2. Invalide TOUT le cache lié à cet utilisateur
    await invalidate_user_cache(user_id)
```

### Bonnes pratiques

1. **Utiliser des TTL appropriés** :
   - Données statiques : 1 heure (3600s)
   - Données fréquemment modifiées : 5 minutes (300s)
   - Statistiques : 10-30 minutes

2. **Nommer les clés de façon cohérente** :
   ```
   resource:id:attribute
   user:123:profile
   challenge:456:leaderboard
   stats:daily:2024-10-30
   ```

3. **Invalider le cache lors des mutations** :
   ```python
   # Après création/mise à jour/suppression
   await cache_service.delete(f"user:{user_id}")
   ```

4. **Gérer les erreurs gracieusement** :
   ```python
   # Si Redis est down, l'app continue de fonctionner
   cached_value = await cache_service.get(key)
   if cached_value is None:
       # Charge depuis la DB normalement
       value = load_from_db()
   ```

## Monitoring Prometheus

### Configuration

Prometheus est activé via `.env` :

```env
METRICS_ENABLED=True
METRICS_ENDPOINT=/metrics
```

### Accès aux métriques

Les métriques sont exposées sur : `http://localhost:8000/metrics`

Exemple de réponse :

```
# HELP focus_api_http_requests_total Total des requetes HTTP
# TYPE focus_api_http_requests_total counter
focus_api_http_requests_total{method="GET",endpoint="/api/users/me",status="200"} 145.0

# HELP focus_api_http_request_duration_seconds Duree des requetes HTTP
# TYPE focus_api_http_request_duration_seconds histogram
focus_api_http_request_duration_seconds_bucket{method="GET",endpoint="/api/users/me",le="0.005"} 120.0
focus_api_http_request_duration_seconds_bucket{method="GET",endpoint="/api/users/me",le="0.01"} 140.0
```

### Métriques collectées automatiquement

#### HTTP

- `focus_api_http_requests_total` - Total des requêtes HTTP
- `focus_api_http_request_duration_seconds` - Durée des requêtes
- `focus_api_http_requests_in_progress` - Requêtes en cours
- `focus_api_http_errors_total` - Total des erreurs HTTP

#### Base de données

- `focus_api_db_queries_total` - Total des requêtes SQL
- `focus_api_db_query_duration_seconds` - Durée des requêtes SQL
- `focus_api_db_connections_active` - Connexions actives

#### Cache

- `focus_api_cache_hits_total` - Hits de cache
- `focus_api_cache_misses_total` - Misses de cache
- `focus_api_cache_operations_duration_seconds` - Durée des opérations

#### Business

- `focus_api_users_total` - Nombre total d'utilisateurs
- `focus_api_users_registered_total` - Inscriptions totales
- `focus_api_users_logged_in_total` - Connexions totales
- `focus_api_activities_created_total` - Activités créées
- `focus_api_challenges_total` - Nombre de challenges
- `focus_api_emails_sent_total` - Emails envoyés

### Utilisation dans le code

```python
from app.services.metrics_service import (
    track_user_registration,
    track_user_login,
    track_activity_created,
    track_challenge_created,
    track_email_sent,
    track_app_blocked,
    track_limit_reached
)

# Enregistrer une inscription
@router.post("/register")
async def register(user_data: UserCreate, db: Session):
    user = create_user(user_data, db)
    track_user_registration()  # Incrémente le compteur
    return user

# Enregistrer une connexion
@router.post("/login")
async def login(credentials: UserLogin, db: Session):
    user = authenticate_user(credentials, db)
    track_user_login()  # Incrémente le compteur
    return user

# Enregistrer une activité
@router.post("/activities")
async def create_activity(activity: ActivityCreate, db: Session):
    new_activity = save_activity(activity, db)
    track_activity_created(
        app_name=activity.app_name,
        duration_minutes=activity.duration_minutes
    )
    return new_activity

# Enregistrer l'envoi d'un email
async def send_verification_email(email: str, token: str):
    success = await email_service.send(email, token)
    track_email_sent("verification", success)
```

## Grafana Dashboard

### Accès

Grafana est accessible sur : `http://localhost:3001`

**Identifiants par défaut :**
- Username: `admin`
- Password: `admin`

### Configuration initiale

1. **Ajouter Prometheus comme source de données** :
   - Settings > Data Sources > Add data source
   - Choisir "Prometheus"
   - URL: `http://prometheus:9090`
   - Cliquer "Save & Test"

2. **Créer un dashboard** :
   - Cliquer sur "+" > Dashboard
   - Add new panel

### Requêtes Prometheus utiles

#### Trafic HTTP

```promql
# Requêtes par seconde
rate(focus_api_http_requests_total[5m])

# Requêtes par endpoint
sum by (endpoint) (focus_api_http_requests_total)

# Temps de réponse moyen
rate(focus_api_http_request_duration_seconds_sum[5m]) /
rate(focus_api_http_request_duration_seconds_count[5m])

# Taux d'erreur
rate(focus_api_http_errors_total[5m])
```

#### Performance cache

```promql
# Hit rate du cache
rate(focus_api_cache_hits_total[5m]) /
(rate(focus_api_cache_hits_total[5m]) + rate(focus_api_cache_misses_total[5m]))

# Temps de réponse du cache
focus_api_cache_operations_duration_seconds
```

#### Métriques business

```promql
# Nouvelles inscriptions (dernière heure)
increase(focus_api_users_registered_total[1h])

# Connexions par minute
rate(focus_api_users_logged_in_total[1m])

# Activités créées par app
sum by (app_name) (focus_api_activities_created_total)

# Challenges actifs
focus_api_challenges_total{status="active"}
```

### Dashboard recommandé

Structure d'un dashboard complet :

1. **Vue d'ensemble**
   - Total utilisateurs
   - Requêtes/seconde
   - Temps de réponse moyen
   - Taux d'erreur

2. **Performance HTTP**
   - Requêtes par endpoint
   - Temps de réponse par endpoint
   - Erreurs par type

3. **Cache**
   - Hit rate
   - Miss rate
   - Temps de réponse

4. **Base de données**
   - Requêtes/seconde
   - Connexions actives
   - Temps de réponse

5. **Business metrics**
   - Inscriptions
   - Connexions
   - Activités créées
   - Challenges actifs

## Alertes (Optionnel)

### Alertes Prometheus

Créer un fichier `alerts.yml` :

```yaml
groups:
  - name: focus_api_alerts
    interval: 30s
    rules:
      # Taux d'erreur élevé
      - alert: HighErrorRate
        expr: rate(focus_api_http_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Taux d'erreur HTTP élevé"
          description: "Plus de 5% d'erreurs HTTP sur les 5 dernières minutes"

      # Temps de réponse lent
      - alert: SlowResponseTime
        expr: |
          rate(focus_api_http_request_duration_seconds_sum[5m]) /
          rate(focus_api_http_request_duration_seconds_count[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Temps de réponse lent"
          description: "Temps de réponse moyen > 1 seconde"

      # Cache hit rate faible
      - alert: LowCacheHitRate
        expr: |
          rate(focus_api_cache_hits_total[5m]) /
          (rate(focus_api_cache_hits_total[5m]) + rate(focus_api_cache_misses_total[5m])) < 0.5
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Hit rate du cache faible"
          description: "Hit rate < 50% sur les 15 dernières minutes"

      # API down
      - alert: APIDown
        expr: up{job="focus-api"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API Focus inaccessible"
          description: "L'API ne répond plus depuis 2 minutes"
```

## Debugging

### Vérifier le statut du cache

```bash
# Via l'endpoint health
curl http://localhost:8000/api/health

# Réponse:
{
  "status": "healthy",
  "database": "connected",
  "cache": {
    "enabled": true,
    "status": "connected",
    "version": "7.0.0",
    "used_memory": "2.5M",
    "total_keys": 145
  }
}
```

### Vérifier les métriques

```bash
# Récupérer toutes les métriques
curl http://localhost:8000/metrics

# Filtrer une métrique spécifique
curl http://localhost:8000/metrics | grep focus_api_cache_hits
```

### Logs

Les logs incluent automatiquement les informations sur le cache :

```
2024-10-30 10:30:15 - Cache HIT: user:123:profile
2024-10-30 10:30:16 - Cache MISS: challenge:456:leaderboard
2024-10-30 10:30:17 - Cache SET: user:123:stats (TTL: 300s)
```

## Performance

### Gain de performance avec le cache

| Opération | Sans cache | Avec cache | Gain |
|-----------|------------|------------|------|
| Profil utilisateur | 45ms | 2ms | **95%** |
| Statistiques | 150ms | 3ms | **98%** |
| Leaderboard | 200ms | 5ms | **97%** |

### Recommandations

1. **Mettre en cache** :
   - Données fréquemment lues
   - Calculs coûteux
   - Résultats de requêtes complexes
   - Données qui changent rarement

2. **Ne PAS mettre en cache** :
   - Données en temps réel
   - Informations sensibles (mots de passe, tokens)
   - Données très volatiles

3. **Monitorer** :
   - Hit rate > 80% = bon
   - Hit rate 50-80% = moyen
   - Hit rate < 50% = revoir la stratégie

## Ressources

- [Documentation Redis](https://redis.io/documentation)
- [Documentation Prometheus](https://prometheus.io/docs/)
- [Documentation Grafana](https://grafana.com/docs/)
- [Best practices caching](https://aws.amazon.com/caching/best-practices/)

---

**Focus API** - Système de cache et monitoring intégré 🚀
