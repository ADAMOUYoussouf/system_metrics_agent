import pytest

from app.config import Settings


def test_defaults(monkeypatch):
    for name in ("METRICS_ENDPOINT", "COLLECTION_INTERVAL", "REQUEST_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://127.0.0.1:8000/metrics"
    assert settings.collection_interval == 5
    assert settings.request_timeout == 5


def test_values_from_environment(monkeypatch):
    monkeypatch.setenv("METRICS_ENDPOINT", "http://api:8000/metrics")
    monkeypatch.setenv("COLLECTION_INTERVAL", "10")
    monkeypatch.setenv("REQUEST_TIMEOUT", "2.5")

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://api:8000/metrics"
    assert settings.collection_interval == 10
    assert settings.request_timeout == 2.5


def test_non_numeric_value_is_rejected(monkeypatch):
    monkeypatch.setenv("COLLECTION_INTERVAL", "abc")

    with pytest.raises(ValueError, match="numériques"):
        Settings.from_env()


def test_non_positive_value_is_rejected(monkeypatch):
    monkeypatch.setenv("COLLECTION_INTERVAL", "0")

    with pytest.raises(ValueError, match="> 0"):
        Settings.from_env()
