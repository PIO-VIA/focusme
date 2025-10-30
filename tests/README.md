# Tests Focus Backend

Suite complète de tests unitaires et d'intégration pour l'API Focus Backend.

## 📋 Table des Matières

- [Structure](#structure)
- [Installation](#installation)
- [Lancer les Tests](#lancer-les-tests)
- [Coverage](#coverage)
- [Types de Tests](#types-de-tests)
- [Écrire des Tests](#écrire-des-tests)

## 📁 Structure

```
tests/
├── __init__.py
├── conftest.py              # Configuration pytest et fixtures
├── test_auth.py            # Tests authentification (JWT, OAuth)
├── test_users.py           # Tests gestion utilisateurs
├── test_activities.py      # Tests suivi activités
├── test_challenges.py      # Tests challenges
├── test_blocked.py         # Tests applications bloquées
├── test_admin.py           # Tests administration
├── test_websocket.py       # Tests WebSocket notifications
├── test_cache.py           # Tests cache Redis
├── test_oauth.py           # Tests OAuth Google
└── README.md               # Ce fichier
```

## 🚀 Installation

### Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt
```

### Dépendances de test

- **pytest** (8.3.3) - Framework de test
- **pytest-asyncio** (0.24.0) - Support tests asynchrones
- **pytest-cov** (6.0.0) - Coverage des tests
- **httpx** (0.27.2) - Client HTTP pour tests
- **faker** (33.1.0) - Génération données de test

## 🧪 Lancer les Tests

### Tous les tests

```bash
# Lancer tous les tests
pytest

# Avec verbose
pytest -v

# Avec capture de sortie
pytest -s
```

### Tests spécifiques

```bash
# Un fichier de test
pytest tests/test_auth.py

# Une classe de tests
pytest tests/test_auth.py::TestRegister

# Un test spécifique
pytest tests/test_auth.py::TestRegister::test_register_success

# Tests par marker
pytest -m auth          # Tests d'authentification
pytest -m unit          # Tests unitaires
pytest -m integration   # Tests d'intégration
```

### Tests parallèles

```bash
# Installer pytest-xdist
pip install pytest-xdist

# Lancer en parallèle
pytest -n auto
```

## 📊 Coverage

### Générer le rapport de coverage

```bash
# Coverage dans le terminal
pytest --cov=app --cov-report=term-missing

# Rapport HTML (plus détaillé)
pytest --cov=app --cov-report=html

# Ouvrir le rapport HTML
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Objectifs de coverage

- **Global**: 80%+
- **Critique (auth, users)**: 90%+
- **Services**: 85%+
- **Routers**: 80%+

### Rapport de coverage actuel

```bash
# Voir le rapport complet
pytest --cov=app --cov-report=term-missing
```

## 📝 Types de Tests

### 1. Tests d'Authentification (`test_auth.py`)

- ✅ Inscription (register)
- ✅ Connexion (login)
- ✅ Vérification email
- ✅ Réinitialisation mot de passe
- ✅ Refresh token
- ✅ OAuth Google

**Exemple:**
```python
def test_register_success(client, mock_email_service):
    """Test inscription réussie"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123!",
        "full_name": "Test User"
    }
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
```

### 2. Tests Utilisateurs (`test_users.py`)

- ✅ Récupération profil
- ✅ Mise à jour profil
- ✅ Statistiques utilisateur
- ✅ Suppression compte
- ✅ Validation données

### 3. Tests Activités (`test_activities.py`)

- ✅ Création activité
- ✅ Liste activités (pagination, filtres)
- ✅ Activités du jour
- ✅ Statistiques (quotidiennes, hebdomadaires)
- ✅ Suppression activité

### 4. Tests Challenges (`test_challenges.py`)

- ✅ Création challenge (public/privé)
- ✅ Rejoindre/Quitter challenge
- ✅ Classement (leaderboard)
- ✅ Suppression challenge

### 5. Tests Applications Bloquées (`test_blocked.py`)

- ✅ Blocage application
- ✅ Mise à jour limites
- ✅ Réinitialisation compteur
- ✅ Logique de blocage

### 6. Tests Administration (`test_admin.py`)

- ✅ Gestion utilisateurs
- ✅ Statistiques globales
- ✅ Gestion challenges
- ✅ Logs système
- ✅ Health check

### 7. Tests WebSocket (`test_websocket.py`)

- ✅ Connexion WebSocket
- ✅ Authentification JWT
- ✅ Messages (ping, stats)
- ✅ Notifications

### 8. Tests Cache (`test_cache.py`)

- ✅ Opérations CRUD cache
- ✅ TTL et expiration
- ✅ Invalidation cache
- ✅ Décorateur @cached

### 9. Tests OAuth (`test_oauth.py`)

- ✅ Flow OAuth Google
- ✅ Création utilisateur OAuth
- ✅ Tokens JWT
- ✅ Sécurité (state, CSRF)

## ✍️ Écrire des Tests

### Structure d'un test

```python
class TestFeature:
    """Description de la feature testée"""

    def test_feature_success(self, client, auth_headers):
        """Test cas de succès"""
        # Arrange - Préparer les données
        data = {"key": "value"}

        # Act - Exécuter l'action
        response = client.post("/api/endpoint", headers=auth_headers, json=data)

        # Assert - Vérifier le résultat
        assert response.status_code == 200
        assert response.json()["key"] == "value"

    def test_feature_error(self, client):
        """Test cas d'erreur"""
        response = client.post("/api/endpoint", json={})
        assert response.status_code == 422
```

### Fixtures disponibles

#### Fixtures de base

```python
def test_with_database(db_session):
    """Utilise une session de base de données"""
    user = User(username="test")
    db_session.add(user)
    db_session.commit()

def test_with_client(client):
    """Utilise le client de test FastAPI"""
    response = client.get("/api/health")
    assert response.status_code == 200

def test_with_auth(client, auth_headers):
    """Utilise des headers d'authentification"""
    response = client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
```

#### Fixtures utilisateurs

- `test_user` - Utilisateur vérifié
- `test_admin` - Administrateur
- `test_user_unverified` - Utilisateur non vérifié
- `auth_headers` - Headers JWT user
- `admin_headers` - Headers JWT admin

#### Fixtures données

- `test_activity` - Activité de test
- `test_blocked_app` - App bloquée de test
- `test_challenge` - Challenge de test

#### Fixtures services

- `mock_redis` - Mock du service Redis
- `mock_email_service` - Mock du service email

### Helpers de test

```python
from tests.conftest import (
    create_test_user_data,
    create_test_activity_data,
    create_test_challenge_data,
    create_test_blocked_app_data
)

def test_with_helper():
    user_data = create_test_user_data(username="custom")
    # ...
```

### Tests asynchrones

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test fonction asynchrone"""
    result = await async_function()
    assert result is not None
```

### Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test avec mock"""
    mock_service = Mock()
    mock_service.method.return_value = "mocked"

    with patch("app.services.service.method", return_value="mocked"):
        result = function_to_test()
        assert result == "mocked"
```

## 🎯 Bonnes Pratiques

### 1. Nommage

- **Fichiers**: `test_*.py`
- **Classes**: `Test*` (ex: `TestAuthentication`)
- **Fonctions**: `test_*` (ex: `test_register_success`)

### 2. Organisation

- Un test = une assertion principale
- Utiliser AAA (Arrange, Act, Assert)
- Tests indépendants (pas de dépendances entre tests)

### 3. Documentation

```python
def test_feature(self):
    """
    Test description claire en français

    Given: Conditions initiales
    When: Action effectuée
    Then: Résultat attendu
    """
```

### 4. Assertions

```python
# ✅ Bon - Assertion claire
assert response.status_code == 200
assert "email" in response.json()

# ❌ Mauvais - Assertion vague
assert response
```

### 5. Données de test

```python
# ✅ Bon - Données explicites
user_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!"
}

# ❌ Mauvais - Données magiques
user_data = get_random_user()
```

## 🐛 Debugging

### Voir les prints

```bash
pytest -s
```

### Voir les logs

```bash
pytest --log-cli-level=DEBUG
```

### Arrêter au premier échec

```bash
pytest -x
```

### Mode verbose

```bash
pytest -vv
```

### PDB (Python Debugger)

```python
def test_with_debugger():
    import pdb; pdb.set_trace()
    # Code à débugger
```

Ou utiliser:

```bash
pytest --pdb  # Arrêt automatique sur échec
```

## 🚀 CI/CD

Les tests sont exécutés automatiquement via GitHub Actions:

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: |
    pytest tests/ -v --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## 📚 Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

## 🆘 Problèmes Courants

### Erreur: ModuleNotFoundError

```bash
# Solution: Installer en mode développement
pip install -e .
```

### Erreur: Database locked

```python
# Solution: Utiliser la fixture db_session
def test_feature(db_session):
    # ...
```

### Tests lents

```bash
# Solution: Utiliser pytest-xdist
pytest -n auto
```

## ✅ Checklist Avant Commit

- [ ] Tous les tests passent: `pytest`
- [ ] Coverage >= 80%: `pytest --cov=app`
- [ ] Pas de warnings: `pytest --tb=short`
- [ ] Code formaté: `black tests/`
- [ ] Linting: `flake8 tests/`
- [ ] Type hints: `mypy tests/`

## 📈 Statistiques

```bash
# Nombre de tests
pytest --collect-only | grep "test session starts"

# Temps d'exécution
pytest --durations=10

# Tests les plus lents
pytest --durations=0
```

---

**Focus Backend Tests** - Garantir la qualité et la fiabilité de l'API 🧪
