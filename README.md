# System Metrics Agent

Un agent Python modulaire capable de collecter les métriques système,
de les formater et de les transmettre en temps réel vers une API ou un
Webhook externe.

## Fonctionnalités

- Collecte du pourcentage CPU.
- Collecte de la mémoire RAM totale, utilisée et disponible.
- Utilisation de `psutil`.
- Utilisation de **`subprocess`** pour exécuter la commande système
  `uptime` et récupérer la charge système.
- Architecture modulaire :
  - `collector.py` : collecte ;
  - `formatter.py` : normalisation du payload ;
  - `sender.py` : envoi HTTP ;
  - `agent.py` : orchestration ;
  - `api.py` : API de réception avec **FastAPI**.
- Configuration externe avec `.env`.
- Gestion des erreurs réseau et des erreurs de collecte.
- Tests automatisés avec `pytest`.

## Architecture

```text
system_metrics_agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── api.py
│   ├── collector.py
│   ├── config.py
│   ├── formatter.py
│   ├── sender.py
│   └── tests/
│       ├── test_agent.py
│       ├── test_api.py
│       ├── test_collector.py
│       ├── test_config.py
│       ├── test_formatter.py
│       └── test_sender.py
├── Dockerfile.api
├── Dockerfile.agent
├── docker-compose.yml
├── sonar-project.properties
├── .github/workflows/ci-cd.yml
├── .env.example
├── requirements.txt
└── README.md
```

## Installation

Créer un environnement virtuel :

```bash
python -m venv .venv
```

Linux/macOS :

```bash
source .venv/bin/activate
```

Windows :

```powershell
.venv\Scripts\Activate.ps1
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

Créer le fichier de configuration :

```bash
cp .env.example .env
```

Sous Windows, copier manuellement `.env.example` en `.env`.

## Démarrer l'API FastAPI

```bash
uvicorn app.api:app --reload
```

L'API est alors disponible sur :

```text
http://127.0.0.1:8000
```

Documentation interactive FastAPI :

```text
http://127.0.0.1:8000/docs
```

## Démarrer l'agent

Dans un deuxième terminal :

```bash
python -m app.agent
```

L'agent collecte les métriques selon l'intervalle défini dans `.env`
puis les envoie automatiquement vers `METRICS_ENDPOINT`.

## Exemple de configuration

```env
METRICS_ENDPOINT=http://127.0.0.1:8000/metrics
COLLECTION_INTERVAL=5
REQUEST_TIMEOUT=5
```

Pour envoyer vers un webhook externe, remplacer simplement :

```env
METRICS_ENDPOINT=https://example.com/webhook
```

## Exemple de métrique envoyée

```json
{
  "agent": "system-metrics-agent",
  "event_type": "system_metrics",
  "data": {
    "timestamp": "2026-08-27T12:00:00.000000+00:00",
    "hostname": "server-01",
    "cpu": {
      "percent": 23.4,
      "logical_cores": 8
    },
    "memory": {
      "total_bytes": 16777216000,
      "available_bytes": 8000000000,
      "used_bytes": 7777216000,
      "percent": 48.2
    },
    "system": {
      "load_1m": 0.12,
      "load_5m": 0.18,
      "load_15m": 0.20
    }
  }
}
```

## Endpoints

### Vérifier l'état de l'API

```http
GET /health
```

Réponse :

```json
{
  "status": "ok"
}
```

### Envoyer des métriques

```http
POST /metrics
```

### Récupérer la dernière métrique

```http
GET /metrics/latest
```

## Tests

Exécuter toute la suite :

```bash
pytest -q
```

Exécuter avec une couverture de code nécessite l'installation de
`pytest-cov` :

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

## Robustesse

Le projet gère notamment :

- les erreurs d'exécution de `subprocess` ;
- les timeouts ;
- les erreurs de connexion HTTP ;
- les réponses HTTP en erreur ;
- les configurations invalides ;
- les payloads incomplets ;
- l'absence de métriques dans l'API.

## Démonstration du flux

```text
┌──────────────────┐
│ Système          │
│ CPU / RAM        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ collector.py     │
│ psutil           │
│ subprocess       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ formatter.py     │
│ Payload JSON     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ sender.py        │
│ HTTP POST        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ FastAPI          │
│ /metrics         │
└──────────────────┘
```

## Conteneurisation et CI/CD (rapport du TP)

### Lancer avec Docker

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/metrics/latest
```

### Choix techniques

- **Image de base** : `python:3.12.11-slim-bookworm` (tag précis, jamais `latest`).
  Alpine a été écartée : `psutil` et `uvicorn[standard]` n'y ont pas toujours
  de wheels précompilées (musl), ce qui impose un compilateur et alourdit le
  build pour un gain de taille limité.
- **Multi-stage** : une étape `builder` crée un venv `/opt/venv` ; l'image
  finale ne copie que ce venv, sans pip cache ni outils de build.
- **Une image par rôle** : `requirements-api.txt` (FastAPI, uvicorn) et
  `requirements-agent.txt` (psutil, requests, python-dotenv). Seuls les
  fichiers source utiles sont copiés ; les tests ne sont pas dans les images.
- **Sécurité** : utilisateur non-root (UID 10001), aucun secret ni `.env` dans
  l'image (`.dockerignore`), configuration injectée à l'exécution.
- **Prod** : `uvicorn` sans `--reload`, `--host 0.0.0.0`, `EXPOSE 8000`,
  `HEALTHCHECK` Python (pas besoin de `curl` dans l'image).
- **`uptime`** : absente de l'image `slim` à ma connaissance ; fournie par le
  paquet Debian `procps`, ajouté uniquement dans l'image de l'agent.
- **Compose** : l'agent joint l'API par `http://api:8000/metrics` (127.0.0.1
  désignerait son propre conteneur) et attend `service_healthy`.

### Ce que change la conteneurisation pour l'agent

Dans un conteneur, `psutil` lit `/proc`, qui reflète en grande partie l'hôte
pour la RAM et les CPU, mais sans tenir compte des limites cgroups (`--memory`,
`--cpus`) : les valeurs ne décrivent donc pas fidèlement le conteneur. Le
`hostname` remonté est celui du conteneur, pas de la machine. Pour surveiller
réellement un hôte, il faut déployer l'agent sur l'hôte (service systemd,
DaemonSet Kubernetes avec montages adaptés) ou lire les statistiques cgroups.

### Tailles d'images

À compléter après `docker images` : API = ____ Mo, agent = ____ Mo.

### Pipeline

`.github/workflows/ci-cd.yml` : job `test` (pytest + couverture, SonarQube,
Quality Gate bloquante) puis job `build-scan-push` (matrice api/agent : build
local, scan Trivy HIGH/CRITICAL corrigeables, push Docker Hub uniquement sur
`main`, tags SHA et `latest`). Secrets requis : `DOCKERHUB_USERNAME`,
`DOCKERHUB_TOKEN`, `SONAR_TOKEN`, `SONAR_HOST_URL`.

### Difficultés rencontrées

À compléter avec ton expérience (échec volontaire du pipeline, captures).
