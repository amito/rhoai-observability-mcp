import httpx
import pytest
import respx
from rhoai_mcp.backends.loki import LokiBackend


SAMPLE_LOG_RESPONSE = {
    "status": "success",
    "data": {
        "resultType": "streams",
        "result": [
            {
                "stream": {"kubernetes_namespace_name": "vllm", "kubernetes_pod_name": "vllm-0"},
                "values": [
                    ["1708000000000000000", "INFO: Model loaded successfully"],
                    ["1708000001000000000", "ERROR: GPU memory allocation failed"],
                ],
            }
        ],
    },
}


class TestLokiBackend:
    @respx.mock
    @pytest.mark.asyncio
    async def test_query_range(self, settings, auth):
        """Should execute a LogQL range query."""
        respx.get("https://loki.test:8080/api/logs/v1/application/loki/api/v1/query_range").mock(
            return_value=httpx.Response(200, json=SAMPLE_LOG_RESPONSE)
        )

        backend = LokiBackend(settings, auth)
        result = await backend.query_range(
            '{kubernetes_namespace_name="vllm"}',
            tenant="application",
        )
        assert result["status"] == "success"
        assert len(result["data"]["result"]) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_query_with_time_range(self, settings, auth):
        """Should pass start/end/limit parameters."""
        route = respx.get(
            "https://loki.test:8080/api/logs/v1/application/loki/api/v1/query_range"
        ).mock(return_value=httpx.Response(200, json=SAMPLE_LOG_RESPONSE))

        backend = LokiBackend(settings, auth)
        await backend.query_range(
            '{kubernetes_namespace_name="vllm"} |= "error"',
            tenant="application",
            limit=50,
        )
        url = str(route.calls[0].request.url)
        assert "limit=50" in url

    @respx.mock
    @pytest.mark.asyncio
    async def test_infrastructure_tenant(self, settings, auth):
        """Should use the correct tenant path for infrastructure logs."""
        route = respx.get(
            "https://loki.test:8080/api/logs/v1/infrastructure/loki/api/v1/query_range"
        ).mock(return_value=httpx.Response(200, json=SAMPLE_LOG_RESPONSE))

        backend = LokiBackend(settings, auth)
        await backend.query_range('{job="kubelet"}', tenant="infrastructure")
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_labels(self, settings, auth):
        """Should list available labels."""
        respx.get("https://loki.test:8080/api/logs/v1/application/loki/api/v1/labels").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": ["kubernetes_namespace_name", "kubernetes_pod_name", "level"],
                },
            )
        )

        backend = LokiBackend(settings, auth)
        result = await backend.get_labels(tenant="application")
        assert "kubernetes_namespace_name" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error(self, settings, auth):
        """Should return error dict on connection failure."""
        respx.get("https://loki.test:8080/api/logs/v1/application/loki/api/v1/query_range").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        backend = LokiBackend(settings, auth)
        result = await backend.query_range('{job="test"}', tenant="application")
        assert result["status"] == "error"
