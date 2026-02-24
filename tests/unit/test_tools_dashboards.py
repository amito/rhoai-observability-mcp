# tests/unit/test_tools_dashboards.py
import pytest
from unittest.mock import AsyncMock
from rhoai_obs_mcp.tools.dashboards import register_dashboard_tools


class TestDashboardTools:
    def setup_method(self):
        self.grafana = AsyncMock()
        self.tools = register_dashboard_tools(self.grafana)

    @pytest.mark.asyncio
    async def test_list_dashboards(self):
        """Should return formatted dashboard list."""
        self.grafana.search_dashboards.return_value = [
            {"uid": "abc", "title": "vLLM Metrics", "tags": ["vllm"]},
            {"uid": "def", "title": "GPU Metrics", "tags": ["gpu"]},
        ]

        result = await self.tools["list_dashboards"]()
        assert "vLLM Metrics" in result
        assert "abc" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_panels(self):
        """Should return formatted panel list."""
        self.grafana.get_dashboard.return_value = {
            "dashboard": {
                "title": "vLLM Metrics",
                "panels": [
                    {
                        "id": 1,
                        "title": "TTFT",
                        "type": "graph",
                        "targets": [{"expr": "vllm:time_to_first_token_seconds"}],
                    },
                    {
                        "id": 2,
                        "title": "Queue Depth",
                        "type": "stat",
                        "targets": [{"expr": "vllm:num_requests_waiting"}],
                    },
                ],
            },
        }

        result = await self.tools["get_dashboard_panels"](dashboard_uid="abc")
        assert "TTFT" in result
        assert "Queue Depth" in result
