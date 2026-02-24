import httpx
import pytest
import respx
from rhoai_obs_mcp.backends.grafana import GrafanaBackend


class TestGrafanaBackend:
    @respx.mock
    @pytest.mark.asyncio
    async def test_search_dashboards(self, settings, auth):
        """Should search for dashboards."""
        respx.get("https://grafana.test:3000/api/search").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"uid": "abc123", "title": "vLLM Model Metrics", "tags": ["vllm"]},
                    {"uid": "def456", "title": "GPU Metrics", "tags": ["gpu"]},
                ],
            )
        )

        backend = GrafanaBackend(settings, auth)
        result = await backend.search_dashboards()
        assert len(result) == 2
        assert result[0]["uid"] == "abc123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_with_tag(self, settings, auth):
        """Should filter dashboards by tag."""
        route = respx.get("https://grafana.test:3000/api/search").mock(
            return_value=httpx.Response(200, json=[])
        )

        backend = GrafanaBackend(settings, auth)
        await backend.search_dashboards(tag="vllm")
        assert "tag=vllm" in str(route.calls[0].request.url)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_dashboard(self, settings, auth):
        """Should fetch a dashboard by UID."""
        respx.get("https://grafana.test:3000/api/dashboards/uid/abc123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "dashboard": {
                        "title": "vLLM Metrics",
                        "panels": [
                            {
                                "id": 1,
                                "title": "TTFT",
                                "type": "graph",
                                "targets": [{"expr": "vllm:time_to_first_token_seconds"}],
                            },
                        ],
                    },
                },
            )
        )

        backend = GrafanaBackend(settings, auth)
        result = await backend.get_dashboard("abc123")
        assert result["dashboard"]["title"] == "vLLM Metrics"
        assert len(result["dashboard"]["panels"]) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error(self, settings, auth):
        """Should return empty list on connection error for search."""
        respx.get("https://grafana.test:3000/api/search").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        backend = GrafanaBackend(settings, auth)
        result = await backend.search_dashboards()
        assert result == []
