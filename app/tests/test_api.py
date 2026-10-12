import pytest
from fastapi.testclient import TestClient

from app import api

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def reset_store():
    api.received_metrics.clear()
    api.latest_by_host.clear()
    yield
    api.received_metrics.clear()
    api.latest_by_host.clear()


def valid_payload():
    return {
        "agent": "system-metrics-agent",
        "event_type": "system_metrics",
        "data": {"hostname": "test-host", "cpu": {"percent": 12.5}},
    }


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_without_metrics_returns_404():
    response = client.get("/metrics/latest")

    assert response.status_code == 404


def test_post_then_latest():
    post = client.post("/metrics", json=valid_payload())

    assert post.status_code == 201
    assert post.json()["total_received"] == 1

    latest = client.get("/metrics/latest")

    assert latest.status_code == 200
    assert latest.json()["data"]["hostname"] == "test-host"


def test_get_all_metrics():
    client.post("/metrics", json=valid_payload())
    client.post("/metrics", json=valid_payload())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_post_invalid_payload_returns_422():
    response = client.post("/metrics", json={"agent": ""})

    assert response.status_code == 422


def full_payload():
    return {
        "agent": "system-metrics-agent",
        "event_type": "system_metrics",
        "data": {
            "hostname": "srv1",
            "cpu": {"percent": 42.5, "logical_cores": 4},
            "memory": {"percent": 30.0, "used_bytes": 1000, "total_bytes": 4000},
            "system": {"load_1m": 0.5, "load_5m": 0.4, "load_15m": 0.3},
        },
    }


def test_prometheus_without_metrics_has_no_host_samples():
    response = client.get("/prometheus")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "host_cpu_percent{" not in response.text


def test_prometheus_exposes_latest_values():
    client.post("/metrics", json=full_payload())

    text = client.get("/prometheus").text

    assert 'host_cpu_percent{hostname="srv1"} 42.5' in text
    assert 'host_memory_percent{hostname="srv1"} 30.0' in text
    assert 'host_load_1m{hostname="srv1"} 0.5' in text
    assert "metrics_received_total" in text


def test_prometheus_ignores_missing_or_invalid_values():
    payload = valid_payload()
    payload["data"]["memory"] = {"percent": "n/a"}
    client.post("/metrics", json=payload)

    text = client.get("/prometheus").text

    assert 'host_cpu_percent{hostname="test-host"} 12.5' in text
    assert "host_memory_percent{" not in text
