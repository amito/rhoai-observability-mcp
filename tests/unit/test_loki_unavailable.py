import pytest

from rhoai_obs_mcp.auth import AuthProvider
from rhoai_obs_mcp.backends.loki import LokiBackend, _LOKI_NOT_CONFIGURED
from rhoai_obs_mcp.config import Settings
from rhoai_obs_mcp.tools.logs import _LOKI_UNAVAILABLE_MSG, register_log_tools


@pytest.fixture
def unavailable_loki():
    """LokiBackend with no URL configured."""
    settings = Settings(_env_file=None, openshift_token="test-token")
    auth = AuthProvider(settings)
    return LokiBackend(settings, auth)


@pytest.fixture
def available_loki():
    """LokiBackend with a URL configured."""
    settings = Settings(
        _env_file=None,
        loki_url="https://loki.test:8080",
        openshift_token="test-token",
    )
    auth = AuthProvider(settings)
    return LokiBackend(settings, auth)


class TestLokiBackendAvailability:
    def test_unavailable_when_no_url(self, unavailable_loki):
        assert unavailable_loki.available is False

    def test_available_when_url_set(self, available_loki):
        assert available_loki.available is True

    @pytest.mark.asyncio
    async def test_query_range_returns_error_when_unavailable(self, unavailable_loki):
        result = await unavailable_loki.query_range('{app="test"}')
        assert result["status"] == "error"
        assert result["error"] == _LOKI_NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_get_labels_returns_empty_when_unavailable(self, unavailable_loki):
        result = await unavailable_loki.get_labels()
        assert result == []


class TestLogToolsUnavailable:
    @pytest.mark.asyncio
    async def test_query_logs_returns_unavailable_message(self, unavailable_loki):
        tools = register_log_tools(unavailable_loki)
        result = await tools["query_logs"](logql='{app="test"}')
        assert result == _LOKI_UNAVAILABLE_MSG
        assert "get_events" in result
        assert "get_pods" in result

    @pytest.mark.asyncio
    async def test_get_pod_logs_returns_unavailable_message(self, unavailable_loki):
        tools = register_log_tools(unavailable_loki)
        result = await tools["get_pod_logs"](namespace="test", pod_name="pod-1")
        assert result == _LOKI_UNAVAILABLE_MSG
