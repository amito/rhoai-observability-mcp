# tests/unit/test_tools_metrics.py
import pytest
from unittest.mock import AsyncMock
from rhoai_obs_mcp.tools.metrics import register_metrics_tools, _relative_to_epoch


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

    @pytest.mark.asyncio
    async def test_query_prometheus_range(self):
        """Should forward range query with resolved timestamps."""
        self.prometheus.query_range.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "DCGM_FI_DEV_GPU_UTIL", "gpu": "0"},
                        "values": [[1710000000, "45"], [1710000060, "92"], [1710000120, "88"]],
                    }
                ],
            },
        }

        result = await self.tools["query_prometheus_range"](
            query="DCGM_FI_DEV_GPU_UTIL", start="1h", end="now", step="60s"
        )
        assert "success" in result
        assert "matrix" in result
        assert "92" in result
        self.prometheus.query_range.assert_called_once()
        call_kwargs = self.prometheus.query_range.call_args
        assert call_kwargs.kwargs["promql"] == "DCGM_FI_DEV_GPU_UTIL"
        assert call_kwargs.kwargs["step"] == "60s"

    @pytest.mark.asyncio
    async def test_query_prometheus_range_relative_start(self):
        """Should convert relative time strings to epoch timestamps."""
        self.prometheus.query_range.return_value = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }

        await self.tools["query_prometheus_range"](
            query="up", start="30m", end="now", step="15s"
        )
        call_kwargs = self.prometheus.query_range.call_args.kwargs
        # start should be a numeric timestamp (string), roughly 30 min ago
        start_ts = float(call_kwargs["start"])
        import time
        assert time.time() - start_ts == pytest.approx(1800, abs=5)


class TestRelativeToEpoch:
    def test_minutes(self):
        import time
        result = float(_relative_to_epoch("30m"))
        assert time.time() - result == pytest.approx(1800, abs=5)

    def test_hours(self):
        import time
        result = float(_relative_to_epoch("2h"))
        assert time.time() - result == pytest.approx(7200, abs=5)

    def test_days(self):
        import time
        result = float(_relative_to_epoch("1d"))
        assert time.time() - result == pytest.approx(86400, abs=5)

    def test_passthrough_absolute(self):
        assert _relative_to_epoch("2024-01-01T00:00:00Z") == "2024-01-01T00:00:00Z"

    def test_passthrough_unix(self):
        assert _relative_to_epoch("1710000000") == "1710000000"
