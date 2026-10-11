from unittest.mock import patch

import pytest

from app import agent
from app.collector import MetricsCollectionError
from app.config import Settings


def make_settings():
    return Settings(
        metrics_endpoint="http://api:8000/metrics",
        collection_interval=1,
        request_timeout=1,
    )


FAKE_METRICS = {
    "timestamp": "2026-01-01T00:00:00+00:00",
    "hostname": "h",
    "cpu": {},
    "memory": {},
    "system": {},
}


@patch("app.agent.send_metrics", return_value={"status_code": 201})
@patch("app.agent.collect_system_metrics", return_value=FAKE_METRICS)
def test_run_once(mock_collect, mock_send):
    result = agent.run_once(make_settings())

    assert result["status_code"] == 201
    kwargs = mock_send.call_args.kwargs
    assert kwargs["endpoint"] == "http://api:8000/metrics"
    assert kwargs["payload"]["event_type"] == "system_metrics"


@patch("app.agent.time.sleep", side_effect=KeyboardInterrupt)
@patch("app.agent.run_once", side_effect=MetricsCollectionError("boom"))
@patch("app.agent.Settings.from_env", return_value=make_settings())
def test_run_forever_survives_a_failed_cycle(mock_env, mock_run, mock_sleep):
    # Le cycle échoue (erreur loguée), puis sleep lève KeyboardInterrupt
    # pour sortir de la boucle infinie du test.
    with pytest.raises(KeyboardInterrupt):
        agent.run_forever()

    assert mock_run.call_count == 1
