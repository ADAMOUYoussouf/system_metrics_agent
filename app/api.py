"""API FastAPI de réception des métriques."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="System Metrics API",
    description="API de réception des métriques envoyées par les agents.",
    version="1.0.0",
)

received_metrics: list[dict[str, Any]] = []
# Dernière mesure reçue par machine (pour l'export Prometheus).
latest_by_host: dict[str, dict[str, Any]] = {}

registry = CollectorRegistry()
RECEIVED_TOTAL = Counter(
    "metrics_received_total",
    "Nombre de messages de métriques reçus par l'API.",
    registry=registry,
)

# (nom Prometheus, chemin dans le payload, description)
GAUGES = [
    ("host_cpu_percent", ("cpu", "percent"), "Utilisation du processeur (%)."),
    ("host_cpu_logical_cores", ("cpu", "logical_cores"), "Coeurs logiques."),
    ("host_memory_percent", ("memory", "percent"), "Mémoire utilisée (%)."),
    ("host_memory_used_bytes", ("memory", "used_bytes"), "Mémoire utilisée."),
    (
        "host_memory_total_bytes",
        ("memory", "total_bytes"),
        "Mémoire totale.",
    ),
    ("host_load_1m", ("system", "load_1m"), "Charge moyenne sur 1 minute."),
    ("host_load_5m", ("system", "load_5m"), "Charge moyenne sur 5 minutes."),
    ("host_load_15m", ("system", "load_15m"), "Charge moyenne sur 15 min."),
]


def _dig(data: dict[str, Any], path: tuple[str, ...]) -> float | None:
    """Lit une valeur numérique imbriquée, ou None si absente."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


class HostMetricsCollector:
    """Transforme la dernière mesure de chaque machine en jauges Prometheus."""

    def collect(self):
        for name, path, doc in GAUGES:
            family = GaugeMetricFamily(name, doc, labels=["hostname"])
            for hostname, item in latest_by_host.items():
                value = _dig(item.get("data", {}), path)
                if value is not None:
                    family.add_metric([hostname], value)
            yield family


registry.register(HostMetricsCollector())


class MetricsPayload(BaseModel):
    """Payload reçu depuis l'agent."""

    agent: str = Field(..., min_length=1)
    event_type: str
    data: dict[str, Any]


@app.get("/metrics")
def get_metrics() -> dict[str, Any]:
    """Retourne toutes les métriques reçues."""
    return {
        "total": len(received_metrics),
        "metrics": received_metrics,
    }


@app.get("/prometheus")
def prometheus_metrics() -> Response:
    """Expose les métriques au format texte Prometheus."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie l'état de l'API."""
    return {"status": "ok"}


@app.post("/metrics", status_code=status.HTTP_201_CREATED)
def receive_metrics(payload: MetricsPayload) -> dict[str, Any]:
    """Reçoit et stocke temporairement les métriques."""
    item = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    received_metrics.append(item)
    hostname = str(payload.data.get("hostname", payload.agent))
    latest_by_host[hostname] = item
    RECEIVED_TOTAL.inc()

    logger.info(
        "Métriques reçues de %s. Total=%s",
        payload.agent,
        len(received_metrics),
    )

    return {
        "status": "received",
        "message": "Métriques enregistrées avec succès.",
        "total_received": len(received_metrics),
    }


@app.get("/metrics/latest")
def latest_metrics() -> dict[str, Any]:
    """Retourne la dernière métrique reçue."""
    if not received_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune métrique disponible.",
        )

    return received_metrics[-1]
