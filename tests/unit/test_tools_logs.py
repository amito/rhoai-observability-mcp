# tests/unit/test_tools_logs.py
import pytest
from unittest.mock import AsyncMock
from rhoai_mcp.tools.logs import register_log_tools


SAMPLE_LOG_RESPONSE = {
    "status": "success",
    "data": {
        "resultType": "streams",
        "result": [
            {
                "stream": {"kubernetes_pod_name": "vllm-0"},
                "values": [
                    ["1708000000000000000", "ERROR: GPU memory allocation failed"],
                    ["1708000001000000000", "INFO: Retrying..."],
                ],
            }
        ],
    },
}


class TestLogTools:
    def setup_method(self):
        self.loki = AsyncMock()
        self.tools = register_log_tools(self.loki)

    @pytest.mark.asyncio
    async def test_query_logs(self):
        """Should forward LogQL query to backend."""
        self.loki.query_range.return_value = SAMPLE_LOG_RESPONSE
        result = await self.tools["query_logs"](logql='{namespace="vllm"}')
        assert "GPU memory" in result

    @pytest.mark.asyncio
    async def test_get_pod_logs(self):
        """Should build LogQL from pod name and namespace."""
        self.loki.query_range.return_value = SAMPLE_LOG_RESPONSE
        await self.tools["get_pod_logs"](namespace="vllm", pod_name="vllm-0")
        call_args = self.loki.query_range.call_args
        logql = call_args[0][0] if call_args[0] else call_args[1]["logql"]
        assert "vllm-0" in logql

    @pytest.mark.asyncio
    async def test_get_pod_logs_with_filter(self):
        """Should add text filter to LogQL."""
        self.loki.query_range.return_value = SAMPLE_LOG_RESPONSE
        await self.tools["get_pod_logs"](namespace="vllm", pod_name="vllm-0", filter="error")
        call_args = self.loki.query_range.call_args
        logql = call_args[0][0] if call_args[0] else call_args[1]["logql"]
        assert "error" in logql.lower()
