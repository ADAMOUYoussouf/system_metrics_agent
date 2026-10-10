import pytest
from fastapi.testclient import TestClient

from app import api

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def reset_store():
    api.received_metrics.clear()
    yield
    api.received_metrics.clear()


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
