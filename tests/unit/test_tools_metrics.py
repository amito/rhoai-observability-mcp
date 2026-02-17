# tests/unit/test_tools_metrics.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from rhoai_mcp.tools.metrics import register_metrics_tools


class TestMetricsTools:
    def setup_method(self):
        self.prometheus = AsyncMock()
        self.tools = register_metrics_tools(self.prometheus)

    @pytest.mark.asyncio
    async def test_query_prometheus(self):
        """Should forward PromQL query to backend."""
        self.prometheus.query.return_value = {
            "status": "success",
            "data": {"result": [{"metric": {"__name__": "up"}, "value": [1, "1"]}]},
        }

        result = await self.tools["query_prometheus"](query="up")
        assert "success" in result
        self.prometheus.query.assert_called_once_with("up", time=None)

    @pytest.mark.asyncio
    async def test_get_vllm_metrics(self):
        """Should fetch and format vLLM metrics."""
        self.prometheus.query.return_value = {
            "status": "success",
            "data": {"result": [{"metric": {}, "value": [1, "0.42"]}]},
        }

        result = await self.tools["get_vllm_metrics"](model_name="llama")
        assert "llama" in result or "0.42" in result

    @pytest.mark.asyncio
    async def test_list_metrics(self):
        """Should list and optionally filter metrics."""
        self.prometheus.list_metrics.return_value = [
            "vllm:num_requests_running",
            "vllm:gpu_cache_usage_perc",
            "node_cpu_seconds_total",
        ]

        result = await self.tools["list_metrics"](filter="vllm")
        assert "vllm:num_requests_running" in result
        assert "node_cpu_seconds_total" not in result
