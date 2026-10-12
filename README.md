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

### Exposer les métriques pour Prometheus

```bash
curl http://localhost:8000/prometheus
```

Renvoie la dernière mesure de chaque machine au format texte Prometheus
(`host_cpu_percent`, `host_memory_percent`, `host_load_1m`, ... avec le label
`hostname`) et le compteur `metrics_received_total`.

## Supervision (Prometheus + Grafana)

`docker compose up --build` démarre aussi Prometheus et Grafana :

| Service | Adresse | Rôle |
|---|---|---|
| API | http://localhost:8000/prometheus | expose les métriques |
| Prometheus | http://localhost:9090 | collecte l'API toutes les 5 s |
| Grafana | http://localhost:3000 (admin / admin) | tableau de bord « System Metrics » |

Le tableau de bord et la source de données sont provisionnés automatiquement
depuis `monitoring/`. Le mot de passe Grafana se change avec la variable
`GRAFANA_ADMIN_PASSWORD`.

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

Lancer avec Docker : `cp .env.example .env`, puis `docker compose up --build`
et `curl http://localhost:8000/metrics/latest`.

Images publiées : [`youssoufbest/system-metrics-api`](https://hub.docker.com/r/youssoufbest/system-metrics-api)
et [`youssoufbest/system-metrics-agent`](https://hub.docker.com/r/youssoufbest/system-metrics-agent)
(tags `latest` et SHA du commit).

### Choix techniques

- **Base** : `python:3.12.11-slim-bookworm`, tag précis (jamais `latest`). Alpine
  écartée : `psutil` et `uvicorn[standard]` y manquent souvent de wheels (musl),
  ce qui impose un compilateur pour un faible gain de taille.
- **Multi-stage** : un venv `/opt/venv` est construit dans `builder`, seul ce venv
  est copié dans l'image finale (pas de cache pip ni d'outils de build).
- **Une image par rôle** : `requirements-api.txt` et `requirements-agent.txt`,
  seuls les fichiers source utiles sont copiés (pas de tests dans les images).
- **Sécurité** : utilisateur non-root (UID 10001), aucun secret ni `.env` dans
  l'image, configuration injectée à l'exécution, `HEALTHCHECK` Python.
- **`uptime`** : absente de l'image `slim`, fournie par le paquet Debian `procps`,
  installé uniquement dans l'image de l'agent.
- **Compose** : l'agent joint l'API par `http://api:8000/metrics` (127.0.0.1
  désignerait son propre conteneur) et attend `service_healthy`.
- **Limite connue** : dans un conteneur, `psutil` lit `/proc` sans tenir compte
  des limites cgroups, et le `hostname` est celui du conteneur ; pour surveiller
  réellement un hôte, l'agent doit tourner sur l'hôte.

### Tailles d'images

| Image | Taille locale (`docker images`) | Taille compressée (Docker Hub) |
|-------|------|------|
| `system-metrics-api` | ≈ 260 Mo | 76,14 Mo |
| `system-metrics-agent` | ≈ 212 Mo | 65,97 Mo |

La taille locale est mesurée avant l'ajout de `apt-get upgrade` ; la taille
compressée est celle que l'on télécharge (`linux/amd64`).

### Pipeline (`.github/workflows/ci-cd.yml`)

Job `test` : black, flake8, pytest avec couverture, analyse SonarQube Cloud et
Quality Gate bloquante. Job `build-scan-push` (matrice api/agent, après `test`) :
build local, scan Trivy (HIGH/CRITICAL corrigeables, échec bloquant), puis push
Docker Hub (tags SHA et `latest`) uniquement sur un push vers `main`, jamais sur
une Pull Request. Secrets : `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`,
`SONAR_TOKEN`, `SONAR_HOST_URL`.

### Difficultés rencontrées

- **Docker Desktop** : « Virtualization support not detected » malgré le BIOS ;
  résolu en activant WSL et VirtualMachinePlatform, puis redémarrage.
- **Tests sous Windows** : deux tests du collecteur échouaient ; `platform.system`
  est maintenant simulé dans les tests.
- **Lint** : le code existant ne passait pas `black` ; reformatage et suppression
  d'un import inutilisé.
- **SonarQube Cloud** : l'analyse automatique entrait en conflit avec l'analyse
  CI ; elle a été désactivée.
- **Secret Docker Hub** : un retour à la ligne parasite dans `DOCKERHUB_USERNAME`
  rendait le nom d'image invalide pour Trivy ; secret recréé.
- **Échec volontaire du pipeline** : Trivy a bloqué la build (46 vulnérabilités
  HIGH/CRITICAL corrigeables dans les paquets Debian de l'image de base).
  Correction : `apt-get upgrade` dans les deux Dockerfiles, au prix d'un build
  moins reproductible. Le run suivant est vert.
- **Pistes** : l'API conserve les métriques en mémoire sans limite
  (`received_metrics`) ; une supervision Prometheus/Grafana pourrait s'ajouter.
