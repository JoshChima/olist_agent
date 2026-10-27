import importlib

import azure.monitor.opentelemetry
import pytest

import olist_agent.main as main


@pytest.mark.parametrize("conn", [None, "InstrumentationKey=test"])
def test_app_insights_only_when_connection_string_set(
    conn: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        azure.monitor.opentelemetry, "configure_azure_monitor", lambda: calls.append(True)
    )
    if conn:
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", conn)
    else:
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    importlib.reload(main)
    assert calls == ([True] if conn else [])
